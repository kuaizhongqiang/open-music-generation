"""包络：P1 最小集（attack 消爆音、release 截断渐出）。P3 技法精细化从这里扩展。"""
from __future__ import annotations

import numpy as np

ATTACK_S = 0.008
RELEASE_S = 0.05


def attack(sig: np.ndarray, sr: int, attack_s: float = ATTACK_S) -> np.ndarray:
    n = min(len(sig), max(1, int(attack_s * sr)))
    if n == 0 or len(sig) == 0:
        return sig
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float64)
    sig = sig.copy()
    sig[:n] *= ramp
    return sig


def release(sig: np.ndarray, sr: int, release_s: float = RELEASE_S) -> np.ndarray:
    n = min(len(sig), max(1, int(release_s * sr)))
    if n == 0 or len(sig) == 0:
        return sig
    ramp = np.linspace(1.0, 0.0, n, dtype=np.float64)
    sig = sig.copy()
    sig[-n:] *= ramp
    return sig


def soft_clip(sig: np.ndarray, ceiling: float = 0.95) -> np.ndarray:
    """简单 tanh 软限幅保 headroom。"""
    peak = float(np.max(np.abs(sig))) if sig.size else 0.0
    if peak == 0.0:
        return sig
    sig = sig / peak
    out = np.tanh(sig * 2.0) / np.tanh(2.0)
    return (out * ceiling).astype(np.float32)
