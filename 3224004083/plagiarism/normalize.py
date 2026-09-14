# -*- coding: utf-8 -*-
"""文本规范化。

规范化的目标是抹掉"格式差异"、保留"内容差异"：空白、换行、标点、符号一律丢弃，
字母统一转小写，只保留汉字、字母与数字。
"""

from __future__ import annotations

import unicodedata


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


def normalize(text: str) -> str:
    """返回只含字母、数字与汉字的规范化文本。"""
    return "".join(_keep(ch) for ch in text)
