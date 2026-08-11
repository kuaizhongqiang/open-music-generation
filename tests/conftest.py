"""Pytest 共享 fixture：合成一个迷你 VSCO 风格采样库（不依赖真实数据）。"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest


def _write_wav(path: Path, sr: int = 44100, seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    data = (0.3 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


@pytest.fixture
def fake_library(tmp_path: Path) -> Path:
    """覆盖四种方言 + 边界情况的迷你库。"""
    root = tmp_path / "FakeLib"
    # 方言1 token：铜管风格（技法在文件名，vN/rr 小写）
    brass = root / "Brass"
    for art in ("stac", "sus"):
        _write_wav(brass / "F Horn" / art / f"MOHorn_{art}_A#1_v1_rr1.wav")
    # 方言1 变体：弦乐风格（力度 f/p，部分带大写 RR，音高半音采样）
    strings = root / "Strings"
    _write_wav(strings / "Solo Violin" / "Arco Vib" / "LLVln_ArcoVib_A3_f.wav")
    _write_wav(strings / "Solo Violin" / "Arco Vib" / "LLVln_ArcoVib_A3_p.wav")
    _write_wav(strings / "Solo Violin" / "Pizz" / "LLVln_Pizz_C4_f_RR1.wav")
    _write_wav(strings / "Solo Violin" / "Pizz" / "LLVln_Pizz_C4_f_RR2.wav")
    _write_wav(strings / "Solo Violin" / "spic" / "LLVln_spic_A2_v1_rr1.wav")
    # 方言2 mapping_chart：钢琴
    piano = root / "Keys" / "Upright Piano"
    piano.mkdir(parents=True, exist_ok=True)
    (piano / "MappingChart.txt").write_text(
        "Notation=KeyNumber\n000=21\n001=23\n002=25\n", encoding="utf-8"
    )
    _write_wav(piano / "Player_dyn1_rr1_000.wav")
    _write_wav(piano / "Player_dyn1_rr1_002.wav")
    _write_wav(piano / "Player_dyn2_rr1_000.wav")
    # 方言3 fixed_pitch：定音鼓
    _write_wav(root / "Percussion" / "Timpani" / "Timpani1_Hit_v1_rr1_Sum.wav")
    _write_wav(root / "Percussion" / "Timpani" / "Timpani1_Hit_v1_rr2_Sum.wav")
    # 方言4 no_pitch：鼓组
    _write_wav(root / "Percussion" / "drums" / "bass" / "bdrum2_ppp_1.wav")
    return root
