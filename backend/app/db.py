# -*- coding: utf-8 -*-
"""服务侧配置与 SQLite 只读连接（逻辑只读；WAL 物理层 rw 打开以兼容并发）.

配置来源：backend/.env（KEY=VALUE），缺省值与部署说明一致：
  BACKEND_HOST=127.0.0.1（D-29 仅回环监听）
  BACKEND_PORT=8091（D-30 端口约定）
  DB_PATH=data/metrics.db
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterator, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent

_DEFAULTS: Dict[str, str] = {
    "PROJECT_NAME": "dev-metrics-dashboard",
    "BACKEND_HOST": "127.0.0.1",
    "BACKEND_PORT": "8091",
    "DB_PATH": "data/metrics.db",
}


def load_config(env_path: Optional[Path] = None) -> Dict[str, str]:
    """读取 .env（存在则覆盖默认值）；KEY=VALUE 行，# 开头为注释."""
    cfg = dict(_DEFAULTS)
    path = Path(env_path) if env_path else BACKEND_DIR / ".env"
    if not path.exists():
        return cfg
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # 行内注释剥离（值中不含 # 的场景）
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if key in cfg and value:
            cfg[key] = value
    return cfg


def db_file(cfg: Optional[Dict[str, str]] = None) -> Path:
    """metrics.db 路径（相对路径基于 backend 目录解析）."""
    cfg = cfg or load_config()
    p = Path(cfg["DB_PATH"])
    return p if p.is_absolute() else (BACKEND_DIR / p)


def open_conn() -> Optional[sqlite3.Connection]:
    """打开只读用途连接；库文件不存在 → None（空库兜底 D-17）.

    check_same_thread=False（修复-ISS-S8-002）：FastAPI 同步端点跑在 anyio 线程池，
    生成器依赖创建连接的线程与端点执行线程可能不同；sqlite3 默认校验同线程，跨线程即抛
    "SQLite objects created in a thread can only be used in that same thread"。
    本项目每请求独立连接（get_conn 依赖每请求 new、finally close），无两请求共享同一连接，
    跨线程仅创建/使用线程不同，关闭线程校验后并发只读安全。
    """
    path = db_file()
    if not path.exists():
        return None
    conn = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def db_has_data(conn: sqlite3.Connection) -> bool:
    """空库判据：projects 表存在且有行."""
    try:
        row = conn.execute("SELECT COUNT(*) FROM projects").fetchone()
        return bool(row and row[0] > 0)
    except sqlite3.DatabaseError:
        return False


def get_conn() -> Iterator[Optional[sqlite3.Connection]]:
    """FastAPI 依赖：每请求独立连接（WAL 下与 collect 并发安全）."""
    conn = open_conn()
    try:
        yield conn
    finally:
        if conn is not None:
            conn.close()
