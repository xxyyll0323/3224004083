# -*- coding: utf-8 -*-
"""命令行入口、答案写出与异常处理的单元测试。"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import EXIT_OK, EXIT_RUNTIME_ERROR, EXIT_USAGE_ERROR, main  # noqa: E402
from plagiarism.writer import format_score, write_answer  # noqa: E402

ORIGINAL = "代码复用能够缩短开发周期，并且让经过验证的逻辑被更多项目使用。"
COPIED = "代码重用能够缩短研发时间，并且让经过验证的程序逻辑被更多项目使用。"


class FormatScoreTest(unittest.TestCase):
    def test_keeps_two_decimal_places(self) -> None:
        self.assertEqual(format_score(0.8), "0.80")
        self.assertEqual(format_score(2.0 / 3.0), "0.67")

    def test_rounds_half_up(self) -> None:
        self.assertEqual(format_score(0.005), "0.01")
        self.assertEqual(format_score(0.0049), "0.00")

    def test_clamps_to_unit_interval(self) -> None:
        self.assertEqual(format_score(1.4), "1.00")
        self.assertEqual(format_score(-0.2), "0.00")


class WriteAnswerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_writes_value_with_newline(self) -> None:
        path = self.tmp / "ans.txt"
        write_answer(str(path), 2.0 / 3.0)
        self.assertEqual(path.read_text(encoding="utf-8"), "0.67\n")

    def test_rejects_directory_as_result(self) -> None:
        with self.assertRaises(Exception):
            write_answer(str(self.tmp), 0.5)

    def test_rejects_missing_parent_directory(self) -> None:
        with self.assertRaises(Exception):
            write_answer(str(self.tmp / "no_such_dir" / "ans.txt"), 0.5)


class MainTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.original = self.tmp / "orig.txt"
        self.copied = self.tmp / "copied.txt"
        self.answer = self.tmp / "ans.txt"
        self.original.write_text(ORIGINAL, encoding="utf-8")
        self.copied.write_text(COPIED, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_success_returns_zero_and_writes_two_decimals(self) -> None:
        code, _ = self._run([str(self.original), str(self.copied), str(self.answer)])
        self.assertEqual(code, EXIT_OK)
        content = self.answer.read_text(encoding="utf-8")
        self.assertRegex(content, r"^[01]\.\d\d\n$")

    def test_identical_files_produce_one(self) -> None:
        code, _ = self._run([str(self.original), str(self.original), str(self.answer)])
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(self.answer.read_text(encoding="utf-8"), "1.00\n")

    def test_argument_count_zero(self) -> None:
        code, message = self._run([])
        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertIn("用法", message)

    def test_argument_count_one(self) -> None:
        code, _ = self._run([str(self.original)])
        self.assertEqual(code, EXIT_USAGE_ERROR)

    def test_argument_count_two(self) -> None:
        code, _ = self._run([str(self.original), str(self.copied)])
        self.assertEqual(code, EXIT_USAGE_ERROR)

    def test_argument_count_four(self) -> None:
        code, _ = self._run([str(self.original), str(self.copied), str(self.answer), "extra"])
        self.assertEqual(code, EXIT_USAGE_ERROR)

    def test_missing_input_file_keeps_existing_answer(self) -> None:
        self.answer.write_text("keep\n", encoding="utf-8")
        code, message = self._run(
            [str(self.original), str(self.tmp / "missing.txt"), str(self.answer)]
        )
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("不存在", message)
        self.assertEqual(self.answer.read_text(encoding="utf-8"), "keep\n")

    def test_directory_as_result_returns_error(self) -> None:
        code, message = self._run([str(self.original), str(self.copied), str(self.tmp)])
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("目录", message)

    def test_directory_as_input_returns_error(self) -> None:
        code, _ = self._run([str(self.tmp), str(self.copied), str(self.answer)])
        self.assertEqual(code, EXIT_RUNTIME_ERROR)

    def test_empty_copied_file_returns_error(self) -> None:
        empty = self.tmp / "empty.txt"
        empty.write_text("", encoding="utf-8")
        code, message = self._run([str(self.original), str(empty), str(self.answer)])
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("有效文本", message)

    def test_punctuation_only_file_returns_error(self) -> None:
        punct = self.tmp / "punct.txt"
        punct.write_text("。。。！！！", encoding="utf-8")
        code, _ = self._run([str(self.original), str(punct), str(self.answer)])
        self.assertEqual(code, EXIT_RUNTIME_ERROR)

    def test_answer_not_created_when_input_missing(self) -> None:
        answer = self.tmp / "new_answer.txt"
        code, _ = self._run([str(self.original), str(self.tmp / "missing.txt"), str(answer)])
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertFalse(answer.exists())


if __name__ == "__main__":
    unittest.main()
