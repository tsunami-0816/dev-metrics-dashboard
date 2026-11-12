# -*- coding: utf-8 -*-
"""生成可复现种子库（Mock 策略 · 5B 前端联调用，输入卡 mock_policy）.

数据源即本地真实产物（本项目无 Mock 层）；本脚本从 projects/ 真实产物
生成一份快照库 seed/metrics_seed.db 供 5B 并行联调：
- seed 模式：parsed_at 取源文件 mtime、collect_runs.ran_at 取固定值 → 同一源文件状态可复现
- 5B 联调：把种子库拷到 data/metrics.db 即可（cp seed/metrics_seed.db data/metrics.db）

用法（backend 目录下）：
    python scripts/make_seed_db.py [--root 仓库根] [--out seed/metrics_seed.db]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import collect  # noqa: E402  (需要先加 backend 根到 sys.path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成可复现种子库（5B 联调）")
    parser.add_argument("--root", default=None, help="仓库根目录（默认自动探测）")
    parser.add_argument(
        "--out", default=str(BACKEND_DIR / "seed" / "metrics_seed.db"), help="种子库输出路径"
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else collect.autodetect_root(Path.cwd())
    if root is None:
        root = collect.autodetect_root(BACKEND_DIR)
    if root is None:
        print("[seed] 无法探测仓库根目录，请用 --root 指定", file=sys.stderr)
        return 2
    out = Path(args.out)
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()

    stats = collect.run_collection(root, out, seed=True)
    print(f"[seed] 种子库 → {stats['db_path']}")
    print(
        f"[seed] 项目 {stats['total']}，可解析 {stats['parsed_ok']}（{stats['ratio']:.0%}），"
        f"异常登记 {stats['anomalies']} 条"
    )
    print("[seed] 5B 联调：cp seed/metrics_seed.db data/metrics.db 后启动 uvicorn 即可")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
