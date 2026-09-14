# -*- coding: utf-8 -*-
"""答案文件写出。"""

from __future__ import annotations

import os
from decimal import ROUND_HALF_UP, Decimal

from .errors import AnswerWriteError


def format_score(score: float) -> str:
    """把相似度格式化为保留两位小数的字符串（四舍五入，避免二进制误差）。"""
    value = Decimal(str(float(score))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # 夹在合法区间内，防止异常输入产生越界答案。
    if value < 0:
        value = Decimal("0.00")
    elif value > 1:
        value = Decimal("1.00")
    return f"{value:.2f}"


def write_answer(path: str, score: float) -> None:
    """把结果写入答案文件，内容形如 ``0.81`` 加一个换行。"""
    if not isinstance(path, str) or not path:
        raise AnswerWriteError("答案文件路径为空")

    if os.path.isdir(path):
        raise AnswerWriteError(f"答案路径是目录而不是文件: {path}")

    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        raise AnswerWriteError(f"答案文件所在目录不存在: {parent}")

    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(format_score(score) + "\n")
    except OSError as exc:
        raise AnswerWriteError(f"无法写入答案文件 {path}: {exc}") from exc
