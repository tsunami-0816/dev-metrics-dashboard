# -*- coding: utf-8 -*-
"""采集层解析器包（05_代码/backend/parsers）.

模块清单（对应任务拆解）：
- noise      T03 噪声规则集（§3 规则 1-4 + 坏行登记 D-08）
- sniff      T02 版本嗅探器（§3 规则 5）
- board      T04 看板解析器 → step_status
- failures   T05 失败日志解析器 → failures
- issues     T06 台账解析器 → issues（E1 降级口径）
- run_metrics T07 度量台账解析器 → run_metrics
"""
from .noise import AnomalyLog, ParseAnomaly, TableScanner  # noqa: F401
