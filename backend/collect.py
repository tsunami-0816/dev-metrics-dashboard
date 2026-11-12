# -*- coding: utf-8 -*-
"""采集入口（T01/T08/T10 / D-01 / D-08 / D-10）：遍历 projects/ → 解析 → SQLite 幂等落库.

用法（仓库根目录）：
    python projects/dev-metrics-dashboard/05_代码/backend/collect.py
    # 或自定义： --root D:/lg/project/工作流测试 --db <path> --seed

链路（L1）：遍历（豁免 _TEMPLATE_新项目/_archive_v1/_队列）→ 版本嗅探 →
四类解析器（噪声规则）→ 坏行跳过登记不中断（C01）→ 幂等重建 → 统计输出（C02）。
仅用 Python stdlib，零三方依赖（架构 §1 采集选型）。
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import db
from parsers import AnomalyLog
from parsers.board import parse_board, steps_to_dicts
from parsers.failures import failures_to_dicts, parse_failures
from parsers.issues import issues_to_dicts, parse_issues
from parsers.noise import reset_skipped_total, total_skipped_lines
from parsers.run_metrics import parse_run_metrics, run_metrics_to_dicts

# D-01：遍历豁免目录
EXEMPT_DIRS = {"_TEMPLATE_新项目", "_archive_v1", "_队列"}
# 四类产物（只读数据源；只解析项目根目录，不进 _archive 子目录）
ARTIFACTS = ("_项目状态.md", "_失败日志.md", "_问题台账.md", "_运行度量.md")
BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DB = BACKEND_DIR / "data" / "metrics.db"


def autodetect_root(start: Path) -> Optional[Path]:
    """从 start 逐级向上找含 projects/ 子目录的仓库根."""
    for cur in [start, *start.parents]:
        if (cur / "projects").is_dir() and (cur / "WORKFLOW_工作流主控.md").exists():
            return cur
    return None


def read_text(path: Path) -> str:
    """UTF-8 + errors=replace 降级读取（架构 §1）."""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_project(proj_dir: Path, seed: bool) -> Dict:
    """解析单个项目：四类产物逐文件容错（C01：单文件异常不中断）."""
    project_name = proj_dir.name
    anomalies = AnomalyLog(project_name)
    parsed_at = (
        datetime.fromtimestamp((proj_dir / ARTIFACTS[0]).stat().st_mtime).isoformat(timespec="seconds")
        if seed and (proj_dir / ARTIFACTS[0]).exists()
        else datetime.now().isoformat(timespec="seconds")
    )

    board = None
    failures: List = []
    issues: List = []
    run_metrics: List = []

    # ---- 看板（必需，决定 parse_ok）----
    board_path = proj_dir / "_项目状态.md"
    if board_path.exists():
        try:
            board = parse_board(read_text(board_path), project_name, anomalies)
        except Exception as exc:  # noqa: BLE001 单文件异常登记后继续（D-08）
            anomalies.add("_项目状态.md", f"整文件降级：{exc}", action="降级")
    else:
        anomalies.add("_项目状态.md", "文件缺失", action="跳过该文件继续")

    # ---- 失败日志（存在才解析）----
    failures_path = proj_dir / "_失败日志.md"
    if failures_path.exists():
        try:
            failures = parse_failures(read_text(failures_path), project_name, anomalies)
        except Exception as exc:  # noqa: BLE001
            anomalies.add("_失败日志.md", f"整文件降级：{exc}", action="降级")

    # ---- 问题台账（存在才解析）----
    issues_path = proj_dir / "_问题台账.md"
    if issues_path.exists():
        try:
            issues = parse_issues(read_text(issues_path), project_name, anomalies)
        except Exception as exc:  # noqa: BLE001
            anomalies.add("_问题台账.md", f"整文件降级：{exc}", action="降级")

    # ---- 运行度量（存在才解析；无文件=0 行不算异常，T07）----
    metrics_path = proj_dir / "_运行度量.md"
    if metrics_path.exists():
        try:
            run_metrics = parse_run_metrics(read_text(metrics_path), project_name, anomalies)
        except Exception as exc:  # noqa: BLE001
            anomalies.add("_运行度量.md", f"整文件降级：{exc}", action="降级")

    # ---- gate_reds 交叉提取（架构 §4：失败日志 triggered_rule + 度量台账 gate_reds）----
    gate_red_rows: List[Dict] = []
    for f in failures:
        if f.triggered_rule:
            gate_red_rows.append(
                {
                    "project_name": project_name,
                    "step_no": f.step_no,
                    "gate_name": f.triggered_rule,
                    "red_at": f.occurred_at,
                    "detail": f"失败日志[{f.category or ''}] {f.root_cause or ''}".strip(),
                }
            )
    for rm in run_metrics:
        if rm.gate_reds:
            gate_red_rows.append(
                {
                    "project_name": project_name,
                    "step_no": rm.step_no,
                    "gate_name": "度量台账:闸门报红",
                    "red_at": rm.ended_at,
                    "detail": f"步骤 {rm.step_no} 第 {rm.round_no} 轮报红 {rm.gate_reds} 次",
                }
            )

    parse_ok = 1 if (board is not None and len(board.steps) >= 1) else 0
    return {
        "project": {
            "name": project_name,
            "path": str(proj_dir),
            "route": (board.basic.route if board else None) or "生产",
            "board_status": (board.basic.board_status if board else None)
            or (board.basic.current_stage if board else None),
            "parsed_at": parsed_at,
            "parse_ok": parse_ok,
        },
        "steps": steps_to_dicts(project_name, board.steps) if board else [],
        "failures": failures_to_dicts(project_name, failures),
        "issues": issues_to_dicts(project_name, issues),
        "run_metrics": run_metrics_to_dicts(project_name, run_metrics),
        "gate_reds": gate_red_rows,
        "anomalies": [a.__dict__ for a in anomalies.items],
        "board": board,  # 内存对象：declared_failure_count 等对账 B 规则输入（不落库）
    }


def run_collection(root: Path, db_path: Path, seed: bool = False) -> Dict:
    """主流程：遍历 → 解析 → 幂等重建 → 统计. 返回统计 dict（含 collect_runs 行）."""
    projects_dir = root / "projects"
    if not projects_dir.is_dir():
        raise SystemExit(f"[collect] 未找到项目目录：{projects_dir}")

    reset_skipped_total()
    results: List[Dict] = []
    for proj_dir in sorted(projects_dir.iterdir()):
        if not proj_dir.is_dir() or proj_dir.name in EXEMPT_DIRS:
            continue
        if not any((proj_dir / a).exists() for a in ARTIFACTS):
            continue  # 非项目目录（无任何工作流产物）
        results.append(parse_project(proj_dir, seed))

    # ---- 幂等重建 + 批量落库（D-09）----
    conn = db.rebuild(db_path)
    try:
        for r in results:
            db.insert_rows(conn, "projects", [r["project"]])
            db.insert_rows(conn, "step_status", r["steps"])
            db.insert_rows(conn, "failures", r["failures"])
            db.insert_rows(conn, "issues", r["issues"])
            db.insert_rows(conn, "run_metrics", r["run_metrics"])
            db.insert_rows(conn, "gate_reds", r["gate_reds"])
            db.insert_rows(conn, "parse_anomalies", r["anomalies"])
        conn.commit()
        counts = db.table_counts(conn)
    finally:
        conn.close()

    total = len(results)
    parsed_ok = sum(1 for r in results if r["project"]["parse_ok"] == 1)
    ratio = round(parsed_ok / total, 4) if total else 0.0
    anomaly_total = counts.get("parse_anomalies", 0)
    total_skipped = total_skipped_lines()

    # ---- collect_runs 留证（D-10 / C02）----
    ran_at = "1970-01-01T00:00:00" if seed else datetime.now().isoformat(timespec="seconds")
    conn = db.connect(db_path)
    try:
        db.insert_rows(
            conn,
            "collect_runs",
            [
                {
                    "ran_at": ran_at,
                    "total_projects": total,
                    "parsed_projects": parsed_ok,
                    "ratio": ratio,
                    "skipped_lines": total_skipped,
                }
            ],
        )
        conn.commit()
    finally:
        conn.close()

    stats = {
        "db_path": str(db_path),
        "total": total,
        "parsed_ok": parsed_ok,
        "ratio": ratio,
        "anomalies": anomaly_total,
        "counts": counts,
    }
    return stats


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="研发效能度量看板 · 采集入库")
    parser.add_argument("--root", default=None, help="仓库根目录（默认自动探测）")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite 落库路径")
    parser.add_argument("--seed", action="store_true", help="种子模式：时间戳取定值，可复现")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else autodetect_root(Path.cwd())
    if root is None:
        root = autodetect_root(BACKEND_DIR)
    if root is None:
        print("[collect] 无法探测仓库根目录，请用 --root 指定", file=sys.stderr)
        return 2
    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()

    stats = run_collection(root, db_path, seed=args.seed)
    print(f"[collect] 仓库根：{root}")
    print(f"[collect] metrics.db → {stats['db_path']}（幂等重建完成）")
    print(
        f"[collect] 项目总数 {stats['total']}，可解析 {stats['parsed_ok']}，"
        f"比率 {stats['ratio']:.0%}（C02 要求 ≥90%）"
    )
    print(f"[collect] 坏行/降级登记 {stats['anomalies']} 条（parse_anomalies 可查，对账页可见）")
    for table, cnt in stats["counts"].items():
        print(f"    - {table}: {cnt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
