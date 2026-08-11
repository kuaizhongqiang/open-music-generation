"""低音可听性测试：大提琴 + 低音提琴 两轨，无管乐/小提琴。

低音提琴奏 C 大调音阶低八度（C2→C3），大提琴同音高八度（C3→C4）加强谐波。
低混响、无其它声部，隔离验证"低音是否可闻"。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from omg.score import io as score_io
from omg.score.model import Note, Score, Track

# C 大调音阶（低音区）
SCALE_LOW = [36, 38, 40, 41, 43, 45, 47, 48]   # C2 D2 E2 F2 G2 A2 B2 C3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True)
    ap.add_argument("--out", default="out/bass")
    ap.add_argument("--mp3", action="store_true")
    args = ap.parse_args()

    bass = [Note(i, 1.0, p, 100, "sustain_vib") for i, p in enumerate(SCALE_LOW)]
    cello = [Note(i, 1.0, p + 12, 90, "sustain_vib") for i, p in enumerate(SCALE_LOW)]

    score = Score(title="bass-test", tempo_bpm=90.0, tracks=[
        Track(id="bass", name="double bass", instrument="solo_contrabass",
              notes=bass, bass_boost_db=18),
        Track(id="cello", name="cello", instrument="cello_section",
              notes=cello, gain_db=-4),
    ])
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    score_path = outdir / "bass_test.json"
    score_io.save(score, score_path)

    cmd = [sys.executable, "-m", "omg.render.cli", "render", str(score_path),
           "--lib", args.lib, "--out", args.out, "--reverb", "0.1"]
    if args.mp3:
        cmd.append("--mp3")
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
