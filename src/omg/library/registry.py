"""乐器注册表：把库内的乐器目录映射到 (category, adapter, 配置)。

VSCO-2-CE 是约 25 个迷你库的拼盘，命名方言众多。绝大多数走 token 解析器，
个别走专用适配器。key 为乐器目录名，value 为该乐器的解析配置。
"""
from __future__ import annotations

from .dialects.fixed_pitch import FixedPitchAdapter
from .dialects.mapping_chart import MappingChartAdapter
from .dialects.no_pitch import NoPitchAdapter
from .dialects.token import TokenStyleAdapter

_ADAPTERS = {
    "token": TokenStyleAdapter,
    "mapping_chart": MappingChartAdapter,
    "fixed_pitch": FixedPitchAdapter,
    "no_pitch": NoPitchAdapter,
}

# 顶层目录 → 分类
CATEGORY_MAP = {
    "Brass": "brass",
    "Strings": "strings",
    "Woodwinds": "woodwinds",
    "Keys": "keys",
    "Percussion": "percussion",
    "VSCO 1 Percussion": "percussion",
    "Miscellania Raw": "misc",
}

# 乐器目录名 → 配置。未列出的乐器走 token + 自动探测（见 resolve）。
INSTRUMENT_CONFIG: dict[str, dict] = {
    # ---- 铜管 ----
    "F Horn": {"adapter": "token"},
    "OldTrombone": {"adapter": "token"},
    "Tenor Trombone": {"adapter": "token"},
    "Trumpet": {"adapter": "token"},
    "Tuba": {"adapter": "token"},
    # ---- 木管 ----
    "Bassoon": {"adapter": "token", "art_source": "subdir"},
    "Clarinet": {"adapter": "token"},
    "Flute": {"adapter": "token"},
    "Oboe": {"adapter": "token"},
    "Piccolo": {"adapter": "token", "default_art": "sustain"},
    # ---- 弦乐 ----
    "Solo Violin": {"adapter": "token", "default_art": "arco"},
    "Violin Section": {"adapter": "token", "default_art": "sustain"},
    "Viola Section": {"adapter": "token", "default_art": "sustain"},
    "Cello Section": {"adapter": "token", "default_art": "sustain"},
    "Solo Contrabass": {"adapter": "token", "default_art": "sustain"},
    "Harp": {"adapter": "token", "noise": ["KSHarp"], "default_art": "sustain"},
    # ---- 键盘 ----
    "Upright Piano": {"adapter": "mapping_chart", "default_art": "sustain"},
    "Upright Nr1": {"adapter": "token", "noise": ["UR1"], "default_art": "sustain"},
    "Organ": {"adapter": "no_pitch"},
    # ---- 打击（有音高） ----
    "Timpani": {"adapter": "fixed_pitch", "default_art": "hit"},
    "Marimba": {"adapter": "token", "noise": ["Outrigger"], "default_art": "sustain"},
    "Xylo": {"adapter": "token", "default_art": "sustain"},
    "Glock": {"adapter": "token", "default_art": "sustain"},
    "temp": {"adapter": "no_pitch"},
    # ---- 无音高 ----
    "drums": {"adapter": "no_pitch"},
    "varMetal": {"adapter": "no_pitch"},
    "varWood": {"adapter": "no_pitch"},
    "Misc 1": {"adapter": "no_pitch"},
    "Misc 2": {"adapter": "no_pitch"},
}


def get_adapter(adapter_name: str) -> object:
    cls = _ADAPTERS[adapter_name]
    return cls()


def resolve_config(category: str, instrument_label: str) -> dict:
    """取乐器配置；未注册乐器给一个默认 token 配置（探测用）。"""
    cfg = dict(INSTRUMENT_CONFIG.get(instrument_label, {}))
    cfg.setdefault("adapter", "token")
    cfg.setdefault("art_source", "auto")
    cfg["category"] = cfg.get("category", category)
    return cfg
