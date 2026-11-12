# -*- coding: utf-8 -*-
"""版本嗅探器（D-02 / 架构 §3 规则 5）：按实际表头列名集合判定格式代际.

真实仓内已核实的代际（2026-11-11 侦察）：
- 失败日志 4 代：G1 8列 / G2 11列（+影响文件/复现命令/触发规则）/ G3 翻新7列 / G4 9列（ID/处置）
- 问题台账 2 代：生产 8列（台账主表）/ 翻新 9列（问题清单）
- 看板步骤表 2 代：生产 6列（含完成时间）/ 翻新 5列（含备注）
- 运行度量 1 代：9列步骤度量表
未知代际 → 整文件记 parse_anomalies（action=降级），不阻塞采集。
"""
from __future__ import annotations

import re
from typing import List, Optional


def _norm_cols(cols: List[str]) -> List[str]:
    """表头列名归一：去空白（'AI 所犯错误' 与 'AI所犯错误' 同列）."""
    return [re.sub(r"\s+", "", c) for c in cols]


def sniff_failure_log(cols: List[str]) -> Optional[str]:
    """失败日志代际嗅探：返回 fail_g1 / fail_g2 / fail_g3 / fail_g4 / None."""
    c = set(_norm_cols(cols))
    if not (c & {"时间", "日期"}):
        return None
    if "失败类别" in c and "根因分类" in c:  # 生产线代际
        return "fail_g2" if "触发规则" in c else "fail_g1"
    if "处理" in c and "日期" in c:  # 翻新线 7 列
        return "fail_g3"
    if "处置" in c and "ID" in c:  # 9 列代际
        return "fail_g4"
    return None


def sniff_issues(cols: List[str]) -> Optional[str]:
    """问题台账代际嗅探：返回 iss_prod / iss_renov / None."""
    c = set(_norm_cols(cols))
    if "ID" not in c or "级别" not in c:
        return None
    if "来源阶段" in c:  # 生产 8 列（台账主表）
        return "iss_prod"
    if "发现步骤" in c:  # 翻新 9 列（问题清单）
        return "iss_renov"
    return None


def sniff_board(cols: List[str]) -> Optional[str]:
    """看板步骤表代际嗅探：返回 board_prod / board_renov / board_v0 / None.

    - board_prod：6 列（步骤/名称/状态/产物路径/完成时间/备注·遗留）
    - board_renov：5 列（步骤/名称/状态/产物路径/备注）
    - board_v0：4 列（步骤/名称/状态/实际情况）——smart-outbound-platform 实测代际
    """
    c = set(_norm_cols(cols))
    if "步骤" not in c or "状态" not in c:
        return None
    if "完成时间" in c:  # 生产 6 列
        return "board_prod"
    if "备注" in c:  # 翻新 5 列
        return "board_renov"
    if "实际情况" in c:  # 早期 4 列
        return "board_v0"
    return None


def sniff_run_metrics(cols: List[str]) -> Optional[str]:
    """运行度量代际嗅探：返回 run_metrics_v1 / None."""
    c = set(_norm_cols(cols))
    if "步骤" in c and "耗时(分钟)" in c and "闸门报红次数" in c:
        return "run_metrics_v1"
    return None
