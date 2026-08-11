"""变调（重采样采样器语义）。

这是重采样采样器：变调 = 播放速率变化（共振峰随动，像磁带变速）。
因此排除相位声码器（改变共振峰、音色走样）。默认用 libsamplerate(sinc)，
numpy 线性回退用于无 wheel/离线环境，并与 sinc 后端做数值对照。
"""
from __future__ import annotations

import numpy as np


def compute_ratio(semitones: float, sample_sr: int, project_sr: int) -> float:
    """重采样比（输出/输入样本数）。升调 k 半音 → ratio=2^(-k/12)，同时合并采样率转换。"""
    return (project_sr / sample_sr) * (2 ** (-semitones / 12))


def _resample_samplerate(data: np.ndarray, ratio: float) -> np.ndarray:
    import samplerate as sr

    return sr.resample(data.astype(np.float32), ratio, converter_type="sinc_best")


def _resample_numpy(data: np.ndarray, ratio: float) -> np.ndarray:
    n = len(data)
    n_out = max(1, int(round(n * ratio)))
    src = np.arange(n, dtype=np.float64)
    out = np.interp(np.arange(n_out, dtype=np.float64) / ratio, src, data.astype(np.float64))
    return out.astype(np.float32)


def pitch_shift(
    data: np.ndarray,
    sample_sr: int,
    project_sr: int,
    semitones: float,
    backend: str = "samplerate",
) -> np.ndarray:
    """把 mono 样本变调并转采样率，返回 project_sr 下的 float32 buffer。

    data 为任意 float 数组；semitones>0 升调。
    """
    ratio = compute_ratio(semitones, sample_sr, project_sr)
    if abs(ratio - 1.0) < 1e-9:
        return data.astype(np.float32)
    if backend == "numpy":
        return _resample_numpy(data, ratio)
    try:
        return _resample_samplerate(data, ratio)
    except Exception:
        # 无 libsamplerate 环境时回退
        return _resample_numpy(data, ratio)
