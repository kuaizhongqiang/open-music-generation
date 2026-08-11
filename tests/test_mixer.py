"""P2 混音器与导出测试。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from omg.io.export import export_mp3, write_wav
from omg.library.importer import import_library
from omg.library.index import get_library_id, open_db
from omg.render.engine import RenderEngine
from omg.render.mixer import mix_tracks, pan_gain
from omg.score.model import Note, Score, Track

C4, G4 = 261.63, 392.00


def _write_sine(path: Path, freq: float, sr: int = 44100, seconds: float = 1.5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr * seconds)) / sr
    sf.write(str(path), (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32), sr)


@pytest.fixture
def two_note_lib(tmp_path: Path):
    root = tmp_path / "TwoLib"
    _write_sine(root / "Strings" / "Solo Violin" / "Arco Vib" / "LLVln_ArcoVib_C4_f.wav", C4)
    _write_sine(root / "Strings" / "Solo Violin" / "Arco Vib" / "LLVln_ArcoVib_G4_f.wav", G4)
    db = tmp_path / "i.sqlite3"
    import_library(root, db, "two")
    conn = open_db(db)
    lid = get_library_id(conn, "two")
    return RenderEngine(conn, lid, root)


def _peaks(buf: np.ndarray, sr: int, top: int = 3) -> list[float]:
    mono = buf.mean(axis=1)
    n = min(int(0.3 * sr), len(mono))
    seg = mono[len(mono) // 2 - n // 2: len(mono) // 2 + n // 2] * np.hanning(n)
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(n, 1 / sr)
    idx = np.argsort(spec)[-top:][::-1]
    return sorted(float(freqs[i]) for i in idx)


def _score(tracks: list[Track]) -> Score:
    return Score(title="t", tempo_bpm=90.0, tracks=tracks)


def test_mix_contains_both_notes(two_note_lib):
    score = _score([
        Track(id="a", name="a", instrument="solo_violin", notes=[Note(0, 1.0, 60, 100, "arco_vib")]),
        Track(id="b", name="b", instrument="solo_violin", notes=[Note(0, 1.0, 67, 100, "arco_vib")]),
    ])
    mix = mix_tracks(two_note_lib, score)
    peaks = _peaks(mix, two_note_lib.project_sr, top=4)
    ok = lambda f: any(abs(p - f) / f < 0.03 for p in peaks)  # noqa: E731
    assert ok(C4), f"缺 C4 峰, peaks={peaks}"
    assert ok(G4), f"缺 G4 峰, peaks={peaks}"


def test_gain_db_reduces_rms(two_note_lib):
    def rms(gain_db: float) -> float:
        score = _score([Track(id="a", name="a", instrument="solo_violin",
                              gain_db=gain_db, notes=[Note(0, 1.0, 60, 100, "arco_vib")])])
        return float(np.sqrt(np.mean(mix_tracks(two_note_lib, score) ** 2)))

    assert rms(-12.0) < rms(0.0) * 0.4


def test_pan_equal_power(two_note_lib):
    def lr(pan: float):
        score = _score([Track(id="a", name="a", instrument="solo_violin",
                              pan=pan, notes=[Note(0, 1.0, 60, 100, "arco_vib")])])
        m = mix_tracks(two_note_lib, score)
        return float(np.sqrt(np.mean(m[:, 0] ** 2))), float(np.sqrt(np.mean(m[:, 1] ** 2)))

    ll, lr_ = lr(-1.0)
    assert ll > lr_ * 5
    cl, cr = lr(0.0)
    assert abs(cl - cr) / max(cl, cr) < 0.05
    rl, rr = lr(1.0)
    assert rr > rl * 5
    # 等功率：声道功率之和（平方和）大致不变
    power = lambda a, b: a * a + b * b  # noqa: E731
    assert abs(power(cl, cr) - power(ll, lr_)) / power(cl, cr) < 0.15
    assert abs(power(cl, cr) - power(rl, rr)) / power(cl, cr) < 0.15


def test_pan_gain_unit():
    l, r = pan_gain(0.0)
    assert abs(l - 0.7071) < 0.001 and abs(r - 0.7071) < 0.001
    l, r = pan_gain(-1.0)
    assert l == 1.0 and r == 0.0


@pytest.mark.skipif(__import__("shutil").which("ffmpeg") is None, reason="需要 ffmpeg")
def test_export_mp3(two_note_lib, tmp_path):
    score = _score([Track(id="a", name="a", instrument="solo_violin",
                          notes=[Note(0, 1.0, 60, 100, "arco_vib")])])
    mix = mix_tracks(two_note_lib, score)
    wav = write_wav(tmp_path / "mix.wav", mix, two_note_lib.project_sr)
    mp3 = export_mp3(wav, tmp_path / "mix.mp3")
    assert mp3.exists() and mp3.stat().st_size > 1000
