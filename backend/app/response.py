# -*- coding: utf-8 -*-
"""统一响应包（架构 §5）：{"code": 0, "msg": "ok", "data": {...}}.

错误码：0 成功 / 1 参数错误 / 2 库未初始化（引导先跑 collect.py，D-17）/ 500 服务器内部错。
HTTP 状态码恒为 200（错误语义进响应包 code 字段，供前端统一处理；/health 供探活）。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

CODE_OK = 0
CODE_PARAM = 1
CODE_EMPTY_DB = 2
CODE_INTERNAL = 500

EMPTY_DB_MSG = "库未初始化：请先运行 python 05_代码/backend/collect.py 生成 metrics.db"


def ok(data: Any) -> Dict[str, Any]:
    """成功响应包."""
    return {"code": CODE_OK, "msg": "ok", "data": data}


def err(code: int, msg: str, data: Optional[Any] = None) -> Dict[str, Any]:
    """错误响应包（code=2 空库兜底 / code=1 参数 / code=500 内部错）."""
    return {"code": code, "msg": msg, "data": data}


def empty_db() -> Dict[str, Any]:
    """D-17 空库兜底：code=2 + 引导提示."""
    return err(CODE_EMPTY_DB, EMPTY_DB_MSG)


def coverage_tag(scope: str, source: str, note: str = "") -> Dict[str, str]:
    """D-25 数据源覆盖范围标注（全量/增量/推断 三级口径）."""
    return {"scope": scope, "source": source, "note": note}
