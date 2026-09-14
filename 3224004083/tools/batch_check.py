# -*- coding: utf-8 -*-
"""批量查重工具（扩展功能）。

作业下发的样例除了 ``orig.txt``，通常还有 ``orig_add.txt``、
``orig_0.8_dis_1.txt`` … 十几个抄袭版文件。一个个手敲命令太慢，这个工具
一次把目录里的抄袭版文件全部算完，输出一张表并可选写出 CSV。

它**不改变** ``main.py`` 的命令行契约（永远是三个参数）——评测用的入口
仍然只有 ``main.py``，这个脚本是给人看的辅助工具。

用法::

    # 原文 + 一个目录（自动收集目录里除原文以外的 .txt）
    python tools/batch_check.py sample/orig.txt sample/

    # 原文 + 若干个抄袭版文件
    python tools/batch_check.py sample/orig.txt sample/orig_0.8_add.txt sample/orig_0.8_del.txt

    # 追加输出 CSV
    python tools/batch_check.py sample/orig.txt sample/ --csv result.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from plagiarism.errors import PaperCheckError  # noqa: E402
from plagiarism.similarity import compute_similarity  # noqa: E402

# 目录模式下要跳过的文件：原文本身、以及非正文的辅助文件。
SKIP_SUFFIXES = {".py", ".md", ".csv", ".json", ".png", ".jpg"}


def collect_candidates(original: Path, targets: list[str]) -> list[Path]:
    """把命令行给出的目标展开成待查重的文件列表。

    ``targets`` 里既可以是文件，也可以是目录；目录会被展开成其中的文本文件，
    并排除原文自身与非文本文件。
    """
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if not child.is_file():
                    continue
                if child.suffix.lower() in SKIP_SUFFIXES:
                    continue
                if child.resolve() == original.resolve():
                    continue
                files.append(child)
        elif path.is_file():
            files.append(path)
        else:
            print(f"警告：目标不存在，已跳过 -> {path}", file=sys.stderr)
    return files


def check_all(
    original: Path, candidates: list[Path]
) -> tuple[list[tuple[str, float | None, float]], list[tuple[str, str]]]:
    """逐个计算相似度。

    返回 ``(结果行, 失败原因)``；结果行为 ``(文件名, 相似度或 None, 耗时毫秒)``。
    失败原因单独返回，避免 stderr 与 stdout 交错导致表格被冲散。
    """
    rows: list[tuple[str, float | None, float]] = []
    failures: list[tuple[str, str]] = []
    for path in candidates:
        start = time.perf_counter()
        try:
            score: float | None = compute_similarity(str(original), str(path))
        except PaperCheckError as exc:
            score = None
            failures.append((path.name, str(exc)))
        elapsed = (time.perf_counter() - start) * 1000
        rows.append((path.name, score, elapsed))
    return rows, failures


def print_table(rows: list[tuple[str, float | None, float]]) -> None:
    """在终端打印结果表格。"""
    width = max((len(name) for name, _, _ in rows), default=8)
    print(f"{'抄袭版文件':<{width}}  {'相似度':>8}  {'耗时(ms)':>10}")
    print("-" * (width + 24))
    for name, score, elapsed in rows:
        shown = f"{score:.4f}" if score is not None else "无法计算"
        print(f"{name:<{width}}  {shown:>8}  {elapsed:>10.1f}")


def write_csv(rows: list[tuple[str, float | None, float]], path: Path) -> None:
    """把结果写成 CSV，方便丢进表格软件画图。"""
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "similarity", "elapsed_ms"])
        for name, score, elapsed in rows:
            writer.writerow([name, "" if score is None else f"{score:.4f}", f"{elapsed:.1f}"])


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。"""
    parser = argparse.ArgumentParser(description="批量论文查重（辅助工具）")
    parser.add_argument("original", help="原文文件路径")
    parser.add_argument("targets", nargs="+", help="抄袭版文件或所在目录，可以给多个")
    parser.add_argument("--csv", dest="csv_path", default=None, help="把结果同时写入该 CSV 文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    """脚本入口。"""
    args = build_parser().parse_args(argv)

    original = Path(args.original)
    if not original.is_file():
        print(f"原文文件不存在: {original}", file=sys.stderr)
        return 1

    candidates = collect_candidates(original, args.targets)
    if not candidates:
        print("没有找到需要查重的文件。", file=sys.stderr)
        return 1

    print(f"原文：{original.name}")
    print(f"待查重文件 {len(candidates)} 个\n")
    rows, failures = check_all(original, candidates)
    print_table(rows)

    for name, reason in failures:
        print(f"\n[{name}] 无法计算：{reason}")

    if rows:
        scored = [score for _, score, _ in rows if score is not None]
        if scored:
            print(f"\n相似度区间：{min(scored):.4f} ~ {max(scored):.4f}")
        slowest = max(rows, key=lambda item: item[2])
        print(f"最慢的一个：{slowest[0]}  {slowest[2]:.1f} ms")

    if args.csv_path:
        csv_path = Path(args.csv_path)
        write_csv(rows, csv_path)
        print(f"\n结果已写入 {csv_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover - 脚本入口
    sys.exit(main())
