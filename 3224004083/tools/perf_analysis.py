# -*- coding: utf-8 -*-
"""性能分析与基准测试。

做三件事：

1. 在小/中/大三档输入上测量运行时间与峰值内存；
2. 用 ``cProfile`` 剖析 "读取 → 规范化 → 特征统计 → Dice" 流水线，找出热点函数；
3. 把热点函数画成柱状图（需要 matplotlib），并把文字报告写入 ``docs/perf_report.txt``。

运行::

    python tools/perf_analysis.py
"""

from __future__ import annotations

import cProfile
import io
import pstats
import random
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from plagiarism.normalize import normalize, normalize_reference  # noqa: E402
from plagiarism.reader import read_text  # noqa: E402
from plagiarism.similarity import compute_similarity, count_ngrams, dice_overlap  # noqa: E402

SAMPLE_DIR = ROOT / "sample"
DOCS_DIR = ROOT / "docs"

REPEAT = 5


def build_large_pair(target_chars: int, seed: int = 20260914) -> tuple[Path, Path]:
    """把样例原文放大到目标规模，构造一对"删改+乱序"的长文本。"""
    base = (SAMPLE_DIR / "orig.txt").read_text(encoding="utf-8")
    unit = base.strip("\n")
    times = max(1, target_chars // len(unit) + 1)
    big = "".join(unit for _ in range(times))[:target_chars]

    rng = random.Random(seed)
    sentences = [s + "。" for s in big.replace("\n", "。").split("。") if s]
    rng.shuffle(sentences)
    sentences = sentences[: int(len(sentences) * 0.85)]
    variant = "。".join(sentences)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    big_path = DOCS_DIR / "perf_orig.txt"
    variant_path = DOCS_DIR / "perf_copied.txt"
    big_path.write_text(big, encoding="utf-8")
    variant_path.write_text(variant, encoding="utf-8")
    return big_path, variant_path


def measure(path_a: Path, path_b: Path) -> tuple[float, float]:
    """返回 (耗时中位数秒, 峰值内存 MiB)。"""
    times: list[float] = []
    for _ in range(REPEAT):
        start = time.perf_counter()
        compute_similarity(str(path_a), str(path_b))
        times.append(time.perf_counter() - start)

    tracemalloc.start()
    compute_similarity(str(path_a), str(path_b))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return statistics.median(times), peak / 1024 / 1024


def profile_pipeline(path_a: Path, path_b: Path, top: int = 20) -> list[tuple[str, float, float]]:
    """剖析一次完整调用，返回按自身耗时降序的 (函数, tottime, cumtime) 列表。"""
    profiler = cProfile.Profile()
    profiler.enable()
    compute_similarity(str(path_a), str(path_b))
    profiler.disable()

    stats = pstats.Stats(profiler)
    rows: list[tuple[str, float, float]] = []
    for (_, _, func), (cc, nc, tt, ct, _) in stats.stats.items():
        rows.append((f"{Path(func).name}:{nc}", tt, ct))
    rows.sort(key=lambda item: item[1], reverse=True)
    return rows[:top]


def profile_business_only() -> list[tuple[str, float, float]]:
    """只剖析业务函数本身（去掉文件读取与解释器噪声）。"""
    original = normalize(read_text(str(SAMPLE_DIR / "orig.txt")))
    copied = normalize(read_text(str(SAMPLE_DIR / "orig_0.8_dis_2.txt")))

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(200):
        for order in (1, 2, 3, 4):
            dice_overlap(count_ngrams(original, order), count_ngrams(copied, order))
    profiler.disable()

    stats = pstats.Stats(profiler)
    rows: list[tuple[str, float, float]] = []
    for (_, _, func), (cc, nc, tt, ct, _) in stats.stats.items():
        rows.append((f"{Path(func).name}:{nc}", tt, ct))
    rows.sort(key=lambda item: item[1], reverse=True)
    return rows[:12]


def draw_chart(rows: list[tuple[str, float, float]], out_path: Path) -> bool:
    """把热点函数画成左右两张横向柱状图：左为自身耗时，右为累计耗时。"""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.font_manager as fm
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    # 让图表能显示中文：优先使用系统里的微软雅黑。
    for candidate in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        if Path(candidate).exists():
            fm.fontManager.addfont(candidate)
            plt.rcParams["font.family"] = fm.FontProperties(fname=candidate).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False

    # 自身耗时排前 8、累计耗时排前 8，分别取并集保证两张图都能看清热点。
    top_self = [row for row in rows if row[1] > 0][:8]
    top_cum = sorted([row for row in rows if row[2] > 0], key=lambda item: item[2], reverse=True)[:8]

    figure, axes_pair = plt.subplots(1, 2, figsize=(14, 5.6), dpi=140)

    for axes, panel, index in ((axes_pair[0], top_self, 1), (axes_pair[1], top_cum, 2)):
        panel = list(reversed(panel))
        labels = [row[0] for row in panel]
        values = [row[index] for row in panel]
        colors = ["#c0392b" if value == max(values) else "#5b8ff9" for value in values]
        axes.barh(labels, values, color=colors)
        for position, value in enumerate(values):
            axes.text(value, position, f" {value * 1000:.1f} ms", va="center", fontsize=8.5)
        axes.grid(axis="x", linestyle="--", alpha=0.35)
        axes.set_xlim(0, max(values) * 1.28)

    axes_pair[0].set_title("自身耗时 self time（tottime）")
    axes_pair[1].set_title("累计耗时 total time（cumtime，含子调用）")
    axes_pair[0].set_xlabel("秒")
    axes_pair[1].set_xlabel("秒")
    figure.suptitle("论文查重程序 CPU 热点函数（cProfile / 55 万字符大文本）", fontsize=13)
    figure.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out_path)
    plt.close(figure)
    return True


