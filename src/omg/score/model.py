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
    gain_db: float = 0.0       # 轨道增益（dB），混音时叠加
    pan: float = 0.0           # 声像 -1(左)..1(右)，0 居中，等功率
    bass_boost_db: float = 0.0 # 低频搁架 EQ 增益（低音提琴基频弱，用 +10~15dB 补偿）


@dataclass
class Score:
    title: str = "untitled"
    tempo_bpm: float = 90.0
    tracks: list[Track] = field(default_factory=list)


def transpose(score: Score, semitones: int) -> Score:
    """整体移调：所有音符 pitch 平移 semitones 半音（负数降低）。"""
    shifted = []
    for track in score.tracks:
        shifted.append(Track(
            id=track.id,
            name=track.name,
            instrument=track.instrument,
            gain_db=track.gain_db,
            pan=track.pan,
            bass_boost_db=track.bass_boost_db,
            notes=[Note(n.start_beat, n.duration, n.pitch + semitones,
                        n.velocity, n.technique) for n in track.notes],
        ))
    return Score(title=score.title, tempo_bpm=score.tempo_bpm, tracks=shifted)
