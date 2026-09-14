# -*- coding: utf-8 -*-
"""论文查重的核心算法。

思路：中文没有天然的分词边界，于是用"相邻两个字符"组成的片段当文章的指纹，
统计每个指纹在文中出现的次数（多重集，重复片段不会被抹平），再用 Dice 系数
衡量两份指纹表的重合程度：

    overlap = Σ_g min(A(g), B(g))
    Dice    = 2 × overlap / (|A| + |B|)

结果天然落在 [0,1]：完全相同为 1，完全不重合为 0。
"""

from __future__ import annotations

from collections import Counter

from .normalize import normalize
from .reader import read_text

# 特征片段的长度（字符数）。
BIGRAM = 2


def count_bigrams(text: str) -> Counter[str]:
    """统计文本中相邻两个字符组成的片段出现次数。"""
    length = len(text)
    if length < BIGRAM:
        return Counter()
    return Counter(text[i : i + BIGRAM] for i in range(length - BIGRAM + 1))


def dice_overlap(left: Counter[str], right: Counter[str]) -> float:
    """两个多重集之间的 Dice 系数，返回值在 [0,1]。"""
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0

    total = sum(left.values()) + sum(right.values())
    if total == 0:
        return 1.0

    if len(left) > len(right):
        left, right = right, left

    intersection = 0
    for gram, count in left.items():
        other = right.get(gram)
        if other is not None:
            intersection += count if count < other else other
    return 2.0 * intersection / total


def compute_similarity(original_path: str, copied_path: str) -> float:
    """按文件路径计算重复率，供命令行入口调用。"""
    original = normalize(read_text(original_path))
    copied = normalize(read_text(copied_path))

    if not original and not copied:
        return 1.0
    if not original or not copied:
        return 0.0

    return dice_overlap(count_bigrams(original), count_bigrams(copied))
