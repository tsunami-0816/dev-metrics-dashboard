# 项目状态看板 · 夹具（节选自 cpp-game-server-kit）

## 基本信息

- 项目名：cpp-game-server-kit
- 创建日期：2026-11-10
- 原始描述：`00_原始项目描述.md`
- 当前阶段：**生产线已闭环、项目已交付（step11 完成、10.7 环境收尾已执行，公开仓已上线，交付文档已推 `b2bd67e`）；剩余收尾待办：10.6 两份材料待本人过目口径**（step9 已由用户验收通过；10.0 人工放行；step11 采纳项已落地、backlog 已归档；工作流仓已同步远端）
- 总体状态：10.5 GitHub public 推送闭环；10.6 简历描述 + 面试问答库落盘、反向回写 JD/索引完成；step11 triage 报告 + 台账/规则库补源 + 11.2 脚本/提示词/模板落地全部完成，工作流仓 `aa9aad1`/`edbb8fd` 已在 origin/main；10.7 停应用进程 + 端口复查 + §3.4 回填完成；项目仓交付文档随 `b2bd67e` 推送 origin/main，本地/远端 0/0
- **路线**：生产
- **源路径**：（生产线项目，不填）
- **远程仓库 URL**：https://github.com/tsunami-0816/cpp-game-server-kit （PUBLIC，默认分支 main）
- **git 基线 commit**：首版基线 c24f398（feat）；10.5 回写/夹具修复与后续文档迭代 commit 以远程 main 的 `git log` 为准；199 个文件入库；force-with-lease 重写过一次历史清除文档误伤行
- **体检报告路径**：（生产线项目，不填）
- **设计模式**：普通（纯后端基础设施项目，无 UI 美化需求）
- **项目类型**：portfolio（求职作品集，对口杭州游梦光年 C++游戏服务端岗）
- **是否录 demo 视频**：否（纯后端，用压测数据 + ASan 截图做证据）
- **特殊说明**：本项目**无前端**，5B 前端开发步骤标记为"不适用"；代码全部在 `05_代码/backend/`；开发环境为 WSL2 Ubuntu（epoll/KCP/perf 必须 Linux）

## 步骤进度

> 本表须与WORKFLOW_步骤定义.md 步骤编排表保持一致；主控新增/改名步骤时，两处同步。

