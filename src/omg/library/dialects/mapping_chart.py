"""MappingChart 方言 —— 钢琴类：文件名无音高，靠 MappingChart.txt 映射。

例：`Player_dyn1_rr1_000.wav` + MappingChart.txt（`Notation=KeyNumber` 头，
每行 `NNN=NN`）→ dyn1 力度层、rr1 轮次、序号 000 → MIDI 键。
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import BaseMixin, DialectAdapter, ParsedContext, ParsedFields

_DYN_RE = re.compile(r"^dyn(\d+)$", re.IGNORECASE)
_NUM_RE = re.compile(r"^(\d+)$")


class MappingChartAdapter(DialectAdapter, BaseMixin):
    name = "mapping_chart"

    def load_context(self, inst_dir: Path, config: dict) -> dict:
        mapping: dict[int, int] = {}
        for name in ("MappingChart.txt", "MappingChart", "map.txt"):
            p = inst_dir / name
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                left, _, right = line.partition("=")
                left, right = left.strip(), right.strip()
                if left.lower() in ("notation", "keynumber", "key"):
                    continue
                try:
                    mapping[int(left)] = int(right)
                except ValueError:
                    continue
        return {"mapping": mapping}

    def parse(self, ctx: ParsedContext) -> ParsedFields:
        stem = Path(ctx.filename).stem
        mapping = (ctx.mapping or {})
        vel_layer = None
        rr = None
        num = None
        for tok in stem.split("_"):
            if _DYN_RE.match(tok):
                vel_layer = int(_DYN_RE.match(tok).group(1))
            elif _NUM_RE.match(tok):
                num = int(_NUM_RE.match(tok).group(1))
            elif re.match(r"^rr\d+$", tok, re.IGNORECASE):
                rr = int(tok[2:])

        midi_note = mapping.get(num) if num is not None else None
        return ParsedFields(
            midi_note=midi_note,
            articulation_raw=None,
            vel_layer=vel_layer,
            rr=rr,
            valid=True,
        )
