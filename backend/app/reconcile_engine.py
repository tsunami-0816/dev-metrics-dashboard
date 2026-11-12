# -*- coding: utf-8 -*-
"""对账引擎（T14 / D-16）：三类勾稽规则，只读不修数.

- A 产物存在性：projects 表内每个项目的三类产物文件是否在磁盘上存在
- B 条数勾稽：看板声明值 vs DB 实际值（累计失败记录数 / 看板步骤行数 / 度量台账失败条数）
- C 状态词闭环：未归一状态词 / 已交付项目仍有 open·fixed P0/P1 / 失败发生在「未开始」步骤

不一致清单分类返回（/api/reconcile 消费）；parse_anomalies 由接口层单独作为「未解析清单」返回。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List

from parsers.board import parse_board

# 步骤状态 6 值枚举（§3-4 / E4）
STATUS_ENUM = {"未开始", "进行中", "已完成", "卡在人工", "已回流", "不适用"}
# 交付类看板状态前缀（已闭环的项目不应再有阻塞中的问题）
_DELIVERED_PREFIXES = ("已完成", "已交付", "已通过", "已闭环", "已豁免")
# 阻塞中的问题状态（WORKFLOW_执行约定：open/fixed 的 P0/P1 阻塞放行）
_BLOCKING_ISSUE_STATUS = ("open", "fixed")
_EXPECTED_ARTIFACTS = ("_项目状态.md", "_问题台账.md", "_失败日志.md")


def _finding(rule: str, cls: str, project: str, detail: str) -> Dict[str, str]:
    return {"rule": rule, "class": cls, "project": project, "detail": detail}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rule_a(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    """A 产物存在性勾稽：DB 内项目 → 磁盘三类产物文件检查."""
    findings: List[Dict[str, str]] = []
    for row in conn.execute("SELECT name, path FROM projects"):
        proj_dir = Path(row["path"])
        if not proj_dir.is_dir():
            findings.append(
                _finding("A", "产物缺失", row["name"], f"项目目录不存在：{proj_dir}")
            )
            continue
        for artifact in _EXPECTED_ARTIFACTS:
            if not (proj_dir / artifact).exists():
                findings.append(
                    _finding(
                        "A",
                        "产物缺失",
                        row["name"],
                        f"缺 {artifact}（早期项目/翻新线历史形态，供人工核对）",
                    )
                )
    return findings


def rule_b(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    """B 条数勾稽：看板/度量台账声明值 vs DB 实际值（重新读源文件比对）."""
    findings: List[Dict[str, str]] = []
    for row in conn.execute("SELECT name, path FROM projects"):
        name, proj_dir = row["name"], Path(row["path"])
        board_path = proj_dir / "_项目状态.md"
        if not board_path.exists():
            continue  # A 规则已报
        try:
            board = parse_board(_read_text(board_path), name)
        except Exception:  # noqa: BLE001 A/异常清单已覆盖，不重复报
            continue
        # B1: 看板「累计失败记录数」 vs failures 实际行数
        declared = board.basic.declared_failure_count
        if declared is not None:
            actual = conn.execute(
                "SELECT COUNT(*) FROM failures WHERE project_name = ?", (name,)
            ).fetchone()[0]
            if declared != actual:
                findings.append(
                    _finding(
                        "B",
                        "失败条数不符",
                        name,
                        f"看板声明累计失败 {declared} 条，DB 实际 {actual} 条",
                    )
                )
        # B2: 看板步骤表原始行数 vs step_status 行数（解析器漏行自检）
        actual_steps = conn.execute(
            "SELECT COUNT(*) FROM step_status WHERE project_name = ?", (name,)
        ).fetchone()[0]
        if board.step_rows_raw and board.step_rows_raw != actual_steps:
            skipped = board.step_rows_raw - actual_steps
            findings.append(
                _finding(
                    "B",
                    "步骤行数不符",
                    name,
                    f"看板步骤表 {board.step_rows_raw} 行，入库 {actual_steps} 行"
                    f"（差 {skipped} 行，见未解析清单）",
                )
            )
    # B3: 度量台账「失败日志条数」 vs failures 按项目+步骤实际行数
    for row in conn.execute(
        "SELECT project_name, step_no, fail_count FROM run_metrics WHERE fail_count IS NOT NULL"
    ):
        actual = conn.execute(
            "SELECT COUNT(*) FROM failures WHERE project_name = ? AND step_no = ?",
            (row["project_name"], row["step_no"]),
        ).fetchone()[0]
        if row["fail_count"] != actual:
            findings.append(
                _finding(
                    "B",
                    "度量失败条数不符",
                    row["project_name"],
                    f"度量台账声明步骤 {row['step_no']} 失败 {row['fail_count']} 条，"
                    f"DB 实际 {actual} 条",
                )
            )
    return findings


def rule_c(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    """C 状态词闭环：状态机一致性检查."""
    findings: List[Dict[str, str]] = []
    # C1: 未归一状态词（E4 之外的词，提示格式漂移）
    for row in conn.execute(
        "SELECT DISTINCT project_name, status FROM step_status "
        "WHERE status IS NOT NULL AND status NOT IN "
        "('未开始','进行中','已完成','卡在人工','已回流','不适用')"
    ):
        findings.append(
            _finding(
                "C",
                "未归一状态词",
                row["project_name"],
                f"状态「{row['status']}」不在 6 值枚举内（格式漂移候选）",
            )
        )
    # C2: 已交付项目仍有阻塞中 P0/P1 问题
    for proj in conn.execute(
        "SELECT name, board_status FROM projects"
    ):
        status = (proj["board_status"] or "").strip()
        if not status.startswith(_DELIVERED_PREFIXES):
            continue
        blockers = conn.execute(
            "SELECT issue_id, level, status FROM issues "
            "WHERE project_name = ? AND status IN ('open','fixed') "
            "AND level IN ('P0','P1')",
            (proj["name"],),
        ).fetchall()
        if blockers:
            ids = ", ".join(f"{b['issue_id']}({b['level']}/{b['status']})" for b in blockers)
            findings.append(
                _finding(
                    "C",
                    "交付与问题状态矛盾",
                    proj["name"],
                    f"看板状态「{status}」但仍有阻塞中 P0/P1：{ids}",
                )
            )
    # C3: 失败发生在「未开始」的步骤（时序矛盾）
    for row in conn.execute(
        "SELECT f.project_name, f.step_no, COUNT(*) cnt FROM failures f "
        "JOIN step_status s ON s.project_name = f.project_name AND s.step_no = f.step_no "
        "WHERE s.status = '未开始' AND f.step_no IS NOT NULL "
        "GROUP BY f.project_name, f.step_no"
    ):
        findings.append(
            _finding(
                "C",
                "失败时序矛盾",
                row["project_name"],
                f"步骤 {row['step_no']} 状态为「未开始」但有 {row['cnt']} 条失败记录",
            )
        )
    return findings


def run_reconcile(conn: sqlite3.Connection) -> Dict[str, List[Dict[str, str]]]:
    """跑全部三类勾稽规则，返回分类不一致清单（只读不修数）."""
    return {
        "A_产物存在性": rule_a(conn),
        "B_条数勾稽": rule_b(conn),
        "C_状态词闭环": rule_c(conn),
    }
