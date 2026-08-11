"""P3 技法精细化测试：staccato 缩短、力度交叉淡化、混响尾音。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from omg.library.importer import import_library
from omg.library.index import get_library_id, open_db
from omg.render.engine import RenderEngine
from omg.render.mixer import mix_tracks
from omg.score.model import Note, Score, Track

C4 = 261.63


def _write_sine(path: Path, freq: float, sr: int = 44100, seconds: float = 1.5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr * seconds)) / sr
    sf.write(str(path), (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32), sr)


@pytest.fixture
def two_layer_lib(tmp_path: Path):
    """Solo Violin C4 有两层力度（f/p）的迷你库。"""
    root = tmp_path / "TLib"
    base = root / "Strings" / "Solo Violin" / "Arco Vib"
    _write_sine(base / "LLVln_ArcoVib_C4_f.wav", C4)
    _write_sine(base / "LLVln_ArcoVib_C4_p.wav", C4)
    db = tmp_path / "i.sqlite3"
    import_library(root, db, "t")
    conn = open_db(db)
    lid = get_library_id(conn, "t")
    return RenderEngine(conn, lid, root)


def test_staccato_shorter_than_sustain(two_layer_lib):
    e = two_layer_lib
    note_s = 0.5
    st = e.render_note("solo_violin", 60, 100, "staccato", note_s)
    sus = e.render_note("solo_violin", 60, 100, "arco_vib", note_s)
    assert len(st) < len(sus) * 0.8
    assert abs(len(st) - int(note_s * 0.6 * e.project_sr)) < e.project_sr // 10


def test_select_layers_crossfade(two_layer_lib):
    lk = two_layer_lib.lookup
    # f 层 vel 高、p 层 vel 低（导入按两档均分）
    layers_soft = lk.select_layers("solo_violin", 60, 10, "arco_vib")
    assert len(layers_soft) == 1
    layers_loud = lk.select_layers("solo_violin", 60, 120, "arco_vib")
    assert len(layers_loud) == 1
    # 边界速度 → 两层交叉淡化，权重和为 1
    mid = lk.select_layers("solo_violin", 60, 64, "arco_vib")
    assert len(mid) == 2
    assert abs(sum(w for _, w in mid) - 1.0) < 1e-6


def test_crossfade_renders_blend(two_layer_lib):
    e = two_layer_lib
    # 边界速度渲染不崩且非静音
    buf = e.render_note("solo_violin", 60, 64, "arco_vib", 0.5)
    assert len(buf) > 0 and float(np.max(np.abs(buf))) > 0.01


def test_reverb_adds_tail(two_layer_lib):
    e = two_layer_lib
    score = Score(tracks=[Track(id="a", name="a", instrument="solo_violin",
                                notes=[Note(0, 0.5, 60, 100, "arco_vib")])])
    dry = mix_tracks(e, score, reverb=0.0)
    wet = mix_tracks(e, score, reverb=0.4)
    assert len(wet) > len(dry)                    # 混响尾音让输出更长
    tail = wet[len(dry):] if len(wet) > len(dry) else wet[:0]
    assert float(np.sqrt(np.mean(tail ** 2))) > 1e-4   # 尾音区有能量
