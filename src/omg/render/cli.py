"""P1 CLI：渲染乐谱为音频。

用法：
  python -m omg.render.cli demo --out out/            # 生成 demo 乐谱并渲染
  python -m omg.render.cli render score.json --lib data/vsco2.sqlite3 --out out/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import soundfile as sf

from ..library.index import get_library_id, open_db
from ..score import io as score_io
from ..score.model import Note, Score, Track
from .engine import RenderEngine
from .track import render_track


def _make_demo() -> Score:
    """C 大调音阶 + 一段旋律，覆盖技法与力度变化。"""
    scale = [60, 62, 64, 65, 67, 69, 71, 72]
    notes = [Note(start_beat=i, duration=1.0, pitch=p, velocity=100, technique="arco_vib")
             for i, p in enumerate(scale)]
    melody = [
        Note(0, 1.5, 64, 90, "arco_vib"),
        Note(1.5, 0.5, 67, 110, "spiccato"),
        Note(2.0, 1.5, 69, 90, "arco_vib"),
        Note(3.5, 0.5, 72, 110, "spiccato"),
        Note(4.0, 2.0, 71, 80, "arco_vib"),
    ]
    return Score(
        title="demo",
        tempo_bpm=90.0,
        tracks=[
            Track(id="violin", name="violin melody", instrument="solo_violin", notes=notes),
            Track(id="cello", name="cello line", instrument="cello_section",
                  notes=[Note(i * 0.5, 2.0, 48 + i, 80, "sustain_vib") for i in range(8)]),
        ],
    )


def _build_engine(conn, library: str, sr: int, backend: str) -> tuple[RenderEngine, Path]:
    lid = get_library_id(conn, library)
    if lid is None:
        raise SystemExit(f"库不存在: {library}")
    row = conn.execute("SELECT root FROM libraries WHERE id=?", (lid,)).fetchone()
    engine = RenderEngine(conn, lid, row["root"], project_sr=sr, backend=backend)
    return engine, Path(row["root"])


def _cmd_render(args: argparse.Namespace) -> int:
    score = score_io.load(args.score)
    conn = open_db(args.lib)
    engine, _ = _build_engine(conn, args.library, args.sr, args.backend)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    for track in score.tracks:
        buf = render_track(engine, score, track)
        if len(buf) == 0:
            print(f"[跳过] 空轨 {track.id}")
            continue
        path = outdir / f"trk_{track.id}.wav"
        sf.write(str(path), buf, engine.project_sr, subtype="PCM_16")
        print(f"写出 {path}  ({len(buf) / engine.project_sr:.2f}s)")
    conn.close()
    print("完成")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    score = _make_demo()
    score_path = outdir / "demo.json"
    score_io.save(score, score_path)
    print(f"demo 乐谱: {score_path}")
    return _cmd_render(
        argparse.Namespace(
            score=str(score_path), lib=args.lib, library=args.library,
            sr=args.sr, backend=args.backend, out=args.out,
        )
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="omg-render")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_render = sub.add_parser("render", help="渲染乐谱 JSON 为音频")
    p_render.add_argument("score")
    p_render.add_argument("--lib", required=True, help="SQLite 索引路径")
    p_render.add_argument("--library", default="vsco2")
    p_render.add_argument("--out", default="out")
    p_render.add_argument("--sr", type=int, default=44100)
    p_render.add_argument("--backend", default="samplerate", choices=["samplerate", "numpy"])
    p_render.set_defaults(func=_cmd_render)

    p_demo = sub.add_parser("demo", help="生成并渲染 demo 乐谱")
    p_demo.add_argument("--lib", required=True)
    p_demo.add_argument("--library", default="vsco2")
    p_demo.add_argument("--out", default="out")
    p_demo.add_argument("--sr", type=int, default=44100)
    p_demo.add_argument("--backend", default="samplerate", choices=["samplerate", "numpy"])
    p_demo.set_defaults(func=_cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
