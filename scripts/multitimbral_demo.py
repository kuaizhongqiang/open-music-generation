"""跨乐器族合奏 demo：弦乐(小提琴旋律) + 木管(长笛对位) + 铜管(圆号和声)
+ 键盘(钢琴和弦) + 打击(定音鼓)。

验证引擎对"多种音色 / 跨族编曲"的支持。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from omg.score import io as score_io
from omg.score.model import Note, Score, Track


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True)
    ap.add_argument("--out", default="out/multi")
    ap.add_argument("--mp3", action="store_true")
    args = ap.parse_args()

    # 小提琴旋律（C 大调音阶上行，两小节）
    violin = [Note(i, 0.5, 60 + [0, 2, 4, 5, 7, 9, 11, 12][i], 95, "arco_vib")
              for i in range(8)]
    # 长笛对位（高八度，更柔和）
    flute = [Note(i, 0.5, 60 + [0, 2, 4, 5, 7, 9, 11, 12][i] + 12, 80, "sustain_vib")
             for i in range(8)]
    # 圆号和声（长音，低音区）
    horn = [Note(0, 2.0, 55, 85, "sustain"), Note(2.0, 2.0, 52, 85, "sustain"),
            Note(4.0, 2.0, 55, 85, "sustain"), Note(6.0, 2.0, 60, 85, "sustain")]
    # 钢琴和弦（每两拍一个分解/柱式）
    piano = [Note(i * 1.0, 1.0, p, 70, None) for i, p in
             enumerate([60, 64, 67, 64] * 2)]
    # 定音鼓点缀
    timp = [Note(i * 2.0, 0.3, 41, 90, "hit") for i in range(4)]

    score = Score(title="multitimbral", tempo_bpm=120.0, tracks=[
        Track(id="violin", name="violin", instrument="solo_violin", notes=violin),
        Track(id="flute", name="flute", instrument="flute", notes=flute, gain_db=-3, pan=0.3),
        Track(id="horn", name="horn", instrument="f_horn", notes=horn, gain_db=-2, pan=-0.2),
        Track(id="piano", name="piano", instrument="upright_piano", notes=piano, gain_db=-6),
        Track(id="timp", name="timpani", instrument="timpani", notes=timp, gain_db=-3),
    ])
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    score_path = outdir / "multitimbral.json"
    score_io.save(score, score_path)

    cmd = [sys.executable, "-m", "omg.render.cli", "render", str(score_path),
           "--lib", args.lib, "--out", args.out, "--reverb", "0.25"]
    if args.mp3:
        cmd.append("--mp3")
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
