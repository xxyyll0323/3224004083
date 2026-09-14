# -*- coding: utf-8 -*-
"""文本规范化。

规范化的目标是抹掉"格式差异"、保留"内容差异"：

* 换行、空格、Tab、标点、符号一律丢弃；
* 字母统一转小写；
* 全角字符在读取阶段已通过 NFKC 转成半角；
* 保留汉字、字母与数字，因此中英混排文本同样可用。

实现说明（性能改进点）
----------------------
第一版直接对每个字符调用一次 ``isinstance``/``isupper``/``unicodedata.category``
判断，纯 Python 循环在 55 万字符的文本上耗掉了整个流水线约四分之一的时间。

现在改成"**字符 → 目标字符**"查表 + ``str.translate``：

* ``str.translate`` 在 C 层完成映射，不再逐字符回调 Python；
* 映射表按**字符**缓存，中文文章里不同字符只有几千个，缓存命中率接近 100%，
  因此表只建一次，后续调用几乎是纯 C 开销。

注意 ``str.translate`` 对表里没有的码点会原样保留，所以建表时把文本里出现的
每个字符都写进表，避免漏映射。
"""

from __future__ import annotations

import unicodedata

# 码点 → 保留的字符（空串表示丢弃）。进程内共享，只增不减。
_TRANSLATION: dict[int, str] = {}


def _keep(ch: str) -> str:
    """返回单个字符规范化后的结果，被丢弃的字符返回空串。"""
    if ch.isdigit():
        return ch
    if "a" <= ch <= "z":
        return ch
    if "A" <= ch <= "Z":
        return ch.lower()
    category = unicodedata.category(ch)
    if category.startswith("L") or category.startswith("N"):
        return ch.lower() if ch.isupper() else ch
    return ""


def _translation_for(text: str) -> dict[int, str]:
    """补齐并返回覆盖 ``text`` 全部字符的翻译表。"""
    for ch in set(text):
        code = ord(ch)
        if code not in _TRANSLATION:
            _TRANSLATION[code] = _keep(ch)
    return _TRANSLATION


def normalize(text: str) -> str:
    """返回只含字母、数字与汉字的规范化文本。"""
    return text.translate(_translation_for(text))


def normalize_reference(text: str) -> str:
    """逐字符版本的参考实现，仅供测试与基准对照使用。"""
    return "".join(_keep(ch) for ch in text)
