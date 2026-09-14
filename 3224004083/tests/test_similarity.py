# -*- coding: utf-8 -*-
"""核心相似度算法的单元测试。

运行方式（在学号目录下）::

    python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import math
import unittest

from plagiarism.similarity import count_ngrams, cosine_similarity, explain, ngram_similarity


class CountNgramsTest(unittest.TestCase):
    """特征切片与频次统计。"""

    def test_counts_adjacent_pairs(self) -> None:
        self.assertEqual(count_ngrams("abcd", 2), {"ab": 1, "bc": 1, "cd": 1})

    def test_single_order_uses_fast_path(self) -> None:
        self.assertEqual(count_ngrams("aba", 1), {"a": 2, "b": 1})

    def test_keeps_multiplicity(self) -> None:
        # "aa" 在 "aaaa" 中出现 3 次，必须保留频次而不是只记录"是否出现"。
        self.assertEqual(count_ngrams("aaaa", 2), {"aa": 3})

    def test_returns_empty_when_text_shorter_than_n(self) -> None:
        self.assertEqual(count_ngrams("ab", 4), {})

    def test_rejects_non_positive_n(self) -> None:
        with self.assertRaises(ValueError):
            count_ngrams("abc", 0)


class CosineOverlapTest(unittest.TestCase):
    """余弦相似度的边界与可手算数值。"""

    def test_identical_counters_give_one(self) -> None:
        grams = count_ngrams("abcd", 2)
        self.assertAlmostEqual(cosine_similarity(grams, grams), 1.0)

    def test_no_common_grams_gives_zero(self) -> None:
        grams_a = count_ngrams("abcd", 2)
        grams_b = count_ngrams("wxyz", 2)
        self.assertAlmostEqual(cosine_similarity(grams_a, grams_b), 0.0)

    def test_both_empty_gives_one(self) -> None:
        self.assertAlmostEqual(cosine_similarity({}, {}), 1.0)

    def test_one_empty_gives_zero(self) -> None:
        self.assertAlmostEqual(cosine_similarity(count_ngrams("abcd", 2), {}), 0.0)

    def test_hand_computed_multiplicity_case(self) -> None:
        # 两个向量的分量可以完全手算出来：
        #   A = "甲乙甲乙" -> {"甲乙": 2, "乙甲": 1}   |A|² = 4 + 1       = 5
        #   B = "甲乙乙甲" -> {"甲乙": 1, "乙乙": 1, "乙甲": 1}   |B|² = 1+1+1 = 3
        #   点积 = 2×1 + 1×1 = 3
        #   cos  = 3 / (√5 × √3) = 3 / √15 ≈ 0.774597
        grams_a = count_ngrams("甲乙甲乙", 2)
        grams_b = count_ngrams("甲乙乙甲", 2)
        self.assertAlmostEqual(cosine_similarity(grams_a, grams_b), 3 / math.sqrt(15), places=12)

    def test_single_dimension_vector_scores_one(self) -> None:
        # 只有一个维度时余弦恒为 1——这正是余弦"对长度不敏感"的体现，
        # 也就是说单纯把原文复制几遍不会降低得分。这是一个已知取舍，
        # 在多阶加权里由更长的 n-gram 与超长文本降阶来平衡。
        grams_a = count_ngrams("aaaa", 2)  # {"aa": 3}
        grams_b = count_ngrams("aaaaaa", 2)  # {"aa": 5}
        self.assertAlmostEqual(cosine_similarity(grams_a, grams_b), 1.0, places=12)

    def test_is_symmetric(self) -> None:
        grams_a = count_ngrams("今天是星期天天气晴", 2)
        grams_b = count_ngrams("今天是周天天气晴朗", 2)
        forward = cosine_similarity(grams_a, grams_b)
        backward = cosine_similarity(grams_b, grams_a)
        self.assertAlmostEqual(forward, backward, places=12)


class NgramSimilarityTest(unittest.TestCase):
    """多阶加权相似度在各类改写下的表现。"""

    def test_identical_text_scores_exactly_one(self) -> None:
        text = "今天是星期天，天气晴，今天晚上我要去看电影。"
        self.assertEqual(ngram_similarity(text, text), 1.0)

    def test_both_empty_scores_one(self) -> None:
        self.assertEqual(ngram_similarity("", ""), 1.0)

    def test_one_empty_scores_zero(self) -> None:
        self.assertEqual(ngram_similarity("今天天气很好", ""), 0.0)
        self.assertEqual(ngram_similarity("", "今天天气很好"), 0.0)

    def test_fully_unrelated_text_stays_low(self) -> None:
        red_mangrove = "红树林生长在热带与亚热带海岸的潮间带上"
        software = "代码复用是软件工程中被反复讨论的核心议题之一"
        self.assertLess(ngram_similarity(red_mangrove, software), 0.15)

    def test_insertion_keeps_score_high(self) -> None:
        base = "代码复用能够缩短开发周期并且让经过验证的逻辑被更多项目使用"
        longer = base + "同时也要控制复用带来的耦合风险"
        score = ngram_similarity(base, longer)
        self.assertGreater(score, 0.6)
        self.assertLess(score, 1.0)

    def test_deletion_keeps_score_high(self) -> None:
        base = "代码复用能够缩短开发周期并且让经过验证的逻辑被更多项目使用"
        shorter = "代码复用能够缩短开发周期"
        score = ngram_similarity(base, shorter)
        self.assertGreater(score, 0.5)
        self.assertLess(score, 1.0)

    def test_paragraph_reordering_keeps_score_high(self) -> None:
        # 段落顺序变化不应该让相似度塌掉，这是作业要求的显式场景。
        first = "第一段描述问题背景与已有工作。"
        second = "第二段给出算法设计与实现细节。"
        third = "第三段展示实验结果并分析误差来源。"
        original = first + second + third
        shuffled = third + first + second
        self.assertGreater(ngram_similarity(original, shuffled), 0.9)

    def test_synonym_rewrite_keeps_high_but_below_one(self) -> None:
        original = "今天是星期天，天气晴，今天晚上我要去看电影。"
        copied = "今天是周天，天气晴朗，我晚上要去看电影。"
        score = ngram_similarity(original, copied)
        self.assertGreater(score, 0.2)
        self.assertLess(score, 1.0)

    def test_single_character_uses_first_order(self) -> None:
        self.assertEqual(ngram_similarity("a", "a"), 1.0)
        self.assertEqual(ngram_similarity("a", "b"), 0.0)

    def test_score_always_within_unit_interval(self) -> None:
        pairs = [
            ("", ""),
            ("a", ""),
            ("代码复用", "代码复用"),
            ("代码复用", "代码重用"),
            ("abc", "xyz"),
            ("今天是星期天天气晴", "今天天气很好我们出去玩"),
        ]
        for original, copied in pairs:
            score = ngram_similarity(original, copied)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_score_is_symmetric(self) -> None:
        first = "论文查重算法需要兼顾准确率与运行效率"
        second = "查重算法要同时考虑准确度与执行速度"
        forward = ngram_similarity(first, second)
        backward = ngram_similarity(second, first)
        self.assertAlmostEqual(forward, backward, places=12)


class ExplainTest(unittest.TestCase):
    """逐阶明细接口。"""

    def test_explain_reports_every_order(self) -> None:
        original = "今天是星期天天气晴"
        copied = "今天是周天天气晴朗"
        detail = explain(original, copied)
        for order in (1, 2, 3, 4):
            self.assertIn(f"{order}-gram", detail)
            self.assertGreaterEqual(detail[f"{order}-gram"], 0.0)
            self.assertLessEqual(detail[f"{order}-gram"], 1.0)
        self.assertIn("最终相似度", detail)
        self.assertAlmostEqual(
            detail["最终相似度"], ngram_similarity(original, copied), places=12
        )


if __name__ == "__main__":
    unittest.main()
