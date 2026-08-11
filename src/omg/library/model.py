"""采样库数据模型：统一规范化后的元数据与命名常量。

方言差异在 dialects/ 层被吸收，下游（索引、渲染）只面对统一的 SampleMeta。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------- 音高解析 ----------

_NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d+)$")
_LETTER_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_to_midi(note: str) -> int | None:
    """科学音高标记 → MIDI 键号。例：C4→60, A0→21, A#1→34, A#0→22。非法返回 None。"""
    m = _NOTE_RE.match(note.strip())
    if not m:
        return None
    letter, acc, octave = m.group(1).upper(), m.group(2), int(m.group(3))
    semis = _LETTER_BASE[letter] + (1 if acc == "#" else -1 if acc == "b" else 0)
    return (octave + 1) * 12 + semis


def midi_to_note(midi: int) -> str:
    """MIDI 键号 → 科学音高标记（仅用于报表/调试）。"""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[midi % 12]}{midi // 12 - 1}"


# ---------- 规范化技法 id ----------

# 原始技法串 → 规范化 id。未收录的串统一小写化并保留原样（见 normalize_articulation）。
ARTICULATION_MAP = {
    # 弓弦
    "arco": "arco", "arco vib": "arco_vib", "arcovib": "arco_vib",
    "sustain": "sustain", "sus": "sustain", "susnv": "sustain_no_vib",
    "susvib": "sustain_vib", "sustain_vib": "sustain_vib",
    "stac": "staccato", "stacc": "staccato", "staccato": "staccato", "short": "staccato",
    "pizz": "pizzicato", "pizzt": "pizzicato", "pizzicato": "pizzicato",
    "spic": "spiccato", "spiccato": "spiccato",
    "trem": "tremolo", "tremolo": "tremolo",
    "legato": "legato",
    # 管乐
    "vib": "vibrato", "vibrato": "vibrato", "expvib": "expressive_vib",
    "suslong": "sustain_long",
    "mute": "mute", "harmonm-sus": "mute_harmon", "straightm-sus": "mute_straight",
    "buzz": "buzz", "fall": "fall", "roll": "roll",
    # 打击
    "hit": "hit", "hitstick": "hit",
    # 竖琴/马林巴强度标记当作技法丢弃
}
# 力度记号（含竖琴 mf、马林巴 loud/soft）→ 力度层语义，见 pitch_config.json
DYNAMICS = ("ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "loud", "soft")

# 应丢弃的非语义 token（话筒位置、混音标记等）
NOISE_TOKENS = {
    "sum", "main", "mid", "far", "near", "outrigger", "medium", "loud", "soft",
}


def normalize_articulation(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower().replace("_", " ").replace("-", " ")
    compact = key.replace(" ", "")
    if compact in ARTICULATION_MAP:
        return ARTICULATION_MAP[compact]
    if key in ARTICULATION_MAP:
        return ARTICULATION_MAP[key]
    # 形如 "staccato1"/"sustain1"：去掉尾部数字再查一次
    import re as _re

    m = _re.match(r"^([a-z_]+)\d+$", compact)
    if m and m.group(1) in ARTICULATION_MAP:
        return ARTICULATION_MAP[m.group(1)]
    return None


def slugify(text: str) -> str:
    """目录名 → 规范化乐器 id。例："F Horn"→f_horn, "VSCO 1 Percussion"→vsco_1_percussion。"""
    out = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return out


# ---------- 元数据 ----------


@dataclass
class SampleMeta:
    """一个样本文件的规范化元数据（入库前的中间形态）。"""
    instrument: str
    instrument_label: str
    category: str
    file_rel: str
    midi_note: int | None = None
    articulation: str | None = None
    articulation_raw: str | None = None
    vel_layer: int | None = None
    vel_min: int = 0
    vel_max: int = 127
    rr: int | None = None
    rr_count: int = 1
    vel_dynamic: str | None = None   # 力度记号（如 f/p/mf），用于后处理力度区间
    importer: str = ""


@dataclass
class ImportReport:
    """一次导入的审计结果。"""
    total_files: int = 0
    parsed: int = 0
    no_pitch: int = 0
    failed: int = 0
    per_instrument: dict[str, dict[str, int]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def parse_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.parsed + self.no_pitch) / self.total_files
