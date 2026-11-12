# -*- coding: utf-8 -*-
"""噪声规则集单测（T03 / D-07 / 架构 §3 规则 1-4）."""
from __future__ import annotations

from parsers.noise import (
    STATUS_ENUM,
    TableScanner,
    align_row,
    extract_section,
    is_separator_row,
    normalize_status,
    normalize_step_label,
    split_row,
    to_float,
    to_int,
)

from conftest import fixture_text


class TestCommentSkip:
    """§3-1 HTML 注释跳过."""

    def test_single_line_comment(self):
        text = "<!-- | Q-001 | P0 | 7 | 示例行 | -->\n| Q-002 | P1 | 8 | 真实 |"
        rows = list(TableScanner().rows(text))
        assert len(rows) == 1
        assert rows[0][1][0] == "Q-002"

    def test_multiline_comment(self):
        text = "<!--\n| Q-001 | P0 | 示例 |\n-->\n| Q-002 | P1 | 真实 |"
        scanner = TableScanner()
        rows = list(scanner.rows(text))
        assert len(rows) == 1
        # 注释起始行 + 内部行 + 结束行 = 3 行均被跳过计数
        assert scanner.skipped_comment_lines == 3

    def test_template_issue_ledger_comment(self):
        """真实夹具：台账主表含注释示例行，不得出数."""
        text = fixture_text("issues_prod.md")
        section = extract_section(text, "台账主表")
        rows = [c for _, c in TableScanner().rows(section)]
        ids = [r[0] for r in rows]
        assert "Q-001" in ids  # 真实行
        assert all("示例" not in i for i in ids)  # 注释示例行未混入


class TestCellTolerance:
    """§3-2 空单元格容错."""

    def test_split_row_keeps_empty(self):
        assert split_row("| a | | c |") == ["a", "", "c"]

    def test_separator_row(self):
        assert is_separator_row(["---", ":---:", "---"])
        assert not is_separator_row(["a", "b"])

    def test_align_row_pad(self):
        assert align_row(["a", "b"], 4) == ["a", "b", "", ""]

    def test_align_row_all_empty(self):
        assert align_row(["", ""], 3) is None

    def test_align_row_overflow_absorbs(self):
        from parsers.noise import AnomalyLog

        log = AnomalyLog("p")
        out = align_row(["a", "b", "c", "d", "e"], 3, log, "f.md", 7)
        assert out == ["a", "b", "c | d | e"]
        assert len(log.items) == 1
        assert log.items[0].line_no == 7


class TestStepNormalize:
    """§3-3 步骤号归一."""

    def test_variants(self):
        assert normalize_step_label("第5.5步") == "5.5"
        assert normalize_step_label("step6.5") == "6.5"
        assert normalize_step_label("6.5") == "6.5"
        assert normalize_step_label("5A") == "5A"
        assert normalize_step_label("f0") == "F0"
        assert normalize_step_label("👤 R-1") == "R-1"
        assert normalize_step_label("👤 9") == "9"
        assert normalize_step_label("10.0") == "10.0"  # 与 10 不撞车

    def test_invalid(self):
        assert normalize_step_label("0.1-0.5") is None
        assert normalize_step_label("F0~F4") is None
        assert normalize_step_label("") is None
        assert normalize_step_label(None) is None


class TestStatusNormalize:
    """§3-4 状态词归一映射 + 尾注剥离（E4）."""

    def test_enum_mapping(self):
        assert normalize_status("未开始") == ("未开始", None)
        assert normalize_status("进行中") == ("进行中", None)
        assert normalize_status("已完成") == ("已完成", None)
        assert normalize_status("卡在人工（等用户）") == ("卡在人工", "等用户")
        assert normalize_status("已回流") == ("已回流", None)

    def test_synonyms(self):
        assert normalize_status("✅ 已完成") == ("已完成", None)
        assert normalize_status("✅ 已通过") == ("已完成", None)
        assert normalize_status("已闭环") == ("已完成", None)
        assert normalize_status("已人工放行") == ("已完成", "人工放行")
        assert normalize_status("⏭️ 跳过") == ("不适用", "跳过")
        assert normalize_status("忽略") == ("不适用", "忽略")
        assert normalize_status("已豁免") == ("不适用", "已豁免")

    def test_note_extraction(self):
        assert normalize_status("已完成（附条件通过）") == ("已完成", "附条件通过")
        assert normalize_status("已完成（代码骨架）") == ("已完成", "代码骨架")

    def test_unmapped_returns_raw(self):
        status, note = normalize_status("待定")
        assert status == "待定"
        assert status not in STATUS_ENUM

    def test_empty(self):
        assert normalize_status("") == (None, None)
        assert normalize_status(None) == (None, None)


class TestValueHelpers:
    def test_to_int(self):
        assert to_int("1") == 1
        assert to_int("R2") == 2
        assert to_int("") is None
        assert to_int(None) is None

    def test_to_float(self):
        assert to_float("12.5") == 12.5
        assert to_float("") is None

    def test_extract_section_levels(self):
        text = "# 顶层\n\n## 目标段\n\n内容行\n\n## 下一节\n\n其他"
        assert "内容行" in extract_section(text, "目标段")
        assert "其他" not in extract_section(text, "目标段")
