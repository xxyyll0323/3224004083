# -*- coding: utf-8 -*-
"""论文查重程序可预期错误的异常定义。

评测环境把"异常退出"视为失败，因此程序内部所有可预期的错误都转换成这里的
自定义异常，再由 ``main`` 统一捕获、打印提示并以非零退出码结束。
"""

from __future__ import annotations


class PaperCheckError(Exception):
    """本项目所有可预期错误的基类。"""


class FileReadError(PaperCheckError):
    """输入文件不可用：不存在、是目录或无法读取。"""


class AnswerWriteError(PaperCheckError):
    """答案文件无法写入：路径是目录、上级目录不存在、磁盘不可写等。"""
