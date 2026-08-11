"""单音符渲染：查样本（含力度层交叉淡化）→ 变调 → 技法包络 → mono buffer。

技法语义（P3）：
  - staccato/spiccato：时长压缩到名义值的 ~60%，快起快收，节奏利落
  - pizzicato：自然衰减，短尾
  - sustain/legato/arco：名义时长 + 尾音重叠（连奏感，音符不硬切）
  - 其余：名义时长截断 + 渐变
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import envelope, pitch
from .cache import SampleCache
from .lookup import Lookup, SampleSelection
from .rr import RoundRobin

_STACCATO = {"staccato", "spiccato", "short", "staccato"}
_PIZZ = {"pizzicato"}
_SUSTAIN = {"arco", "arco_vib", "sustain", "sustain_vib", "sustain_long",
            "sustain_no_vib", "legato", "vibrato", "expressive_vib"}
_TAIL_S = 0.09        # sustain 音符尾部重叠时长
_RELEASE_S = 0.08     # sustain 释放时长
_RELEASE_S_SHORT = 0.03


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

    def _technique_family(self, technique: str | None) -> str:
        if technique in _STACCATO:
            return "staccato"
        if technique in _PIZZ:
            return "pizz"
        if technique in _SUSTAIN:
            return "sustain"
        return "default"

    def _shape(self, sig: np.ndarray, technique: str | None, note_dur_s: float) -> np.ndarray:
        """技法相关的时长与包络塑造。"""
        sr = self.project_sr
        note_len = max(0, int(note_dur_s * sr))
        fam = self._technique_family(technique)

        if fam == "staccato":
            target = int(note_len * 0.6)
            if len(sig) > target:
                sig = envelope.release(sig[:target], sr, _RELEASE_S_SHORT)
            sig = envelope.attack(sig, sr, 0.005)
        elif fam == "pizz":
            target = note_len + int(0.04 * sr)
            if len(sig) > target:
                sig = envelope.release(sig[:target], sr, 0.05)
            sig = envelope.attack(sig, sr, 0.003)
        elif fam == "sustain":
            target = note_len + int(_TAIL_S * sr)   # 尾部重叠，衔接自然
            if len(sig) > target:
                sig = envelope.release(sig[:target], sr, _RELEASE_S)
            else:
                sig = envelope.release(sig, sr, _RELEASE_S)
            sig = envelope.attack(sig, sr, 0.012)
        else:
            if len(sig) > note_len:
                sig = envelope.release(sig[:note_len], sr, 0.05)
            else:
                sig = envelope.release(sig, sr, 0.05)
            sig = envelope.attack(sig, sr, envelope.ATTACK_S)
        return sig

    def _render_selection(self, sel: SampleSelection, vel_layer: tuple[int, int] | None,
                          note_dur_s: float, shape_technique: str | None) -> np.ndarray:
        if not sel.rows:
            return np.zeros(0, dtype=np.float32)
        key = (sel.instrument, sel.articulation, sel.midi_note, vel_layer)
        row = sel.rows[self.rr.next(key, len(sel.rows))]
        path = self.library_root / row["file_rel"]
        data, sample_sr = self.cache.get(path)
        sig = pitch.pitch_shift(data, sample_sr, self.project_sr, sel.shift_semitones, self.backend)
        sig = sig * sel.gain
        # 用"请求的技法"做时长/包络塑造（即使回退到了别的样本，语义仍按请求来）
        return self._shape(sig, shape_technique, note_dur_s)

    def render_note(
        self,
        instrument: str,
        pitch_midi: int,
        velocity: int,
        technique: str | None,
        note_dur_s: float,
    ) -> np.ndarray:
        layers = self.lookup.select_layers(instrument, pitch_midi, velocity, technique)
        if not layers:
            return np.zeros(0, dtype=np.float32)

        parts = []
        for sel, weight in layers:
            vel_range = (sel.rows[0]["vel_min"], sel.rows[0]["vel_max"]) if sel.rows else None
            sig = self._render_selection(sel, vel_range, note_dur_s, technique)
            if len(sig) > 0:
                parts.append((sig, weight))
        if not parts:
            return np.zeros(0, dtype=np.float32)
        n = max(len(s) for s, _ in parts)
        out = np.zeros(n, dtype=np.float32)
        for sig, weight in parts:
            out[: len(sig)] += sig * weight
        return out.astype(np.float32)
