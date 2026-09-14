# -*- coding: utf-8 -*-
"""边界场景与异常分支的补充测试。

这些用例专门覆盖正常路径之外的代码：超长文本的降阶策略、编码全部失败的兜底、
打开文件时的 OSError 包装、以脚本方式启动入口等。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main as cli  # noqa: E402
from plagiarism.errors import AnswerWriteError, EmptyTextError, FileReadError  # noqa: E402
from plagiarism.similarity import _select_orders, compute_similarity  # noqa: E402
from plagiarism.reader import read_text, strip_html  # noqa: E402
from plagiarism.writer import write_answer  # noqa: E402


class SelectOrdersTest(unittest.TestCase):
    def test_very_short_text_uses_first_order_only(self) -> None:
        self.assertEqual(_select_orders(1), [1])

    def test_normal_text_uses_all_orders(self) -> None:
        self.assertEqual(_select_orders(10_000), [1, 2, 3, 4])

    def test_large_text_drops_fourth_order(self) -> None:
        self.assertEqual(_select_orders(1_000_000), [1, 2, 3])

    def test_huge_text_keeps_middle_orders_only(self) -> None:
        self.assertEqual(_select_orders(5_000_000), [2, 3])


class ComputeSimilarityBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_both_files_empty_raises(self) -> None:
        empty_a = self.tmp / "a.txt"
        empty_b = self.tmp / "b.txt"
        empty_a.write_text("", encoding="utf-8")
        empty_b.write_text("，，。", encoding="utf-8")
        with self.assertRaises(EmptyTextError) as ctx:
            compute_similarity(str(empty_a), str(empty_b))
        self.assertIn("两个输入文件", str(ctx.exception))

    def test_empty_original_raises(self) -> None:
        empty = self.tmp / "empty.txt"
        normal = self.tmp / "normal.txt"
        empty.write_text("", encoding="utf-8")
        normal.write_text("代码复用能够缩短开发周期", encoding="utf-8")
        with self.assertRaises(EmptyTextError) as ctx:
            compute_similarity(str(empty), str(normal))
        self.assertIn("原文文件", str(ctx.exception))


class ReaderFallbackTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_numeric_html_entities_are_decoded(self) -> None:
        cleaned = strip_html("<p>&#65;&#x4e2d;&#20013;</p>")
        self.assertIn("A", cleaned)
        self.assertIn("中", cleaned)

    def test_bom_is_removed_even_without_utf8_sig(self) -> None:
        path = self.tmp / "bom.txt"
        path.write_bytes("\ufeff论文查重".encode("utf-8"))
        with mock.patch("plagiarism.reader._ENCODINGS", ("utf-8",)):
            self.assertEqual(read_text(str(path)), "论文查重")

    def test_unrecognized_encoding_raises(self) -> None:
        path = self.tmp / "cn.txt"
        path.write_text("论文查重程序", encoding="utf-8")
        with mock.patch("plagiarism.reader._ENCODINGS", ("ascii",)):
            with self.assertRaises(FileReadError) as ctx:
                read_text(str(path))
        self.assertIn("编码", str(ctx.exception))

    def test_open_failure_is_wrapped(self) -> None:
        path = self.tmp / "x.txt"
        path.write_text("内容", encoding="utf-8")
        with mock.patch("builtins.open", side_effect=OSError("设备不可用")):
            with self.assertRaises(FileReadError) as ctx:
                read_text(str(path))
        self.assertIn("无法读取", str(ctx.exception))


class WriterFailureTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_empty_path_raises(self) -> None:
        with self.assertRaises(AnswerWriteError):
            write_answer("", 0.5)

    def test_open_failure_is_wrapped(self) -> None:
        target = self.tmp / "ans.txt"
        with mock.patch("builtins.open", side_effect=OSError("只读文件系统")):
            with self.assertRaises(AnswerWriteError) as ctx:
                write_answer(str(target), 0.5)
        self.assertIn("无法写入", str(ctx.exception))


class MainBranchTest(unittest.TestCase):
    def test_force_utf8_streams_is_callable(self) -> None:
        cli._force_utf8_streams()

    def test_unexpected_oserror_returns_runtime_error(self) -> None:
        with mock.patch("main.compute_similarity", side_effect=OSError("磁盘故障")):
            with mock.patch("sys.stderr", new_callable=lambda: __import__("io").StringIO()):
                code = cli.main(["a.txt", "b.txt", "c.txt"])
        self.assertEqual(code, cli.EXIT_RUNTIME_ERROR)

    def test_entry_point_script_reports_usage(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(completed.returncode, cli.EXIT_USAGE_ERROR)
        self.assertIn("用法", completed.stderr)

    def test_entry_point_script_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            original = tmp_path / "orig.txt"
            copied = tmp_path / "copied.txt"
            answer = tmp_path / "ans.txt"
            original.write_text("代码复用能够缩短开发周期", encoding="utf-8")
            copied.write_text("代码复用能够缩短开发周期", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), str(original), str(copied), str(answer)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(completed.returncode, cli.EXIT_OK)
            self.assertEqual(answer.read_text(encoding="utf-8"), "1.00\n")


if __name__ == "__main__":
    unittest.main()
