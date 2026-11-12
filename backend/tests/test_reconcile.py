# -*- coding: utf-8 -*-
"""对账引擎单测（T14 / D-16）：三类勾稽规则 + 人工制造不一致验收."""
from __future__ import annotations

import sqlite3

import collect
from app.reconcile_engine import run_reconcile


def _build_db(tmp_project_root, tmp_path):
    db_path = tmp_path / "m.db"
    collect.run_collection(tmp_project_root, db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class TestReconcileEngine:
    def test_all_three_classes_present(self, tmp_project_root, tmp_path):
        """T15 验收：返回 3 类勾稽（每类可为空但不缺类）."""
        conn = _build_db(tmp_project_root, tmp_path)
        result = run_reconcile(conn)
        assert set(result.keys()) == {"A_产物存在性", "B_条数勾稽", "C_状态词闭环"}
        conn.close()

    def test_tamper_failure_count_caught_by_b(self, tmp_project_root, tmp_path):
        """T14 验收：人工制造失败条数不一致 → B 规则捕获归类."""
        conn = _build_db(tmp_project_root, tmp_path)
        # fixture-prod 看板声明累计失败 3 条（夹具），fail_g2 夹具实际 2 条 → 已有差异
        # 再注入一条，确保 B 捕获且归类为 失败条数不符
        conn.execute(
            "INSERT INTO failures (project_name, occurred_at, step_no, category, root_cause, round_no) "
            "VALUES ('fixture-prod', '2026-01-01 00:00', '6', '注入', '测试', 1)"
        )
        conn.commit()
        result = run_reconcile(conn)
        b = result["B_条数勾稽"]
        assert any("失败条数不符" in f["class"] and f["project"] == "fixture-prod" for f in b)
        conn.close()

    def test_tamper_unmapped_status_caught_by_c(self, tmp_project_root, tmp_path):
        """未归一状态词 → C 规则捕获."""
        conn = _build_db(tmp_project_root, tmp_path)
        conn.execute(
            "UPDATE step_status SET status='待定' WHERE project_name='fixture-prod' AND step_no='6'"
        )
        conn.commit()
        result = run_reconcile(conn)
        assert any("未归一状态词" in f["class"] for f in result["C_状态词闭环"])
        conn.close()

    def test_tamper_missing_dir_caught_by_a(self, tmp_project_root, tmp_path):
        """产物目录不存在 → A 规则捕获."""
        conn = _build_db(tmp_project_root, tmp_path)
        conn.execute("UPDATE projects SET path='D:/不存在' WHERE name='fixture-prod'")
        conn.commit()
        result = run_reconcile(conn)
        assert any("项目目录不存在" in f["detail"] for f in result["A_产物存在性"])
        conn.close()

    def test_delivered_with_open_p1_caught_by_c(self, tmp_project_root, tmp_path):
        """已交付项目仍有 open P1 → 状态闭环矛盾."""
        conn = _build_db(tmp_project_root, tmp_path)
        conn.execute(
            "UPDATE projects SET board_status='已完成' WHERE name='fixture-prod'"
        )
        conn.execute(
            "INSERT INTO issues (project_name, issue_id, level, status, title, found_step) "
            "VALUES ('fixture-prod', 'Q-099', 'P1', 'open', '注入问题', '7')"
        )
        conn.commit()
        result = run_reconcile(conn)
        assert any("交付与问题状态矛盾" in f["class"] for f in result["C_状态词闭环"])
        conn.close()

    def test_failure_at_unstarted_step_caught_by_c(self, tmp_project_root, tmp_path):
        """失败发生在「未开始」步骤 → 时序矛盾."""
        conn = _build_db(tmp_project_root, tmp_path)
        # 夹具来自已交付项目：先人工把步骤 6 置为「未开始」，再注入 6 步失败
        conn.execute(
            "UPDATE step_status SET status='未开始' WHERE project_name='fixture-prod' AND step_no='6'"
        )
        conn.execute(
            "INSERT INTO failures (project_name, occurred_at, step_no, category, root_cause, round_no) "
            "VALUES ('fixture-prod', '2026-01-02 00:00', '6', '注入', '时序测试', 1)"
        )
        conn.commit()
        result = run_reconcile(conn)
        assert any("失败时序矛盾" in f["class"] for f in result["C_状态词闭环"])
        conn.close()
