# -*- coding: utf-8 -*-
"""httpx 压测计时脚本（T25 / D-28 / C03）：5 个聚合接口全量数据计时 → P95 报告.

用法（backend 目录，服务需已启动）：
    .venv/Scripts/python scripts/bench_p95.py [--base http://127.0.0.1:8091] [--n 50] [--out reports/bench_p95.md]

判据：每接口 P95 < 500ms（C03）。
"""
from __future__ import annotations

import argparse
import statistics
import time
from datetime import datetime
from pathlib import Path

import httpx

ENDPOINTS = [
    "/api/projects",
    "/api/steps",
    "/api/failures",
    "/api/metrics",
    "/api/reconcile",
]


def bench_one(client: httpx.Client, path: str, n: int):
    """单接口计时：预热 1 次 + 正式 n 次，返回 (p95_ms, avg_ms, fails)."""
    latencies = []
    fails = 0
    for i in range(n + 1):
        t0 = time.perf_counter()
        try:
            resp = client.get(path, timeout=10.0)
            resp.raise_for_status()
        except Exception:  # noqa: BLE001 记失败样本（D-28：超时/失败均记录）
            fails += 1
            continue
        if i == 0:
            continue  # 预热不计数
        latencies.append((time.perf_counter() - t0) * 1000)
    if not latencies:
        return None, None, fails
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1 if len(latencies) >= 20 else -1]
    return round(p95, 1), round(statistics.mean(latencies), 1), fails


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="聚合接口 P95 压测（C03）")
    parser.add_argument("--base", default="http://127.0.0.1:8091")
    parser.add_argument("--n", type=int, default=50, help="每接口采样次数")
    parser.add_argument("--out", default=None, help="报告落盘路径")
    args = parser.parse_args(argv)

    rows = []
    all_pass = True
    # trust_env=False：忽略系统代理（本机回环压测，走代理会 404）
    with httpx.Client(base_url=args.base, trust_env=False) as client:
        for path in ENDPOINTS:
            p95, avg, fails = bench_one(client, path, args.n)
            ok = p95 is not None and p95 < 500 and fails == 0
            all_pass = all_pass and ok
            rows.append((path, p95, avg, fails, ok))

    print(f"[bench] base={args.base} n={args.n}")
    print(f"{'接口':<16} {'P95(ms)':>8} {'均值(ms)':>9} {'失败':>4}  判定")
    for path, p95, avg, fails, ok in rows:
        print(f"{path:<16} {p95 if p95 is not None else '-':>8} {avg if avg is not None else '-':>9} {fails:>4}  {'✅' if ok else '❌'}")
    verdict = "全绿（C03 达标）" if all_pass else "存在超标/失败样本"
    print(f"[bench] 结论：{verdict}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# 聚合接口 P95 压测报告（D-28 / C03）",
            "",
            f"- 时间：{datetime.now().isoformat(timespec='seconds')}",
            f"- 目标：{args.base}（仅回环）｜采样：每接口 {args.n} 次（预热 1 次不计数）",
            f"- 判据：P95 < 500ms（C03）｜结论：**{verdict}**",
            "",
            "| 接口 | P95(ms) | 均值(ms) | 失败样本 | 判定 |",
            "|---|---|---|---|---|",
        ]
        for path, p95, avg, fails, ok in rows:
            lines.append(
                f"| {path} | {p95 if p95 is not None else '-'} | "
                f"{avg if avg is not None else '-'} | {fails} | {'✅' if ok else '❌'} |"
            )
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[bench] 报告落盘 → {out}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
