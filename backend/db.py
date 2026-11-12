# -*- coding: utf-8 -*-
"""SQLite 建库与幂等重建（T09 / D-09）：8 表 + 2 视图 + 索引.

幂等语义：rebuild() 先 DROP 全部视图/表再 CREATE，executemany 批量落库；
连跑两次 collect 全表 count 不变（T09 验收口径）。
表/字段命名与架构《第二轮技术架构设计文档》§4 逐字一致。
说明：step_no/found_step 等步骤号统一存 TEXT 归一 label（'5.5'/'5A'/'F0'），
因为 '10' 与 '10.0' 是两个不同步骤，浮点化会撞车（§3-3 归一的实现取舍）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

SCHEMA_STATEMENTS = [
    # ---- 8 表（架构 §4）----
    """
    CREATE TABLE projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        path TEXT NOT NULL,
        route TEXT,
        board_status TEXT,
        parsed_at TEXT,
        parse_ok INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE step_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        step_no TEXT NOT NULL,
        step_name TEXT,
        status TEXT,
        note TEXT,
        finished_at TEXT,
        artifact_path TEXT
    )
    """,
    """
    CREATE TABLE failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        occurred_at TEXT,
        step_no TEXT,
        category TEXT,
        root_cause TEXT,
        round_no INTEGER,
        response_type TEXT,
        findings_count INTEGER,
        impact_files TEXT,
        triggered_rule TEXT
    )
    """,
    """
    CREATE TABLE issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        issue_id TEXT,
        level TEXT,
        status TEXT,
        title TEXT,
        found_step TEXT,
        source_step_inferred TEXT,
        root_cause_tag TEXT,
        round_no INTEGER
    )
    """,
    """
    CREATE TABLE run_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        step_no TEXT,
        round_no INTEGER,
        started_at TEXT,
        ended_at TEXT,
        duration_min REAL,
        gate_reds INTEGER,
        fail_count INTEGER,
        review_score TEXT
    )
    """,
    """
    CREATE TABLE parse_anomalies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        file_name TEXT,
        line_no INTEGER,
        reason TEXT,
        action TEXT
    )
    """,
    """
    CREATE TABLE gate_reds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        step_no TEXT,
        gate_name TEXT,
        red_at TEXT,
        detail TEXT
    )
    """,
    """
    CREATE TABLE collect_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ran_at TEXT,
        total_projects INTEGER,
        parsed_projects INTEGER,
        ratio REAL,
        skipped_lines INTEGER
    )
    """,
    # ---- 2 视图（架构 §4）----
    """
    CREATE VIEW v_rework_top AS
        SELECT project_name, step_no, COUNT(*) AS fail_count
        FROM failures
        WHERE step_no IS NOT NULL
        GROUP BY project_name, step_no
    """,
    """
    CREATE VIEW v_escape_matrix AS
        SELECT found_step, source_step_inferred, COUNT(*) AS cnt
        FROM issues
        WHERE found_step IS NOT NULL AND source_step_inferred IS NOT NULL
        GROUP BY found_step, source_step_inferred
    """,
    # ---- 索引（架构 §4：全表 project_name；failures(step_no)、issues(status)）----
    "CREATE INDEX idx_step_status_project ON step_status (project_name)",
    "CREATE INDEX idx_failures_project ON failures (project_name)",
    "CREATE INDEX idx_failures_step ON failures (step_no)",
    "CREATE INDEX idx_issues_project ON issues (project_name)",
    "CREATE INDEX idx_issues_status ON issues (status)",
    "CREATE INDEX idx_run_metrics_project ON run_metrics (project_name)",
    "CREATE INDEX idx_anomalies_project ON parse_anomalies (project_name)",
    "CREATE INDEX idx_gate_reds_project ON gate_reds (project_name)",
]

_TABLES = (
    "collect_runs",
    "gate_reds",
    "parse_anomalies",
    "run_metrics",
    "issues",
    "failures",
    "step_status",
    "projects",
)
_VIEWS = ("v_rework_top", "v_escape_matrix")


def connect(db_path: Path | str, readonly: bool = False) -> sqlite3.Connection:
    """打开连接；WAL 模式（架构 §1 存储选型：collect 与 uvicorn 可同时运行）."""
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def rebuild(db_path: Path | str) -> sqlite3.Connection:
    """幂等重建：DROP 全部视图/表 → 建表建视图建索引（D-09）."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    for view in _VIEWS:
        conn.execute(f"DROP VIEW IF EXISTS {view}")
    for table in _TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(stmt)
    conn.commit()
    return conn


def insert_rows(conn: sqlite3.Connection, table: str, rows: Sequence[Dict]) -> int:
    """executemany 批量落库（值全参数化；表名/列名仅允许内部白名单，非外部输入）."""
    if table not in _TABLES:
        raise ValueError(f"表名不在白名单内：{table}")
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    conn.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
    return len(rows)


def table_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    """全表行数（幂等验证：连跑两次不变）。静态 SQL，无动态表名拼接."""
    row = conn.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM projects)          AS projects,
          (SELECT COUNT(*) FROM step_status)       AS step_status,
          (SELECT COUNT(*) FROM failures)          AS failures,
          (SELECT COUNT(*) FROM issues)            AS issues,
          (SELECT COUNT(*) FROM run_metrics)       AS run_metrics,
          (SELECT COUNT(*) FROM parse_anomalies)   AS parse_anomalies,
          (SELECT COUNT(*) FROM gate_reds)         AS gate_reds,
          (SELECT COUNT(*) FROM collect_runs)      AS collect_runs
        """
    ).fetchone()
    return dict(row)


def missing_tables(conn: sqlite3.Connection) -> List[str]:
    """库内缺失的表（空库兜底 D-17 判据之一）."""
    present = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    return [t for t in _TABLES if t not in present]
