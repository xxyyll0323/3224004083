# -*- coding: utf-8 -*-
"""一键运行单元测试并生成覆盖率报告。

输出三样东西：

* 终端上的逐文件覆盖率表；
* ``docs/coverage_report.txt``  文字版报告（可直接贴进博客）；
* ``docs/coverage_chart.png``   逐文件覆盖率柱状图（博客里的"覆盖率截图"）；
* ``docs/coverage_html/index.html``  可点开的 HTML 明细报告。

依赖 ``coverage`` 与 ``matplotlib``：``pip install -r requirements-dev.txt``

运行::

    python tools/test_coverage.py
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOCS_DIR = ROOT / "docs"
TESTS_DIR = ROOT / "tests"

# 统计整个学号目录，但排除测试脚本、辅助工具与样例数据。
SOURCE = [str(ROOT)]
OMIT = [str(TESTS_DIR / "*"), str(ROOT / "tools" / "*"), str(DOCS_DIR / "*")]


def run_tests() -> unittest.result.TestResult:
    """运行 tests/ 目录下的全部用例。"""
    print("正在运行单元测试 ...\n")
    suite = unittest.TestLoader().discover(str(TESTS_DIR), top_level_dir=str(ROOT))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=1)
    return runner.run(suite)


def collect_per_file(coverage_instance) -> list[tuple[str, int, int]]:
    """返回 [(文件, 已覆盖语句数, 语句总数)]。"""
    rows: list[tuple[str, int, int]] = []
    data = coverage_instance.get_data()
    for filename in sorted(data.measured_files()):
        path = Path(filename)
        if "plagiarism" not in path.parts and path.name != "main.py":
            continue
        analysis = coverage_instance.analysis2(filename)
        statements = analysis[1]
        missing = analysis[3]
        total = len(statements)
        covered = total - len(missing)
        label = "main.py" if path.name == "main.py" else f"plagiarism/{path.name}"
        rows.append((label, covered, total))
    rows.sort(key=lambda item: item[0])
    return rows


def draw_chart(rows: list[tuple[str, int, int]], out_path: Path) -> bool:
    """画逐文件覆盖率柱状图。"""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.font_manager as fm
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    for candidate in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        if Path(candidate).exists():
            fm.fontManager.addfont(candidate)
            plt.rcParams["font.family"] = fm.FontProperties(fname=candidate).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False

    labels = [row[0] for row in rows]
    percents = [row[1] / row[2] * 100 if row[2] else 100.0 for row in rows]

    figure, axes = plt.subplots(figsize=(9, 4.6), dpi=140)
    bars = axes.bar(labels, percents, color="#2e9e5b", width=0.55)
    for bar, row, percent in zip(bars, rows, percents):
        axes.text(
            bar.get_x() + bar.get_width() / 2,
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
    figure.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out_path)
    plt.close(figure)
    return True


def main() -> int:
    """脚本入口。"""
    try:
        import coverage
    except ImportError:
        print("缺少 coverage，请先执行：pip install -r requirements-dev.txt")
        return 1

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 数据文件放进临时目录：避免在仓库里留下覆盖率缓存，也避免重复运行时
    # 需要删除已有文件。
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

    rows = collect_per_file(cov)

    report_lines = ["单元测试与覆盖率报告", "", table.rstrip(), ""]
    report_lines.append("逐文件覆盖情况")
    for label, covered, total in rows:
        percent = covered / total * 100 if total else 100.0
        report_lines.append(f"  {label:<28}{covered:>5}/{total:<5}{percent:>7.1f}%")
    report_lines.append("")
    report_lines.append(f"用例总数：{result.testsRun}")
    report_lines.append(f"失败：{len(result.failures)}    错误：{len(result.errors)}")
    report_lines.append(f"总体语句覆盖率：{total_percent:.1f}%")

    chart_ok = draw_chart(rows, DOCS_DIR / "coverage_chart.png")
    report_lines.append(f"覆盖率柱状图：{'docs/coverage_chart.png' if chart_ok else '（未安装 matplotlib，跳过）'}")

    try:
        cov.html_report(directory=str(DOCS_DIR / "coverage_html"), title="论文查重 覆盖率报告")
        report_lines.append("HTML 明细报告：docs/coverage_html/index.html")
    except OSError as exc:  # 目录权限等问题不应让整个脚本失败
        report_lines.append(f"HTML 明细报告生成失败：{exc}")

    text = "\n".join(report_lines)
    (DOCS_DIR / "coverage_report.txt").write_text(text, encoding="utf-8", newline="\n")
    print("\n" + text.split("逐文件覆盖情况")[-1].strip())
    print(f"\n报告已写入 {DOCS_DIR / 'coverage_report.txt'}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":  # pragma: no cover - 脚本入口
    sys.exit(main())
