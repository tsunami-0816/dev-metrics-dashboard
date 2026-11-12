# 问题台账夹具（模板表头含注释示例 + nestjs 真实行）

## 台账主表


| ID | 级别 | 来源阶段 | 现象 | 根因标签 | 状态 | 轮次 | 归属 |
|---|---|---|---|---|---|---|---|
<!-- 行示例（不要留着，记第一条时替换掉）：
| Q-001 | P0 | 7 | 创建后列表页查不到，跨租户读到别人数据 | 多租户过滤缺失 | open | R1 | 第 7 步修复 |
-->
| Q-001 | P1 | 5.5 | 前端注册页有 email 输入框但后端 DTO 无 email，whitelist 静默剥离 | 跨文件不一致 | verified | R1 | 第6步已修（删前端 email 字段） |
| Q-002 | P1 | 5.5 | WS chunk 前端未按 conversationId 过滤，切对话串气泡 | 逻辑错误 | verified | R1 | 第6步已修（Chat.vue 加守卫） |
| Q-003 | P1 | 5.5 | WS close() 后 onclose 仍触发重连，退出登录后空 token 重连 | 逻辑错误 | verified | R1 | 第6步已修（ws.ts 清空回调+manuallyClosed） |