| 步骤 | 名称 | 状态 | 产物路径 | 完成时间 | 备注/遗留 |
|---|---|---|---|---|---|
| 1 | 项目基线定义 | 已完成 | `01_项目基线说明书.md` | 2026-11-10 | M1~M8 全量化，机器闸门全绿 |
| 2 | 技术架构设计（第一轮） | 已完成 | `02_架构设计/第一轮技术架构设计文档.md` | 2026-11-10 | 30 个 D 编号设计项 |
| 3 | 架构评审卡点 | 已完成 | `03_评审报告/第一轮架构评审报告.md` + `02_架构设计/第二轮技术架构设计文档.md` + `03_评审报告/第二轮架构复审报告.md` | 2026-11-10 | 用户人工通过 |
| 4 | 任务拆解与开发规范 | 已完成 | `04_任务拆解与开发规范.md` + `_设计实施映射表.md`（30 D 项） | 2026-11-10 | stage4 机器闸门通过 |
| 5A | 后端开发（模块 A→B→C→D→E） | 已完成 | `05_代码/backend/` + `后端开发实现文档.md` | 2026-11-10 | T-01~T-25 编译跑通；M1/M2/M3/M4/M5/M7 实测通过；遗留 deferred：M6 比值 1.03 未达 1.30、M8 1748 行待补、perf 不可用、日志模块未接业务链路 |
| 5B | 前端开发 | 不适用 | — | | 本项目无前端，跳过 |
| 5.5 | 独立代码 Review | 已完成（附条件通过） | `05.5_代码Review/代码Review报告.md` | 2026-11-11 | 🟢 通过但有条件：stage6 闸门 0❌；8 行映射表降级为 ⚠️；发现 P1 隐患（sessions_ 无锁/UAF/token 未实现/Redis 房间 key 未落地/错误码漂移/KCP 未上业务路径）待 step6/7/8 闭环 |
| 6 | 本地运行与冒烟 | 已完成 | `06_冒烟/冒烟记录.md` + `06_冒烟/阶段二人工走查清单.md` + `06_冒烟/evidence/`（含 `walkthrough/`） | 2026-11-11 | 阶段一 11/11 探活通过；阶段二 S1–S7/N1–N5/矩阵 16 格实测通过；用户人工确认「主流程已通」，卡点解除 |
| 6.5 | 接口契约校验 | 已完成 | `06.5_契约/契约校验记录.md` + `proto_game.proto` + `evidence/proto_contract_check.log` | 2026-11-11 | 🤖 机器闸门通过：`proto_contract_check.py` exit 0，10 条消息 C++/Python/proto 三方一致，0 臆造；偏差 D1–D5 入账（Q-014 open P2 阈值 8→50 待 step8 前对齐；Q-015 deferred；D1/D4 文档已回写；D3 沿用 Q-009 deferred） |
| 7 | 全链路联调 | 已完成 | `07_联调/联调检查清单.md` + `07_联调/联调修复说明.md` + `evidence/`（step7_integration.log / members_observe.log / mysql_before·after.txt / gw·bt.log） | 2026-11-11 | 串联 22/22 通过，exit 0；来源阶段=7 无 open/fixed P0/P1；新增 Q-016/Q-017 两条 P2 deferred；stage6 映射表 0 ❌ 无回退 |
| 7.5 | 测试数据重置与干净交接 | 已完成 | `07_联调/数据重置记录.md` + `evidence/reset/`（备份/users 前后快照/Redis 清理/utf8mb4 验证/登录回归） | 2026-11-11 | users 回到种子 id=1/2，Redis 无残留，服务重启清内存态，中文回读正常；Q-018 P3 verified |
| 8 | 全量测试 | 已完成 | `08_测试/`（`p0_cases.json`、`基线指标验证表.md`、`全量测试用例清单.md`、`perf-report.md`、`Bug修复说明.md`、`step8_放行核对.md`、`qa-automation/`、`qa-automation/reports/html/` Allure） | 2026-11-11 | 49 passed/2 xfailed/0 failed，P0 7/7；M1/M2/M3/M4/M7 达标，M5 部分达标（广播 P99 未验证），M6 1.046/M8 1935 行技术债 deferred；Q-014/011/012 verified，新增 Q-019/020/021 deferred；CI `test.yml` 本地 collect-only 绿，远程 badge 待建仓回填 |
| 8.5 | 安全扫描 | 已完成 | `08.5_安全扫描/docs/安全扫描报告.md` + `安全扫描问题清单.md` + `evidence/`（secrets_sast_scan.log / osv_check.log·json / penetration_probe.log / cleanup.log / pip_audit.md） | 2026-11-11 | 👤 卡点已解除：用户回复「安全问题已清零」放行；P0=0/P1=0；secrets+SAST 0 真实密钥；OSV 直查 requests 4 CVE 不可达；渗透 34 条拦截；Q-022~026 P2、Q-027~033 P3 deferred，Q-017 复核维持 |
| 9 | 最终验收 | 已完成 | `09_验收/最终验收清单与报告.md` + `evidence/`（precheck_step9.log / p0_step9.log / full_step9.log / final_snapshot_step9.txt / services_step9.log / gw·bt_step9_final.log / p0_step9_resume.log） | 2026-11-11 | 👤 两段式验收通过：Agent 预走 P0 7/7、全量 49 passed/2 xfailed/0 failed；跨会话恢复复跑 P0 7/7；用户口头「验收通过」放行；M6/M8 未达标技术债、M5 P99 未验证边界已如实标注 |
| 10 | 交付复盘 | 已完成 | `10_交付/交付复盘.md` + `10_交付/交付包与上线方案.md` | 2026-11-11 | 失败归因 4 条聚类 + 选题准确率复盘 + 结果卡 5 个数 + 映射核对 30/30 + JD 落地验证回填；补 unit_probe 探针 12 项断言，修 LogMacros.h 两处缺陷（Q-034 P3 verified）；M8 复测 1935 行；**10.7 环境收尾已执行**：停 gateway/battle/echo 应用进程、端口复查无占用、MySQL/Redis 与种子数据保留，§3.4 复查记录已回填（build 2.8M / build-asan 22M / 缓存 332K 未回收） |
| 10.0 | 完成门禁（机器卡点） | 已人工放行 | `python scripts/workflow_completion_check.py .`（17 ✅ / 1 skipped / 3 已知误判） | 2026-11-11 | 台账/映射/日志缺口/step6·6.5·7·8.5·9·10 文档均 ✅；3 项纯后端不适用已补登记占位；3 项词表误判（5.5/7.5/基线表）维持原文、人工确认放行，脚本词表粗粒度缺陷交 step11；详见 `10_交付/10.0_门禁放行核对.md` |
| 10.5 | GitHub 推送 | 已完成 | https://github.com/tsunami-0816/cpp-game-server-kit （PUBLIC，main，199 文件；HEAD 见 git log） | 2026-11-11 | prepush 四项 all_green：.gitignore 覆盖 ✅ / 历史密钥 0（.secretignore 豁免测试夹具）/ 无真实 .env 与 >5MB / 远端 PUBLIC ✅；精简 21 个一次性探针脚本不入库（本地工作流仓留痕），保留脚本 ROOT 改相对推导；README badge 已回填。CI 首跑发现 `data/test_accounts.yaml` 被 `.gitignore` 的 `data/` 规则误伤未入库（collect 1 error），加 gitignore 例外并入 secretignore 后复跑 51 collected **success** 绿；第二版 commit 文档举例误伤历史扫描，reset 重打干净 commit 后 force-with-lease 覆盖 |
| 10.6 | 简历适配产出 | 已完成 | `10_交付/简历项目描述.md` + `面试问答库.md` + `D:\lg\resume\当前投递\游梦光年_C++游戏服务端\`（PDF + 话术） | 2026-11-11 | 口径拍板：实测数字全留、短板（未达1.30/1935行/P99未验证/无连接池/房间未落Redis/KCP未丢包验证/20并发后TPS掉530）不进投递版纯文本。PDF 已出、门禁 0 meta 泄漏；打招呼话术版本A/B 已写；JD 状态已回写"已生成"，待本人在Boss投递 |
| 11 | 工作流自迭代 | 已完成 | `10_交付/工作流自迭代报告.md` | 2026-11-11 | 全量体检 27 条；采纳 #93/#82/#95/#96/#97/#98/#99/#100/#101/#102，暂缓 #79/#80/#81，新增 R 规则 0。11.2 已落地：门禁脚本 forbid 语境豁免/模式精确匹配/纯后端跳过、prepush .env 后缀模式与密钥白名单、step06 预走查、step08 CI·badge 拆分与压测工具选型、steps.yaml 三条目 requires_frontend、9 份产物模板预置表头关键字、gitignore 夹具例外段；backlog 归档、复跑门禁/prepush/steps/queue 校验；工作流仓 `aa9aad1`/`edbb8fd` 已在 origin/main（0/0 同步，2026-11-11 fetch 核实） |

状态取值：未开始 / 进行中 / 已完成 / 卡在人工 / 已回流 / 不适用。
本项目为生产线项目，F0~F4 翻新线 5 行全部忽略。

## 循环轮次计数

| 循环 | 已用轮次 | 上限 | 本轮问题数 | 结果 |
|---|---|---|---|---|
| 第 6 步 冒烟 | 2 | 不限（同一根因 ≤3 次修复无效 → 回流 2/3） | 0 open P0/P1 | R1 阶段一收敛；R2 阶段二代走查全绿；用户人工确认主流程已通，卡点解除 |
| 第 6.5 步 契约 | 1 | 机器闸门 | 0 open P0/P1 | R1 对账 exit 0，0 臆造；Q-014 open P2 / Q-015 deferred，闸门通过 |
| 第 7 步 联调 | 1 | 不限，问题数须单调下降 | 0 open P0/P1 | R1 收敛：22/22 通过；Q-016/Q-017 记 P2 deferred；放行 7.5 |
| 第 7.5 步 数据重置 | 1 | 自动步骤 | 0 open P0/P1 | R1 users 回到种子 id=1/2、Redis 清空、登录回归通过；Q-018 P3 verified；放行 step8 |
| 第 8 步 测试 | 1 | 不限，问题数须单调下降 | 0 open P0/P1 | R1 收敛：51 条用例 49 passed/2 xfailed/0 failed，P0 7/7；Q-014/011/012 verified，新增 Q-019/020/021 均 deferred；放行 8.5 安全扫描 |
| 第 8.5 步 安全扫描 | 1 | 不限，问题数须单调下降 | 0 open/fixed P0/P1 | R1 收敛：secrets+SAST 0 真实密钥；OSV 直查 6 直连包；渗透 34 条实测；新增 Q-022~026 P2、Q-027~033 P3 deferred，Q-017 复核维持；用户「安全问题已清零」放行 step9 |
| 第 9 步 验收 | 1 | 不限，问题数须单调下降 | 0 open/fixed P0/P1 | R1：Agent 预走脚本编排返工 1 轮（未自包含拉起中间件，WSL 跨会话进程回收致连接被拒），修正后复验 P0 7/7、全量 49 passed/2 xfailed/0 failed；无业务代码改动；待用户两段式人工验收回填 |

## 失败日志

- 累计失败记录数：3
