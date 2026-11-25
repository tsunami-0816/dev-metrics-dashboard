# dev-metrics-dashboard · 研发效能度量看板

把散在多个项目目录里的过程台账（进度看板 / 失败日志 / 问题台账 / 运行度量）聚成一个可下钻、可对账的看板：Python 解析入库 → SQLite → FastAPI 聚合接口 → Vue3 + ECharts 六视图。

它是我在做「AI 全栈项目自动交付工作流」时给自己写的消费层工具——项目跑多了以后，哪个步骤最常返工、哪类根因反复出现、哪些问题逃逸到验收，靠翻目录已经看不出来，于是把这套数据做成了页面。

| 维度 | 值 |
|---|---|
| 采集 | Python stdlib 零依赖，六代际容错解析（格式嗅探 / 坏行登记 / 噪声归一），单文件失败不中断 |
| 存储 | SQLite 8 表 2 视图，幂等重建，重跑不产生重复数据 |
| 接口 | FastAPI 7 个（5 个只读聚合 + `/health` + `POST /api/collect`） |
| 前端 | Vue3 + TypeScript + ECharts + Vite，6 个视图 + 三方对账页 |
| 实测 | 项目 15/15 全部可解析（100%）；pytest 67 passed、覆盖率 92%；契约 7/7 命中、0 臆造；交付时 open P0/P1 = 0 |

## 六个视图

| 视图 | 回答的问题 |
|---|---|
| 项目 × 步骤热力图 | 哪些项目在哪些步骤卡住（项目色块矩阵，hover 显示步骤名与备注） |
| 返工 TOP | 返工次数最多的步骤排序 |
| 根因环形 | 失败根因的类别占比 |
| 报红趋势 | 机器闸门报红随时间的走势 |
| 跨项目对比 + 逃逸矩阵 | 同一类问题在哪些项目逃逸到了验收阶段 |
| 三方对账页 | 产物存在性 / 条数勾稽 / 状态词闭环三类规则出差异清单 |

## 架构

```
projects/<项目>/                    backend/                          frontend/
  _项目状态.md   ┐                    ┌ 版本嗅探 sniff.py              ┌ 6 个 View
  _失败日志.md   ├→ 容错解析器 ────────┤ 四类解析器 board/failures/      ├ ECharts 图表
  _问题台账.md   │   (坏行登记不中断)   │   issues/run_metrics          ├ CoverageBadge
  _运行度量.md   ┘                    ├ SQLite 8 表 2 视图（幂等重建） └ 一键刷新按钮
                                     └ FastAPI 7 接口（统一响应包）
```

## 目录结构

```
dev-metrics-dashboard/
├── requirements.txt
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 装配（127.0.0.1:8091；dist 就绪后托管前端）
│   │   ├── api/                 # projects / steps / metrics / failures / reconcile / collect
│   │   ├── reconcile_engine.py  # 三方对账引擎（存在性 / 条数勾稽 / 状态词闭环）
│   │   └── response.py          # 统一响应包 {code,msg,data}，空库兜底
│   ├── parsers/                 # board / failures / issues / run_metrics / sniff / noise
│   ├── db.py                    # 建表 + 幂等重建
│   ├── collect.py               # 采集入口（stdlib 零依赖）
│   ├── tests/                   # pytest 6 个测试文件 / 67 用例
│   └── pytest.ini
└── frontend/                    # Vue3 + TS + ECharts + Vite（dev 5184，代理 /api → 8091）
```

## 快速开始

需要 Python 3.11+、Node 18+。

**1）装依赖**

```bash
python -m venv .venv
# Windows
.venv/Scripts/pip install -r requirements.txt
# macOS / Linux
.venv/bin/pip install -r requirements.txt
```

**2）采集数据**（`--root` 指向**包含 `projects/` 的目录**）

```bash
cd backend
python collect.py --root /path/to/your-workflow-repo --db data/metrics.db
```

输出示例：

```
[collect] 项目总数 15，可解析 15，比率 100%
[collect] 坏行/降级登记 17 条（parse_anomalies 可查，对账页可见）
```

> 不传 `--root` 时脚本会从当前目录向上自动探测“含 `projects/` 且含工作流主控文件”的仓库根；探测不到会提示用 `--root` 指定。解析规则见 `parsers/`。

**3）起后端**

```bash
python -m app.main                       # 127.0.0.1:8091
# 或：uvicorn app.main:app --host 127.0.0.1 --port 8091
```

**4）起前端（开发态）**

```bash
cd ../frontend
npm install
npm run dev                              # 127.0.0.1:5184，/api 与 /health 代理到 8091
```

也可以只跑后端：`npm run build` 产出 `frontend/dist` 后，后端 `/` 会直接托管前端静态资源（同源，无需代理）。

**5）测试**

```bash
cd backend
pytest                                   # 67 passed，覆盖率 92%（pytest.ini 内置 --cov）
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 探活 |
| GET | `/api/projects` | 项目列表与步骤完成度 |
| GET | `/api/steps` | 步骤返工 TOP |
| GET | `/api/metrics` | 指标全景（返工率 / 报红趋势 / 逃逸矩阵 / 跨项目对比） |
| GET | `/api/failures` | 失败根因与类别分布 |
| GET | `/api/reconcile` | 三方对账（A 产物存在性 / B 条数勾稽 / C 状态词闭环） |
| POST | `/api/collect` | 触发重新采集（侧栏「刷新数据」按钮，进程内锁防并发重入） |

所有响应统一为 `{code, msg, data}`；空库时 `code=2` 兜底，不会 500。OpenAPI 见 `/docs`、`/openapi.json`。

## 输入数据格式

解析的是每个项目目录下的四份 markdown 过程产物：

```
projects/<项目名>/
├── _项目状态.md      # 阶段看板：步骤、状态、备注
├── _失败日志.md      # 失败记录：类别、根因、处理
├── _问题台账.md      # 问题：等级、状态、逃逸情况
└── _运行度量.md      # 每次运行的耗时/规模等度量
```

解析器按小节标题与表格列名做容错匹配（同名格式在历史上有过 6 代漂移，这正是 `sniff.py` 与代际解析存在的原因）；缺字段不报错，记入 `parse_anomalies` 并在对账页可见。`_TEMPLATE_新项目`、`_archive_v1`、`_队列` 目录会被跳过。

## 实测与边界

实测（本机单实例，2026-11 交付验收）：

- 解析：15/15 项目（100%）；坏行登记 17 条，单文件失败不中断
- 测试：pytest 67 passed，总覆盖率 92%
- 契约：7/7 接口命中，0 臆造
- 页面：6/6 视图全部出数；一键刷新端到端通过
- 并发：10/20 并发两接口 P95 80.7–204.2ms；50 并发 `/api/metrics` P95 275.5/314.2ms 达标

已知短板（如实记录，未做的部分不包装）：

- 50 并发 `/api/projects` P95 574–587ms，略超 500ms 目标；根因是 N+1 查询与每请求新开 SQLite 连接，下版本改批量查询 + 连接复用
- 无鉴权 / 无用户体系，仅回环 `127.0.0.1` 监听；对外部署前需补鉴权
- 依赖 `starlette 0.41.3` 存在未修复 HIGH CVE，当前功能路径不可达（全 GET 只读、无文件上传），对外暴露前必须升级
- 数据来自本地历史产物，不接线上埋点；非企业级多存储栈
