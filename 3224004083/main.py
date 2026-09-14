#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文查重程序入口。

用法::

    python main.py <原文文件> <抄袭版论文文件> <答案文件>

三个参数均为文件的绝对路径。程序把两篇文章的重复率（[0,1] 浮点数，保留两位
小数）写入第三个参数指定的答案文件，正常结束时进程退出码为 0。
"""

from __future__ import annotations

import sys

from plagiarism.errors import PaperCheckError
from plagiarism.similarity import compute_similarity
from plagiarism.writer import write_answer

USAGE = "用法: python main.py <原文文件> <抄袭版论文文件> <答案文件>"

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_USAGE_ERROR = 2


def _force_utf8_streams() -> None:
    """让标准输出/标准错误在 Windows 控制台上也能打印中文。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - 依赖具体运行环境
                pass


def main(argv: list[str] | None = None) -> int:
    """程序主流程，返回值即进程退出码（便于单元测试直接断言）。"""
    args = list(sys.argv[1:] if argv is None else argv)

    # 1. 参数个数校验：必须是三个路径，否则打印用法并返回 2。
    if len(args) != 3:
        print(USAGE, file=sys.stderr)
        return EXIT_USAGE_ERROR

    original_path, copied_path, answer_path = args

    # 2. 计算相似度并写出答案；所有可预期错误都在这里统一转换成退出码。
    try:
        score = compute_similarity(original_path, copied_path)
        write_answer(answer_path, score)
    except PaperCheckError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except OSError as exc:  # 磁盘、权限等无法归入业务异常的情况
        print(f"错误: 文件操作失败（{exc}）", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - 进程入口，由子进程测试覆盖
    _force_utf8_streams()
    sys.exit(main())
