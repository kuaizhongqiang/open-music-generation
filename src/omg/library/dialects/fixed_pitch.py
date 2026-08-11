"""固定音高方言 —— 打击件：每个鼓件一个固定音高，无音高字段。

例：`Timpani1_Hit_v1_rr1_Sum.wav` → 鼓件 Timpani1 的音高查 pitch_config 的
percussion_pitch（可人工校准），技法 Hit/Roll，力度 vN，轮次 rr。
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import BaseMixin, DialectAdapter, ParsedContext, ParsedFields

_PREFIX_RE = re.compile(r"^([A-Za-z]+)(\d+)$")
_VEL_RE = re.compile(r"^v(\d+)$", re.IGNORECASE)
_RR_RE = re.compile(r"^(?:rr|RR)(\d+)$")


class FixedPitchAdapter(DialectAdapter, BaseMixin):
    name = "fixed_pitch"

    def load_context(self, inst_dir: Path, config: dict) -> dict:
        return {}

    def parse(self, ctx: ParsedContext) -> ParsedFields:
        stem = Path(ctx.filename).stem
        notes = ctx.notes or {}

        drum_id = None
        vel_layer = None
        rr = None
        art_candidates: list[str] = []
        for tok in stem.split("_"):
            # 先识别力度层/轮次，避免 v1/rr1 被前缀正则误吞
            if _VEL_RE.match(tok):
                vel_layer = int(_VEL_RE.match(tok).group(1))
            elif _RR_RE.match(tok):
                rr = int(_RR_RE.match(tok).group(1))
            elif (m := _PREFIX_RE.match(tok)) is not None:
                drum_id = f"{m.group(1)}{m.group(2)}"
            elif tok in ("Hit", "Roll"):
                art_candidates.append(tok)

        midi_note = notes.get(drum_id) if drum_id else None
        art_raw = art_candidates[-1] if art_candidates else None
        art, art_raw = self._resolve_articulation(art_raw)
        return ParsedFields(
            midi_note=midi_note,
            articulation=art,
            articulation_raw=art_raw,
            vel_layer=vel_layer,
            rr=rr,
            # 鼓件未映射音高不算解析失败（配置缺口），由 importer 记"无音高"警告
            valid=True,
        )
