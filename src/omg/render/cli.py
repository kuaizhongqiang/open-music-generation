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

from ..io.export import export_mp3, write_wav
from ..library.index import get_library_id, open_db
from ..score import io as score_io
from ..score.model import Note, Score, Track, transpose
from .engine import RenderEngine
from .mixer import apply_track_stereo, mix_tracks
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
    # 大提琴协和低音：C3/G3 交替（C 大调主属持续音，永远和谐）
    cello = Track(id="cello", name="cello bass", instrument="cello_section",
                  notes=[Note(i * 0.5, 1.0, 48 if (i // 2) % 2 == 0 else 55, 80, "sustain_vib")
                         for i in range(16)],
                  gain_db=-6.0, pan=-0.3)
    # 定音鼓低音点缀（每两拍一下，略右）
    timpani = Track(id="timpani", name="timpani hits", instrument="timpani",
                    notes=[Note(i * 2.0, 0.5, 41, 90, "hit") for i in range(3)],
                    gain_db=-4.0, pan=0.4)
    return Score(
        title="demo",
        tempo_bpm=90.0,
        tracks=[
            Track(id="violin", name="violin melody", instrument="solo_violin", notes=notes),
            cello,
            timpani,
        ],
    )


def _make_chords() -> Score:
    """C 大调 I-IV-V-I 大三和弦进行（三声部：根音/三音/五音）。

    用来验证"和音"：和弦内的音应是纯五度/大三度的协和关系。
    """
    # (根音, 三音, 五音) MIDI
    chords = [
        ("C", (48, 52, 55)),   # C 大三和弦
        ("F", (53, 57, 60)),   # F 大三和弦
        ("G", (55, 59, 62)),   # G 大三和弦
        ("C", (48, 52, 55)),   # C
    ]
    beat_s = 0.667  # 90bpm
    dur = 2.0
    cello, viola, violin = [], [], []
    for i, (name, (r, third, fifth)) in enumerate(chords):
        t = i * dur
        cello.append(Note(t, dur, r, 90, "sustain_vib"))
        viola.append(Note(t, dur, third, 85, "sustain_vib"))
        violin.append(Note(t, dur, fifth, 90, "arco_vib"))
    return Score(
        title="chords-I-IV-V-I",
        tempo_bpm=90.0,
        tracks=[
            Track(id="cello", name="root", instrument="cello_section",
                  notes=cello, gain_db=-4.0, pan=-0.3),
            Track(id="viola", name="third", instrument="viola_section",
                  notes=viola, gain_db=-2.0, pan=0.0),
            Track(id="violin", name="fifth", instrument="violin_section",
                  notes=violin, pan=0.3),
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
    if getattr(args, "transpose", 0):
        score = transpose(score, args.transpose)
        print(f"[移调] 全体音符 {args.transpose:+d} 半音")
    conn = open_db(args.lib)
    engine, _ = _build_engine(conn, args.library, args.sr, args.backend)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    for track in score.tracks:
        buf = render_track(engine, score, track)
        if len(buf) == 0:
            print(f"[跳过] 空轨 {track.id}")
            continue
        # 单轨导出应用轨道增益/声像/EQ，与混音内听感一致
        buf = apply_track_stereo(buf, track.gain_db, track.pan, track.bass_boost_db,
                                 engine.project_sr)
        path = outdir / f"trk_{track.id}.wav"
        write_wav(path, buf, engine.project_sr)
        print(f"写出 {path}  ({len(buf) / engine.project_sr:.2f}s)")
    # 混音
    mix = mix_tracks(engine, score, reverb=args.reverb)
    if len(mix):
        mix_path = outdir / "mix.wav"
        write_wav(mix_path, mix, engine.project_sr)
        print(f"写出 {mix_path}  (混音 {len(mix) / engine.project_sr:.2f}s, reverb={args.reverb})")
        if args.mp3:
            mp3_path = export_mp3(mix_path, mix_path.with_suffix(".mp3"))
            print(f"写出 {mp3_path}")
    conn.close()
    print("完成")
    return 0


def _cmd_chords(args: argparse.Namespace) -> int:
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    score = _make_chords()
    score_path = outdir / "chords.json"
    score_io.save(score, score_path)
    print(f"和弦乐谱: {score_path}")
    return _cmd_render(
        argparse.Namespace(
            score=str(score_path), lib=args.lib, library=args.library,
            sr=args.sr, backend=args.backend, out=args.out, mp3=args.mp3,
            reverb=args.reverb, transpose=args.transpose,
        )
    )


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
            sr=args.sr, backend=args.backend, out=args.out, mp3=args.mp3,
            reverb=args.reverb, transpose=args.transpose,
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
    p_render.add_argument("--mp3", action="store_true", help="同时导出 mp3")
    p_render.add_argument("--reverb", type=float, default=0.0, help="房间混响 wet 比例 0..1")
    p_render.add_argument("--transpose", type=int, default=0, help="全体音符移调 N 半音（负数为降）")
    p_render.set_defaults(func=_cmd_render)

    p_chords = sub.add_parser("chords", help="渲染 C 大调 I-IV-V-I 大三和弦进行（验证和音）")
    p_chords.add_argument("--lib", required=True)
    p_chords.add_argument("--library", default="vsco2")
    p_chords.add_argument("--out", default="out")
    p_chords.add_argument("--sr", type=int, default=44100)
    p_chords.add_argument("--backend", default="samplerate", choices=["samplerate", "numpy"])
    p_chords.add_argument("--mp3", action="store_true", help="同时导出 mp3")
    p_chords.add_argument("--reverb", type=float, default=0.25)
    p_chords.add_argument("--transpose", type=int, default=0, help="全体音符移调 N 半音（负数为降）")
    p_chords.set_defaults(func=_cmd_chords)

    p_demo = sub.add_parser("demo", help="生成并渲染 demo 乐谱")
    p_demo.add_argument("--lib", required=True)
    p_demo.add_argument("--library", default="vsco2")
    p_demo.add_argument("--out", default="out")
    p_demo.add_argument("--sr", type=int, default=44100)
    p_demo.add_argument("--backend", default="samplerate", choices=["samplerate", "numpy"])
    p_demo.add_argument("--mp3", action="store_true", help="同时导出 mp3")
    p_demo.add_argument("--reverb", type=float, default=0.25, help="房间混响 wet 比例 0..1（demo 默认 0.25）")
    p_demo.add_argument("--transpose", type=int, default=0, help="全体音符移调 N 半音（负数为降）")
    p_demo.set_defaults(func=_cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
