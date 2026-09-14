# -*- coding: utf-8 -*-
"""对 sample/ 目录下的全部样例跑一遍查重，输出结果表格。

用途：
1. 快速验收程序在各类修改（增、删、乱序、近义替换、无关、空）下的表现；
2. 为实验报告提供可直接引用的分数表。

运行::

    python tools/run_samples.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from plagiarism.errors import PaperCheckError  # noqa: E402
from plagiarism.similarity import compute_similarity  # noqa: E402

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


def main() -> int:
    original = SAMPLE_DIR / "orig.txt"
    if not original.exists():
        print("未找到 sample/orig.txt，请先运行 python tools/make_samples.py")
        return 1

    print(f"{'样例文件':<24}{'相似度':>8}{'耗时(ms)':>12}  说明")
    print("-" * 74)

    failures: list[str] = []
    for name, low, high, note in CASES:
        path = SAMPLE_DIR / name
        if not path.exists():
            print(f"{name:<24}{'--':>8}{'--':>12}  文件缺失")
            failures.append(name)
            continue
        start = time.perf_counter()
        score = compute_similarity(str(original), str(path))
        elapsed = (time.perf_counter() - start) * 1000
        flag = "OK " if low <= score <= high else "!! "
        if not (low <= score <= high):
            failures.append(name)
        print(f"{flag}{name:<21}{score:>8.4f}{elapsed:>12.1f}  {note}")

    # 空文件应当在异常处理路径上被拦住，而不是给出一个分数。
    for name in ("orig_empty.txt", "orig_punct_only.txt"):
        try:
            compute_similarity(str(original), str(SAMPLE_DIR / name))
        except PaperCheckError as exc:
            print(f"OK {name:<21}{'异常':>8}{'--':>12}  {exc}")
        else:
            failures.append(name)
            print(f"!! {name:<21}{'未拦截':>8}{'--':>12}  应当抛出空文本异常")

    print("-" * 74)
    if failures:
        print(f"有 {len(failures)} 个样例不在期望区间内: {', '.join(failures)}")
    else:
        print("全部样例均在期望区间内。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
