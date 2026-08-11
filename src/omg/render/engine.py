"""单音符渲染编排：查样本 → 变调 → 力度 → 包络 → mono buffer。"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import envelope, pitch
from .cache import SampleCache
from .lookup import Lookup
from .rr import RoundRobin


class RenderEngine:
    def __init__(
        self,
        conn,
        library_id: int,
        library_root: str | Path,
        project_sr: int = 44100,
        backend: str = "samplerate",
        max_cache_bytes: int = 512 * 1024 * 1024,
    ) -> None:
        self.conn = conn
        self.library_id = library_id
        self.library_root = Path(library_root)
        self.project_sr = project_sr
        self.backend = backend
        self.lookup = Lookup(conn, library_id)
        self.cache = SampleCache(max_cache_bytes)
        self.rr = RoundRobin()

    def render_note(
        self,
        instrument: str,
        pitch_midi: int,
        velocity: int,
        technique: str | None,
        note_dur_s: float,
    ) -> np.ndarray:
        sel = self.lookup.select(instrument, pitch_midi, velocity, technique)
        if sel is None or not sel.rows:
            return np.zeros(0, dtype=np.float32)

        key = (instrument, sel.articulation, sel.midi_note, velocity)
        row = sel.rows[self.rr.next(key, len(sel.rows))]
        path = self.library_root / row["file_rel"]

        data, sample_sr = self.cache.get(path)
        sig = pitch.pitch_shift(data, sample_sr, self.project_sr, sel.shift_semitones, self.backend)
        sig = sig * sel.gain

        note_len = max(0, int(note_dur_s * self.project_sr))
        if len(sig) > note_len:
            sig = envelope.release(sig[:note_len], self.project_sr)
        else:
            # 音符比样本长：放完自然衰减，尾端渐出（P3 再做 loop/sustain）
            sig = envelope.release(sig, self.project_sr)
        sig = envelope.attack(sig, self.project_sr)
        return sig.astype(np.float32)
