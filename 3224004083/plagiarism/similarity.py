# -*- coding: utf-8 -*-
"""核心相似度算法：字符 n-gram 多重集 Dice 加权融合。

设计要点
--------
1. **字符 n-gram**：中文没有天然分词边界，不引入任何外部分词词典或模型，
   直接把规范化后的字符流切成相邻 n 个字符的片段（n-gram）。
   一个 n-gram 就是文章的一个"指纹片段"。
2. **多重集而不是普通集合**：``aaaa`` 里的 ``aa`` 出现 3 次，频次要参与计算，
   这样重复段落的权重不会被抹平。
3. **Dice 系数**：设两个文本中片段 g 的频次分别为 A(g)、B(g)，则

       overlap = Σ_g min(A(g), B(g))
       Dice    = 2 × overlap / (|A| + |B|)

   完全相同 → 1，完全不重合 → 0，天然落在 [0, 1] 内。
4. **多阶融合**：短片段（n=1,2）对局部改写敏感，长片段（n=3,4）更能体现
   稳定内容、对无关文本更有区分度，因此按 0.10/0.20/0.35/0.35 加权。
5. **与顺序无关**：n-gram 频次是全文统计量，所以"把段落顺序打乱"不会让
   相似度塌掉——这正是作业要求里"能处理段落顺序发生变化的相似内容"。
"""

from __future__ import annotations

from collections import Counter

from .errors import EmptyTextError
from .normalize import normalize
from .reader import read_text

# 各阶 n-gram 的权重。长片段更能区分不同文章，所以权重更高。
NGRAM_WEIGHTS: dict[int, float] = {1: 0.10, 2: 0.20, 3: 0.35, 4: 0.35}

# 文本规模上限：超过后主动降低阶数，保证内存与运行时间可控。
_SKIP_N4_THRESHOLD = 800_000
_ONLY_MIDDLE_ORDER_THRESHOLD = 2_000_000

# 规范化后有效字符数少于该值时，退化为按单字符比较。
_MIN_LENGTH_FOR_NGRAM = 2


def count_ngrams(text: str, n: int) -> Counter[str]:
    """统计 ``text`` 中相邻 n 字符片段的出现次数。"""
    if n <= 0:
        raise ValueError("n 必须为正整数")
    length = len(text)
    if length < n:
        return Counter()
    if n == 1:
        # 单字符是最常见的一阶特征，直接用 C 层实现，跳过生成器与切片。
        return Counter(text)
    return Counter(text[i : i + n] for i in range(length - n + 1))


def dice_overlap(left: Counter[str], right: Counter[str]) -> float:
    """两个片段频次表的多重集 Dice 系数，取值 [0, 1]。"""
    left_total = sum(left.values())
    right_total = sum(right.values())
    if left_total == 0 and right_total == 0:
        return 1.0
    if left_total == 0 or right_total == 0:
        return 0.0

    if len(left) > len(right):
        left, right = right, left

    overlap = 0
    get = right.get
    for gram, count in left.items():
        other = get(gram)
        if other is not None:
            overlap += count if count < other else other

    return 2.0 * overlap / (left_total + right_total)


def _select_orders(max_length: int) -> list[int]:
    """根据文本规模挑选参与计算的 n 值，防止超长文本耗尽内存。"""
    if max_length < _MIN_LENGTH_FOR_NGRAM:
        return [1]
    if max_length > _ONLY_MIDDLE_ORDER_THRESHOLD:
        return [2, 3]
    if max_length > _SKIP_N4_THRESHOLD:
        return [1, 2, 3]
    return sorted(NGRAM_WEIGHTS)


def ngram_similarity(original: str, copied: str) -> float:
    """对规范化后的两段文本计算 n-gram Dice 加权相似度。"""
    if original == copied:
        return 1.0
    if not original or not copied:
        return 0.0

    orders = _select_orders(max(len(original), len(copied)))
    weights = {order: NGRAM_WEIGHTS.get(order, 1.0) for order in orders}
    weight_sum = sum(weights.values())

    score = 0.0
    for order in orders:
        left = count_ngrams(original, order)
        right = count_ngrams(copied, order)
        score += weights[order] * dice_overlap(left, right)

    return score / weight_sum


def explain(original: str, copied: str) -> dict[str, float]:
    """给出各阶 n-gram 的得分明细，供测试与实验报告使用。"""
    detail = {"原始长度": float(len(original)), "抄袭版长度": float(len(copied))}
    for order in _select_orders(max(len(original), len(copied))):
        detail[f"{order}-gram"] = dice_overlap(
            count_ngrams(original, order), count_ngrams(copied, order)
        )
    detail["最终相似度"] = ngram_similarity(original, copied)
    return detail


def compute_similarity(original_path: str, copied_path: str) -> float:
    """按文件路径计算重复率，供命令行入口调用。"""
    original = normalize(read_text(original_path))
    copied = normalize(read_text(copied_path))

    if not original and not copied:
        raise EmptyTextError("两个输入文件都没有可比较的有效文本")
    if not original:
        raise EmptyTextError(f"原文文件没有可比较的有效文本: {original_path}")
    if not copied:
        raise EmptyTextError(f"抄袭版文件没有可比较的有效文本: {copied_path}")

    return ngram_similarity(original, copied)
