# -*- coding: utf-8 -*-
"""一键运行单元测试并生成覆盖率报告。

输出：

* 终端上的逐文件覆盖率表；
* ``docs/coverage_report.txt``  文字版报告（可直接贴进博客）；
* ``docs/coverage_chart.png``   逐文件覆盖率柱状图（博客里的"覆盖率截图"）；
* ``docs/coverage_html/index.html``  可点开的 HTML 明细报告。

依赖 ``coverage`` 与 ``matplotlib``：``pip install -r requirements-dev.txt``

运行（在学号目录下）::

    python tools/test_coverage.py
"""

from __future__ import annotations

import dataclasses
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 脚本要能直接从源码目录运行，因此手动补上项目根目录；由此产生的"导入不在文件
# 顶部"是刻意为之。
# pylint: disable=wrong-import-position
sys.path.insert(0, str(ROOT))

from tools import plotting

try:
    import coverage
except ImportError:  # pragma: no cover - 取决于本机是否安装 coverage
    coverage = None  # type: ignore[assignment]

DOCS_DIR = ROOT / "docs"
TESTS_DIR = ROOT / "tests"

# 统计整个学号目录，但排除测试脚本、辅助工具与样例数据。
SOURCE = [str(ROOT)]
OMIT = [str(TESTS_DIR / "*"), str(ROOT / "tools" / "*"), str(DOCS_DIR / "*")]

# 覆盖率柱状图的颜色阈值（低于这两个值的柱子标红，便于一眼看出缺口）。
GOOD_RATIO = 90.0
FAIR_RATIO = 75.0


def run_tests() -> unittest.result.TestResult:
    """运行 tests/ 目录下的全部用例。"""
    print("正在运行单元测试 ...\n")
    suite = unittest.TestLoader().discover(str(TESTS_DIR), top_level_dir=str(ROOT))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=1)
    return runner.run(suite)


def collect_per_file(coverage_instance) -> list[tuple[str, int, int]]:
    """返回 [(文件标签, 已覆盖语句数, 语句总数)]。"""
    rows: list[tuple[str, int, int]] = []
    for filename in sorted(coverage_instance.get_data().measured_files()):
        path = Path(filename)
        if "plagiarism" not in path.parts and path.name != "main.py":
            continue
        analysis = coverage_instance.analysis2(filename)
        statements = analysis[1]
        missing = analysis[3]
        label = path.name if path.name == "main.py" else f"plagiarism/{path.name}"
        rows.append((label, len(statements) - len(missing), len(statements)))
    rows.sort(key=lambda item: item[0])
    return rows


def _bar_color(percent: float) -> str:
    """按覆盖率高低给出柱子的颜色：绿=达标、黄=及格、红=有缺口。"""
    if percent >= GOOD_RATIO:
        return "#2e9e5b"
    if percent >= FAIR_RATIO:
        return "#e8a33d"
    return "#c0392b"


def draw_chart(rows: list[tuple[str, int, int]], out_path: Path) -> bool:
    """画逐文件覆盖率柱状图。"""
    if not plotting.prepare():
        return False
    plt = plotting.pyplot()

    labels = [row[0] for row in rows]
    percents = [row[1] / row[2] * 100 if row[2] else 100.0 for row in rows]

    figure, axes = plt.subplots(figsize=(9, 4.6), dpi=140)
    rectangles = axes.bar(
        labels,
        percents,
        width=0.55,
        color=[_bar_color(percent) for percent in percents],
    )
    for rectangle, row, percent in zip(rectangles, rows, percents):
        axes.text(
            rectangle.get_x() + rectangle.get_width() / 2,
            percent + 1.0,
            f"{percent:.1f}%\n{row[1]}/{row[2]}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    axes.set_ylim(0, 118)
    axes.set_ylabel("语句覆盖率（%）")
    axes.set_title("单元测试语句覆盖率（unittest + coverage）")
    axes.grid(axis="y", linestyle="--", alpha=0.35)
    plt.setp(axes.get_xticklabels(), rotation=18, ha="right")
    plotting.save(figure, out_path)
    return True


@dataclasses.dataclass
class CoverageSummary:
    """一次覆盖率统计的全部结果。"""

    table: str
    rows: list[tuple[str, int, int]]
    result: unittest.result.TestResult
    total_percent: float
    chart_ok: bool
    html_note: str


def _report_lines(summary: CoverageSummary) -> list[str]:
    """拼装文字版报告。"""
    lines = ["单元测试与覆盖率报告", "", summary.table.rstrip(), "", "逐文件覆盖情况"]
    for label, covered, total in summary.rows:
        percent = covered / total * 100 if total else 100.0
        lines.append(f"  {label:<28}{covered:>5}/{total:<5}{percent:>10.1f}%")
    chart_note = "docs/coverage_chart.png" if summary.chart_ok else "（未安装 matplotlib，跳过）"
    lines.extend(
        [
            "",
            f"用例总数：{summary.result.testsRun}",
            f"失败：{len(summary.result.failures)}    错误：{len(summary.result.errors)}",
            f"总体语句覆盖率：{summary.total_percent:.1f}%",
            f"覆盖率柱状图：{chart_note}",
            summary.html_note,
        ]
    )
    return lines


def main() -> int:
    """运行测试、统计覆盖率并输出报告。"""
    if coverage is None:
        print("缺少 coverage，请先执行：pip install -r requirements-dev.txt")
        return 1

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 数据文件放进临时目录：既不污染仓库，也避免重复运行时需要删除已有文件。
    workdir = Path(tempfile.mkdtemp(prefix="papercheck_cov_"))
    cov = coverage.Coverage(data_file=str(workdir / "covdata"), source=SOURCE, omit=OMIT)

    cov.start()
    result = run_tests()
    cov.stop()
    cov.save()

    buffer = io.StringIO()
    total_percent = cov.report(show_missing=True, file=buffer)
    table = buffer.getvalue()
    print(table)

    try:
        cov.html_report(directory=str(DOCS_DIR / "coverage_html"), title="论文查重 覆盖率报告")
        html_note = "HTML 明细报告：docs/coverage_html/index.html"
    except OSError as exc:  # 目录权限等问题不应让整个脚本失败
        html_note = f"HTML 明细报告生成失败：{exc}"

    rows = collect_per_file(cov)
    summary = CoverageSummary(
        table=table,
        rows=rows,
        result=result,
        total_percent=total_percent,
        chart_ok=draw_chart(rows, DOCS_DIR / "coverage_chart.png"),
        html_note=html_note,
    )
    text = "\n".join(_report_lines(summary))
    (DOCS_DIR / "coverage_report.txt").write_text(text, encoding="utf-8", newline="\n")

    print("\n" + text.rsplit("逐文件覆盖情况", maxsplit=1)[-1].strip())
    print(f"\n报告已写入 {DOCS_DIR / 'coverage_report.txt'}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":  # pragma: no cover - 脚本入口
    sys.exit(main())
