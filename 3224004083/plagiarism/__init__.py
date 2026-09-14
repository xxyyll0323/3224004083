# -*- coding: utf-8 -*-
"""论文查重程序的模块包。

模块划分::

    errors.py      可预期错误的异常定义
    reader.py      文件读取、编码识别、HTML 噪声剥离
    normalize.py   文本规范化（去标点/空白、统一大小写）
    similarity.py  核心算法：字符 n-gram 多重集 Dice 加权融合
    writer.py      答案文件写出与格式控制
"""

from .errors import AnswerWriteError, EmptyTextError, FileReadError, PaperCheckError
from .normalize import normalize
from .reader import read_text, strip_html
from .similarity import compute_similarity, count_ngrams, dice_overlap, explain, ngram_similarity
from .writer import format_score, write_answer

__all__ = [
    "AnswerWriteError",
    "EmptyTextError",
    "FileReadError",
    "PaperCheckError",
    "compute_similarity",
    "count_ngrams",
    "dice_overlap",
    "explain",
    "format_score",
    "ngram_similarity",
    "normalize",
    "read_text",
    "strip_html",
    "write_answer",
]
