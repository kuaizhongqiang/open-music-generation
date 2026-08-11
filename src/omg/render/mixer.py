"""多轨混音：逐轨渲染 → 每轨 gain_db/pan（等功率）→ 叠加 → 主输出 soft-clip。"""
from __future__ import annotations

import numpy as np

from ..score.model import Score
from . import envelope
from .effects import RoomReverb
from .engine import RenderEngine
from .track import render_track


def pan_gain(pan: float) -> tuple[float, float]:
    """等功率声像。pan: -1(左)..1(右)，0 居中。返回 (left_gain, right_gain)。"""
    pan = max(-1.0, min(1.0, pan))
    angle = (pan + 1.0) * np.pi / 4.0
    return float(np.cos(angle)), float(np.sin(angle))


def apply_track_stereo(buf: np.ndarray, gain_db: float, pan: float) -> np.ndarray:
    """对整轨 stereo 应用增益与声像。"""
    gain = 10.0 ** (gain_db / 20.0)
    l, r = pan_gain(pan)
    out = np.empty_like(buf)
    out[:, 0] = buf[:, 0] * gain * l
    out[:, 1] = buf[:, 1] * gain * r
    return out


def mix_tracks(engine: RenderEngine, score: Score, reverb: float = 0.0) -> np.ndarray:
    """渲染全部轨道并混音，返回 stereo (N,2)。reverb 为房间混响 wet 比例 (0..1)。"""
    rendered = []
    max_len = 0
    for track in score.tracks:
        buf = render_track(engine, score, track)
        if len(buf) == 0:
            continue
        buf = apply_track_stereo(buf, track.gain_db, track.pan)
        rendered.append(buf)
        max_len = max(max_len, len(buf))
    if not rendered:
        return np.zeros((0, 2), dtype=np.float32)
    master = np.zeros((max_len, 2), dtype=np.float32)
    for buf in rendered:
        master[: len(buf)] += buf
    if reverb > 0.0:
        master = RoomReverb(engine.project_sr).process(master, min(1.0, reverb))
    return envelope.soft_clip(master)
