# 问题台账夹具（节选自 SparrowScheduler：翻新9列）

## 问题清单

| ID | 级别 | 标题 | 状态 | 发现步骤 | 根因路由 | 修复步骤 | 轮次 | 备注 |
|---|---|---|---|---|---|---|---|---|
| ISS-001 | P1 | Python 延时消息 SDK 空骨架 | fixed | F2 | 实现缺口 | F3 补实现 | F2-体检 | `__init__.py` 已有完整实现（SparrowClient+submit/cancel+HMAC 签名），与 Go/Java 一致；导入验证通过 |
| ISS-002 | P1 | 零自动化测试 | fixed | F2 | 实现缺口 | F3 补 P0 测试 | F2-体检 | 4 个测试类 6 个用例全部通过（登录/创建任务/触发/延时消息/告警）；`08_测试/p0_cases.json` 已落盘 |
| ISS-003 | P1 | `InitProperties.java` 默认管理员密码硬编码 `123456` | fixed | F2 | 安全 | F3 | F2-体检 | 默认密码改为空；DataInitializer 启动时对空/弱密码打 WARN |
| ISS-004 | P2 | 文档/脚本里 6 处示例密码未标注 | fixed | F2 | 文档 | F3 | F2-体检 | 使用指南 5 处 + cluster-verification.md 1 处 + create-test-task.ps1 1 处均已加 ⚠️ 示例密码标注 |
| ISS-005 | P2 | 内存吃紧 + 端口 6379 被占用 | open | F2 | 环境 | F3 启动时确认 | F2-体检 | 可用内存 3.0GB；6379 可能已有 Redis |
| ISS-006 | P3 | pinia 版本号 `2.1.16` 不存在（幻觉） | fixed | F2 | 依赖 | F3 | F2-体检 | 改为 `^2.1.7`（npm 2.1.x 最后正式版），package.json + package-lock.json 同步 |
| ISS-007 | P3 | Flyway 混合设计 | deferred | F1 | 架构 | - | F2-体检 | B-2 拍板接受现状，不重构 |
| ISS-008 | deferred | OpenTelemetry 分布式追踪未实现 | deferred | F1 | 功能 | - | F2-体检 | B-6 拍板保持现状 |
| ISS-009 | deferred | DAG 子任务依赖未实现 | deferred | F1 | 功能 | - | F2-体检 | B-5 拍板保持单任务 |

---
