# -*- coding: utf-8 -*-
"""GET /api/steps（D-12）：步骤返工 TOP（v_rework_top 视图聚合）."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..db import db_has_data, get_conn
from ..response import coverage_tag, empty_db, ok

router = APIRouter()


@router.get("/steps", summary="步骤返工 TOP", tags=["metrics"])
def rework_top(conn=Depends(get_conn)) -> Dict[str, Any]:
    """按步骤聚合失败数降序（视图②柱状图数据）+ 每项目明细."""
    if conn is None or not db_has_data(conn):
        return empty_db()
    top = [
        {"step_no": r["step_no"], "fail_count": r["cnt"], "projects": r["projects"]}
        for r in conn.execute(
            "SELECT step_no, SUM(fail_count) AS cnt, GROUP_CONCAT(DISTINCT project_name) "
            "AS projects FROM v_rework_top GROUP BY step_no ORDER BY cnt DESC, step_no"
        )
    ]
    per_project = [
        {
            "project_name": r["project_name"],
            "step_no": r["step_no"],
            "fail_count": r["fail_count"],
        }
        for r in conn.execute(
            "SELECT project_name, step_no, fail_count FROM v_rework_top "
            "ORDER BY fail_count DESC, project_name, step_no"
        )
    ]
    return ok(
        {
            "coverage": coverage_tag("全量", "failures", "失败日志全量解析聚合"),
            "top": top,
            "per_project": per_project,
        }
    )
