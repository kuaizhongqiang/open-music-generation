"""音符 → 样本匹配（四层回退链）：技法 → 音高 → 力度 → 轮次。

技法合法集由索引 articulation 去重集驱动；音高取最近样本并计算变调量；
力度按 [vel_min, vel_max] 命中层（无命中取层中心最近）；轮次候选集交给 rr.py。
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

    def _rows_for_note(self, instrument: str, articulation: str, midi_note: int,
                       velocity: int | None) -> list[sqlite3.Row]:
        """取 (inst, art, note) 的样本；velocity 给定则优先命中力度层。"""
        sql = """SELECT * FROM samples
                 WHERE library_id=? AND instrument=? AND articulation=? AND midi_note=?"""
        args: list = [self.library_id, instrument, articulation, midi_note]
        if velocity is not None:
            sql += " AND vel_min<=? AND vel_max>=?"
            args += [velocity, velocity]
        sql += " ORDER BY vel_min, rr"
        rows = self.conn.execute(sql, args).fetchall()
        if rows or velocity is None:
            return rows
        # 力度层未命中 → 取层中心最近的层
        all_rows = self.conn.execute(
            """SELECT * FROM samples WHERE library_id=? AND instrument=? AND articulation=?
               AND midi_note=? ORDER BY vel_min, rr""",
            (self.library_id, instrument, articulation, midi_note),
        ).fetchall()
        if not all_rows:
            return []
        best = min(all_rows, key=lambda r: abs((r["vel_min"] + r["vel_max"]) / 2 - velocity))
        return [best]

    def select(self, instrument: str, pitch: int, velocity: int,
               technique: str | None = None) -> SampleSelection | None:
        art = self._resolve_articulation(instrument, technique)
        if not art:
            return None
        notes = self.available_notes(instrument, art)
        if not notes:
            return None
        nearest = min(notes, key=lambda n: abs(n - pitch))
        shift = float(pitch - nearest)
        if abs(shift) > MAX_SHIFT_SEMITONES:
            shift = min(max(shift, -MAX_SHIFT_SEMITONES), MAX_SHIFT_SEMITONES)
        rows = self._rows_for_note(instrument, art, nearest, velocity)
        gain = (velocity / 127.0) ** _VEL_GAMMA
        return SampleSelection(
            instrument=instrument,
            articulation=art,
            midi_note=nearest,
            shift_semitones=shift,
            gain=gain,
            rows=rows,
        )
