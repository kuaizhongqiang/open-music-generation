"""导入编排：遍历库根 → 按乐器/方言解析 → 读头 → 后处理力度与轮次 → 入库。

流程：
  1. 顶层目录 → category
  2. 逐乐器目录：registry 解析配置 → 加载上下文（钢琴 MappingChart 等）
  3. 逐 .wav：适配器 parse → 中间结构
  4. 后处理：力度区间（vN 按层均分、动态记号按乐器内动态档均分）、rr_count 分组统计
  5. soundfile 读头（dur/sr/channels）→ 单事务入库
  6. 审计报表
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import soundfile as sf

from .dialects.base import ParsedContext, ParsedFields
from .index import add_library, clear_library, insert_samples, open_db
from .model import ImportReport, SampleMeta, slugify
from .registry import CATEGORY_MAP, get_adapter, resolve_config

_CFG_PATH = Path(__file__).parent / "pitch_config.json"


def _load_pitch_config() -> dict:
    return json.loads(_CFG_PATH.read_text(encoding="utf-8"))


def _even_layer_ranges(n_layers: int) -> list[tuple[int, int]]:
    if n_layers <= 1:
        return [(0, 127)]
    size = 127 / n_layers
    return [(round(i * size), round((i + 1) * size - 1) if i < n_layers - 1 else 127)
            for i in range(n_layers)]


def _assign_velocity_ranges(samples: list[SampleMeta], dynamics_order: list[str]) -> None:
    """按乐器分两派计算力度区间：vN 层按最大层均分；动态记号按乐器内动态档均分。"""
    by_instrument: dict[str, list[SampleMeta]] = defaultdict(list)
    for s in samples:
        by_instrument[s.instrument].append(s)

    for inst_samples in by_instrument.values():
        # 派1：vN 层
        layer_samples = [s for s in inst_samples if s.vel_layer is not None]
        if layer_samples:
            n_layers = max(s.vel_layer for s in layer_samples)
            ranges = _even_layer_ranges(n_layers)
            for s in layer_samples:
                lo, hi = ranges[min(s.vel_layer - 1, len(ranges) - 1)]
                s.vel_min, s.vel_max = lo, hi
        # 派2：动态记号
        dyn_samples = [s for s in inst_samples if s.vel_dynamic is not None]
        if dyn_samples:
            order = {d: i for i, d in enumerate(dynamics_order)}
            distinct = sorted({s.vel_dynamic for s in dyn_samples}, key=lambda d: order.get(d, 99))
            ranges = _even_layer_ranges(len(distinct))
            dyn_to_range = dict(zip(distinct, ranges))
            for s in dyn_samples:
                s.vel_min, s.vel_max = dyn_to_range[s.vel_dynamic]


def _assign_rr_counts(samples: list[SampleMeta]) -> None:
    groups: dict[tuple, list[SampleMeta]] = defaultdict(list)
    for s in samples:
        key = (s.instrument, s.articulation, s.midi_note, s.vel_layer, s.vel_min, s.vel_max)
        groups[key].append(s)
    for group in groups.values():
        for s in group:
            s.rr_count = len(group)


def import_library(root: str | Path, db_path: str | Path, library_name: str | None = None,
                   version: str | None = None) -> ImportReport:
    root = Path(root)
    report = ImportReport()
    samples: list[SampleMeta] = []
    cfg_data = _load_pitch_config()
    dynamics_order = cfg_data["dynamics_order"]
    percussion_pitch = cfg_data["percussion_pitch"]

    conn = open_db(db_path)
    library_id = add_library(conn, library_name or root.name, str(root), version)
    clear_library(conn, library_id)

    for category_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        category = CATEGORY_MAP.get(category_dir.name, slugify(category_dir.name))
        for inst_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            inst_label = inst_dir.name
            config = resolve_config(category, inst_label)
            adapter = get_adapter(config["adapter"])
            ctx_parts = adapter.load_context(inst_dir, config)

            inst_key = f"{category}/{inst_label}"
            report.per_instrument[inst_key] = {"total": 0, "parsed": 0}
            inst_samples: list[SampleMeta] = []
            for wav in sorted(inst_dir.rglob("*.wav")):
                report.total_files += 1
                report.per_instrument[inst_key]["total"] += 1
                subdir = wav.parent.relative_to(inst_dir).as_posix()
                if subdir == ".":
                    subdir = ""
                pc = ParsedContext(
                    inst_dir=inst_dir,
                    subdir=subdir,
                    filename=wav.name,
                    config=config,
                    mapping=ctx_parts.get("mapping"),
                    notes=percussion_pitch,
                )
                try:
                    parsed: ParsedFields = adapter.parse(pc)
                except Exception as exc:  # noqa: BLE001 —— 单文件解析失败不中断
                    report.failed += 1
                    report.warnings.append(f"异常 {wav.relative_to(root)}: {exc}")
                    continue

                if not parsed.valid:
                    report.failed += 1
                    report.warnings.append(f"解析失败 {wav.relative_to(root)}")
                    continue

                meta = SampleMeta(
                    instrument=slugify(inst_label),
                    instrument_label=inst_label,
                    category=category,
                    file_rel=wav.relative_to(root).as_posix(),
                    midi_note=parsed.midi_note,
                    articulation=parsed.articulation or config.get("default_art"),
                    articulation_raw=parsed.articulation_raw,
                    vel_layer=parsed.vel_layer,
                    rr=parsed.rr,
                    vel_dynamic=parsed.vel_dynamic,
                    importer=adapter.name,
                )
                # 无音高样本（no_pitch / 未映射打击件）
                if meta.midi_note is None:
                    if config.get("adapter") == "no_pitch":
                        report.no_pitch += 1
                    else:
                        report.warnings.append(f"无音高 {wav.relative_to(root)}")
                        report.no_pitch += 1
                else:
                    report.parsed += 1
                    report.per_instrument[inst_key]["parsed"] += 1

                info = sf.info(str(wav))
                meta.dur_ms = info.frames / info.samplerate * 1000
                meta.sr = info.samplerate
                meta.channels = info.channels
                inst_samples.append(meta)

            samples.extend(inst_samples)

    # 后处理力度区间 + 轮次计数
    _assign_velocity_ranges(samples, dynamics_order)
    _assign_rr_counts(samples)
    insert_samples(conn, library_id, samples)
    conn.close()
    return report
