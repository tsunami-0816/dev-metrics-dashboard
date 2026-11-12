# -*- coding: utf-8 -*-
"""GET /api/reconcile（D-15 / T15）：三类勾稽 + 未解析清单."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..db import db_has_data, get_conn
from ..reconcile_engine import run_reconcile
from ..response import coverage_tag, empty_db, ok

router = APIRouter()


@router.get("/reconcile", summary="三方对账（A 产物存在性 / B 条数勾稽 / C 状态词闭环）", tags=["reconcile"])
def reconcile(conn=Depends(get_conn)) -> Dict[str, Any]:
    """返回 3 类分类不一致清单（每类可为空但不缺类）+ 未解析清单（parse_anomalies）."""
    if conn is None or not db_has_data(conn):
        return empty_db()
    classes = run_reconcile(conn)
    anomalies = [
        {
            "project_name": r["project_name"],
            "file_name": r["file_name"],
            "line_no": r["line_no"],
            "reason": r["reason"],
            "action": r["action"],
        }
        for r in conn.execute(
            "SELECT project_name, file_name, line_no, reason, action FROM parse_anomalies "
            "ORDER BY project_name, id"
        )
    ]
    total = sum(len(v) for v in classes.values())
    return ok(
        {
            "coverage": coverage_tag(
                "全量", "对账引擎（DB × 源文件三方勾稽）", "只读不修数"
            ),
            "summary": {
                "total_findings": total,
                "by_class": {k: len(v) for k, v in classes.items()},
                "unresolved_count": len(anomalies),
            },
            "classes": classes,
            "unresolved": anomalies,
        }
    )
