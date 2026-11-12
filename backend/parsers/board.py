# -*- coding: utf-8 -*-
"""看板解析器（D-03）：`_项目状态.md` → 基本信息 / 步骤表 / 循环轮次.

- 步骤表 → step_status 出数（T04 验收：SQL 行数 = 看板步骤行数）
- 状态词按 §3-4 归一（E4），尾注不丢
- 循环轮次表已解析并返回（架构 §4 无对应表，不入库，供对账引擎与测试交叉校验）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .noise import (
    AnomalyLog,
    TableScanner,
    align_row,
    extract_section,
    nonempty,
    normalize_status,
    normalize_step_label,
    to_int,
)
from .sniff import sniff_board

BOARD_FILE = "_项目状态.md"
# 步骤进度表列（三代：prod 6 列 / renov 5 列 / v0 4 列，见 sniff.py）
_PROD_COLS = ["步骤", "名称", "状态", "产物路径", "完成时间", "备注/遗留"]
_RENOV_COLS = ["步骤", "名称", "状态", "产物路径", "备注"]
_V0_COLS = ["步骤", "名称", "状态", "实际情况"]


class UnknownGeneration(Exception):
    """未知格式代际（§3-5）：整文件降级登记用."""


@dataclass
class BoardBasic:
    """基本信息段（projects 表落点）."""

    name: Optional[str] = None
    route: Optional[str] = None
    board_status: Optional[str] = None
    current_stage: Optional[str] = None
    declared_failure_count: Optional[int] = None  # 「累计失败记录数」（对账 B 规则用）


@dataclass
class StepRow:
    """step_status 表一行."""

    step_no: str
    step_name: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    finished_at: Optional[str] = None
    artifact_path: Optional[str] = None


@dataclass
class RoundRow:
    """循环轮次表一行（解析不入库，交叉校验用）."""

    loop_name: Optional[str] = None
    step_no: Optional[str] = None
    used_rounds: Optional[int] = None
    limit_text: Optional[str] = None
    problems: Optional[str] = None
    result: Optional[str] = None


@dataclass
class BoardResult:
    basic: BoardBasic = field(default_factory=BoardBasic)
    steps: List[StepRow] = field(default_factory=list)
    rounds: List[RoundRow] = field(default_factory=list)
    step_rows_raw: int = 0  # 源文件步骤表实际数据行数（对账 B 规则勾稽用）
    gen: Optional[str] = None


def parse_board(text: str, project_name: str, anomaly_log: Optional[AnomalyLog] = None) -> BoardResult:
    """解析看板全文，返回基本信息 + 步骤表 + 循环轮次.

    未知代际抛 UnknownGeneration，由 collect 捕获后整文件降级（§3-5 / D-08）。
    """
    result = BoardResult()
    result.basic = _parse_basic(text)
    result.steps, result.step_rows_raw, result.gen = _parse_steps(
        text, project_name, anomaly_log
    )
    result.rounds = _parse_rounds(text)
    return result


def _parse_basic(text: str) -> BoardBasic:
    """基本信息段：项目名 / 路线 / 总体状态 / 当前阶段 / 累计失败记录数.

    「累计失败记录数」可能在「## 失败日志」段（新代际看板）而非基本信息段，
    兜底全文搜索（对账 B1 规则输入）。
    """
    basic = BoardBasic()
    section = extract_section(text, r"基本信息")
    for line in section.splitlines():
        s = line.strip().lstrip("-").strip()
        if not s:
            continue
        m = re.match(r"^\*{0,2}项目名\*{0,2}\s*[：:]\s*(.+)$", s)
        if m and basic.name is None:
            basic.name = m.group(1).replace("**", "").strip()
            continue
        m = re.match(r"^\*{0,2}路线\*{0,2}\s*[：:]\s*(.+)$", s)
        if m and basic.route is None:
            v = m.group(1).replace("**", "").strip()
            basic.route = "翻新" if v.startswith("翻新") else ("生产" if v.startswith("生产") else v)
            continue
        m = re.match(r"^\*{0,2}总体状态\*{0,2}\s*[：:]\s*(.+)$", s)
        if m and basic.board_status is None:
            basic.board_status = m.group(1).replace("**", "").strip()
            continue
        m = re.match(r"^\*{0,2}当前阶段\*{0,2}\s*[：:]\s*(.+)$", s)
        if m and basic.current_stage is None:
            basic.current_stage = m.group(1).replace("**", "").strip()
            continue
        m = re.match(r"^累计失败记录数\s*[：:]\s*(\d+)\s*$", s)
        if m and basic.declared_failure_count is None:
            basic.declared_failure_count = int(m.group(1))
            continue
    if basic.declared_failure_count is None:  # 兜底：全文搜索（失败日志段）
        m = re.search(r"累计失败记录数\s*[：:]\s*(\d+)", text)
        if m:
            basic.declared_failure_count = int(m.group(1))
    return basic


def _parse_steps(
    text: str, project_name: str, anomaly_log: Optional[AnomalyLog]
):
    """步骤进度表 → StepRow 列表（状态归一 §3-4）."""
    section = extract_section(text, r"步骤进度")
    scanner = TableScanner()
    rows = list(scanner.rows(section))
    if not rows:
        raise UnknownGeneration(f"{BOARD_FILE}：未找到步骤进度表或表为空")
    header = rows[0][1]
    gen = sniff_board(header)
    if gen is None:
        raise UnknownGeneration(f"{BOARD_FILE}：步骤表表头无法识别代际：{header}")
    if gen == "board_prod":
        header_len = len(_PROD_COLS)
    elif gen == "board_renov":
        header_len = len(_RENOV_COLS)
    else:  # board_v0（早期 4 列：无产物路径/完成时间，实际情况并入 note）
        header_len = len(_V0_COLS)
    steps: List[StepRow] = []
    raw_count = 0
    for lineno, cells in rows[1:]:
        aligned = align_row(
            cells, header_len, anomaly_log, BOARD_FILE, lineno
        )
        if aligned is None:
            continue
        raw_count += 1
        label = normalize_step_label(aligned[0])
        if label is None:  # 区间汇总行（'0.1-0.5'/'F0~F4'）等无法归一的行
            if anomaly_log is not None:
                anomaly_log.add(
                    BOARD_FILE,
                    f"步骤列无法归一：{aligned[0]!r}",
                    line_no=lineno,
                    action="跳过该行",
                )
            continue
        status, note = normalize_status(aligned[2])
        if gen == "board_prod":
            remark = nonempty(aligned[5])
            finished_at = nonempty(aligned[4])
            artifact_path = nonempty(aligned[3])
        elif gen == "board_renov":
            remark = nonempty(aligned[4])
            finished_at = None
            artifact_path = nonempty(aligned[3])
        else:  # board_v0
            remark = nonempty(aligned[3])
            finished_at = None
            artifact_path = None
        if note and remark:
            note = f"{note}；{remark}"
        elif remark:
            note = remark
        steps.append(
            StepRow(
                step_no=label,
                step_name=nonempty(aligned[1]),
                status=status,
                note=note,
                finished_at=finished_at,
                artifact_path=artifact_path,
            )
        )
    return steps, raw_count, gen


def _parse_rounds(text: str) -> List[RoundRow]:
    """循环轮次计数表（D-03 解析范围之一；不入库，交叉校验用）."""
    section = extract_section(text, r"循环轮次计数")
    scanner = TableScanner()
    rounds: List[RoundRow] = []
    for _, cells in scanner.rows(section):
        if cells[0] in ("循环", ""):
            continue
        m = re.search(r"第\s*([0-9]+(?:\.[0-9]+)?)\s*步", cells[0] or "")
        rounds.append(
            RoundRow(
                loop_name=nonempty(cells[0]),
                step_no=m.group(1) if m else None,
                used_rounds=to_int(cells[1]) if len(cells) > 1 else None,
                limit_text=nonempty(cells[2]) if len(cells) > 2 else None,
                problems=nonempty(cells[3]) if len(cells) > 3 else None,
                result=nonempty(cells[4]) if len(cells) > 4 else None,
            )
        )
    return rounds


def steps_to_dicts(project_name: str, steps: List[StepRow]) -> List[Dict]:
    """StepRow 列表 → step_status 表插入行."""
    return [
        {
            "project_name": project_name,
            "step_no": s.step_no,
            "step_name": s.step_name,
            "status": s.status,
            "note": s.note,
            "finished_at": s.finished_at,
            "artifact_path": s.artifact_path,
        }
        for s in steps
    ]
