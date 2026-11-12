# -*- coding: utf-8 -*-
"""pytest 共享夹具：backend 根加入 sys.path + 临时项目根构造器."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture()
def tmp_project_root(tmp_path):
    """构造临时仓库根：projects/ 下放夹具项目，供 collect/reconcile/api 全链路测试."""
    root = tmp_path
    projects = root / "projects"
    good = projects / "fixture-prod"
    good.mkdir(parents=True)
    (good / "_项目状态.md").write_text(fixture_text("board_prod.md"), encoding="utf-8")
    (good / "_失败日志.md").write_text(fixture_text("fail_g2.md"), encoding="utf-8")
    (good / "_问题台账.md").write_text(fixture_text("issues_prod.md"), encoding="utf-8")
    (good / "_运行度量.md").write_text(fixture_text("run_metrics_filled.md"), encoding="utf-8")
    renov = projects / "fixture-renov"
    renov.mkdir(parents=True)
    (renov / "_项目状态.md").write_text(fixture_text("board_renov.md"), encoding="utf-8")
    (renov / "_问题台账.md").write_text(fixture_text("issues_renov.md"), encoding="utf-8")
    # 豁免目录（应被遍历器跳过）
    for exempt in ("_TEMPLATE_新项目", "_archive_v1", "_队列"):
        (projects / exempt).mkdir()
        (projects / exempt / "_项目状态.md").write_text("垃圾", encoding="utf-8")
    return root
