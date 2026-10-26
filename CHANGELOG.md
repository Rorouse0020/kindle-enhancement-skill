# Changelog

## 1.0.0 — 2026-10-26

首版，基于 Kindle Paperwhite 3 / 5.16.2.1.1 的完整实机流程。

### 包含
- 越狱：WinterBreak2 官方流程 + **本地 jb.sh 执行变体**（解决 GitHub Pages 拉不到脚本导致"点了没反应"）
- KOReader v2026.07.1（kindlepw2 包）+ scriptlet 启动器（remount exec）+ 书库路径修正
- 插件：SimpleUI 3.0.0-qiaomu.16、微信读书 v1.6.0、SSH 插件配置
- 无线传书：send2kindle 配对/信任/发送 + **AZW3/MOBI/PRC 自动转 EPUB 补丁**（KindleUnpack）
- 内容：资讯源整理（117/20）+ **英文原文优先补丁** + 24 个英文 RSS（News downloader）
- 体验：15 张睡眠壁纸 + 随机屏保配置
- 运维：一键体检 `verify-setup.sh`、逐项回滚、完整撤销越狱

### 记录并修复的实机问题
1. 设备时钟停在 2023 → 所有 HTTPS 报 `certificate is not yet valid` → 资讯更新失败（T1）
2. `kindlemodding.org` 为 GitHub Pages，设备拉不到 jb.sh → 越狱静默失败（T2）
3. KOReader `home_dir` 指向空目录 → 书库空白、"传成功但看不见"（T4）
4. KOReader 不支持 AZW3/KF8 → 需转 EPUB（T5）
5. 路由器 fake-IP DNS（198.18.x.x）的辨识与验证方法（T6）
6. KOReader 运行时 USB 不挂载、设置被回写覆盖（T7）
7. rsync 备份卡住 → 逐文件 + 看门狗（T8）
8. uv Python 创建 venv 后 `base_prefix=/install` → 用真实路径重建（04 §2）
9. 壁纸过暗导致墨水屏残影 → gamma + 白色混合提亮（06 §2）
