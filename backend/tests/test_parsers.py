# -*- coding: utf-8 -*-
"""四类产物解析器单测（T04–T07 / D-03~D-06）：全部用仓内真实夹具."""
from __future__ import annotations

import pytest

from parsers.board import UnknownGeneration, parse_board
from parsers.failures import parse_failures
from parsers.issues import parse_issues
from parsers.run_metrics import parse_run_metrics
from parsers.sniff import (
    sniff_board,
    sniff_failure_log,
    sniff_issues,
    sniff_run_metrics,
)

from conftest import fixture_text


class TestSniff:
    """T02 版本嗅探：各代际表头识别."""

    def test_failure_gens(self):
        assert sniff_failure_log(["时间", "步骤", "失败类别", "问题描述", "AI 所犯错误", "人工卡点发现的 AI 遗漏", "修复轮次", "根因分类"]) == "fail_g1"
        assert sniff_failure_log(["时间", "步骤", "失败类别", "问题描述", "AI 所犯错误", "人工卡点发现的 AI 遗漏", "修复轮次", "根因分类", "影响文件", "复现命令", "触发规则"]) == "fail_g2"
        assert sniff_failure_log(["日期", "步骤", "类别", "根因", "影响文件", "复现命令", "处理"]) == "fail_g3"
        assert sniff_failure_log(["ID", "日期", "步骤", "类别", "现象", "根因", "影响文件", "复现命令", "处置"]) == "fail_g4"
        assert sniff_failure_log(["随便", "列"]) is None

    def test_issues_gens(self):
        assert sniff_issues(["ID", "级别", "来源阶段", "现象", "根因标签", "状态", "轮次", "归属"]) == "iss_prod"
        assert sniff_issues(["ID", "级别", "标题", "状态", "发现步骤", "根因路由", "修复步骤", "轮次", "备注"]) == "iss_renov"
        assert sniff_issues(["ID", "级别"]) is None

    def test_board_gens(self):
        assert sniff_board(["步骤", "名称", "状态", "产物路径", "完成时间", "备注/遗留"]) == "board_prod"
        assert sniff_board(["步骤", "名称", "状态", "产物路径", "备注"]) == "board_renov"
        assert sniff_board(["步骤", "名称", "状态", "实际情况"]) == "board_v0"
        assert sniff_board(["步骤", "名称"]) is None

    def test_run_metrics(self):
        assert sniff_run_metrics(["步骤", "开始时间", "结束时间", "耗时(分钟)", "轮次", "闸门报红次数", "失败日志条数", "Review/评审评分", "备注"]) == "run_metrics_v1"
        assert sniff_run_metrics(["步骤", "名称"]) is None


class TestBoardParser:
    """T04 看板解析器（真实夹具：cpp 生产代 / SparrowScheduler 翻新代）."""

    def test_prod_generation(self):
        board = parse_board(fixture_text("board_prod.md"), "fixture-prod")
        assert board.gen == "board_prod"
        assert board.basic.route == "生产"
        assert board.basic.declared_failure_count == 3  # 失败日志段兜底解析
        assert len(board.steps) >= 15
        assert board.step_rows_raw == len(board.steps)  # 本夹具无区间行
        # E4：附加条件通过 → note
        by_step = {s.step_no: s for s in board.steps}
        assert by_step["5.5"].status == "已完成"
        assert by_step["9"].status == "已完成"
        # 循环轮次已解析
        assert len(board.rounds) >= 1

    def test_renov_generation(self):
        board = parse_board(fixture_text("board_renov.md"), "fixture-renov")
        assert board.gen == "board_renov"
        assert board.basic.route == "翻新"
        by_step = {s.step_no: s for s in board.steps}
        # 👤 前缀人工卡点行（§3-3 扩展）
        assert by_step["R-1"].step_name == "基线拍板"
        assert by_step["R-1"].status == "已完成"
        # ⏭️ 跳过 → 不适用 + note（状态尾注「跳过」+ 备注列合并）
        assert by_step["7.5"].status == "不适用"
        assert by_step["7.5"].note.startswith("跳过")

    def test_v0_generation_inline(self):
        text = (
            "## 基本信息\n\n- 项目名：早期项目\n- 当前阶段：已完成\n- 总体状态：已完成\n\n"
            "## 步骤进度\n\n| 步骤 | 名称 | 状态 | 实际情况 |\n|---|---|---|---|\n"
            "| 1 | 基线 | ✅ 已完成 | 用户确认过 |\n| 5A | 后端 | ✅ 已完成 | mvn 通过 |\n"
        )
        board = parse_board(text, "early")
        assert board.gen == "board_v0"
        assert len(board.steps) == 2
        assert board.steps[0].status == "已完成"
        assert board.steps[0].note == "用户确认过"
        assert board.steps[0].artifact_path is None

    def test_range_row_registered_not_parsed(self):
        text = (
            "## 基本信息\n\n- 项目名：X\n- 总体状态：进行中\n\n"
            "## 步骤进度\n\n| 步骤 | 名称 | 状态 | 产物路径 | 完成时间 | 备注/遗留 |\n"
            "|---|---|---|---|---|---|\n"
            "| 0.1-0.5 | 汇总行 | 已完成 | - | | |\n"
            "| 6 | 冒烟 | 未开始 | `06_冒烟/` | | |\n"
        )
        from parsers.noise import AnomalyLog

        log = AnomalyLog("X")
        board = parse_board(text, "X", log)
        assert len(board.steps) == 1
        assert board.steps[0].step_no == "6"
        assert len(log.items) == 1  # 0.1-0.5 显式登记
        assert board.step_rows_raw == 2  # 原始行数与入库行数分离（对账 B 输入）

    def test_unknown_generation(self):
        with pytest.raises(UnknownGeneration):
            parse_board("# 垃圾\n没有表格", "X")


