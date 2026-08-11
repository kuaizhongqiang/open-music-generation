"""轮次（round-robin）游标：连续同音不重复样本，避免"机关枪效果"。

进程内存态即可满足 P1；P3 若要跨会话不重复，把游标放进 project JSON。
"""
from __future__ import annotations


class RoundRobin:
    def __init__(self) -> None:
        self._cursor: dict[tuple, int] = {}

    def reset(self) -> None:
        self._cursor.clear()

    def next(self, key: tuple, count: int) -> int:
        """count 个候选里取下一个索引。count<=1 恒返回 0。"""
        if count <= 1:
            return 0
        i = self._cursor.get(key, 0)
        self._cursor[key] = (i + 1) % count
        return i
