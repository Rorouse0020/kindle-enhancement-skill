# 更新日志

## v1.0.1 — 2026-10-28

文档默认语言改为英文，中文保留为镜像版本。

### 变更

- **英文成为默认文档语言**：`README.md`、`SKILL.md`、`references/*.md`
- 中文镜像移至 `README.zh-CN.md`、`SKILL.zh-CN.md`、`references/zh-CN/*.md`
- 同步更新交叉链接，使每种语言内部指向各自语言路径

## v1.0.0 — 2026-10-28

首个公开发布版本，基于一台实机 Kindle Paperwhite 3（固件 5.16.2.1.1，soft-float）完整验证。

### 新增

- **kindle-enhancement 主技能**
  - 越狱流水线：WinterBreak2 判定、本地执行版载荷（去掉 GitHub Pages 依赖）、三件验收证据
  - KOReader + SimpleUI 安装、启动器 scriptlet、`home_dir` 修复
  - 无线传书编排：SSH 配对、SHA-256 回读收据、状态目录丢失后免配对恢复
  - **书源质量门禁**（四条硬指标：元数据/豆瓣、结构、体积、正文安全）
  - **豆瓣自动化**：多查询回退（ISBN → 主标题 → 完整标题 → 去「全集/共N册」变体 → 标题+作者）、占位 ISBN 识别、本地 ISBN 校验位校验、按年份匹配版次
  - **元数据回填**：`backfill_isbn.py` 支持 ISBN / 出版社 / 出版日期 / 语言（`--fill-metadata`、`--fix-language`），只改 OPF、自动 `.orig` 备份、写入后结构复验
  - **设备文件名策略**：`name_policy.py` 按豆瓣书名命名（中文书名用中文、英文书名用英文），FAT32 合法化，重名自动编号
  - 可选增强：微信读书插件、RSS 资讯策展、睡眠壁纸、回滚、T1–T12 排障（合并自早期 kindle-modding-stack 迭代）
- **qiaomu-send2kindle 传输层（本地增强）**
  - AZW3/AZW/MOBI/PRC → EPUB 自动转换（KindleUnpack，双路径：mobi8 直接取、mobi7 重打包）
  - `--name-mode douban|metadata|source` 命名策略
  - 收据新增 `name_source` / `title` / `douban_url` / `renamed_from`
- **发布包**：技能包、companion 包、完整仓库包与 `SHA256SUMS`

### 修复

- 豆瓣搜索对 ISBN 支持差 → 多查询回退
- 书名带括号或「全集」后缀匹配不到 → 查询词变体
- 豆瓣占位 ISBN（`9787001xxxxxx`）被误判冲突 → 识别并忽略
- 多作者 EPUB（含扫描站水印如 `SoBooKs.cc`）作者比对失败 → 比对全部 creator
- 不同版次 ISBN/年份差异导致误 block → 降级 warn；`block` 仅保留书名冲突、结构非法、正文不安全
- `backfill_isbn.py` 在 ISBN 已一致时无法仅修语言 → 拆分变更判断
- 设备文件名回退成拼音（上传沿用源文件名）→ 默认使用豆瓣书名

### 已知限制

- 豆瓣无官方 API；页面变化或触发风控时该项降级为 `warn`（人工核对）
- 豆瓣部分电子书条目只有占位 ISBN（如《刘慈欣短篇科幻小说合集》），无法回填真 ISBN
- 格式转换依赖独立安装的 KindleUnpack（GPL，不随包分发）
- 原生模式（EPUB→AZW3 接收端）未做完整实机验收
