"""P0 CLI：导入 VSCO2 库、列出乐器、查询样本。

用法：
  python -m omg.library.cli import --root data/VSCO-2-CE-master --db data/vsco2.sqlite3
  python -m omg.library.cli list-instruments --db data/vsco2.sqlite3
  python -m omg.library.cli query --db data/vsco2.sqlite3 --instrument solo_violin --note 60
"""
from __future__ import annotations

import argparse
import sys

from .importer import import_library
from .index import get_library_id, list_instruments, open_db
from .model import midi_to_note


def _cmd_import(args: argparse.Namespace) -> int:
    print(f"导入 {args.root} → {args.db} ...")
    report = import_library(args.root, args.db, args.library)
    print(f"文件总数   : {report.total_files}")
    print(f"有音高解析 : {report.parsed}")
    print(f"无音高收录 : {report.no_pitch}")
    print(f"解析失败   : {report.failed}")
    print(f"可解析率   : {report.parse_rate * 100:.2f}%")
    if report.warnings:
        print(f"\n警告 {len(report.warnings)} 条（前 20 条）:")
        for w in report.warnings[:20]:
            print(f"  - {w}")
    print("\n各乐器统计:")
    for key, v in report.per_instrument.items():
        print(f"  {key:32s} {v['total']:5d} 文件, 有音高 {v['parsed']:5d}")
    if report.parse_rate < 0.99:
        print("\n[失败] 解析率 < 99%，未达 P0→P1 硬门槛")
        return 1
    print("\n[通过] 解析率 >= 99%，P0 验收门槛达成")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    conn = open_db(args.db)
    lid = get_library_id(conn, args.library)
    if lid is None:
        print(f"未找到库 {args.library}")
        return 1
    for row in list_instruments(conn, lid):
        arts = (row["arts"] or "").replace(",", ", ")
        print(f"{row['instrument']:24s} [{row['category']:9s}] {row['pitched']:4d}/{row['n']:4d} 有音高 | 技法: {arts}")
    conn.close()
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    conn = open_db(args.db)
    lid = get_library_id(conn, args.library)
    rows = conn.execute(
        """SELECT instrument, articulation, midi_note, vel_layer, vel_min, vel_max,
                  rr, rr_count, file_rel, dur_ms, sr
           FROM samples WHERE library_id=? AND instrument=? AND midi_note=?
           ORDER BY articulation, vel_min, rr LIMIT 30""",
        (lid, args.instrument, args.note),
    ).fetchall()
    if not rows:
        print(f"{args.instrument} 无 {args.note} ({midi_to_note(args.note)}) 样本")
        return 0
    for r in rows:
        print(
            f"{r['articulation']:12s} v{r['vel_layer'] or '-'} "
            f"[{r['vel_min']:3d},{r['vel_max']:3d}] rr{r['rr'] or '-'}/{r['rr_count']} "
            f"{r['file_rel']} ({r['dur_ms']:.0f}ms {r['sr']}Hz)"
        )
    conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    # Windows 控制台默认 GBK，强制 UTF-8 避免中文报表乱码
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="omg-library")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_import = sub.add_parser("import", help="导入采样库生成索引")
    p_import.add_argument("--root", required=True, help="库根目录")
    p_import.add_argument("--db", required=True, help="SQLite 索引路径")
    p_import.add_argument("--library", default="vsco2", help="库名（默认 vsco2）")
    p_import.set_defaults(func=_cmd_import)

    p_list = sub.add_parser("list-instruments", help="列出库内乐器")
    p_list.add_argument("--db", required=True)
    p_list.add_argument("--library", default="vsco2")
    p_list.set_defaults(func=_cmd_list)

    p_q = sub.add_parser("query", help="按音高查询样本")
    p_q.add_argument("--db", required=True)
    p_q.add_argument("--library", default="vsco2")
    p_q.add_argument("--instrument", required=True)
    p_q.add_argument("--note", type=int, required=True, help="MIDI 键号")
    p_q.set_defaults(func=_cmd_query)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