def bench_normalize(text: str, repeat: int = 5) -> tuple[float, float]:
    """对比"逐字符循环"与"查表 + str.translate"两种规范化的耗时（秒）。"""

    def median_time(func) -> float:
        samples: list[float] = []
        for _ in range(repeat):
            start = time.perf_counter()
            func(text)
            samples.append(time.perf_counter() - start)
        return statistics.median(samples)

    normalize(text)  # 预热翻译表，只测量稳定状态下的耗时
    return median_time(normalize_reference), median_time(normalize)


def draw_normalize_chart(before: float, after: float, out_path: Path) -> bool:
    """画一张规范化改前/改后的对比柱状图。"""
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

    figure, axes = plt.subplots(figsize=(5.6, 4.2), dpi=140)
    bars = axes.bar(["改进前\n逐字符循环", "改进后\n查表 + translate"], [before, after], color=["#c0392b", "#2e9e5b"])
    for bar, value in zip(bars, (before, after)):
        axes.text(bar.get_x() + bar.get_width() / 2, value, f"{value * 1000:.0f} ms", ha="center", va="bottom")
    axes.set_ylabel("规范化耗时（秒）")
    axes.set_title(f"文本规范化耗时对比（提速 {before / after:.1f} 倍）")
    axes.grid(axis="y", linestyle="--", alpha=0.35)
    figure.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out_path)
    plt.close(figure)
    return True


def main() -> int:
    if not (SAMPLE_DIR / "orig.txt").exists():
        print("未找到 sample/orig.txt，请先运行 python tools/make_samples.py")
        return 1

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report: list[str] = []
    report.append("论文查重程序性能分析报告")
    report.append(f"Python: {sys.version.split()[0]}    平台: {sys.platform}    重复次数: {REPEAT}")
    report.append("")

    # 1. 三档规模的时间与内存
    report.append("一、不同输入规模下的运行时间与峰值内存")
    report.append(f"{'规模档位':<10}{'原文(字符)':>12}{'抄袭版(字符)':>14}{'耗时中位数(ms)':>16}{'峰值内存(MiB)':>15}")
    cases: list[tuple[Path, Path]] = []
    for level, target in (("小", 6_000), ("中", 60_000), ("大", 600_000)):
        path_a, path_b = build_large_pair(target)
        elapsed, peak = measure(path_a, path_b)
        chars_a = len(normalize(read_text(str(path_a))))
        chars_b = len(normalize(read_text(str(path_b))))
        report.append(
            f"{level:<10}{chars_a:>12}{chars_b:>14}{elapsed * 1000:>16.1f}{peak:>15.1f}"
        )
        cases.append((path_a, path_b))

    # 2. 完整流水线的热点
    biggest_a, biggest_b = cases[-1]
    rows = profile_pipeline(biggest_a, biggest_b)
    report.append("")
    report.append("二、cProfile 热点函数（按自身耗时 tottime 降序，大文本）")
    report.append(f"{'函数':<34}{'调用次数':>10}{'tottime(s)':>13}{'cumtime(s)':>13}")
    for name, tottime, cumtime in rows[:12]:
        func, _, calls = name.rpartition(":")
        share = tottime / sum(row[1] for row in rows) * 100 if rows else 0
        report.append(f"{func:<34}{calls:>10}{tottime:>13.3f}({share:>4.1f}%){cumtime:>13.3f}")

    # 3. 只统计业务函数
    report.append("")
    report.append("三、只保留业务函数（200 次重复调用，剔除文件读取与解释器噪声）")
    business = profile_business_only()
    total = sum(row[1] for row in business) or 1.0
    for name, tottime, cumtime in business:
        func, _, calls = name.rpartition(":")
        report.append(f"{func:<34}{tottime:>9.4f}s  {tottime / total * 100:>5.1f}%")

    # 4. 规范化实现的改进对比
    normalize_source = (DOCS_DIR / "perf_orig.txt").read_text(encoding="utf-8")
    before, after = bench_normalize(normalize_source)
    report.append("")
    report.append("四、文本规范化实现的改进对比（输入为 55 万字符的大文本）")
    report.append(f"{'实现方式':<24}{'耗时(s)':>10}{'相对提速':>10}")
    report.append(f"{'逐字符 Python 循环':<24}{before:>10.3f}{'1.00x':>10}")
    report.append(f"{'查表 + str.translate':<24}{after:>10.3f}{f'{before / after:.2f}x':>10}")

    normalize_chart = DOCS_DIR / "normalize_compare.png"
    normalize_chart_ok = draw_normalize_chart(before, after, normalize_chart)

    chart_path = DOCS_DIR / "perf_chart.png"
    chart_ok = draw_chart(rows, chart_path)
    report.append("")
    report.append("五、图表")
    report.append(
        f"- 热点函数柱状图：{'已生成 docs/perf_chart.png' if chart_ok else '未安装 matplotlib，跳过'}"
    )
    report.append(
        f"- 规范化改进对比图：{'已生成 docs/normalize_compare.png' if normalize_chart_ok else '未安装 matplotlib，跳过'}"
    )

    text = "\n".join(report)
    (DOCS_DIR / "perf_report.txt").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    print(f"\n报告已写入 {DOCS_DIR / 'perf_report.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
