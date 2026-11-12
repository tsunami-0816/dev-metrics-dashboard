# -*- coding: utf-8 -*-
"""建库/幂等/采集全链路单测（T08/T09/T10 / D-01/D-08/D-09/D-10）."""
from __future__ import annotations

import sqlite3

import db
import collect

from conftest import fixture_text


class TestDb:
    """T09 建库与幂等重建."""

    def test_rebuild_creates_schema(self, tmp_path):
        conn = db.rebuild(tmp_path / "t.db")
        counts = db.table_counts(conn)
        assert set(counts.keys()) == {
            "projects", "step_status", "failures", "issues",
            "run_metrics", "parse_anomalies", "gate_reds", "collect_runs",
        }
        assert all(v == 0 for v in counts.values())
        views = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'")]
        assert set(views) == {"v_rework_top", "v_escape_matrix"}
        conn.close()

    def test_rebuild_twice_keeps_counts(self, tmp_path):
        """幂等验收口径：连跑两次全表 count 不变."""
        path = tmp_path / "t.db"
        conn = db.rebuild(path)
        db.insert_rows(conn, "projects", [{"name": "p", "path": "/p", "parse_ok": 1}])
        db.insert_rows(conn, "failures", [
            {"project_name": "p", "step_no": "6", "category": "x", "root_cause": "y"}
        ] * 3)
        conn.commit()
        first = db.table_counts(conn)
        conn.close()
        # 模拟重跑：rebuild 后重插同样数据
        conn = db.rebuild(path)
        db.insert_rows(conn, "projects", [{"name": "p", "path": "/p", "parse_ok": 1}])
        db.insert_rows(conn, "failures", [
            {"project_name": "p", "step_no": "6", "category": "x", "root_cause": "y"}
        ] * 3)
        conn.commit()
        assert db.table_counts(conn) == first
        conn.close()

    def test_missing_tables_detects_empty(self, tmp_path):
        conn = sqlite3.connect(tmp_path / "empty.db")
        assert db.missing_tables(conn)  # 空库判据


class TestCollect:
    """T01/T08/T10：遍历豁免 + 坏文件不中断 + 统计输出 + collect_runs 留证."""

    def test_full_collection_on_tmp_root(self, tmp_project_root, tmp_path):
        db_path = tmp_path / "metrics.db"
        stats = collect.run_collection(tmp_project_root, db_path)
        # 豁免目录不计入
        assert stats["total"] == 2
        assert stats["parsed_ok"] == 2
        assert stats["ratio"] == 1.0
        c = stats["counts"]
        assert c["projects"] == 2
        assert c["step_status"] > 0
        assert c["failures"] == 2  # fail_g2 夹具 2 行
        assert c["issues"] == 12  # issues_prod 3 行 + issues_renov（ISS-001~009）9 行
        assert c["run_metrics"] == 2
        # collect_runs 留证（D-10）
        conn = sqlite3.connect(db_path)
        ran = conn.execute("SELECT total_projects, parsed_projects, ratio FROM collect_runs").fetchone()
        assert ran == (2, 2, 1.0)
        conn.close()
        # 幂等：重跑 count 不变
        stats2 = collect.run_collection(tmp_project_root, db_path)
        assert stats2["counts"] == c

    def test_bad_file_does_not_interrupt(self, tmp_project_root, tmp_path):
        """T08 验收：坏文件 → 退出码 0 语义 + 异常显式登记."""
        bad = tmp_project_root / "projects" / "bad-one"
        bad.mkdir()
        (bad / "_项目状态.md").write_text("垃圾内容没有表格", encoding="utf-8")
        (bad / "_失败日志.md").write_text(
            "| 时间 | 步骤 | 随便 | 列 |\n|---|---|---|---|\n| 2026-01-01 | 第6步 | x | y |",
            encoding="utf-8",
        )
        db_path = tmp_path / "metrics.db"
        stats = collect.run_collection(tmp_project_root, db_path)
        assert stats["total"] == 3
        assert stats["parsed_ok"] == 2  # 坏项目 parse_ok=0，好项目不受影响
        assert stats["anomalies"] >= 2  # 两个坏文件均显式登记
        conn = sqlite3.connect(db_path)
        reasons = [r[0] for r in conn.execute("SELECT reason FROM parse_anomalies WHERE project_name='bad-one'")]
        assert any("未找到步骤进度表" in r for r in reasons)
        assert any("无法识别代际" in r for r in reasons)
        conn.close()

    def test_seed_mode_deterministic_ran_at(self, tmp_project_root, tmp_path):
        db_path = tmp_path / "seed.db"
        collect.run_collection(tmp_project_root, db_path, seed=True)
        conn = sqlite3.connect(db_path)
        ran_at = conn.execute("SELECT ran_at FROM collect_runs").fetchone()[0]
        assert ran_at == "1970-01-01T00:00:00"
        conn.close()

    def test_gate_reds_cross_extraction(self, tmp_project_root, tmp_path):
        """gate_reds = 失败日志 triggered_rule + 度量台账 交叉提取（架构 §4）."""
        db_path = tmp_path / "metrics.db"
        collect.run_collection(tmp_project_root, db_path)
        conn = sqlite3.connect(db_path)
        names = [r[0] for r in conn.execute("SELECT gate_name FROM gate_reds")]
        assert "R9" in names  # fail_g2 夹具 triggered_rule
        assert "度量台账:闸门报红" in names  # run_metrics 夹具 gate_reds=1
        conn.close()

    def test_route_default(self, tmp_project_root, tmp_path):
        db_path = tmp_path / "metrics.db"
        collect.run_collection(tmp_project_root, db_path)
        conn = sqlite3.connect(db_path)
        routes = dict(conn.execute("SELECT name, route FROM projects"))
        assert routes["fixture-prod"] == "生产"
        assert routes["fixture-renov"] == "翻新"
        conn.close()
