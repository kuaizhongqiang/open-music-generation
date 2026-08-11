"""方言适配器抽象：把各采样库文件名/目录的差异收敛为统一的 ParsedFields。

一个适配器只负责"解析出原始字段"，规范化（技法→id、音高→midi、力度→层）
由 resolve() 完成。乐器身份永远来自目录路径，不由文件名决定。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from ..model import note_to_midi, normalize_articulation


@dataclass
class ParsedFields:
    """解析出的原始字段（方言层面的中间结果）。"""
    midi_note: int | None = None
    articulation: str | None = None       # 规范化技法 id
    articulation_raw: str | None = None   # 原始技法串（保真）
    vel_layer: int | None = None          # 力度层序号 1..N；None=单层
    vel_dynamic: str | None = None        # 力度记号如 f/p/mf/loud（若有）
    rr: int | None = None                 # 轮次序号；None=无轮次
    valid: bool = True                    # False = 该文件坏/不可解析


@dataclass
class ParsedContext:
    """解析所需的上下文：目录、乐器配置、映射表等。"""
    inst_dir: Path
    subdir: str                     # 相对 inst_dir 的子目录（"" 表示根）
    filename: str
    config: dict                    # registry 中的乐器配置
    mapping: dict[int, int] | None = None   # 映射表类乐器：{序号: midi}
    notes: dict[str, int] | None = None     # 固定音高类：{文件名前缀: midi}


class DialectAdapter(ABC):
    """把文件名+子目录解析成 ParsedFields。每个适配器对应一类命名方言。"""

    name: str = "base"

    @abstractmethod
    def load_context(self, inst_dir: Path, config: dict) -> dict:
        """加载乐器级上下文（如钢琴 MappingChart），返回给 parse 用。默认空。"""

    @abstractmethod
    def parse(self, ctx: ParsedContext) -> ParsedFields: ...


class BaseMixin:
    """共享解析小工具。"""

    def _resolve_articulation(self, raw: str | None) -> tuple[str | None, str | None]:
        art = normalize_articulation(raw)
        return art, (raw.strip() if raw else None)

    def _resolve_note(self, token: str) -> int | None:
        return note_to_midi(token)

    def _resolve_velocity(
        self,
        vel_layer: int | None,
        vel_dynamic: str | None,
        dynamics: dict,
        layer_ranges: list[list[int]],
    ) -> tuple[int | None, int, int]:
        """力度层 → (vel_layer, vel_min, vel_max)。"""
        if vel_layer is not None:
            if 1 <= vel_layer <= len(layer_ranges):
                lo, hi = layer_ranges[vel_layer - 1]
                return vel_layer, lo, hi
            return vel_layer, 0, 127
        if vel_dynamic:
            dyn = vel_dynamic.lower()
            if dyn in dynamics:
                lo, hi = dynamics[dyn]
                # 动态记号也算一层（序号由调用方在分组阶段确定，这里标记 1）
                return 1, lo, hi
        return None, 0, 127
