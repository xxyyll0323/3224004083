# -*- coding: utf-8 -*-
"""文件读取。

当前版本只按 UTF-8 读取命令行指定的输入文件。文件读取独立成一个模块，
是为了让相似度计算可以脱离磁盘单独测试。
"""

from __future__ import annotations

import os

from .errors import FileReadError


def read_text(path: str) -> str:
    """按 UTF-8 读取文本文件，不可用时抛出 :class:`FileReadError`。"""
    if not isinstance(path, str) or not path:
        raise FileReadError("输入文件路径为空")

    if os.path.isdir(path):
        raise FileReadError(f"输入路径是目录而不是文件: {path}")

    if not os.path.exists(path):
        raise FileReadError(f"输入文件不存在: {path}")

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError as exc:
        raise FileReadError(f"输入文件不是合法的 UTF-8 文本: {path}") from exc
    except OSError as exc:
        raise FileReadError(f"无法读取输入文件 {path}: {exc}") from exc
