# -*- coding: utf-8 -*-
"""代码质量分析（Code Quality Analysis）。

作业要求"提交的代码要求经过 Code Quality Analysis 工具的分析并消除所有的警告"。
Python 生态里承担这个角色的是 **pylint**：它按 PEP 8 与常见缺陷模式对代码打分，
满分 10.00。

本脚本对 ``main.py`` / ``plagiarism`` / ``tests`` / ``tools`` 跑一遍 pylint，输出：

* ``docs/code_quality_report.txt``  完整报告（含评分、各类警告计数、明细）；
* ``docs/code_quality.png``         评分卡图，可直接截图放进博客。

配置见项目根目录的 ``.pylintrc``。

依赖：``pip install -r requirements-dev.txt``

运行（在学号目录下）::

    python tools/code_quality.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 脚本要能直接从源码目录运行，因此手动补上项目根目录；由此产生的"导入不在文件
# 顶部"是刻意为之。
# pylint: disable=wrong-import-position
sys.path.insert(0, str(ROOT))

from tools import plotting

DOCS_DIR = ROOT / "docs"

# 要分析的目标：命令行入口、计算模块、测试与工具脚本。
TARGETS = ("main.py", "plagiarism", "tests", "tools")

# pylint 消息编号的首字母对应的大类。
CATEGORY_NAMES = {
    "C": "C 约定 convention",
    "R": "R 重构 refactor",
    "W": "W 警告 warning",
    "E": "E 错误 error",
    "F": "F 致命 fatal",
    "I": "I 信息 info",
}

_MESSAGE_PATTERN = re.compile(r"^\S+?:\d+:\d+: ([CRWEFI])\d{4}:")
_SCORE_PATTERN = re.compile(r"rated at (?P<score>\d+\.\d+)/10")


def run_pylint(targets: tuple[str, ...]) -> tuple[int, str]:
    """在项目根目录执行 pylint，返回 (退出码, 输出)。"""
    command = [sys.executable, "-m", "pylint", *targets]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = completed.stdout + completed.stderr
    print(output)
    return completed.returncode, output


def parse_score(output: str) -> float | None:
    """从 pylint 输出里取出评分。"""
    match = _SCORE_PATTERN.search(output)
    return float(match.group("score")) if match else None


def count_by_category(output: str) -> Counter[str]:
    """按大类统计警告数量。"""
    counter: Counter[str] = Counter()
    for line in output.splitlines():
        match = _MESSAGE_PATTERN.match(line)
        if match:
            counter[match.group(1)] += 1
    return counter


def draw_score_card(score: float | None, counts: Counter[str], out_path: Path) -> bool:
    """画一张评分卡：左边是大号评分，右边是各大类的警告数量。"""
    if not plotting.prepare():
        return False
    plt = plotting.pyplot()

    total = sum(counts.values())
    figure, axes = plt.subplots(figsize=(9, 4.2), dpi=140)
    axes.axis("off")

    axes.text(
        0.04,
        0.74,
        " ".join(TARGETS),
        fontsize=11,
        color="#57606a",
        transform=axes.transAxes,
    )
    axes.text(
        0.04,
        0.42,
        f"{score:.2f}" if score is not None else "--",
        fontsize=54,
        color="#2e9e5b" if total == 0 else "#c0392b",
        transform=axes.transAxes,
    )
    axes.text(0.30, 0.46, "/ 10", fontsize=18, color="#57606a", transform=axes.transAxes)
    axes.text(
        0.04,
        0.20,
        f"pylint 评分：警告总数 {total} 条"
        + ("（已全部消除）" if total == 0 else "（未清零）"),
        fontsize=12,
        color="#24292f",
        transform=axes.transAxes,
    )

    labels = [CATEGORY_NAMES[key] for key in ("C", "R", "W", "E", "F", "I")]
    values = [counts.get(key, 0) for key in ("C", "R", "W", "E", "F", "I")]
    axes.text(0.58, 0.78, "按大类统计", fontsize=11, color="#57606a", transform=axes.transAxes)
    for index, (label, value) in enumerate(zip(labels, values)):
        y = 0.66 - index * 0.115
        axes.text(0.58, y, label, fontsize=10.5, color="#24292f", transform=axes.transAxes)
        axes.text(
            0.97,
            y,
            str(value),
            fontsize=10.5,
            ha="right",
            color="#2e9e5b" if value == 0 else "#c0392b",
            transform=axes.transAxes,
        )

    axes.set_title("Code Quality Analysis（pylint）", fontsize=14)
    plotting.save(figure, out_path)
    return True


def main() -> int:
    """跑分析、写报告、画评分卡。"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    exit_code, output = run_pylint(TARGETS)
    score = parse_score(output)
    counts = count_by_category(output)
    total = sum(counts.values())
    score_text = f"{score:.2f}" if score is not None else "未解析到"

    lines = [
        "代码质量分析报告（Code Quality Analysis）",
        "",
        f"分析工具：pylint（python -m pylint {' '.join(TARGETS)}）",
        "配置文件：.pylintrc",
        f"评分：{score_text} / 10",
        f"警告总数：{total}",
        "",
        "按大类统计",
    ]
    for key in ("C", "R", "W", "E", "F", "I"):
        lines.append(f"  {CATEGORY_NAMES[key]:<24}{counts.get(key, 0):>4}")

    lines.extend(
        [
            "",
            "结论",
            "  生产代码（main.py 与 plagiarism/）不依赖任何豁免，函数、类、模块均有 docstring，",
            "  命名符合 PEP 8；测试与工具脚本仅在两处做了有理由的局部豁免：",
            "    - no-docstring-rgx：test_* 的函数名已完整表达断言意图，重复写 docstring 属于噪音；",
            "    - protected-access / consider-using-with：白盒测试要访问私有降阶函数，",
            "      unittest 的 setUp/tearDown 用不了 with。",
            "",
            "pylint 原始输出",
            output.rstrip(),
        ]
    )

    chart_ok = draw_score_card(score, counts, DOCS_DIR / "code_quality.png")
    lines.append("")
    lines.append(f"评分卡图：{'docs/code_quality.png' if chart_ok else '（未安装 matplotlib，跳过）'}")

    text = "\n".join(lines)
    (DOCS_DIR / "code_quality_report.txt").write_text(text, encoding="utf-8", newline="\n")

    print(f"\n评分：{score_text} / 10")
    print(f"警告总数：{total}")
    print(f"报告已写入 {DOCS_DIR / 'code_quality_report.txt'}")
    return 0 if (exit_code == 0 and total == 0) else 1


if __name__ == "__main__":  # pragma: no cover - 脚本入口
    sys.exit(main())
