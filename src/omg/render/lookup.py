"""音符 → 样本匹配（四层回退链）：技法 → 音高 → 力度 → 轮次。

力度支持**层间交叉淡化**：返回相邻力度层各带权重，由引擎混合，
避免力度跳变。技法合法集由索引 articulation 去重集驱动。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class SampleSelection:
    instrument: str
    articulation: str
    midi_note: int
    shift_semitones: float
    gain: float
    rows: list[sqlite3.Row] = field(default_factory=list)


MAX_SHIFT_SEMITONES = 6.0
_VEL_GAMMA = 1.2


class Lookup:
    def __init__(self, conn: sqlite3.Connection, library_id: int):
        self.conn = conn
        self.library_id = library_id

    # ---------- 元信息 ----------

    def available_articulations(self, instrument: str) -> list[str]:
        rows = self.conn.execute(
            """SELECT DISTINCT articulation FROM samples
               WHERE library_id=? AND instrument=? AND articulation IS NOT NULL""",
            (self.library_id, instrument),
        ).fetchall()
        return [r["articulation"] for r in rows]

    def available_notes(self, instrument: str, articulation: str) -> list[int]:
        rows = self.conn.execute(
            """SELECT DISTINCT midi_note FROM samples
               WHERE library_id=? AND instrument=? AND articulation=?
                 AND midi_note IS NOT NULL ORDER BY midi_note""",
            (self.library_id, instrument, articulation),
        ).fetchall()
        return [r["midi_note"] for r in rows]

    # ---------- 匹配 ----------

    def _resolve_articulation(self, instrument: str, technique: str | None) -> str:
        arts = self.available_articulations(instrument)
        if not arts:
            return ""
        if technique and technique in arts:
            return technique
        for default in ("arco", "sustain", "sustain_vib"):
            if default in arts:
                return default
        return arts[0]

    def _layers_for_note(self, instrument: str, articulation: str, midi_note: int) -> list[list[sqlite3.Row]]:
        """(inst, art, note) 按力度层分组，组内按 rr 排序。"""
        rows = self.conn.execute(
            """SELECT * FROM samples WHERE library_id=? AND instrument=? AND articulation=?
               AND midi_note=? ORDER BY vel_min, rr""",
            (self.library_id, instrument, articulation, midi_note),
        ).fetchall()
        groups: dict[tuple[int, int], list[sqlite3.Row]] = {}
        for r in rows:
            groups.setdefault((r["vel_min"], r["vel_max"]), []).append(r)
        return list(groups.values())

    def _gain(self, velocity: int) -> float:
        return (velocity / 127.0) ** _VEL_GAMMA

    def select_layers(
        self,
        instrument: str,
        pitch: int,
        velocity: int,
        technique: str | None = None,
    ) -> list[tuple[SampleSelection, float]]:
        """返回 [(SampleSelection, weight)]，weight 之和为 1。

        力度交叉淡化：velocity 落在某层内部 → 单层；落在两层中心之间 →
        按距离给相邻两层加权。
        """
        art = self._resolve_articulation(instrument, technique)
        if not art:
            return []
        notes = self.available_notes(instrument, art)
        if not notes:
            return []
        nearest = min(notes, key=lambda n: abs(n - pitch))
        shift = float(pitch - nearest)
        if abs(shift) > MAX_SHIFT_SEMITONES:
            shift = min(max(shift, -MAX_SHIFT_SEMITONES), MAX_SHIFT_SEMITONES)

        layers = self._layers_for_note(instrument, art, nearest)
        if not layers:
            return []
        gain = self._gain(velocity)

        def mk(rows: list[sqlite3.Row]) -> SampleSelection:
            return SampleSelection(
                instrument=instrument, articulation=art, midi_note=nearest,
                shift_semitones=shift, gain=gain, rows=rows,
            )

        if len(layers) == 1:
            return [(mk(layers[0]), 1.0)]

        centers = [((r[0]["vel_min"] + r[0]["vel_max"]) / 2.0) for r in layers]
        if velocity <= centers[0]:
            return [(mk(layers[0]), 1.0)]
        if velocity >= centers[-1]:
            return [(mk(layers[-1]), 1.0)]
        for i in range(len(centers) - 1):
            if centers[i] <= velocity <= centers[i + 1]:
                span = max(centers[i + 1] - centers[i], 1e-6)
                w = (velocity - centers[i]) / span
                return [(mk(layers[i]), 1 - w), (mk(layers[i + 1]), w)]
        return [(mk(layers[-1]), 1.0)]
