# -*- coding: utf-8 -*-
"""运行度量解析器（D-06）：`_运行度量.md` 步骤度量表 → run_metrics 表.

列映射：步骤→step_no / 开始时间→started_at / 结束时间→ended_at /
耗时(分钟)→duration_min / 轮次→round_no / 闸门报红次数→gate_reds /
失败日志条数→fail_count / Review/评审评分→review_score。
全空度量行跳过（文件存在但尚未填数时表 0 行，不算异常，T07 验收口径）。
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
    to_float,
    to_int,
)
from .sniff import sniff_run_metrics

RUN_METRICS_FILE = "_运行度量.md"

_FIELD_MAP = {
    "步骤": "step_no",
    "开始时间": "started_at",
    "结束时间": "ended_at",
    "耗时(分钟)": "duration_min",
    "轮次": "round_no",
    "闸门报红次数": "gate_reds",
    "失败日志条数": "fail_count",
    "Review/评审评分": "review_score",  # 归一后 'Review/评审评分'
}


class UnknownGeneration(Exception):
    """未知格式代际（§3-5）."""


@dataclass
class RunMetricRow:
    """run_metrics 表一行."""

    step_no: Optional[str] = None
    round_no: Optional[int] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_min: Optional[float] = None
    gate_reds: Optional[int] = None
    fail_count: Optional[int] = None
    review_score: Optional[str] = None


def parse_run_metrics(
    text: str, project_name: str, anomaly_log: Optional[AnomalyLog] = None
) -> List[RunMetricRow]:
    """解析步骤度量表；无该段落 → 空列表（不算异常）."""
    section = extract_section(text, r"步骤度量")
    if not section.strip():
        return []
    scanner = TableScanner()
    rows = list(scanner.rows(section))
    if not rows:
        return []
    header = rows[0][1]
    if sniff_run_metrics(header) is None:
        raise UnknownGeneration(f"{RUN_METRICS_FILE}：步骤度量表头无法识别：{header}")
    norm_header = [re.sub(r"\s+", "", c) for c in header]
    fields = [_FIELD_MAP.get(h) for h in norm_header]
    header_len = len(header)
    out: List[RunMetricRow] = []
    for lineno, cells in rows[1:]:
        aligned = align_row(
            cells, header_len, anomaly_log, RUN_METRICS_FILE, lineno
        )
        if aligned is None:
            continue
        raw: Dict[str, Optional[str]] = {}
        for field_name, cell in zip(fields, aligned):
            if field_name is None or field_name in raw:
                continue
            raw[field_name] = nonempty(cell)
        # 全空度量行跳过（模板占位行）
        if not any(
            raw.get(k)
            for k in ("started_at", "ended_at", "duration_min", "round_no",
                      "gate_reds", "fail_count", "review_score")
        ):
            continue
        out.append(
            RunMetricRow(
                step_no=normalize_step_label(raw.get("step_no") or ""),
                round_no=to_int(raw.get("round_no")),
                started_at=raw.get("started_at"),
                ended_at=raw.get("ended_at"),
                duration_min=to_float(raw.get("duration_min")),
                gate_reds=to_int(raw.get("gate_reds")),
                fail_count=to_int(raw.get("fail_count")),
                review_score=raw.get("review_score"),
            )
        )
    return out


def run_metrics_to_dicts(project_name: str, rows: List[RunMetricRow]) -> List[Dict]:
    """RunMetricRow 列表 → run_metrics 表插入行."""
    return [
        {
            "project_name": project_name,
            "step_no": r.step_no,
            "round_no": r.round_no,
            "started_at": r.started_at,
            "ended_at": r.ended_at,
            "duration_min": r.duration_min,
            "gate_reds": r.gate_reds,
            "fail_count": r.fail_count,
            "review_score": r.review_score,
        }
        for r in rows
    ]
