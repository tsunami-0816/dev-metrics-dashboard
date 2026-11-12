# -*- coding: utf-8 -*-
"""失败日志解析器（D-04）：`_失败日志.md` → failures 表.

覆盖仓内 4 个格式代际（表头嗅探路由，§3-5）：
- fail_g1（8列）  时间/步骤/失败类别/问题描述/AI所犯错误/人工卡点发现的AI遗漏/修复轮次/根因分类
- fail_g2（11列） g1 + 影响文件/复现命令/触发规则
- fail_g3（7列·翻新） 日期/步骤/类别/根因/影响文件/复现命令/处理
- fail_g4（9列）  ID/日期/步骤/类别/现象/根因/影响文件/复现命令/处置

列映射（→ failures 表字段）：
  时间|日期→occurred_at；步骤→step_no；失败类别|类别→category；
  根因分类|根因→root_cause；修复轮次→round_no；影响文件→impact_files；
  触发规则→triggered_rule；响应类型→response_type（§3-6，现有代际均缺列→NULL）；
  findings数→findings_count（同上）。
  以下源列不入库（源文件是唯一事实源，可随时重跑采集）：
  ID/现象/问题描述/AI所犯错误/人工卡点发现的AI遗漏/复现命令/处理/处置。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .noise import (
    AnomalyLog,
    TableScanner,
    align_row,
    nonempty,
    normalize_step_label,
    to_int,
)
from .sniff import sniff_failure_log

FAILURES_FILE = "_失败日志.md"

# 归一后表头名 → failures 字段
_FIELD_MAP = {
    "时间": "occurred_at",
    "日期": "occurred_at",
    "步骤": "step_no",
    "失败类别": "category",
    "类别": "category",
    "根因分类": "root_cause",
    "根因": "root_cause",
    "修复轮次": "round_no",
    "影响文件": "impact_files",
    "触发规则": "triggered_rule",
    "响应类型": "response_type",  # §3-6 新列可空策略
    "findings数": "findings_count",  # §3-6
}


class UnknownGeneration(Exception):
    """未知格式代际（§3-5）."""


@dataclass
class FailureRow:
    """failures 表一行."""

    occurred_at: Optional[str] = None
    step_no: Optional[str] = None
    category: Optional[str] = None
    root_cause: Optional[str] = None
    round_no: Optional[int] = None
    response_type: Optional[str] = None
    findings_count: Optional[int] = None
    impact_files: Optional[str] = None
    triggered_rule: Optional[str] = None


def parse_failures(
    text: str, project_name: str, anomaly_log: Optional[AnomalyLog] = None
) -> List[FailureRow]:
    """解析失败日志全文 → FailureRow 列表.

    未知代际抛 UnknownGeneration；坏行跳过登记（D-08），不中断。
    """
    scanner = TableScanner()
    rows = list(scanner.rows(text))
    header_idx: Optional[int] = None
    for i, (_, cells) in enumerate(rows):
        if any(c in ("时间", "日期") for c in cells):
            header_idx = i
            break
    if header_idx is None:
        raise UnknownGeneration(f"{FAILURES_FILE}：未找到含 时间/日期 列的表头")
    header = rows[header_idx][1]
    gen = sniff_failure_log(header)
    if gen is None:
        raise UnknownGeneration(f"{FAILURES_FILE}：表头无法识别代际：{header}")
    norm_header = [re.sub(r"\s+", "", c) for c in header]
    fields = [_FIELD_MAP.get(h) for h in norm_header]  # None = 不入库列
    # §3-6 记录日期双策略：G1 表头（8列）下 2026-10-28 后的行带 3 个新增列
    # （影响文件/复现命令/触发规则），按 G2 行兼容解析，显式登记不静默
    fields_g2_drift = fields + ["impact_files", None, "triggered_rule"]
    header_len = len(header)
    out: List[FailureRow] = []
    for lineno, cells in rows[header_idx + 1 :]:
        row_fields = fields
        if gen == "fail_g1" and len(cells) == len(fields_g2_drift):
            if anomaly_log is not None:
                anomaly_log.add(
                    FAILURES_FILE,
                    "表头 8 列但本行 11 列（2026-10-28 后新增列未同步表头，代际漂移），按 G2 行兼容解析",
                    line_no=lineno,
                    action="按日期兼容",
                )
            row_fields = fields_g2_drift
            aligned = cells
        else:
            aligned = align_row(
                cells, header_len, anomaly_log, FAILURES_FILE, lineno
            )
        if aligned is None:
            continue
        row = FailureRow()
        raw: Dict[str, Optional[str]] = {}
        for field_name, cell in zip(row_fields, aligned):
            if field_name is None or field_name in raw:
                continue
            raw[field_name] = nonempty(cell)
        if not any(v for k, v in raw.items() if k != "step_no"):
            continue  # 全空行（§3-2）
        row.occurred_at = raw.get("occurred_at")
        row.step_no = normalize_step_label(raw.get("step_no") or "")
        row.category = raw.get("category")
        row.root_cause = raw.get("root_cause")
        row.round_no = to_int(raw.get("round_no"))
        row.response_type = raw.get("response_type")  # 缺列 → None（E2）
        row.findings_count = to_int(raw.get("findings_count"))
        row.impact_files = raw.get("impact_files")
        # '—'/'-' 是「无」的占位写法，不算有效触发规则
        trig = raw.get("triggered_rule")
        row.triggered_rule = None if trig in ("—", "-", "–", "无") else trig
        out.append(row)
    return out


def failures_to_dicts(project_name: str, rows: List[FailureRow]) -> List[Dict]:
    """FailureRow 列表 → failures 表插入行."""
    return [
        {
            "project_name": project_name,
            "occurred_at": r.occurred_at,
            "step_no": r.step_no,
            "category": r.category,
            "root_cause": r.root_cause,
            "round_no": r.round_no,
            "response_type": r.response_type,
            "findings_count": r.findings_count,
            "impact_files": r.impact_files,
            "triggered_rule": r.triggered_rule,
        }
        for r in rows
    ]