class TestFailuresParser:
    """T05 失败日志解析器（4 代真实夹具）."""

    def test_g1_with_drift(self):
        """G1 表头 + G2 漂移行（saas 真实形态，§3-6 按日期双策略）."""
        from parsers.noise import AnomalyLog

        log = AnomalyLog("saas")
        rows = parse_failures(fixture_text("fail_g1.md"), "saas", log)
        assert len(rows) >= 5
        drift = [a for a in log.items if a.action == "按日期兼容"]
        assert drift, "漂移行应显式登记"
        # 漂移行的 triggered_rule 已按 G2 兼容解析（R8/R12 类）
        assert any(r.triggered_rule and r.triggered_rule.startswith("R") for r in rows)
        # 旧 8 列行：response_type/findings_count 为 NULL（E2 缺列）
        assert all(r.response_type is None and r.findings_count is None for r in rows)
        assert all(r.occurred_at for r in rows)
        assert any(r.step_no == "6" for r in rows)

    def test_g2(self):
        rows = parse_failures(fixture_text("fail_g2.md"), "shopmate")
        assert len(rows) == 2
        r = rows[0]
        assert r.step_no == "5.5"
        assert r.triggered_rule == "R9"
        assert r.impact_files is not None

    def test_g3_renov(self):
        rows = parse_failures(fixture_text("fail_g3.md"), "sparrow")
        assert len(rows) == 2
        assert all(r.round_no is None for r in rows)  # 翻新代无修复轮次列

    def test_g4(self):
        rows = parse_failures(fixture_text("fail_g4.md"), "llm-eval")
        assert len(rows) == 1  # llm-eval 真实日志仅 1 条记录
        assert rows[0].occurred_at == "2026-10-30"
        assert rows[0].step_no == "6.5"
        assert rows[0].category == "脚本误报"

    def test_unknown(self):
        from parsers.failures import UnknownGeneration

        with pytest.raises(UnknownGeneration):
            parse_failures("| 时间 | 步骤 | 随便 | 列 |\n|---|---|---|---|\n| x | y | z | w |", "X")


class TestIssuesParser:
    """T06 台账解析器（E1 降级口径核心）."""

    def test_prod_generation(self):
        """真实夹具：nestjs 行 + 模板注释示例行跳过."""
        rows = parse_issues(fixture_text("issues_prod.md"), "nestjs")
        assert len(rows) == 3
        q1 = rows[0]
        assert q1.issue_id == "Q-001"
        assert q1.found_step == "5.5"  # 来源阶段全量可算
        assert q1.source_step_inferred == "6"  # 归属「第6步已修」文本推断
        assert q1.root_cause_tag == "跨文件不一致"
        assert q1.round_no == 1

    def test_inference_variants(self):
        assert parse_issues(fixture_text("issues_prod.md"), "x")[0].source_step_inferred == "6"

    def test_renov_generation(self):
        rows = parse_issues(fixture_text("issues_renov.md"), "sparrow")
        assert len(rows) >= 8
        iss1 = [r for r in rows if r.issue_id == "ISS-001"][0]
        assert iss1.found_step == "F2"
        assert iss1.source_step_inferred is None  # 「F3 补实现」不可推断 → NULL（E1）
        assert iss1.root_cause_tag == "实现缺口"

    def test_unknown(self):
        from parsers.issues import UnknownGeneration

        with pytest.raises(UnknownGeneration):
            parse_issues("# 没有台账", "X")


class TestRunMetricsParser:
    """T07 度量台账解析器."""

    def test_filled_rows_skip_empty(self):
        rows = parse_run_metrics(fixture_text("run_metrics_filled.md"), "x")
        assert len(rows) == 2  # 5B 全空行被跳过
        r5a = rows[0]
        assert r5a.step_no == "5A"
        assert r5a.duration_min == 80.0
        assert r5a.round_no == 1
        assert r5a.gate_reds == 1
        assert r5a.fail_count == 2
        assert r5a.review_score == "4.5"
        assert rows[1].step_no == "6"

    def test_no_section_returns_empty(self):
        assert parse_run_metrics("# 无度量文件", "x") == []
