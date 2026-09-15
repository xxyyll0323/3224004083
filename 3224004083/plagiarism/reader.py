# -*- coding: utf-8 -*-
"""文件读取与编码识别。

只读取命令行参数指定的文件，不访问任何其他业务文件，也不联网。
"""

from __future__ import annotations

import os
import re
import unicodedata

from .errors import FileReadError

# 依次尝试的编码。utf-8-sig 会顺手吃掉 BOM；gb18030 覆盖 GBK/GB2312。
_ENCODINGS = ("utf-8-sig", "gb18030", "utf-16")

# 粗略判断文本是否像 HTML 片段。评测样例里有部分内容是从网页抓下来的，
# 夹带了 <html>/<div>/<script> 之类样板，这些噪声会把相似度拉低。
_HTML_HINT = re.compile(
    r"<\s*(html|head|body|div|p|span|script|style|br|table|ul|li|a)\b|&[a-zA-Z]{2,10};|&#\d+;",
    re.IGNORECASE,
)
_SCRIPT_BLOCK = re.compile(r"<\s*(script|style)\b.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)
# 去掉单个 HTML 标签。长度上限给到 2000：普通标签几十个字符，而网页头部
# 的 <link> 标签带 integrity="sha384-..."（一段 base64）能到几百字符，上限太小
# 会导致这类长标签漏剥、把样板混进正文。2000 已足够覆盖，又能避免病态输入。
_HTML_TAG = re.compile(r"<[^>]{0,2000}>")
_HTML_ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]{2,10});")

_NAMED_ENTITIES = {
    "nbsp": " ",
    "lt": "<",
    "gt": ">",
    "amp": "&",
    "quot": '"',
    "apos": "'",
    "ldquo": "“",
    "rdquo": "”",
    "hellip": "…",
    "mdash": "—",
    "middot": "·",
}


def _decode_entity(match: re.Match[str]) -> str:
    body = match.group(1)
    if body.startswith(("#x", "#X")):
        try:
            return chr(int(body[2:], 16))
        except ValueError:  # pragma: no cover - 畸形实体
            return ""
    if body.startswith("#"):
        try:
            return chr(int(body[1:]))
        except ValueError:  # pragma: no cover - 畸形实体
            return ""
    return _NAMED_ENTITIES.get(body.lower(), "")


def strip_html(text: str) -> str:
    """剥离 HTML 标签与实体；对纯文本原样返回。"""
    if not _HTML_HINT.search(text):
        return text
    cleaned = _SCRIPT_BLOCK.sub(" ", text)
    cleaned = _HTML_TAG.sub(" ", cleaned)
    cleaned = _HTML_ENTITY.sub(_decode_entity, cleaned)
    return cleaned if cleaned.strip() else text


def read_text(path: str) -> str:
    """读取文本文件并返回字符串。

    先按 UTF-8 读取并去掉 BOM，失败时依次尝试 GB18030、UTF-16；全部失败则
    抛出 :class:`FileReadError`。读到的内容会做基础清洗（去除 NUL、统一换行、
    剥离 HTML 噪声）以及 Unicode NFKC 归一化（全角转半角等）。
    """
    if not isinstance(path, str) or not path:
        raise FileReadError("输入文件路径为空")

    if os.path.isdir(path):
        raise FileReadError(f"输入路径是目录而不是文件: {path}")

    if not os.path.exists(path):
        raise FileReadError(f"输入文件不存在: {path}")

    raw: bytes | None = None
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise FileReadError(f"无法读取输入文件 {path}: {exc}") from exc

    for encoding in _ENCODINGS:
        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        break
    else:
        raise FileReadError(f"无法识别的文件编码（已尝试 UTF-8/GB18030/UTF-16）: {path}")

    if text.startswith("\ufeff"):
        text = text[1:]

    text = text.replace("\x00", "")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return strip_html(text)
