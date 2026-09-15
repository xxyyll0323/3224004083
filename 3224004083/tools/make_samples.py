# -*- coding: utf-8 -*-
"""生成自测样例数据。

老师下发的官方样例（``orig.txt`` / ``orig_add.txt`` / ``orig_0.8_dis_1.txt`` 等）
应当以课程发布的为准；本脚本用于在没有官方样例时**自造一份等价的测试集**，
以及为单元测试和实验报告提供可复现的输入。

每个抄袭版变体都由一个独立函数生成，便于单独调整和阅读。

运行（在学号目录下）::

    python tools/make_samples.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "sample"
RANDOM_SEED = 20260914

# 原文：一篇关于"软件工程中的代码复用"的短文，四段共 20 句。
ORIGINAL_PARAGRAPHS = [
    [
        "代码复用是软件工程中被反复讨论的核心议题之一。",
        "从最早的子程序库到今天的包管理生态，工程师一直在寻找降低重复劳动的办法。",
        "复用的收益非常直观，它能够缩短开发周期，并且让经过验证的逻辑被更多项目使用。",
        "然而复用的代价往往被低估，被复用的组件会带来额外的耦合与升级压力。",
        "因此复用不是越多越好，而是要在收益与成本之间找到一个合适的平衡点。",
    ],
    [
        "在工程实践中，复用通常发生在三个层次上。",
        "最底层是代码片段的复用，例如工具函数与数据结构实现。",
        "中间层是模块与服务的复用，这一层要求接口稳定并且文档齐全。",
        "最高层是架构与设计经验的复用，它最难量化，却往往带来最大的长期收益。",
        "三个层次并不是互斥的，一个成熟的团队会同时在这三个层次上积累资产。",
    ],
    [
        "判断一段代码是否值得被复用，需要考察几个具体指标。",
        "第一是使用频次，只被调用过一次的逻辑通常不值得抽象。",
        "第二是稳定性，频繁变动的代码被复用后会放大变更的影响范围。",
        "第三是语义清晰度，含义模糊的接口会让调用方产生误解。",
        "把这三条放在一起看，就会发现抽象应当发生在第三次重复出现的时候。",
    ],
    [
        "自动化测试是安全复用的前提条件。",
        "没有测试覆盖的组件，被复用得越多，潜藏缺陷的影响面就越大。",
        "持续集成把测试固化在流水线中，让复用者可以放心地升级依赖版本。",
        "文档与示例同样重要，它们决定了新成员理解一个组件所需的成本。",
        "当测试、文档与版本策略都到位时，复用才真正从个人技巧变成团队能力。",
    ],
]

# 完全不同主题的短文，用来验证"无关文本得分应该接近 0"。
UNRELATED_PARAGRAPHS = [
    [
        "红树林生长在热带与亚热带海岸的潮间带上。",
        "它们的根系露出水面，能够在咸水环境中完成气体交换。",
        "红树林为鱼虾提供育幼场所，也削弱了风暴潮对海岸的冲击。",
        "近年来沿海地区通过退塘还林的方式恢复红树林面积。",
        "监测数据显示，恢复区的底栖生物多样性明显回升。",
    ],
]

# 术语替换表，用来模拟"同义改写"这一类抄袭手段。
SYNONYM_MAP = {
    "代码复用": "代码重用",
    "软件工程": "软件工程学科",
    "核心议题": "关键话题",
    "工程师": "开发者",
    "开发周期": "研发时间",
    "逻辑": "程序逻辑",
    "耦合": "依赖耦合",
    "平衡点": "均衡位置",
}

# 插入到原文中的新句子，用来模拟"增"。
EXTRA_SENTENCES = [
    "需要强调的是，复用决策必须结合团队的实际交付节奏来判断。",
    "在小规模原型阶段，适度的重复反而比过早抽象更加经济。",
    "当项目进入长期维护期之后，抽象带来的收益才会逐步显现出来。",
    "团队应当定期回顾已有的公共组件，清理不再被使用的部分。",
    "把复用当作一次性任务，是很多技术债产生的直接原因。",
]


def _flatten(paragraphs: list[list[str]]) -> list[str]:
    """把段落列表拍平成一个句子列表。"""
    return [sentence for paragraph in paragraphs for sentence in paragraph]


def _join(paragraphs: list[list[str]]) -> str:
    """把段落列表拼成最终文本（段内直接相连，段间换行）。"""
    return "\n".join("".join(paragraph) for paragraph in paragraphs) + "\n"


def _chunk(sentences: list[str], size: int) -> list[list[str]]:
    """把句子列表按固定长度重新分段。"""
    return [sentences[start : start + size] for start in range(0, len(sentences), size)]


def variant_added() -> str:
    """增：在每段末尾插入一句新内容。"""
    paragraphs = [list(paragraph) for paragraph in ORIGINAL_PARAGRAPHS]
    for index, extra in enumerate(EXTRA_SENTENCES):
        paragraphs[index % len(paragraphs)].append(extra)
    return _join(paragraphs)


def variant_deleted() -> str:
    """删：每段删掉倒数第二句，总量约减少 20%。"""
    paragraphs = [
        [sentence for position, sentence in enumerate(paragraph) if position % 4 != 3]
        for paragraph in ORIGINAL_PARAGRAPHS
    ]
    return _join(paragraphs)


def variant_rotated() -> str:
    """乱序（轻）：每个段落内部的句子做一次循环旋转。"""
    paragraphs = [list(paragraph) for paragraph in ORIGINAL_PARAGRAPHS]
    for index, sentences in enumerate(paragraphs):
        cut = len(sentences) // 2
        paragraphs[index] = sentences[cut:] + sentences[:cut]
    return _join(paragraphs)


def variant_shuffled(rng: random.Random) -> str:
    """乱序（重）：全部句子整体打乱后重新分段。"""
    sentences = _flatten(ORIGINAL_PARAGRAPHS)
    rng.shuffle(sentences)
    return _join(_chunk(sentences, 4))


def variant_word_disorder(rng: random.Random) -> str:
    """乱序（句内）：把每个句子内部的分句顺序颠倒。"""
    sentences: list[str] = []
    for sentence in _flatten(ORIGINAL_PARAGRAPHS):
        raw_pieces = sentence.replace("，", "|").replace("。", "|").split("|")
        pieces = [piece for piece in raw_pieces if piece]
        rng.shuffle(pieces)
        sentences.append("，".join(pieces) + "。")
    return _join(_chunk(sentences, 5))


def variant_synonym() -> str:
    """改：把若干术语替换成同义表达。"""
    sentences: list[str] = []
    for sentence in _flatten(ORIGINAL_PARAGRAPHS):
        replaced = sentence
        for source, target in SYNONYM_MAP.items():
            replaced = replaced.replace(source, target)
        sentences.append(replaced)
    return _join(_chunk(sentences, 5))


def variant_html() -> str:
    """正文不变，但外面包了一层网页外壳，用来验证 HTML 噪声被剥离。"""
    body = "".join(_flatten(ORIGINAL_PARAGRAPHS))
    return (
        "<html><head><title>转载文章</title>"
        "<style>body{font-size:14px;}</style></head><body>"
        f"<div class='article'><p>{body}</p>"
        "<script>var pageId=1024;function track(){return 1;}</script>"
        "<span>&nbsp;&copy;&nbsp;版权所有&nbsp;</span></div></body></html>\n"
    )


def build_samples() -> dict[str, str]:
    """返回 {文件名: 文本内容}。"""
    rng = random.Random(RANDOM_SEED)
    original = _join(ORIGINAL_PARAGRAPHS)

    samples: dict[str, str] = {
        "orig.txt": original,
        "orig_1.0.txt": original,
        "orig_1.0_html.txt": variant_html(),
        "orig_0.8_add.txt": variant_added(),
        "orig_0.8_del.txt": variant_deleted(),
        "orig_0.8_dis_1.txt": variant_rotated(),
        "orig_0.8_dis_2.txt": variant_shuffled(rng),
        "orig_0.8_dis_3.txt": variant_word_disorder(rng),
        "orig_0.8_syn.txt": variant_synonym(),
        "orig_0.0.txt": _join(UNRELATED_PARAGRAPHS),
        "orig_empty.txt": "",
        "orig_punct_only.txt": "。。。！！！？？？,,,...\n",
    }
    return samples


def main() -> int:
    """写出全部样例文件。"""
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    samples = build_samples()
    for name, content in samples.items():
        (SAMPLE_DIR / name).write_text(content, encoding="utf-8")
        print(f"已生成 sample/{name}  ({len(content)} 字符)")

    # 额外生成一份 GB18030 编码的样例，用于验证编码识别。
    gbk_bytes = samples["orig_0.8_del.txt"].encode("gb18030")
    (SAMPLE_DIR / "orig_0.8_del_gbk.txt").write_bytes(gbk_bytes)
    print("已生成 sample/orig_0.8_del_gbk.txt  (GB18030 编码)")
    return 0


if __name__ == "__main__":  # pragma: no cover - 脚本入口
    sys.exit(main())
