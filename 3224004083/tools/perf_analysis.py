# -*- coding: utf-8 -*-
"""性能分析与基准测试。

做四件事：

1. 在小/中/大三档输入上测量运行时间与峰值内存；
2. 用 ``cProfile`` 剖析"读取 → 规范化 → 特征统计 → 余弦相似度"流水线，找出热点函数；
3. 对比"逐字符循环"与"查表 + str.translate"两种规范化的耗时；
4. 把结果画成图表，并把文字报告写入 ``docs/perf_report.txt``。

运行（在学号目录下）::

    python tools/perf_analysis.py
"""

from __future__ import annotations

import cProfile
import dataclasses
import gc
import pstats
import random
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 脚本要能直接从源码目录运行，不需要先 pip install，因此手动补上项目根目录；
# 由此产生的"导入不在文件顶部"是刻意为之。
# pylint: disable=wrong-import-position
sys.path.insert(0, str(ROOT))

from tools import plotting
from plagiarism.normalize import normalize, normalize_reference
from plagiarism.reader import read_text
from plagiarism.similarity import compute_similarity, count_ngrams, cosine_similarity

SAMPLE_DIR = ROOT / "sample"
DOCS_DIR = ROOT / "docs"

# 每个档位重复测量的次数，用于取中位数。
REPEAT = 5

# 四档规模：前两档贴近作业样例的实际大小，后两档用于观察线性扩展能力。
SCALES = (
    ("样例级", 6_000),
    ("中篇", 60_000),
    ("长篇", 200_000),
    ("极端", 600_000),
)

# 抄袭版相对原文的保留比例（模拟"打乱 + 删除"后的抄袭版）。
KEEP_RATIO = 0.85


@dataclasses.dataclass
class ProfileRow:
    """一条剖析记录。"""

    name: str
    self_time: float
    total_time: float


