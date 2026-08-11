"""令牌式方言解析器 —— 库内绝大多数乐器的通用解析。

处理形如 `MOHorn_stac_A#1_v1_rr1.wav`、`LLVln_ArcoVib_A3_f.wav`、
`PSBassoon_A#0_v2_rr1.wav`、`KSHarp_A2_mf.wav`、`Sum_SHTrumpet_harmonM-sus_A#2_v1_rr1.wav`
等各类变体：按 `_` 切令牌，逐个分类（音高/力度层/轮次/力度记号/噪音/候选技法），
技法取最后一个非语义令牌，找不到则回退到子目录名。
"""
from __future__ import annotations

import re
from pathlib import Path

from ..model import NOISE_TOKENS, DYNAMICS
from .base import BaseMixin, DialectAdapter, ParsedContext, ParsedFields

_NOTE_RE = re.compile(r"^[A-Ga-g](?:[#b])?-?\d+$")
_VEL_RE = re.compile(r"^v(\d+)$", re.IGNORECASE)
_RR_RE = re.compile(r"^(?:rr|RR)(\d+)$")
_NUM_RE = re.compile(r"^\d{1,3}$")
_DYN_RE = re.compile(r"^(?:ppp|pp|p|mp|mf|f|ff|fff|ffff|loud|soft)$", re.IGNORECASE)


class TokenStyleAdapter(DialectAdapter, BaseMixin):
    name = "token"

    def load_context(self, inst_dir: Path, config: dict) -> dict:
        return {}

    def parse(self, ctx: ParsedContext) -> ParsedFields:
        cfg = ctx.config
        stem = Path(ctx.filename).stem
        tokens = stem.split("_")

        midi_note = None
        vel_layer = None
        vel_dynamic = None
        rr = None
        art_candidates: list[str] = []
        noise = set(NOISE_TOKENS) | set(cfg.get("noise", []))
        inst_label = Path(ctx.inst_dir).name.lower()

        for tok in tokens:
            t = tok
            if not t:
                continue
            if _NOTE_RE.match(t):
                midi_note = self._resolve_note(t)
            elif _VEL_RE.match(t):
                vel_layer = int(_VEL_RE.match(t).group(1))
            elif _RR_RE.match(t):
                rr = int(_RR_RE.match(t).group(1))
            elif _DYN_RE.match(t):
                vel_dynamic = t.lower()
            elif _NUM_RE.match(t):
                if rr is None:
                    rr = int(t)
            elif t.lower() in noise or t.lower() == inst_label:
                continue
            else:
                art_candidates.append(t)

        # 技法：文件名最后一个候选；缺失则回退子目录
        articulation_raw = None
        art_source = cfg.get("art_source", "auto")
        if art_candidates and art_source != "subdir":
            articulation_raw = art_candidates[-1]
        if articulation_raw is None and ctx.subdir:
            articulation_raw = ctx.subdir.split("/")[-1]

        art, art_raw = self._resolve_articulation(articulation_raw)
        if art is None:
            art = cfg.get("default_art")
        return ParsedFields(
            midi_note=midi_note,
            articulation=art,
            articulation_raw=art_raw,
            vel_layer=vel_layer,
            vel_dynamic=vel_dynamic,
            rr=rr,
            valid=midi_note is not None,  # 无音高字段视为坏文件（应由 no_pitch 适配器处理）
        )
