# -*- coding: utf-8 -*-
"""对 sample/ 目录下的全部样例跑一遍查重，输出结果表格。

用途：

1. 快速验收程序在各类修改（增、删、乱序、近义替换、无关、空）下的表现；
2. 为实验报告提供可直接引用的分数表。

运行（在学号目录下）::

    python tools/run_samples.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 这个脚本要能从源码目录里直接运行，不需要先 pip install，所以手动把项目根目录
# 加进搜索路径；由此产生的"导入不在文件顶部"是刻意为之。
# pylint: disable=wrong-import-position
sys.path.insert(0, str(ROOT))

from plagiarism.errors import PaperCheckError
from plagiarism.similarity import compute_similarity

SAMPLE_DIR = ROOT / "sample"

# (文件名, 期望区间下限, 期望区间上限, 说明)
CASES = [
    ("orig_1.0.txt", 0.99, 1.00, "与原文完全一致"),
    ("orig_1.0_html.txt", 0.95, 1.00, "正文相同但夹带 HTML 样板"),
    ("orig_0.8_add.txt", 0.60, 0.95, "插入新句子（增）"),
    ("orig_0.8_del.txt", 0.70, 0.95, "删除部分句子（删）"),
    ("orig_0.8_del_gbk.txt", 0.70, 0.95, "删改版且为 GB18030 编码"),
    ("orig_0.8_syn.txt", 0.60, 1.00, "术语替换为近义词（改）"),
    ("orig_0.8_dis_1.txt", 0.80, 1.00, "段内句子局部旋转（乱序）"),
    ("orig_0.8_dis_2.txt", 0.80, 1.00, "全部句子整体打乱（乱序）"),
    ("orig_0.8_dis_3.txt", 0.50, 1.00, "句子内部分句顺序颠倒（乱序）"),
    ("orig_0.0.txt", 0.00, 0.15, "完全不同主题"),
]

# 这两个文件应当被异常处理路径拦住，而不是给出一个没有意义的分数。
EXPECTED_ERROR_CASES = ("orig_empty.txt", "orig_punct_only.txt")


def _check_expectation_failures(original: Path) -> tuple[list[str], list[str]]:
    """跑完所有正常样例，返回 (输出行, 未达预期的样例名)。"""
    lines: list[str] = []
    failures: list[str] = []
    for name, low, high, note in CASES:
        path = SAMPLE_DIR / name
        if not path.exists():
            lines.append(f"-- {name:<21}{'--':>8}{'--':>12}  文件缺失")
            failures.append(name)
            continue

        start = time.perf_counter()
        score = compute_similarity(str(original), str(path))
        elapsed = (time.perf_counter() - start) * 1000

        within_expectation = low <= score <= high
        if not within_expectation:
            failures.append(name)
        flag = "OK " if within_expectation else "!! "
        lines.append(f"{flag}{name:<21}{score:>8.4f}{elapsed:>12.1f}  {note}")
    return lines, failures


def _check_error_cases(original: Path) -> tuple[list[str], list[str]]:
    """确认空文件与纯标点文件被正确拦截。"""
    lines: list[str] = []
    failures: list[str] = []
    for name in EXPECTED_ERROR_CASES:
        try:
            compute_similarity(str(original), str(SAMPLE_DIR / name))
        except PaperCheckError as exc:
            lines.append(f"OK {name:<21}{'异常':>8}{'--':>12}  {exc}")
        else:
            failures.append(name)
            lines.append(f"!! {name:<21}{'未拦截':>8}{'--':>12}  应当抛出空文本异常")
    return lines, failures


def main() -> int:
    """跑完全部样例并打印分数表。"""
    original = SAMPLE_DIR / "orig.txt"
    if not original.exists():
        print("未找到 sample/orig.txt，请先运行 python tools/make_samples.py")
        return 1

    print(f"{'样例文件':<24}{'相似度':>8}{'耗时(ms)':>12}  说明")
    print("-" * 74)

    normal_lines, failures = _check_expectation_failures(original)
    for line in normal_lines:
        print(line)

    error_lines, error_failures = _check_error_cases(original)
    for line in error_lines:
        print(line)
    failures.extend(error_failures)

    print("-" * 74)
    if failures:
        print(f"有 {len(failures)} 个样例不符合预期: {', '.join(failures)}")
        return 1
    print("全部样例均符合预期。")
    return 0


if __name__ == "__main__":  # pragma: no cover - 脚本入口
    sys.exit(main())
