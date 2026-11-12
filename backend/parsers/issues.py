# -*- coding: utf-8 -*-
"""问题台账解析器（D-05 / E1 修订核心）：`_问题台账.md` → issues 表.

覆盖 2 个格式代际：
- iss_prod（生产 8列·台账主表） ID/级别/来源阶段/现象/根因标签/状态/轮次/归属
- iss_renov（翻新 9列·问题清单） ID/级别/标题/状态/发现步骤/根因路由/修复步骤/轮次/备注

E1 降级口径落点：
- found_step = 来源阶段|发现步骤 列原值归一（全量可算）
- source_step_inferred = 归属|修复步骤 列文本推断（正则取「第X步」；可空，翻新 F3 类文本不可算 → NULL）
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .noise import (
    AnomalyLog,
    TableScanner,
    align_row,
    extract_section,
    nonempty,
    normalize_step_label,
    to_int,
)
from .sniff import sniff_issues

ISSUES_FILE = "_问题台账.md"

# 归一后表头名 → issues 字段
_FIELD_MAP = {
    "ID": "issue_id",
    "级别": "level",
    "现象": "title",
    "标题": "title",
    "根因标签": "root_cause_tag",
    "根因路由": "root_cause_tag",
    "状态": "status",
    "轮次": "round_no",
    "来源阶段": "found_step",
    "发现步骤": "found_step",
    "归属": "source_step_inferred_src",  # 文本推断（E1）
    "修复步骤": "source_step_inferred_src",  # 文本推断（E1）
}

# 归属/修复步骤文本中推断步骤号的正则（「第 7 步修复」→ 7）
_INFER_RE = re.compile(r"第\s*([0-9]+(?:\.[0-9]+)?)\s*步")


class UnknownGeneration(Exception):
    """未知格式代际（§3-5）."""


@dataclass
class IssueRow:
    """issues 表一行."""

    issue_id: Optional[str] = None
    level: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None
    found_step: Optional[str] = None
    source_step_inferred: Optional[str] = None
    root_cause_tag: Optional[str] = None
    round_no: Optional[int] = None


def parse_issues(
    text: str, project_name: str, anomaly_log: Optional[AnomalyLog] = None
) -> List[IssueRow]:
    """解析台账主表（生产代际）或问题清单（翻新代际）→ IssueRow 列表."""
    # 先找「台账主表」段（生产），找不到再找「问题清单」段（翻新）
    section = extract_section(text, r"台账主表")
    if not section.strip():
        section = extract_section(text, r"问题清单")
    if not section.strip():
        raise UnknownGeneration(f"{ISSUES_FILE}：未找到 台账主表/问题清单 段落")
    scanner = TableScanner()
    rows = list(scanner.rows(section))
    if not rows:
        raise UnknownGeneration(f"{ISSUES_FILE}：问题表为空")
    header = rows[0][1]
    gen = sniff_issues(header)
    if gen is None:
        raise UnknownGeneration(f"{ISSUES_FILE}：表头无法识别代际：{header}")
    norm_header = [re.sub(r"\s+", "", c) for c in header]
    fields = [_FIELD_MAP.get(h) for h in norm_header]
    header_len = len(header)
    out: List[IssueRow] = []
    for lineno, cells in rows[1:]:
        aligned = align_row(cells, header_len, anomaly_log, ISSUES_FILE, lineno)
        if aligned is None:
            continue
        raw: Dict[str, Optional[str]] = {}
        for field_name, cell in zip(fields, aligned):
            if field_name is None or field_name in raw:
                continue
            raw[field_name] = nonempty(cell)
        if not raw.get("issue_id"):  # 无 ID 的行（表尾合计等）跳过
            continue
        infer_src = raw.get("source_step_inferred_src")
        inferred = None
        if infer_src:
            m = _INFER_RE.search(infer_src)
            if m:
                inferred = m.group(1)  # E1：仅可推断时才参与逃逸矩阵计数
        out.append(
            IssueRow(
                issue_id=raw.get("issue_id"),
                level=raw.get("level"),
                status=raw.get("status"),
                title=raw.get("title"),
                found_step=normalize_step_label(raw.get("found_step") or ""),
                source_step_inferred=inferred,
                root_cause_tag=raw.get("root_cause_tag"),
                round_no=to_int(raw.get("round_no")),
            )
        )
    return out


def issues_to_dicts(project_name: str, rows: List[IssueRow]) -> List[Dict]:
    """IssueRow 列表 → issues 表插入行."""
    return [
        {
            "project_name": project_name,
            "issue_id": r.issue_id,
            "level": r.level,
            "status": r.status,
            "title": r.title,
            "found_step": r.found_step,
            "source_step_inferred": r.source_step_inferred,
            "root_cause_tag": r.root_cause_tag,
            "round_no": r.round_no,
        }
        for r in rows
    ]
