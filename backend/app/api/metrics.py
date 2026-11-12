# -*- coding: utf-8 -*-
"""GET /api/metrics（D-14 / T13）：指标全景.

- 返工率（全量口径）
- 门禁报红趋势（增量口径：gate_reds = 失败日志 triggered_rule + 度量台账交叉提取）
- 逃逸矩阵（E1 降级口径：found_step × source_step_inferred，仅可推断项目计数；覆盖率 N/M 同步返回）
- 跨项目对比（全量口径）
每个指标块带 D-25 覆盖范围标注。
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..db import db_has_data, get_conn
from ..response import coverage_tag, empty_db, ok

router = APIRouter()


@router.get("/metrics", summary="指标全景（返工率/报红趋势/逃逸矩阵/跨项目对比）", tags=["metrics"])
def metrics_overview(conn=Depends(get_conn)) -> Dict[str, Any]:
    if conn is None or not db_has_data(conn):
        return empty_db()

    # ---- 返工率（全量）：有失败记录的项目占比 + 每项目失败数 ----
    total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    per_project_failures = [
        {"project": r["project_name"], "failure_count": r["cnt"]}
        for r in conn.execute(
            "SELECT project_name, COUNT(*) AS cnt FROM failures "
            "GROUP BY project_name ORDER BY cnt DESC"
        )
    ]
    with_rework = len(per_project_failures)

    # ---- 报红趋势（增量口径）：按日期聚合 gate_reds ----
    gate_trend = [
        {"date": r["d"], "count": r["cnt"]}
        for r in conn.execute(
            "SELECT SUBSTR(red_at, 1, 10) AS d, COUNT(*) AS cnt FROM gate_reds "
            "WHERE red_at IS NOT NULL AND LENGTH(red_at) >= 10 "
            "GROUP BY d ORDER BY d"
        )
    ]
    gate_total = conn.execute("SELECT COUNT(*) FROM gate_reds").fetchone()[0]

    # ---- 逃逸矩阵（E1 降级口径 + 覆盖率 D-25）----
    matrix_rows = [
        {
            "found_step": r["found_step"],
            "source_step_inferred": r["source_step_inferred"],
            "count": r["cnt"],
        }
        for r in conn.execute(
            "SELECT found_step, source_step_inferred, cnt FROM v_escape_matrix "
            "ORDER BY cnt DESC, found_step, source_step_inferred"
        )
    ]
    cov = conn.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(source_step_inferred IS NOT NULL AND found_step IS NOT NULL) AS inferable "
        "FROM issues"
    ).fetchone()
    issues_total = cov["total"] or 0
    inferable = cov["inferable"] or 0

    # ---- 跨项目对比（全量）----
    cross = []
    for row in conn.execute(
        "SELECT name, route, board_status FROM projects ORDER BY name"
    ):
        steps = conn.execute(
            "SELECT COUNT(*) AS t, SUM(status = '已完成') AS d, "
            "SUM(status = '不适用') AS na FROM step_status "
            "WHERE project_name = ?",
            (row["name"],),
        ).fetchone()
        failures_n = conn.execute(
            "SELECT COUNT(*) FROM failures WHERE project_name = ?", (row["name"],)
        ).fetchone()[0]
        open_issues = conn.execute(
            "SELECT COUNT(*) FROM issues WHERE project_name = ? "
            "AND status IN ('open','fixed')",
            (row["name"],),
        ).fetchone()[0]
        reds = conn.execute(
            "SELECT COUNT(*) FROM gate_reds WHERE project_name = ?", (row["name"],)
        ).fetchone()[0]
        steps_total = steps["t"] or 0
        steps_done = steps["d"] or 0
        # ISS-REV-002（5.5 Review P1）：completion 口径与 /api/projects 统一，
        # 排除「不适用」步骤（done/(total-na)），避免同项目两页完成度不一致
        effective = steps_total - (steps["na"] or 0)
        cross.append(
            {
                "project": row["name"],
                "route": row["route"],
                "board_status": row["board_status"],
                "steps_total": steps_total,
                "steps_done": steps_done,
                "completion": round(steps_done / effective, 3) if effective else 0.0,
                "failures": failures_n,
                "open_issues": open_issues,
                "gate_reds": reds,
            }
        )

    return ok(
        {
            "rework_rate": {
                "coverage": coverage_tag("全量", "failures", "有失败记录项目占比"),
                "overall": {
                    "projects_with_rework": with_rework,
                    "total_projects": total_projects,
                    "rate": round(with_rework / total_projects, 3) if total_projects else 0.0,
                },
                "per_project": per_project_failures,
            },
            "gate_reds_trend": {
                "coverage": coverage_tag(
                    "增量",
                    "gate_reds",
                    "失败日志 triggered_rule + 度量台账 gate_reds 交叉提取",
                ),
                "total": gate_total,
                "points": gate_trend,
            },
            "escape_matrix": {
                "coverage": coverage_tag(
                    "推断",
                    "issues",
                    "降级口径：仅「归属/修复步骤」文本可推断的问题参与计数（E1）",
                ),
                "coverage_ratio": {
                    "inferable": inferable,
                    "total": issues_total,
                    "ratio": round(inferable / issues_total, 3) if issues_total else 0.0,
                },
                "rows": matrix_rows,
            },
            "cross_compare": {
                "coverage": coverage_tag("全量", "projects/step_status/failures/issues"),
                "projects": cross,
            },
        }
    )
