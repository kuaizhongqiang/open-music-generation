"""无音高方言 —— 风琴/鼓组/音效等无旋律音高语义的样本。

原样收录进索引（midi_note=NULL），供审计与完整性统计；渲染期不可用于旋律。
"""
from __future__ import annotations

from pathlib import Path

from .base import DialectAdapter, ParsedContext, ParsedFields


class NoPitchAdapter(DialectAdapter):
    name = "no_pitch"

    def load_context(self, inst_dir: Path, config: dict) -> dict:
        return {}

    def parse(self, ctx: ParsedContext) -> ParsedFields:
        return ParsedFields(midi_note=None, valid=True)
