# -*- coding: utf-8 -*-
"""生成自测样例数据。

老师下发的官方样例（``orig.txt`` / ``orig_add.txt`` / ``orig_0.8_dis_1.txt`` 等）
应当以课程发布的为准；本脚本用于在没有官方样例时**自造一份等价的测试集**，
以及为单元测试和实验报告提供可复现的输入。

运行::

    python tools/make_samples.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "sample"

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

UNRELATED_PARAGRAPHS = [
    [
        "红树林生长在热带与亚热带海岸的潮间带上。",
        "它们的根系露出水面，能够在咸水环境中完成气体交换。",
        "红树林为鱼虾提供育幼场所，也削弱了风暴潮对海岸的冲击。",
        "近年来沿海地区通过退塘还林的方式恢复红树林面积。",
        "监测数据显示，恢复区的底栖生物多样性明显回升。",
    ],
]

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


def _flatten(paragraphs: list[list[str]]) -> list[str]:
    return [sentence for paragraph in paragraphs for sentence in paragraph]


def _join(paragraphs: list[list[str]]) -> str:
    return "\n".join("".join(paragraph) for paragraph in paragraphs) + "\n"


def _split_into_sentences(paragraphs: list[list[str]]) -> list[str]:
    sentences: list[str] = []
    for paragraph in paragraphs:
        sentences.extend(paragraph)
    return sentences


def build_samples() -> dict[str, str]:
    """返回 {文件名: 文本内容}。"""
    rng = random.Random(20260914)
    original = _join(ORIGINAL_PARAGRAPHS)
    flat = _flatten(ORIGINAL_PARAGRAPHS)
    samples: dict[str, str] = {"orig.txt": original}

    # 1. 完全一致
    samples["orig_1.0.txt"] = original

    # 2. 增加约 25% 内容：在每段后面插入新句子
    added_paragraphs = [list(paragraph) for paragraph in ORIGINAL_PARAGRAPHS]
    extra_sentences = [
        "需要强调的是，复用决策必须结合团队的实际交付节奏来判断。",
        "在小规模原型阶段，适度的重复反而比过早抽象更加经济。",
        "当项目进入长期维护期之后，抽象带来的收益才会逐步显现出来。",
        "团队应当定期回顾已有的公共组件，清理不再被使用的部分。",
        "把复用当作一次性任务，是很多技术债产生的直接原因。",
    ]
    for index, extra in enumerate(extra_sentences):
        added_paragraphs[index % len(added_paragraphs)].append(extra)
    samples["orig_0.8_add.txt"] = _join(added_paragraphs)

    # 3. 删除约 20% 内容：每段删掉倒数第二句
    deleted_paragraphs = [
        [sentence for position, sentence in enumerate(paragraph) if position % 4 != 3]
        for paragraph in ORIGINAL_PARAGRAPHS
    ]
    samples["orig_0.8_del.txt"] = _join(deleted_paragraphs)

    # 4. 轻微乱序：只在相邻段之间交换 2 句
    shuffled = [list(paragraph) for paragraph in ORIGINAL_PARAGRAPHS]
    normal_order = list(range(len(shuffled)))
    for index, order in zip(normal_order, rng.sample(normal_order, len(normal_order))):
        sentences = shuffled[index]
        cut = len(sentences) // 2
        shuffled[index] = sentences[cut:] + sentences[:cut]
    samples["orig_0.8_dis_1.txt"] = _join(shuffled)

    # 5. 大幅乱序：全部句子整体打乱后重新分段
    all_sentences = list(flat)
    rng.shuffle(all_sentences)
    chunks = [
        all_sentences[start : start + 4] for start in range(0, len(all_sentences), 4)
    ]
    samples["orig_0.8_dis_2.txt"] = _join(chunks)

    # 6. 段内词序打乱：每个句子内部把分句顺序颠倒
    word_disorder = []
    for sentence in flat:
        pieces = [piece for piece in sentence.replace("，", "|").replace("。", "|").split("|") if piece]
        rng.shuffle(pieces)
        word_disorder.append("，".join(pieces) + "。")
    disorder_chunks = [
        word_disorder[start : start + 5] for start in range(0, len(word_disorder), 5)
    ]
    samples["orig_0.8_dis_3.txt"] = _join(disorder_chunks)

    # 7. 近义词替换：把若干术语换成同义表达
    synonyms = []
    for sentence in flat:
        replaced = sentence
        for source, target in SYNONYM_MAP.items():
            replaced = replaced.replace(source, target)
        synonyms.append(replaced)
    samples["orig_0.8_syn.txt"] = _join(
        [synonyms[start : start + 5] for start in range(0, len(synonyms), 5)]
    )

    # 8. 完全无关：另一主题的短文
    samples["orig_0.0.txt"] = _join(UNRELATED_PARAGRAPHS)

    # 9. 空文件与纯标点文件
    samples["orig_empty.txt"] = ""
    samples["orig_punct_only.txt"] = "。。。！！！？？？,,,...\n"

    # 10. HTML 噪声：正文外面包一层网页样板（模拟从网页抓取的内容）
    noise_sentences = _split_into_sentences(ORIGINAL_PARAGRAPHS)
    samples["orig_1.0_html.txt"] = (
        "<html><head><title>转载文章</title>"
        "<style>body{font-size:14px;}</style></head><body>"
        "<div class='article'><p>"
        + "".join(noise_sentences)
        + "</p><script>var pageId=1024;function track(){return 1;}</script>"
        "<span>&nbsp;&copy;&nbsp;版权所有&nbsp;</span></div></body></html>\n"
    )

    return samples


def main() -> int:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    samples = build_samples()
    for name, content in samples.items():
        (SAMPLE_DIR / name).write_text(content, encoding="utf-8", newline="\n")

    # 额外生成一份 GBK 编码的样例，用于验证编码识别。
    gbk_text = samples["orig_0.8_del.txt"]
    (SAMPLE_DIR / "orig_0.8_del_gbk.txt").write_bytes(gbk_text.encode("gb18030"))

    for name in sorted(samples):
        print(f"已生成 sample/{name}  ({len(samples[name])} 字符)")
    print("已生成 sample/orig_0.8_del_gbk.txt  (GB18030 编码)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
