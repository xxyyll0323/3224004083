# -*- coding: utf-8 -*-
"""核心相似度算法的单元测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from plagiarism.similarity import (  # noqa: E402
    count_ngrams,
    dice_overlap,
    explain,
    ngram_similarity,
)


class CountNgramsTest(unittest.TestCase):
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


class DiceOverlapTest(unittest.TestCase):
    def test_identical_counters_give_one(self) -> None:
        self.assertAlmostEqual(dice_overlap(count_ngrams("abcd", 2), count_ngrams("abcd", 2)), 1.0)

    def test_no_common_grams_gives_zero(self) -> None:
        self.assertAlmostEqual(dice_overlap(count_ngrams("abcd", 2), count_ngrams("wxyz", 2)), 0.0)

    def test_both_empty_gives_one(self) -> None:
        self.assertAlmostEqual(dice_overlap({}, {}), 1.0)

    def test_one_empty_gives_zero(self) -> None:
        self.assertAlmostEqual(dice_overlap(count_ngrams("abcd", 2), {}), 0.0)

    def test_hand_computed_multiplicity_case(self) -> None:
        # A："aaaa" → {"aa": 3}；B："aaaaaa" → {"aa": 5}
        # 2 × min(3,5) / (3+5) = 0.75
        left = count_ngrams("aaaa", 2)
        right = count_ngrams("aaaaaa", 2)
        self.assertAlmostEqual(dice_overlap(left, right), 0.75, places=12)

    def test_is_symmetric(self) -> None:
        left = count_ngrams("今天是星期天天气晴", 2)
        right = count_ngrams("今天是周天天气晴朗", 2)
        self.assertAlmostEqual(dice_overlap(left, right), dice_overlap(right, left), places=12)


class NgramSimilarityTest(unittest.TestCase):
    def test_identical_text_scores_exactly_one(self) -> None:
        text = "今天是星期天，天气晴，今天晚上我要去看电影。"
        self.assertEqual(ngram_similarity(text, text), 1.0)

    def test_both_empty_scores_one(self) -> None:
        self.assertEqual(ngram_similarity("", ""), 1.0)

    def test_one_empty_scores_zero(self) -> None:
        self.assertEqual(ngram_similarity("今天天气很好", ""), 0.0)
        self.assertEqual(ngram_similarity("", "今天天气很好"), 0.0)

    def test_fully_unrelated_text_stays_low(self) -> None:
        russian = "红树林生长在热带与亚热带海岸的潮间带上"
        software = "代码复用是软件工程中被反复讨论的核心议题之一"
        self.assertLess(ngram_similarity(russian, software), 0.15)

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
        for left, right in pairs:
            score = ngram_similarity(left, right)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_score_is_symmetric(self) -> None:
        left = "论文查重算法需要兼顾准确率与运行效率"
        right = "查重算法要同时考虑准确度与执行速度"
        self.assertAlmostEqual(ngram_similarity(left, right), ngram_similarity(right, left), places=12)


class ExplainTest(unittest.TestCase):
    def test_explain_reports_every_order(self) -> None:
        detail = explain("今天是星期天天气晴", "今天是周天天气晴朗")
        for order in (1, 2, 3, 4):
            self.assertIn(f"{order}-gram", detail)
            self.assertGreaterEqual(detail[f"{order}-gram"], 0.0)
            self.assertLessEqual(detail[f"{order}-gram"], 1.0)
        self.assertIn("最终相似度", detail)
        self.assertAlmostEqual(
            detail["最终相似度"], ngram_similarity("今天是星期天天气晴", "今天是周天天气晴朗"), places=12
        )


if __name__ == "__main__":
    unittest.main()
