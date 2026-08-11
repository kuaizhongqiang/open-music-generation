"""样本解码 LRU 缓存：按路径缓存 mono float64 缓冲，容量上限按字节估算。"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import soundfile as sf

_DEFAULT_MAX_BYTES = 512 * 1024 * 1024  # 512MB


class SampleCache:
    def __init__(self, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        self._max_bytes = max_bytes
        self._cache: OrderedDict[Path, tuple[np.ndarray, int]] = OrderedDict()
        self._bytes = 0

    def get(self, path: Path) -> tuple[np.ndarray, int]:
        """读取样本 → (mono float64, sample_rate)。LRU 缓存解码结果。"""
        if path in self._cache:
            self._cache.move_to_end(path)
            return self._cache[path]
        data, sr = sf.read(str(path), dtype="float64", always_2d=False)
        if data.ndim == 2:
            data = data.mean(axis=1)
        item = (data, int(sr))
        nbytes = data.nbytes
        self._cache[path] = item
        self._bytes += nbytes
        while self._bytes > self._max_bytes and len(self._cache) > 1:
            _, evicted = self._cache.popitem(last=False)
            self._bytes -= evicted[0].nbytes
        return item
