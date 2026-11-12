# -*- coding: utf-8 -*-
"""GET /api/failures（D-13）：失败根因/类别分布聚合."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..db import db_has_data, get_conn
from ..response import coverage_tag, empty_db, ok

router = APIRouter()


def _distribution(conn, column: str):
    return [
        {column: r[column], "count": r["cnt"]}
        for r in conn.execute(
            f"SELECT {column}, COUNT(*) AS cnt FROM failures "  # noqa: S608 列名白名单
            f"WHERE {column} IS NOT NULL AND {column} != '' "
            "GROUP BY {0} ORDER BY cnt DESC".format(column)
        )
    ]


@router.get("/failures", summary="失败根因/类别分布", tags=["metrics"])
def failure_distribution(conn=Depends(get_conn)) -> Dict[str, Any]:
    """根因/类别/项目三个维度分布 + 最近失败明细（视图③饼图数据）."""
    if conn is None or not db_has_data(conn):
        return empty_db()
    total = conn.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
    recent = [
        {
            "project_name": r["project_name"],
            "occurred_at": r["occurred_at"],
            "step_no": r["step_no"],
            "category": r["category"],
            "root_cause": r["root_cause"],
            "round_no": r["round_no"],
        }
        for r in conn.execute(
            "SELECT project_name, occurred_at, step_no, category, root_cause, round_no "
            "FROM failures ORDER BY occurred_at DESC, id DESC LIMIT 20"
        )
    ]
    return ok(
        {
            "coverage": coverage_tag("全量", "failures", "失败日志全量解析聚合"),
            "total": total,
            "by_category": _distribution(conn, "category"),
            "by_root_cause": _distribution(conn, "root_cause"),
            "by_project": _distribution(conn, "project_name"),
            "recent": recent,
        }
    )
