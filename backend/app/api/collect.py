# -*- coding: utf-8 -*-
"""POST /api/collect（一键刷新数据源）：在服务端触发一次 collect.py 幂等重建.

- 复用采集入口 ``collect.run_collection``，不另写解析/落库逻辑（D-09 幂等重建）
- 不接收请求体里的 root/db 路径（防路径穿越；仓库根由 autodetect_root 探测，
  库路径取 .env 的 DB_PATH）；仅本机回环调用（D-29）
- 进程内锁防并发重入：采集是全量重建，重复点击直接返回忙，不并发跑两个 rebuild
- 成功返回采集统计 + 最新 collect_runs 时间，供前端刷新「数据截至」
"""
from __future__ import annotations

import sqlite3
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter

from .. import db as app_db
from ..response import CODE_INTERNAL, err, ok

BACKEND_DIR: Path = app_db.BACKEND_DIR
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import collect  # noqa: E402  后端根目录采集脚本（stdlib，无三方依赖）

router = APIRouter()

# 全量重建期间拒绝第二次并发采集（非阻塞；重复点击直接返回忙）
_collect_lock = threading.Lock()


def _latest_run(conn: Optional[sqlite3.Connection]) -> Tuple[Optional[str], Optional[int]]:
    """回读最近一次 collect_runs 的 ran_at / total_projects（缺表/无记录降级 null）."""
    if conn is None:
        return None, None
    try:
        row = conn.execute(
            "SELECT ran_at, total_projects FROM collect_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None, None
        return row["ran_at"], row["total_projects"]
    except sqlite3.Error:
        return None, None


@router.post("/collect", summary="触发重新采集（一键刷新）", tags=["ops"])
def trigger_collect() -> Dict[str, Any]:
    """全量重采 projects/ 四类产物并幂等重建 metrics.db，返回最新统计与采集时间."""
    if not _collect_lock.acquire(blocking=False):
        return err(CODE_INTERNAL, "采集正在进行中，请稍候再试")
    try:
        cfg = app_db.load_config()
        db_path = app_db.db_file(cfg)
        root = collect.autodetect_root(BACKEND_DIR)
        if root is None:
            return err(CODE_INTERNAL, "无法定位仓库根目录（含 projects/ 与主控文档）")
        stats = collect.run_collection(root, db_path, seed=False)
        conn = app_db.open_conn()
        try:
            collected_at, projects = _latest_run(conn)
        finally:
            if conn is not None:
                conn.close()
        return ok({**stats, "collected_at": collected_at, "projects": projects})
    except (Exception, SystemExit) as exc:
        # SystemExit：run_collection 找不到 projects/ 目录时抛出，转统一错误包
        return err(CODE_INTERNAL, f"采集失败：{exc}")
    finally:
        _collect_lock.release()
