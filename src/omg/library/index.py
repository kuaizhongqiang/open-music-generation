"""SQLite 索引：建表、写入与查询封装。

schema 从第一版就带 library_id 外键，为 P4 多库预留。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .model import SampleMeta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS libraries (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    root       TEXT NOT NULL,
    format     TEXT NOT NULL DEFAULT 'wav',
    version    TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS samples (
    id               INTEGER PRIMARY KEY,
    library_id       INTEGER NOT NULL REFERENCES libraries(id),
    instrument       TEXT NOT NULL,
    instrument_label TEXT,
    category         TEXT NOT NULL,
    articulation     TEXT,
    articulation_raw TEXT,
    midi_note        INTEGER,
    vel_layer        INTEGER,
    vel_min          INTEGER,
    vel_max          INTEGER,
    rr               INTEGER,
    rr_count         INTEGER,
    file_rel         TEXT NOT NULL,
    dur_ms           REAL,
    sr               INTEGER,
    channels         INTEGER,
    importer         TEXT,
    indexed_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_samples_lookup
    ON samples (library_id, instrument, articulation, midi_note, vel_min, vel_max);
"""


def open_db(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    return conn


def add_library(conn: sqlite3.Connection, name: str, root: str, version: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO libraries (name, root, version) VALUES (?, ?, ?) "
        "ON CONFLICT(name) DO UPDATE SET root=excluded.root, version=excluded.version",
        (name, root, version),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM libraries WHERE name=?", (name,)).fetchone()
    return int(row["id"])


def clear_library(conn: sqlite3.Connection, library_id: int) -> None:
    conn.execute("DELETE FROM samples WHERE library_id=?", (library_id,))
    conn.commit()


def insert_samples(conn: sqlite3.Connection, library_id: int, samples: list[SampleMeta]) -> None:
    rows = [
        (
            library_id,
            s.instrument, s.instrument_label, s.category,
            s.articulation, s.articulation_raw,
            s.midi_note, s.vel_layer, s.vel_min, s.vel_max,
            s.rr, s.rr_count,
            s.file_rel, s.dur_ms, s.sr, s.channels,
            s.importer,
        )
        for s in samples
    ]
    conn.executemany(
        """INSERT INTO samples (
            library_id, instrument, instrument_label, category,
            articulation, articulation_raw, midi_note, vel_layer, vel_min, vel_max,
            rr, rr_count, file_rel, dur_ms, sr, channels, importer)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()


# ---------- 查询 ----------


def list_instruments(conn: sqlite3.Connection, library_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT instrument, instrument_label, category,
                  COUNT(*) AS n, COUNT(midi_note) AS pitched,
                  GROUP_CONCAT(DISTINCT articulation) AS arts
           FROM samples WHERE library_id=?
           GROUP BY instrument ORDER BY instrument""",
        (library_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_library_id(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute("SELECT id FROM libraries WHERE name=?", (name,)).fetchone()
    return int(row["id"]) if row else None


def find_samples(
    conn: sqlite3.Connection,
    instrument: str,
    library_id: int,
    articulation: str | None = None,
    midi_note: int | None = None,
    vel: int | None = None,
    limit: int = 1000,
) -> list[sqlite3.Row]:
    """P1 渲染侧查询。按技法/音高/力度区间过滤。"""
    sql = "SELECT * FROM samples WHERE library_id=? AND instrument=?"
    args: list = [library_id, instrument]
    if articulation is not None:
        sql += " AND articulation=?"
        args.append(articulation)
    if midi_note is not None:
        sql += " AND midi_note=?"
        args.append(midi_note)
    if vel is not None:
        sql += " AND vel_min<=? AND vel_max>=?"
        args += [vel, vel]
    sql += " ORDER BY midi_note LIMIT ?"
    args.append(limit)
    return conn.execute(sql, args).fetchall()
