"""P0 导入器与索引的单元测试（合成库，离线可跑）。"""
from __future__ import annotations

from pathlib import Path

from omg.library.importer import import_library
from omg.library.index import get_library_id, open_db
from omg.library.model import midi_to_note, note_to_midi


def test_note_to_midi():
    assert note_to_midi("C4") == 60
    assert note_to_midi("A0") == 21
    assert note_to_midi("A#1") == 34
    assert note_to_midi("A#0") == 22
    assert note_to_midi("C8") == 108
    assert note_to_midi("bogus") is None


def test_midi_to_note_roundtrip():
    for midi in (21, 45, 60, 108):
        assert note_to_midi(midi_to_note(midi)) == midi


def test_import_fake_library(fake_library: Path, tmp_path: Path):
    db = tmp_path / "index.sqlite3"
    report = import_library(fake_library, db, "fakelib")

    # 全部文件应解析（含 no_pitch），无一失败
    assert report.failed == 0
    assert report.parse_rate == 1.0

    conn = open_db(db)
    lid = get_library_id(conn, "fakelib")
    assert lid is not None

    def q(sql: str, *args) -> list:
        return conn.execute(sql, args).fetchall()

    def count(inst: str) -> int:
        return q("SELECT COUNT(*) n FROM samples WHERE library_id=? AND instrument=?",
                 lid, inst)[0]["n"]

    # 有音高乐器计数
    assert count("f_horn") == 2
    assert count("solo_violin") == 5
    assert count("upright_piano") == 3
    assert count("timpani") == 2
    # no_pitch 收录
    assert count("drums") == 1

    # 钢琴 MappingChart：_000 → 21, _002 → 25
    notes = sorted(r["midi_note"] for r in q(
        "SELECT midi_note FROM samples WHERE library_id=? AND instrument='upright_piano' AND vel_layer=1",
        lid))
    assert notes == [21, 25]

    # 定音鼓固定音高
    assert q("SELECT DISTINCT midi_note FROM samples WHERE library_id=? AND instrument='timpani'",
             lid)[0]["midi_note"] == 41

    # 小提琴力度区间：f→上段, p→下段
    f_rows = q(
        "SELECT vel_min, vel_max FROM samples WHERE library_id=? AND instrument='solo_violin' "
        "AND articulation='arco_vib' AND midi_note=57", lid)  # A3 = MIDI 57
    ranges = sorted((r["vel_min"], r["vel_max"]) for r in f_rows)
    assert ranges == [(0, 62), (64, 127)]

    # 轮次计数：Pizz C4 f 有 2 个轮次
    rr = q("SELECT DISTINCT rr_count FROM samples WHERE library_id=? AND instrument='solo_violin' "
           "AND articulation='pizzicato' AND midi_note=60", lid)
    assert [r["rr_count"] for r in rr] == [2]

    conn.close()
