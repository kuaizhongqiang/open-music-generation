"""P1 渲染引擎测试：FFT 音高断言、时长、力度单调、轮次逻辑。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from omg.library.importer import import_library
from omg.library.index import get_library_id, open_db
from omg.render.engine import RenderEngine
from omg.render.rr import RoundRobin
from omg.render.track import render_track
from omg.score.model import Note, Score, Track

C4_FREQ = 261.63
D4_FREQ = 293.66


def _write_sine(path: Path, freq: float, sr: int = 44100, seconds: float = 2.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr * seconds)) / sr
    data = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sf.write(str(path), data, sr)


@pytest.fixture
def sine_lib(tmp_path: Path) -> tuple[RenderEngine, Path]:
    """一个纯音 C4 样本的迷你库。"""
    root = tmp_path / "SineLib"
    _write_sine(root / "Strings" / "Solo Violin" / "Arco Vib" / "LLVln_ArcoVib_C4_f.wav", C4_FREQ)
    db = tmp_path / "index.sqlite3"
    import_library(root, db, "sine")
    conn = open_db(db)
    lid = get_library_id(conn, "sine")
    engine = RenderEngine(conn, lid, root)
    return engine, root


def _peak_freq(buf: np.ndarray, sr: int) -> float:
    """取信号中部 0.2s 的 FFT 主频（Hz）。"""
    n = int(0.2 * sr)
    start = len(buf) // 2 - n // 2
    seg = buf[start:start + n] * np.hanning(n)
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(n, 1 / sr)
    peak = freqs[np.argmax(spec)]
    return float(peak)


def _assert_freq(buf: np.ndarray, sr: int, expected: float) -> None:
    got = _peak_freq(buf, sr)
    # 0.5 半音容差
    assert abs(12 * np.log2(got / expected)) < 0.5, f"期望 {expected:.1f}Hz, 实际 {got:.1f}Hz"


def test_pitch_exact_and_shift(sine_lib):
    engine, _ = sine_lib
    # 精确命中 C4 样本
    exact = engine.render_note("solo_violin", 60, 100, "arco_vib", 0.8)
    assert len(exact) > 0
    _assert_freq(exact, engine.project_sr, C4_FREQ)
    # D4 需 +2 半音变调
    shifted = engine.render_note("solo_violin", 62, 100, "arco_vib", 0.8)
    _assert_freq(shifted, engine.project_sr, D4_FREQ)


def test_note_duration(sine_lib):
    engine, _ = sine_lib
    note_s = 0.5
    # 无技法 → default 族：精确截断到名义时长
    buf = engine.render_note("solo_violin", 60, 100, None, note_s)
    expected = int(note_s * engine.project_sr)
    assert abs(len(buf) - expected) <= engine.project_sr // 20, f"长度 {len(buf)} vs {expected}"


def test_velocity_monotonic(sine_lib):
    engine, _ = sine_lib
    soft = engine.render_note("solo_violin", 60, 40, "arco_vib", 0.6)
    loud = engine.render_note("solo_violin", 60, 120, "arco_vib", 0.6)
    assert float(np.sqrt(np.mean(loud ** 2))) > float(np.sqrt(np.mean(soft ** 2)))


def test_no_click_on_attack(sine_lib):
    engine, _ = sine_lib
    buf = engine.render_note("solo_violin", 60, 100, "arco_vib", 0.5)
    # 首样本不出现大幅跳变（attack 生效）
    assert abs(float(buf[0])) < 0.05
    assert abs(float(buf[1] - buf[0])) < 0.01


def test_render_track_stereo(sine_lib):
    engine, _ = sine_lib
    score = Score(title="t", tempo_bpm=90.0, tracks=[
        Track(id="v", name="v", instrument="solo_violin",
              notes=[Note(0, 1.0, 60, 100, "arco_vib")]),
    ])
    out = render_track(engine, score, score.tracks[0])
    assert out.ndim == 2 and out.shape[1] == 2
    assert len(out) > 0


def test_round_robin_logic():
    rr = RoundRobin()
    seen = [rr.next(("v", "arco", 60, 100), 2) for _ in range(4)]
    assert seen == [0, 1, 0, 1]
    assert rr.next(("v", "arco", 60, 100), 1) == 0
