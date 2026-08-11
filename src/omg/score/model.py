"""乐谱模型 v1：AI 编曲的产物与编辑的核心工件。

时间基用"拍"（float）+ 全局 tempo，渲染时换算秒——未来时值/速度/小节编辑不动 schema。
扩展口（向后兼容，均为可空/新增 key）：
  Note   P3 加 tie_to / legato_group / detune
  Track  P2 加 gain_db / pan / channel
  Score  P2/P4 加 libraries / renderer_options / time_signature
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Note:
    start_beat: float
    duration: float
    pitch: int                 # MIDI 0-127
    velocity: int = 100        # 0-127
    technique: str | None = None   # 技法 id，None 时渲染侧用乐器默认技法


@dataclass
class Track:
    id: str
    name: str
    instrument: str            # 索引中的规范化乐器 id
    notes: list[Note] = field(default_factory=list)


@dataclass
class Score:
    title: str = "untitled"
    tempo_bpm: float = 90.0
    tracks: list[Track] = field(default_factory=list)
