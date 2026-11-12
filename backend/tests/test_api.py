# -*- coding: utf-8 -*-
"""API 层单测（T11–T13/T15 / D-11~D-17）：TestClient + 临时库 + 空库兜底."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import collect
import app.db as app_db
from app.main import app
from fastapi.testclient import TestClient


def _make_client(tmp_project_root, tmp_path, monkeypatch) -> TestClient:
    """构造指向临时库的 TestClient（不动真实 data/metrics.db；monkeypatch 自动还原）."""
    db_path = tmp_path / "metrics.db"
    collect.run_collection(tmp_project_root, db_path)
    original_load = app_db.load_config

    def patched_load(env_path=None):
        return {**original_load(), "DB_PATH": str(db_path)}

    monkeypatch.setattr(app_db, "load_config", patched_load)
    return TestClient(app)


class TestApiHappy:
    def test_projects(self, tmp_project_root, tmp_path, monkeypatch):
        c = _make_client(tmp_project_root, tmp_path, monkeypatch)
        d = c.get("/api/projects").json()
        assert d["code"] == 0
        names = [p["name"] for p in d["data"]["projects"]]
        assert names == ["fixture-prod", "fixture-renov"]
        prod = d["data"]["projects"][0]
        assert prod["steps_total"] == len(prod["steps"])
        assert 0.0 <= prod["completion"] <= 1.0
        assert d["data"]["coverage"]["scope"] == "全量"

    def test_steps(self, tmp_project_root, tmp_path, monkeypatch):
        c = _make_client(tmp_project_root, tmp_path, monkeypatch)
        d = c.get("/api/steps").json()
        assert d["code"] == 0
        top = d["data"]["top"]
        assert len(top) >= 1
        counts = [t["fail_count"] for t in top]
        assert counts == sorted(counts, reverse=True)  # 降序（D-20）

    def test_failures(self, tmp_project_root, tmp_path, monkeypatch):
        c = _make_client(tmp_project_root, tmp_path, monkeypatch)
        d = c.get("/api/failures").json()
        assert d["code"] == 0
        assert d["data"]["total"] == 2
        assert len(d["data"]["by_category"]) >= 1
        assert len(d["data"]["recent"]) == 2

    def test_metrics_escape_matrix_self_consistent(self, tmp_project_root, tmp_path, monkeypatch):
        """T13 验收：逃逸矩阵行数与覆盖率角标自洽（仅可推断项目计数）."""
        c = _make_client(tmp_project_root, tmp_path, monkeypatch)
        d = c.get("/api/metrics").json()["data"]
        em = d["escape_matrix"]
        assert em["coverage_ratio"]["inferable"] <= em["coverage_ratio"]["total"]
        matrix_count = sum(r["count"] for r in em["rows"])
        assert matrix_count == em["coverage_ratio"]["inferable"]  # 自洽
        assert d["rework_rate"]["overall"]["total_projects"] == 2
        assert d["cross_compare"]["coverage"]["scope"] == "全量"

    def test_reconcile(self, tmp_project_root, tmp_path, monkeypatch):
        c = _make_client(tmp_project_root, tmp_path, monkeypatch)
        d = c.get("/api/reconcile").json()
        assert d["code"] == 0
        data = d["data"]
        assert set(data["classes"].keys()) == {"A_产物存在性", "B_条数勾稽", "C_状态词闭环"}
        assert "unresolved" in data
        assert data["summary"]["total_findings"] == sum(
            len(v) for v in data["classes"].values()
        )

    def test_openapi_paths(self, tmp_project_root, tmp_path, monkeypatch):
        c = _make_client(tmp_project_root, tmp_path, monkeypatch)
        spec = c.get("/openapi.json").json()
        assert len(spec["paths"]) >= 6  # 5 聚合接口 + /health（导出契约 paths>0 判据）

    def test_health(self, tmp_project_root, tmp_path, monkeypatch):
        c = _make_client(tmp_project_root, tmp_path, monkeypatch)
        d = c.get("/health").json()
        assert d["code"] == 0
        assert d["data"]["db_initialized"] is True


class TestEmptyDb:
    def test_code_2_fallback(self, tmp_path, monkeypatch):
        """D-17 空库兜底：code=2 + 引导提示."""
        original_load = app_db.load_config

        def patched_load(env_path=None):
            return {**original_load(), "DB_PATH": str(tmp_path / "不存在.db")}

        monkeypatch.setattr(app_db, "load_config", patched_load)
        c = TestClient(app)
        for ep in ("/api/projects", "/api/steps", "/api/failures", "/api/metrics", "/api/reconcile"):
            d = c.get(ep).json()
            assert d["code"] == 2, ep
            assert "collect.py" in d["msg"]
        # /health 恒 200 + code=0（探活用途）
        h = c.get("/health").json()
        assert h["code"] == 0
        assert h["data"]["db_initialized"] is False

    def test_empty_db_file_code_2(self, tmp_path, monkeypatch):
        """库文件存在但无表 → 同样 code=2."""
        empty = tmp_path / "empty.db"
        conn = sqlite3.connect(empty)
        conn.close()
        original_load = app_db.load_config

        def patched_load(env_path=None):
            return {**original_load(), "DB_PATH": str(empty)}

        monkeypatch.setattr(app_db, "load_config", patched_load)
        c = TestClient(app)
        assert c.get("/api/projects").json()["code"] == 2


class TestConfig:
    def test_load_config_defaults(self, tmp_path):
        cfg = app_db.load_config(env_path=tmp_path / "不存在.env")
        assert cfg["BACKEND_HOST"] == "127.0.0.1"  # D-29
        assert cfg["BACKEND_PORT"] == "8091"  # D-30

    def test_load_config_from_file(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("BACKEND_PORT=9999\n# 注释\nDB_PATH=x/y.db\n", encoding="utf-8")
        cfg = app_db.load_config(env_path=env)
        assert cfg["BACKEND_PORT"] == "9999"
        assert cfg["DB_PATH"] == "x/y.db"
        assert cfg["BACKEND_HOST"] == "127.0.0.1"
