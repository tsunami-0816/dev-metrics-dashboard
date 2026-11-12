# -*- coding: utf-8 -*-
"""POST /api/collect 单测：一键重采成功 / 异常兜底 / 方法校验（复用 D-09 幂等重建）."""
from __future__ import annotations

import threading
from pathlib import Path

import app.db as app_db
import collect
from app.main import app
from fastapi.testclient import TestClient


def _patch_db(monkeypatch, tmp_path: Path) -> Path:
    """把库路径指到临时库（不动真实 data/metrics.db），monkeypatch 自动还原."""
    db_path = tmp_path / "metrics.db"
    original_load = app_db.load_config

    def patched_load(env_path=None):
        return {**original_load(), "DB_PATH": str(db_path)}

    monkeypatch.setattr(app_db, "load_config", patched_load)
    return db_path


class TestCollectEndpoint:
    def test_post_collect_success(self, tmp_project_root, tmp_path, monkeypatch):
        _patch_db(monkeypatch, tmp_path)
        monkeypatch.setattr(collect, "autodetect_root", lambda start: tmp_project_root)
        c = TestClient(app)

        d = c.post("/api/collect").json()
        assert d["code"] == 0
        data = d["data"]
        assert data["total"] == 2
        assert data["projects"] == 2
        assert data["collected_at"] is not None

        # 重采落库后，只读接口可查到两个 fixture 项目
        proj = c.get("/api/projects").json()
        assert proj["code"] == 0
        names = [p["name"] for p in proj["data"]["projects"]]
        assert names == ["fixture-prod", "fixture-renov"]

    def test_post_collect_failure_returns_err(self, tmp_project_root, tmp_path, monkeypatch):
        _patch_db(monkeypatch, tmp_path)
        monkeypatch.setattr(collect, "autodetect_root", lambda start: tmp_project_root)

        def boom(root, db_path, seed=False):
            raise RuntimeError("boom")

        monkeypatch.setattr(collect, "run_collection", boom)
        c = TestClient(app)
        d = c.post("/api/collect").json()
        assert d["code"] == 500
        assert "采集失败" in d["msg"]

    def test_get_collect_method_not_executed(self, tmp_path, monkeypatch):
        """GET 不触发采集：框架按方法/兜底返回 404 或 405，且不返回成功响应包."""
        _patch_db(monkeypatch, tmp_path)
        c = TestClient(app)
        r = c.get("/api/collect")
        assert r.status_code in (404, 405)
        assert r.json().get("code") != 0

    def test_concurrent_collect_busy_rejected(self, tmp_path, monkeypatch):
        """并发锁：临界区内第二个 POST 非阻塞拿不到锁 → code=500 忙拒绝，不并发重建."""
        _patch_db(monkeypatch, tmp_path)
        monkeypatch.setattr(collect, "autodetect_root", lambda start: tmp_path)

        entered = threading.Event()
        release = threading.Event()

        def slow_run(root, db_path, seed=False):
            entered.set()
            release.wait(timeout=5)
            return {
                "total": 2,
                "parsed_ok": 2,
                "ratio": 1.0,
                "anomalies": 0,
                "counts": {},
                "collected_at": None,
                "projects": 2,
            }

        monkeypatch.setattr(collect, "run_collection", slow_run)
        results: dict = {}

        def worker(tag):
            results[tag] = TestClient(app).post("/api/collect").json()

        t1 = threading.Thread(target=worker, args=("a",))
        t1.start()
        assert entered.wait(timeout=5), "第一个请求未进入临界区"
        t2 = threading.Thread(target=worker, args=("b",))
        t2.start()
        t2.join(timeout=5)
        release.set()
        t1.join(timeout=5)

        assert results["a"]["code"] == 0
        assert results["b"]["code"] == 500
        assert "采集正在进行中" in results["b"]["msg"]
