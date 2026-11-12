# -*- coding: utf-8 -*-
"""FastAPI 服务骨架（T11 / D-17 / D-26 / D-29 / D-30）.

- 统一响应包见 app/response.py；空库兜底 code=2（D-17）
- /health：探活（env_preflight --smoke 目标）
- /docs、/openapi.json：OpenAPI 契约（6.5 契约源；5B 依据）
- /：StaticFiles 托管前端 dist（T26，dist 就绪后自动生效；否则占位页）
- 仅 127.0.0.1 回环监听（D-29）；端口 8091（D-30）

启动（backend 目录）：
    python -m app.main
    # 或：.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8091
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db as app_db
from .api import collect as collect_api
from .api import failures, metrics, projects, reconcile, steps
from .response import CODE_INTERNAL, ok

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"

app = FastAPI(
    title="dev-metrics-dashboard API",
    version="1.0.0",
    description="研发效能度量看板 · 聚合接口（GET 只读 + POST /api/collect 触发重采；统一响应包 {code,msg,data}）",
)

# 开发态：Vite dev (5184) 代理/直连均可访问（仅本机回环场景）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5184",
        "http://localhost:5184",
    ],
    allow_methods=["GET", "POST"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(steps.router, prefix="/api")
app.include_router(failures.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(reconcile.router, prefix="/api")
app.include_router(collect_api.router, prefix="/api")


@app.get("/health", summary="健康检查", tags=["ops"])
def health() -> dict:
    """探活端点（5A/5B/第 6 步冒烟目标）.

    额外返回数据新鲜度（ISS-S6-005）：collected_at = 最近一次 collect.py 的 ran_at，
    projects = 本次采集项目数。前端侧栏展示「数据截至」，避免把采集快照误当实时数据。
    """
    conn = app_db.open_conn()
    initialized = False
    collected_at = None
    projects = None
    try:
        if conn is not None:
            initialized = app_db.db_has_data(conn)
            try:
                row = conn.execute(
                    "select ran_at, total_projects from collect_runs order by id desc limit 1"
                ).fetchone()
                if row is not None:
                    collected_at = row["ran_at"]
                    projects = row["total_projects"]
            except sqlite3.Error:
                # collect_runs 缺失/无记录（旧库、测试夹具）→ 新鲜度留空，不影响探活
                collected_at, projects = None, None
    finally:
        if conn is not None:
            conn.close()
    return ok(
        {
            "status": "ok",
            "db_initialized": initialized,
            "collected_at": collected_at,
            "projects": projects,
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常 → 统一响应包 code=500（HTTP 仍 200，语义在包内）."""
    return JSONResponse(
        status_code=200,
        content={"code": CODE_INTERNAL, "msg": f"服务器内部错误：{exc}", "data": None},
    )


@app.get("/", include_in_schema=False)
def root():
    """根路径：dist 就绪 → 返回整站首页（T26）；未就绪 → 引导占位页."""
    from fastapi.responses import FileResponse, HTMLResponse

    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    placeholder = (
        "<html><head><meta charset='utf-8'><title>dev-metrics-dashboard</title></head>"
        "<body style='font-family:sans-serif;padding:40px;line-height:1.8'>"
        "<h2>研发效能度量看板 · 后端服务已启动（127.0.0.1:8091）</h2>"
        "<p>前端构建产物尚未就绪（5B 完成后 npm run build 自动托管）。</p>"
        "<p>可用入口：<a href='/docs'>/docs</a>（OpenAPI）｜"
        "<a href='/api/projects'>/api/projects</a>｜"
        "<a href='/api/metrics'>/api/metrics</a>｜"
        "<a href='/api/reconcile'>/api/reconcile</a></p>"
        "</body></html>"
    )
    return HTMLResponse(placeholder)


# T26：dist 存在时挂载整站静态托管（5B 构建产物就绪后自动生效）
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


def main() -> None:
    """python -m app.main 启动入口（仅回环监听 D-29）."""
    import uvicorn

    cfg = app_db.load_config()
    uvicorn.run(
        "app.main:app",
        host=cfg["BACKEND_HOST"],  # 默认 127.0.0.1（D-29）
        port=int(cfg["BACKEND_PORT"]),  # 默认 8091（D-30）
    )


if __name__ == "__main__":
    main()
