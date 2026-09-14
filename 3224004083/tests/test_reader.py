# -*- coding: utf-8 -*-
"""文本规范化与文件读取的单元测试。

运行方式（在学号目录下）::

    python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

# unittest 的 setUp/tearDown 本身就是临时资源的标准管理方式，这里没法用 with，
# 因此豁免 consider-using-with 检查（只用在本文件的测试夹具上）。
# pylint: disable=consider-using-with

from plagiarism.errors import FileReadError
from plagiarism.normalize import normalize, normalize_reference
from plagiarism.reader import read_text, strip_html


class NormalizeTest(unittest.TestCase):
    """文本规范化：只保留汉字、字母与数字。"""

    def test_removes_whitespace_and_punctuation(self) -> None:
        self.assertEqual(
            normalize("今天是星期天，天气晴。\n\t 晚上 看电影"), "今天是星期天天气晴晚上看电影"
        )

    def test_lowercases_latin_letters(self) -> None:
        self.assertEqual(normalize("Hello World!"), "helloworld")

    def test_keeps_digits(self) -> None:
        self.assertEqual(normalize("第 1 章：复用率 25%"), "第1章复用率25")

    def test_different_punctuation_yields_same_result(self) -> None:
        self.assertEqual(normalize("你好，世界！"), normalize("你好 世界"))

    def test_translate_version_matches_reference(self) -> None:
        # 查表 + translate 的快速实现必须与逐字符参考实现完全一致，
        # 防止"性能优化改坏了语义"。
        samples = [
            "",
            "。。。！？",
            "Hello, World! 123",
            "ＡＢＣ１２３",
            "今天是星期天，天气晴。",
            "Mixed 中英 text 2026",
            "café Ünïcode ∑∆",
        ]
        for sample in samples:
            self.assertEqual(normalize(sample), normalize_reference(sample))


class StripHtmlTest(unittest.TestCase):
    """HTML 噪声剥离。"""

    def test_plain_text_is_untouched(self) -> None:
        self.assertEqual(strip_html("这是一段普通文本。"), "这是一段普通文本。")

    def test_removes_tags_and_scripts(self) -> None:
        html = "<html><body><p>正文内容</p><script>var a=1;</script></body></html>"
        cleaned = strip_html(html)
        self.assertIn("正文内容", cleaned)
        self.assertNotIn("<", cleaned)
        self.assertNotIn("var a=1", cleaned)

    def test_decodes_entities(self) -> None:
        cleaned = strip_html("<div>甲&nbsp;乙&amp;丙&hellip;</div>")
        self.assertIn("甲", cleaned)
        self.assertIn("&", cleaned)
        self.assertNotIn("&nbsp;", cleaned)


class ReadTextTest(unittest.TestCase):
    """文件读取：编码识别、BOM、归一化与错误处理。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_reads_utf8_file(self) -> None:
        path = self.tmp / "a.txt"
        path.write_text("今天是星期天", encoding="utf-8")
        self.assertEqual(read_text(str(path)), "今天是星期天")

    def test_removes_bom(self) -> None:
        path = self.tmp / "bom.txt"
        path.write_bytes("\ufeff今天是星期天".encode("utf-8"))
        self.assertFalse(read_text(str(path)).startswith("\ufeff"))
        self.assertEqual(read_text(str(path)), "今天是星期天")

    def test_reads_gb18030_file(self) -> None:
        path = self.tmp / "gbk.txt"
        path.write_bytes("论文查重程序".encode("gb18030"))
        self.assertEqual(read_text(str(path)), "论文查重程序")

    def test_normalizes_fullwidth_characters(self) -> None:
        path = self.tmp / "full.txt"
        path.write_text("ＡＢＣ１２３", encoding="utf-8")
        self.assertEqual(read_text(str(path)), "ABC123")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileReadError):
            read_text(str(self.tmp / "missing.txt"))

    def test_directory_path_raises(self) -> None:
        with self.assertRaises(FileReadError):
            read_text(str(self.tmp))

    def test_empty_path_raises(self) -> None:
        with self.assertRaises(FileReadError):
            read_text("")


if __name__ == "__main__":
    unittest.main()
