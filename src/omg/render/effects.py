"""空间感效果：合成冲激响应的卷积混响（纯 numpy FFT，无需 scipy）。

IR = 指数衰减的随机噪声（每声道独立），卷积得到"房间感"。
"""
from __future__ import annotations

import numpy as np


def make_room_ir(sr: int, length_s: float = 1.5, tau: float = 0.35,
                 seed: int = 0) -> np.ndarray:
    """生成 stereo 房间 IR，(N, 2)，已归一化。"""
    rng = np.random.default_rng(seed)
    n = int(sr * length_s)
    t = np.arange(n) / sr
    decay = np.exp(-t / tau)
    left = rng.standard_normal(n) * decay
    right = rng.standard_normal(n) * decay
    # 高切：简单一阶平滑，去低频"轰隆"
    for ch in (left, right):
        for i in range(1, n):
            ch[i] += 0.4 * ch[i - 1]
        ch /= np.max(np.abs(ch)) + 1e-9
    return np.stack([left, right], axis=1)


def fft_convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """对每个声道做 FFT 卷积，返回全长 len(x)+len(ir)-1。x:(N,ch) ir:(M,ch)。"""
    n = len(x) + len(ir) - 1
    out = np.zeros((n, x.shape[1]), dtype=np.float64)
    for ch in range(x.shape[1]):
        X = np.fft.rfft(x[:, ch], n)
        H = np.fft.rfft(ir[:, ch], n)
        out[:, ch] = np.fft.irfft(X * H, n)
    return out


class RoomReverb:
    """可复用的房间混响：IR 生成一次，process 时按 wet 比例混合。"""

    def __init__(self, sr: int, length_s: float = 1.5, tau: float = 0.35) -> None:
        self._ir = make_room_ir(sr, length_s, tau)

    def process(self, x: np.ndarray, wet: float = 0.25) -> np.ndarray:
        """x: stereo (N,2)。返回全长（含混响尾音）的 dry+wet 混合。"""
        if wet <= 0.0:
            return x
        conv = fft_convolve(x, self._ir)               # len = N + M - 1
        out = conv * wet
        out[: len(x)] += x * (1.0 - wet)
        return out
