# 失败日志夹具（节选自 shopmate-ai：G2 11列）

| 时间 | 步骤 | 失败类别 | 问题描述 | AI 所犯错误 | 人工卡点发现的 AI 遗漏 | 修复轮次 | 根因分类 | 影响文件 | 复现命令 | 触发规则 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-04 22:58 | 第5.5步 | 评审打回 | step5.5独立review打回：4个P0缺失+5个P1问题，详见Review报告 |  |  | 1 | 沉默的缺失 | 05.5_代码Review/代码Review报告.md | 读代码目录确认docker-compose.yml/seed_knowledge.py/middleware.py不存在 | R9 |
| 2026-11-04 23:07 | 第5.5步 | 评审打回 | step5.5 独立 Review 打回：4 P0 缺失（docker-compose.yml/seed_knowledge.py/middleware.py/Chat.vue feedback未接后端）+ 5 P1（JWT exp/非SSE/dashboard trend硬编码/badcase regress假重跑/health路径不对） | 5A/5B 只写了路由和前端骨架，部署文件/seed脚本/中间件三个独立产物完全遗漏；feedback链路只alert不调后端；JWT用自定义字段expire不验过期；chat用graph.invoke同步阻塞非SSE |  | 1 | 沉默的缺失 | docker-compose.yml,backend/scripts/seed_knowledge.py,backend/app/core/middleware.py,frontend/src/views/Chat.vue,backend/app/core/security.py,backend/app/api/chat.py,backend/app/api/dashboard.py,backend/app/api/badcase.py,backend/app/api/health.py | 另起 reviewer 上下文读 05.5_代码Review/代码Review报告.md 底部返工清单 | R9 |
