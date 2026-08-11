"""整轨渲染：音符按拍排序 → 逐音符放置 → 归一化 → stereo 输出。"""
from __future__ import annotations

import numpy as np

from ..score.model import Score, Track
from . import envelope
from .engine import RenderEngine


def _beat_to_seconds(score: Score) -> float:
    return 60.0 / score.tempo_bpm


def render_track(engine: RenderEngine, score: Score, track: Track) -> np.ndarray:
    """渲染单轨为 stereo float32 (N, 2)，project_sr 采样率。空轨返回空。"""
    beat_s = _beat_to_seconds(score)
    notes = sorted(track.notes, key=lambda n: n.start_beat)
    if not notes:
        return np.zeros((0, 2), dtype=np.float32)

    offset_beat = min(0.0, min(n.start_beat for n in notes))
    end_beat = max(n.start_beat + n.duration for n in notes)
    total_len = int((end_beat - offset_beat) * beat_s * engine.project_sr) + 1
    buf = np.zeros(total_len, dtype=np.float32)

    for n in notes:
        start_i = int((n.start_beat - offset_beat) * beat_s * engine.project_sr)
        sig = engine.render_note(
            track.instrument, n.pitch, n.velocity, n.technique, n.duration * beat_s
        )
        if len(sig) == 0:
            continue
        end_i = min(start_i + len(sig), total_len)
        buf[start_i:end_i] += sig[: end_i - start_i]

    buf = envelope.soft_clip(buf)
    return np.stack([buf, buf], axis=-1)  # mono → stereo
