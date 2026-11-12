# -*- coding: utf-8 -*-
"""GET /api/projects（D-11）：项目列表 + 步骤完成度 + 项目×步骤状态矩阵（热力图数据源）."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..db import db_has_data, get_conn
from ..response import coverage_tag, empty_db, ok

router = APIRouter()


@router.get("/projects", summary="项目列表与步骤完成度", tags=["metrics"])
def list_projects(conn=Depends(get_conn)) -> Dict[str, Any]:
    """项目 + 完成度 + 每项目步骤状态矩阵（视图①热力图数据）."""
    if conn is None or not db_has_data(conn):
        return empty_db()
    projects = []
    for row in conn.execute(
        "SELECT name, route, board_status, parse_ok, parsed_at FROM projects ORDER BY name"
    ):
        steps = [
            {
                "step_no": s["step_no"],
                "step_name": s["step_name"],
                "status": s["status"],
                "note": s["note"],
                "finished_at": s["finished_at"],
            }
            for s in conn.execute(
                "SELECT step_no, step_name, status, note, finished_at FROM step_status "
                "WHERE project_name = ? ORDER BY id",
                (row["name"],),
            )
        ]
        total = len(steps)
        done = sum(1 for s in steps if s["status"] == "已完成")
        na = sum(1 for s in steps if s["status"] == "不适用")
        effective = total - na
        projects.append(
            {
                "name": row["name"],
                "route": row["route"],
                "board_status": row["board_status"],
                "parse_ok": bool(row["parse_ok"]),
                "parsed_at": row["parsed_at"],
                "steps": steps,
                "steps_total": total,
                "steps_done": done,
                "steps_na": na,
                "completion": round(done / effective, 3) if effective else 0.0,
            }
        )
    return ok(
        {
            "coverage": coverage_tag(
                "全量", "step_status/projects", "全部项目看板步骤表全量解析"
            ),
            "projects": projects,
        }
    )
