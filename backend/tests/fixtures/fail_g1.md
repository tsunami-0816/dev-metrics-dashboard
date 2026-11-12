# 失败日志夹具（节选自 saas-workflow-agent：G1 表头 + G2 漂移行）

| 时间 | 步骤 | 失败类别 | 问题描述 | AI 所犯错误 | 人工卡点发现的 AI 遗漏 | 修复轮次 | 根因分类 |
|---|---|---|---|---|---|---|---|
| 2026-10-28 04:13 | 第6步 | 真实运行报错 | docker compose up rabbitmq mosquitto 失败：compose 含 VAR:? 强校验，未生成 .env 时连中间件都起不来（error while interpolating INTERNAL_API_TOKEN） |  |  | 1 | 环境/配置 |
| 2026-10-31 22:34 | 第8步 | 真实运行报错 | pytest 全量首跑 L3/L2 报 pymysql 1045 Access denied for user 'root'@'172.17.0.1'：测试配置 MySQL 账号漂移（05_代码/.env 实际为 swa/swa123） | 测试框架建成后未与 05_代码/.env 对齐库账号，沿用了 10-28 的 root/root 旧配置 |  | 1 | 环境/配置 | 08_测试/qa-automation/config/config.yaml | cd 08_测试/qa-automation; python -m pytest -q testcases/l3_integration | R12 |
| 2026-10-31 22:34 | 第8步 | 回归未通过 | L1 用例 test_crewai_gateway_llm_normalize_messages 引用已随 R2 降级删除的模块 app.crew_llm，首跑 ModuleNotFoundError 误红 | 10-31 回归删 CrewAI 改 LangGraph 后，L1 用例未同步替换 |  | 1 | 幻觉依赖/版本 | 08_测试/qa-automation/testcases/l1_unit/test_python_agent_unit.py | cd 08_测试/qa-automation; python -m pytest -q testcases/l1_unit | R12 |
| 2026-10-31 22:34 | 第8步 | 回归未通过 | L2 台账用例 test_llm_call_log_records_usage 依赖 7.5 数据重置前的历史 llm_call_log 数据，重置后查空误红（违反用例自足硬规则） | 用例断言了历史数据（台账非空），未自造前置调用 |  | 1 | 沉默的缺失 | 08_测试/qa-automation/testcases/l2_api/test_quota_api.py | cd 08_测试/qa-automation; python -m pytest -q testcases/l2_api/test_quota_api.py::test_llm_call_log_records_usage | R12 |
| 2026-10-31 22:34 | 第8步 | 真实运行报错 | M3/M6 首跑 7 条 node_execution 失败（8085 Connection refused）+ M6 skipped（paho 未安装）：python-agent 未常驻、测试依赖缺失 | 默认服务仍在跑未探活；Start-Process 子进程随父 shell 退出被杀，未及时发现 |  | 1 | 环境/配置 | 服务现场(8085),08_测试/qa-automation/testcases/l4_e2e/test_mqtt_e2e.py | Get-Process python; Invoke-WebRequest http://localhost:8085/health | R5 |