def build_large_pair(target_chars: int, seed: int = 20260914) -> tuple[Path, Path]:
    """把样例原文放大到目标规模，构造一对"删改 + 乱序"的长文本。"""
    unit = (SAMPLE_DIR / "orig.txt").read_text(encoding="utf-8").strip("\n")
    times = max(1, target_chars // len(unit) + 1)
    big = "".join(unit for _ in range(times))[:target_chars]

    rng = random.Random(seed)
    sentences = [piece + "。" for piece in big.replace("\n", "。").split("。") if piece]
    rng.shuffle(sentences)
    sentences = sentences[: int(len(sentences) * KEEP_RATIO)]
    variant = "。".join(sentences)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    big_path = DOCS_DIR / "perf_orig.txt"
    variant_path = DOCS_DIR / "perf_copied.txt"
    big_path.write_text(big, encoding="utf-8")
    variant_path.write_text(variant, encoding="utf-8")
    return big_path, variant_path


def measure(path_a: Path, path_b: Path) -> tuple[float, float, float, float]:
    """返回 (耗时中位数秒, 最快秒, 最慢秒, 峰值内存 MiB)。

    同时给出中位数与极值：这台机器上单次测量的波动可能达到 2~3 倍，
    只看一次结果容易得出错误结论（本项目就因此误判过一次"优化收益"）。
    """
    samples: list[float] = []
    for _ in range(REPEAT):
        start = time.perf_counter()
        compute_similarity(str(path_a), str(path_b))
        samples.append(time.perf_counter() - start)

    tracemalloc.start()
    compute_similarity(str(path_a), str(path_b))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return statistics.median(samples), min(samples), max(samples), peak / 1024 / 1024


def _profile_rows(profiler: cProfile.Profile, top: int) -> list[ProfileRow]:
    """把 cProfile 的原始统计整理成按自身耗时降序的列表。"""
    stats = pstats.Stats(profiler)
    rows: list[ProfileRow] = []
    for (_, _, func), (_cc, nc, self_time, total_time, _) in stats.stats.items():
        rows.append(ProfileRow(f"{Path(func).name}:{nc}", self_time, total_time))
    rows.sort(key=lambda row: row.self_time, reverse=True)
    return rows[:top]


def profile_pipeline(path_a: Path, path_b: Path, top: int = 20) -> list[ProfileRow]:
    """剖析一次完整调用（含文件读取与规范化）。"""
    profiler = cProfile.Profile()
    profiler.enable()
    compute_similarity(str(path_a), str(path_b))
    profiler.disable()
    return _profile_rows(profiler, top)


def profile_business_only() -> list[ProfileRow]:
    """只剖析业务函数本身，剔除文件读取与解释器噪声。"""
    original = normalize(read_text(str(SAMPLE_DIR / "orig.txt")))
    copied = normalize(read_text(str(SAMPLE_DIR / "orig_0.8_dis_2.txt")))

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(200):
        for order in (1, 2, 3, 4):
            cosine_similarity(count_ngrams(original, order), count_ngrams(copied, order))
    profiler.disable()
    return _profile_rows(profiler, 12)


def bench_normalize(text: str, repeat: int = 5) -> tuple[float, float]:
    """对比两种规范化的耗时，返回 (逐字符, 查表) 两个秒数。

    测量方法：两种实现**交替**跑，各自取**最小值**。
    在一台负载会波动的机器上，最小值最接近"没有被打扰时的真实耗时"；
    取中位数或平均都会被偶发的负载尖峰抬高，而先跑完 A 再跑 B 更会把负载漂移
    误当成两者的性能差异。
    """

    def timed(func) -> float:
        start = time.perf_counter()
        func(text)
        return time.perf_counter() - start

    normalize(text)  # 预热翻译表，只测量稳定状态下的耗时
    slow_samples: list[float] = []
    fast_samples: list[float] = []
    for _ in range(repeat):
        slow_samples.append(timed(normalize_reference))
        fast_samples.append(timed(normalize))
    return min(slow_samples), min(fast_samples)


def _draw_profile_panel(axes, panel: list[ProfileRow], field: str, title: str) -> None:
    """在一张子图上画一组热点柱子。"""
    visible = [row for row in reversed(panel) if getattr(row, field) > 0]
    labels = [row.name for row in visible]
    values = [getattr(row, field) for row in visible]
    peak = max(values)
    colors = ["#c0392b" if value == peak else "#5b8ff9" for value in values]
    axes.barh(labels, values, color=colors)
    for position, value in enumerate(values):
        axes.text(value, position, f" {value * 1000:.1f} ms", va="center", fontsize=8.5)
    axes.grid(axis="x", linestyle="--", alpha=0.35)
    axes.set_xlim(0, peak * 1.28)
    axes.set_title(title)
    axes.set_xlabel("秒")


def bench_gc(
    text_a: str, text_b: str, orders: tuple[int, ...] = (1, 2, 3, 4)
) -> tuple[float, float]:
    """对比"计算期间关闭分代 GC"与"保持开启"的耗时。

    这是一个**被否决的方案**的对照实验：n-gram 统计会创建数以百万计的临时字符串，
    直觉上关掉分代 GC 应该更快。实测两者差距在噪声范围内（约 1.0x），
    因此最终代码没有采用这个做法。保留这段基准是为了让结论可复现。

    返回 (GC 开启耗时, GC 关闭耗时)。
    """

    def run(disable_gc: bool) -> float:
        if disable_gc:
            gc.disable()
        else:
            gc.enable()
        try:
            start = time.perf_counter()
            for order in orders:
                left = count_ngrams(text_a, order)
                right = count_ngrams(text_b, order)
                cosine_similarity(left, right)
            return time.perf_counter() - start
        finally:
            gc.enable()

    run(True)  # 预热
    run(False)

    # 关键：两种写法**交替**测量、各自取最小值。如果先把 A 全测完再测 B，
    # 机器的负载漂移会被误读成 A 与 B 的真实差异（本项目第一版就是这么得出错误结论的）。
    enabled_samples: list[float] = []
    disabled_samples: list[float] = []
    for _ in range(REPEAT):
        enabled_samples.append(run(False))
        disabled_samples.append(run(True))
    return min(enabled_samples), min(disabled_samples)


def draw_hotspot_chart(rows: list[ProfileRow], out_path: Path) -> bool:
    """画左右两联热点柱状图：左为自身耗时，右为累计耗时。"""
    if not plotting.prepare():
        return False
    plt = plotting.pyplot()

    panels = [
        (
            sorted(rows, key=lambda row: row.self_time, reverse=True)[:8],
            "self_time",
            "自身耗时 self time（tottime）",
        ),
        (
            sorted(rows, key=lambda row: row.total_time, reverse=True)[:8],
            "total_time",
            "累计耗时 total time（cumtime，含子调用）",
        ),
    ]

    figure, axes_pair = plt.subplots(1, 2, figsize=(14, 5.6), dpi=140)
    for axes, (panel, field, title) in zip(axes_pair, panels):
        _draw_profile_panel(axes, panel, field, title)

    figure.suptitle("论文查重程序 CPU 热点函数（cProfile / 60 万字符极端输入）", fontsize=13)
    plotting.save(figure, out_path)
    return True


def draw_normalize_chart(before: float, after: float, out_path: Path) -> bool:
    """画一张规范化改前/改后的对比柱状图。"""
    if not plotting.prepare():
        return False
    plt = plotting.pyplot()

    figure, axes = plt.subplots(figsize=(5.6, 4.2), dpi=140)
    rectangles = axes.bar(
        ["改进前\n逐字符循环", "改进后\n查表 + translate"],
        [before, after],
        color=["#c0392b", "#2e9e5b"],
    )
    for rectangle, value in zip(rectangles, (before, after)):
        axes.text(
            rectangle.get_x() + rectangle.get_width() / 2,
            value,
            f"{value * 1000:.0f} ms",
            ha="center",
            va="bottom",
        )
    axes.set_ylabel("规范化耗时（秒）")
    axes.set_title(f"文本规范化耗时对比（提速 {before / after:.1f} 倍）")
    axes.grid(axis="y", linestyle="--", alpha=0.35)
    plotting.save(figure, out_path)
    return True


def _scale_table() -> tuple[list[str], list[tuple[Path, Path]]]:
    """跑完三档规模，返回 (报告行, 每档的输入文件对)。"""
    lines = [
        "一、不同输入规模下的运行时间与峰值内存",
        f"{'规模档位':<10}{'原文(字符)':>12}{'抄袭版(字符)':>14}"
        f"{'最快(ms)':>11}{'中位数(ms)':>12}{'最慢(ms)':>11}{'峰值内存(MiB)':>14}",
    ]
    pairs: list[tuple[Path, Path]] = []
    for level, target in SCALES:
        path_a, path_b = build_large_pair(target)
        median, fastest, slowest, peak = measure(path_a, path_b)
        chars_a = len(normalize(read_text(str(path_a))))
        chars_b = len(normalize(read_text(str(path_b))))
        lines.append(
            f"{level:<10}{chars_a:>12}{chars_b:>14}"
            f"{fastest * 1000:>11.1f}{median * 1000:>12.1f}{slowest * 1000:>11.1f}{peak:>14.1f}"
        )
        pairs.append((path_a, path_b))
    return lines, pairs


def _hotspot_lines(rows: list[ProfileRow]) -> list[str]:
    """把热点函数表整理成文本行。"""
    total = sum(row.self_time for row in rows) or 1.0
    lines = [
        "",
        "二、cProfile 热点函数（按自身耗时降序，大文本）",
        f"{'函数':<34}{'调用次数':>10}{'tottime(s)':>15}{'cumtime(s)':>13}",
    ]
    for row in rows[:12]:
        func, _, calls = row.name.rpartition(":")
        share = row.self_time / total * 100
        lines.append(
            f"{func:<34}{calls:>10}{row.self_time:>9.3f}({share:>5.1f}%){row.total_time:>13.3f}"
        )
    return lines


def _business_lines(rows: list[ProfileRow]) -> list[str]:
    """把"只保留业务函数"的结果整理成文本行。"""
    lines = ["", "三、只保留业务函数（200 次重复调用，剔除文件读取与解释器噪声）"]
    total = sum(row.self_time for row in rows) or 1.0
    for row in rows:
        share = row.self_time / total * 100
        lines.append(f"{row.name:<34}{row.self_time:>9.4f}s  {share:>5.1f}%")
    return lines


def _normalize_bench_lines(before: float, after: float) -> list[str]:
    """第四节：两种文本规范化实现的耗时对比。"""
    return [
        "",
        "四、文本规范化实现的改进对比（输入为 60 万字符极端输入）",
        f"{'实现方式':<24}{'耗时(s)':>10}{'相对提速':>10}",
        f"{'逐字符 Python 循环':<24}{before:>10.3f}{'1.00x':>10}",
        f"{'查表 + str.translate':<24}{after:>10.3f}{f'{before / after:.2f}x':>10}",
    ]


def _gc_bench_lines() -> list[str]:
    """第五节：被否决的"计算期间关闭分代 GC"方案的对照实验。"""
    norm_a = normalize((DOCS_DIR / "perf_orig.txt").read_text(encoding="utf-8"))
    norm_b = normalize((DOCS_DIR / "perf_copied.txt").read_text(encoding="utf-8"))
    gc_on, gc_off = bench_gc(norm_a, norm_b)
    return [
        "",
        "五、一个被否决的优化方案：计算期间关闭分代 GC（对照实验）",
        f"{'写法':<24}{'耗时(s)':>10}{'相对提速':>10}",
        f"{'保持分代 GC 开启':<24}{gc_on:>10.3f}{'1.00x':>10}",
        f"{'计算期间关闭分代 GC':<24}{gc_off:>10.3f}{f'{gc_on / gc_off:.2f}x':>10}",
        "结论：两者差距落在测量噪声范围内，收益不足以抵偿引入全局状态的代价，",
        "      因此最终代码没有采用该方案（结论可复现）。",
    ]


def _chart_lines(rows: list[ProfileRow], before: float, after: float) -> list[str]:
    """第六节：图表生成结果。"""
    hotspot_ok = draw_hotspot_chart(rows, DOCS_DIR / "perf_chart.png")
    normalize_ok = draw_normalize_chart(before, after, DOCS_DIR / "normalize_compare.png")
    return [
        "",
        "六、图表",
        f"- 热点函数柱状图：{'已生成 docs/perf_chart.png' if hotspot_ok else '未安装 matplotlib，跳过'}",
        f"- 规范化改进对比图："
        f"{'已生成 docs/normalize_compare.png' if normalize_ok else '未安装 matplotlib，跳过'}",
    ]


def main() -> int:
    """生成性能分析报告与图表。"""
    if not (SAMPLE_DIR / "orig.txt").exists():
        print("未找到 sample/orig.txt，请先运行 python tools/make_samples.py")
        return 1

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report: list[str] = [
        "论文查重程序性能分析报告",
        f"Python: {sys.version.split()[0]}    平台: {sys.platform}    重复次数: {REPEAT}",
        "",
    ]

    scale_lines, pairs = _scale_table()
    report.extend(scale_lines)

    rows = profile_pipeline(*pairs[-1])
    report.extend(_hotspot_lines(rows))
    report.extend(_business_lines(profile_business_only()))

    source = (DOCS_DIR / "perf_orig.txt").read_text(encoding="utf-8")
    before, after = bench_normalize(source)
    report.extend(_normalize_bench_lines(before, after))
    report.extend(_gc_bench_lines())
    report.extend(_chart_lines(rows, before, after))

    text = "\n".join(report)
    (DOCS_DIR / "perf_report.txt").write_text(text, encoding="utf-8")
    print(text)
    print(f"\n报告已写入 {DOCS_DIR / 'perf_report.txt'}")
    return 0


if __name__ == "__main__":  # pragma: no cover - 脚本入口
    sys.exit(main())
