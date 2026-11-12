# 失败日志夹具（节选自 SparrowScheduler：G3 翻新7列）

| 日期 | 步骤 | 类别 | 根因 | 影响文件 | 复现命令 | 处理 |
|---|---|---|---|---|---|---|
| 2026-11-02 | F0 | 环境 | 野生项目无 .git，F0 闸门要求 .git 存在 | - | `git init` + commit | 手动 git init 解决 |
| 2026-11-02 | F0 | 工具 | `shutil.copytree` 复制 15000+ 文件超时被截断 | `scripts/refurbish_intake.py` | 含 node_modules/target | 改用 robocopy /MIR 排除垃圾目录 |
