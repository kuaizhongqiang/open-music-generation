"""导出：wav 直写，mp3 走 ffmpeg（lame，高质量）。"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf


def write_wav(path: str | Path, buf: np.ndarray, sr: int) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), buf, sr, subtype="PCM_16")
    return path


def export_mp3(wav_path: str | Path, mp3_path: str | Path, bitrate: str = "192k") -> Path:
    """用 ffmpeg 把 wav 转 mp3。依赖外部 ffmpeg。"""
    wav_path, mp3_path = Path(wav_path), Path(mp3_path)
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(wav_path),
        "-codec:a", "libmp3lame", "-b:a", bitrate,
        str(mp3_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg mp3 导出失败: {r.stderr[:300]}")
    return mp3_path
