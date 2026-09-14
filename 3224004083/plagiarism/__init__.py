# -*- coding: utf-8 -*-
"""论文查重程序的模块包。

模块划分::

    errors.py      可预期错误的异常定义
    reader.py      文件读取
    normalize.py   文本规范化（去标点/空白、统一大小写）
    similarity.py  核心算法：字符二元组多重集 Dice
    writer.py      答案文件写出与格式控制
"""

from .errors import AnswerWriteError, FileReadError, PaperCheckError
from .normalize import normalize
from .reader import read_text
from .similarity import compute_similarity, count_bigrams, dice_overlap
from .writer import format_score, write_answer

__all__ = [
    "AnswerWriteError",
    "FileReadError",
    "PaperCheckError",
    "compute_similarity",
    "count_bigrams",
    "dice_overlap",
    "format_score",
    "normalize",
    "read_text",
    "write_answer",
]
