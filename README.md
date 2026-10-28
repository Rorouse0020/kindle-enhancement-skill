# Kindle Enhancement Skill

**语言：** 中文（本文件） · [English](README.en.md)

> 把一台越狱 Kindle（重点：Paperwhite 3 / 固件 5.16.2.1.1）做成"能读、能传、能验"的增强机。
> 端到端流水线：**越狱 → KOReader/SimpleUI → 无线传书 → 书源质量门禁 → 元数据规范化 → 验收/回滚**。

[![Skill](https://img.shields.io/badge/agent--skill-v1.0.0-blue)]()
[![License](https://img.shields.io/badge/license-GPL--3.0-green)]()
[![Tested](https://img.shields.io/badge/tested-Kindle%20PW3%205.16.2.1.1-orange)]()

---

## 这是什么

本仓库包含两个配套的 Agent Skill（均为 `SKILL.md` + 脚本 + 参考资料结构，可被 Claude Code / Codex / 兼容 agent-skills 的工具加载）：

| Skill | 作用 |
|---|---|
| **kindle-enhancement**（主技能） | 越狱、KOReader/SimpleUI、传书编排、**书源质量门禁**、豆瓣核对、元数据回填、验收与回滚 |
| **qiaomu-send2kindle**（传输层，本地增强版） | 通过 SSH/SFTP 把书送到 Kindle；本地补丁支持 **AZW3/MOBI 自动转 EPUB**、**豆瓣书名命名** |

> 原上游：`joeseesun/qiaomu-send2kindle`（GPL-3.0）。本仓库的版本包含本地补丁，补丁清单见 `skills/qiaomu-send2kindle/LOCAL_PATCHES.md`。

## 核心能力

### 1. 越狱流水线（PW3 实机验证）

- 方法判定基于官方 `jailbreaks.json`：PW3 + ≤5.16.3 → **WinterBreak2**（免注册）。
- **关键坑与解法**：官方 `dialoger.html` 依赖 GitHub Pages 拉取 `jb.sh`，国内常失败（表现为"点了没反应"）。本项目提供**本地执行版** `assets/dialoger-local.html` + `jb.sh` 本地副本，彻底去掉 GitHub 依赖。
- 三件验收证据：`documents/JAILBROKEN.txt`、`JB_TRACE.txt`（`DIALOGER_EXECUTED`）、`libkh/bin/fbink`。

### 2. KOReader + SimpleUI

- 选对包：PW3（soft-float）用 `koreader-kindlepw2`。
- 启动器 scriptlet（自动 `mount -o remount,exec /mnt/us`）。
- 修复高频问题：`home_dir` 指错导致"书在 documents 但书架为空"。

### 3. 无线传书（Wi-Fi SSH）

- 配对一次（USB）后，走局域网 SSH，私钥只存 macOS 钥匙串。
- SHA-256 回读校验，只有 `ok: true` 才算送达。
- 收据包含：设备路径 / 字节数 / SHA-256 / 转换信息 / 命名来源。

### 4. 书源质量门禁（本技能重点）

传书前对每本书做**四条硬指标**检查，`pass` 才发送、`warn` 需人工确认、`block` 拒绝：

| # | 指标 | 自动化 |
|---|---|---|
| 1 | **ISBN / 出版社 / 版次**（豆瓣自动核对） | `--douban`：搜索 + 详情页比对书名/作者/出版社/年份/ISBN |
| 2 | **EPUB 结构合法**（zip / mimetype / container / OPF / spine） | `quality_check.py` |
| 3 | **文件大小合理**（几十 KB 的大部头 = 残缺/试读） | 体积 vs 章节/图片 + 试读关键词 |
| 4 | **正文无脚本 / 外链跳转**（`script/iframe/javascript`/外部链接） | 全 spine XHTML 扫描 |

判定尺度：**`block` 只保留给「书名冲突 / 结构非法 / 正文含可执行内容」**；ISBN、出版年、出版社不一致降级为 `warn`（不同版次很常见），避免误杀正版。

额外容错：豆瓣占位 ISBN（`9787001xxxxxx`）、本地校验位非法 ISBN 自动忽略比对；查询词自动去括号/去「全集/共N册」变体。

### 5. 元数据规范化

- **ISBN / 出版社 / 日期 / 语言回填**：`backfill_isbn.py`（只改 OPF，不动正文；自动备份 + 结构复验）。
- **设备文件名 = 豆瓣书名**：中文书用中文名、英文书用英文名；豆瓣不可用时回退元数据书名/源文件名。

### 6. 可选增强

插件（微信读书/SSH）、资讯 RSS 频道策展、睡眠屏保壁纸（16 张 PD/CC0 素材）、T1–T12 排障手册、回滚与恢复。

## 仓库结构

```
.
├── README.md / README.en.md        # 中文 / 英文
├── LICENSE                          # GPL-3.0（继承自 qiaomu-send2kindle）
├── CHANGELOG.md
├── dist/                            # 打包产物（zip + SHA256SUMS）
└── skills/
    ├── kindle-enhancement/
    │   ├── SKILL.md                 # 主流程（Phase 0-5，中文）
    │   ├── SKILL.en.md              # 英文版
    │   ├── scripts/
    │   │   ├── quality_check.py     # 四条硬指标门禁（--douban 可选）
    │   │   ├── douban_verify.py     # 豆瓣核对（多查询回退/占位ISBN识别/年份匹配）
    │   │   ├── backfill_isbn.py     # 元数据回填（ISBN/出版社/日期/语言）
    │   │   ├── name_policy.py       # 设备文件名 = 豆瓣书名
    │   │   ├── kindle-push.py       # 通用 SFTP 推送
    │   │   ├── apply-rss-curation.py / apply-wallpapers.py / gen-wallpapers.py
    │   │   └── verify-setup.sh      # 全栈只读体检
    │   ├── references/              # 越狱/KOReader/传书/质量门禁/排障/回滚/许可证
    │   │   └── en/                  # 英文翻译
    │   └── assets/                  # 越狱载荷、启动器、清理脚本、壁纸
    └── qiaomu-send2kindle/          # 传输层（含本地补丁）
```

## 安装

```bash
# 1) 放到 agent 技能目录（或项目内 skills/）
cp -R skills/kindle-enhancement  ~/.claude/skills/
cp -R skills/qiaomu-send2kindle  ~/.claude/skills/

# 2) 传输层运行时（Python 3.10+，隔离 venv）
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" "$HOME/.claude/skills/qiaomu-send2kindle/scripts/setup_runtime.py"

# 3) 格式转换器（独立安装，GPL，不随包分发）
#    https://github.com/kevinhendricks/KindleUnpack
#    解压到 ~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack
#    （需存在 lib/kindleunpack.py；可用 QIAOMU_KINDLEUNPACK_DIR 覆盖）
```

依赖：macOS（已验证）、Python 3.10+、Node.js 20+（仅 native 模式 EPUB→AZW3 需要）、越狱 Kindle + KOReader SSH。

## 使用示例

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/.claude/skills/kindle-enhancement"

# 传书前门禁（含豆瓣核对）
"$RT" "$SK/scripts/quality_check.py" "书.epub" --douban

# 回填元数据（ISBN/出版社/日期/语言）
"$RT" "$SK/scripts/backfill_isbn.py" "书.epub" --douban --fill-metadata --fix-language zh-CN

# 发送（默认按豆瓣书名命名；AZW3/MOBI 自动转 EPUB）
"$RT" ~/.claude/skills/qiaomu-send2kindle/scripts/send_to_kindle.py send "书.epub"
```

## 实测记录

- 设备：Kindle Paperwhite 3（2015）/ 固件 `5.16.2.1.1` / soft-float；越狱 WinterBreak2。
- 已实机验证：越狱、KOReader v2026.07.1 + SimpleUI 3.0.0-qiaomu.16、SSH 配对与传书、AZW3/MOBI7→EPUB 转换、豆瓣核对（多本中文书）、ISBN/出版社/语言回填、批量改名与清理。
- 门禁样例：《战略与路径》《三体（读客版）》达到 `pass`；《刘慈欣短篇科幻小说合集》因豆瓣仅有占位 ISBN 保持 `warn`。

## 边界与免责

- 仅对**自己拥有**的设备与书籍使用；不绕过 DRM、不提供盗版内容获取、不替用户登录第三方账号。
- 越狱可能影响保修；设备变砖风险由使用者承担（本技能包含备份/回滚流程）。
- 豆瓣核对读取公开页面（限速 1.5s、缓存 7 天），可能因风控降级为人工核对。
- 第三方组件与许可证见 `skills/kindle-enhancement/references/ext-credits.md` 与 `skills/qiaomu-send2kindle/LICENSE`。

## 致谢

[KindleModding](https://kindlemodding.org/)（越狱流程/向导数据）、[KOReader](https://github.com/koreader/koreader)、SimpleUI（Doctor Hetfield / joeseesun 定制）、[qiaomu-send2kindle](https://github.com/joeseesun/qiaomu-send2kindle)、[KindleUnpack](https://github.com/kevinhendricks/KindleUnpack)、weread.koplugin（finlater）、以及 [向阳乔木](https://qiaomu.ai) 的创作。

## License

GPL-3.0（见 [LICENSE](LICENSE)）；壁纸素材为 Public Domain / CC0，详见 `skills/kindle-enhancement/assets/wallpapers/sources.json`。
