---
name: kindle-enhancement
display_name: Kindle Enhancement
description: |
  给越狱 Kindle（重点 PW3 / 固件 5.16.2.1.1）搭一套可用的增强环境：越狱、KOReader + SimpleUI、无线传书（qiaomu-send2kindle）、Kindle 格式自动转 EPUB；并在传书前对电子书做「书源质量门禁」（ISBN/出版社/版次、EPUB 结构、文件大小、正文无脚本外链）。
  当用户说“越狱 Kindle / 装 KOReader / 把书传到 Kindle / 检查这本书是否完整靠谱 / 传书质量把关”时使用。
metadata:
  author: Kindle Enhancement (local build)
  version: "1.0.1"
  platform: macOS
  last_verified: "2026-10-26"
  reference_device: "Kindle Paperwhite 7th gen (PW3), firmware 5.16.2.1.1, jailbroken with WinterBreak2"
---

> **语言 / Language:** 中文（本文件） · [English](SKILL.md)

# Kindle Enhancement

一套**经过实机验证**的 Kindle 增强流水线：越狱 → KOReader/SimpleUI → 无线传书 → 书源质量门禁 → 格式转换 → 验收。
所有步骤都带验证点；**任何一步没有拿到证据，就不算完成**。

---

## 0. 核心原则（先读）

1. **证据优先**：每一步都要产出可核对的结果（`ok: true` 收据、SHA-256、设备端文件列表、屏幕日志），禁止"看起来成功了"。
2. **不动未知状态**：写设备前先确认固件版本、挂载点、目标路径；删除前先 dry-run。
3. **质量门禁前置**：书**先过门禁再上传**。劣质书传上去比传不上去更糟（浪费设备空间、读一半发现残缺）。
4. **可回滚**：改动前备份（设置、插件、书），保留官方文件的 SHA-256 与来源链接。

---

## 1. 阶段 0：环境侦察（必须）

```bash
# 设备是否挂载 + 固件版本
mount | grep -i kindle
cat /Volumes/Kindle/system/version.txt          # 期望: Kindle 5.16.2.1.1

# 是否已越狱（搜索框 ;log 也能验，但脚本可验）
ls -d /Volumes/Kindle/libkh /Volumes/Kindle/documents/JAILBROKEN.txt 2>/dev/null

# 空间与更新包
df -m /Volumes/Kindle
ls /Volumes/Kindle/*.bin 2>/dev/null             # 有 update*.bin 必须先删
```

判据：`version.txt` 必须是 **5.16.2.1.1**（PW3 终版）。不同固件对应不同越狱方法，**不要跨版本套用**。

---

## 2. 阶段 1：越狱（PW3 / 5.16.2.1.1 → WinterBreak2）

**方法映射依据**（官方向导数据）：`kindlemodding.org/jailbreaks.json` 中，PW3 + ≤5.16.3 的首选是 **WinterBreak2**（`registration: false`，无需亚马逊账号）；备选 WinterBreak（需注册）；SpiderCat/Sanctuary/AdBreak/SpringBreak/Nosebleed/Véra 均**不支持 PW3**。

### 2.1 准备（Mac 侧，可脚本化）
1. **整盘备份** `documents/ system/ fonts/` → 项目 `backup-<date>/`（逐目录比对文件数）。
2. **填满存储**（防越狱途中 OTA）：目标只剩 **50–90 MB**。`/mnt/us` 是普通 U 盘模式，可直接 `dd` 写填充文件：
   ```bash
   VOL=/Volumes/Kindle; mkdir -p "$VOL/fill_disk"; i=0
   while [ "$(df -m "$VOL" | awk 'NR==2{print $4}')" -gt 90 ]; do
     i=$((i+1)); dd if=/dev/zero of="$VOL/fill_disk/fill_$i.bin" bs=1m count=200 || break
   done
   ```
   注意：不要用带"看门狗 kill"的复杂脚本，`set -e` 下 `kill` 失败会误判并删掉写好的块。
3. 放载荷 `winterbreak2/dialoger.html` 到设备**根目录**。

### 2.2 关键坑：GitHub Pages 依赖
官方 `dialoger.html` 执行的是
`curl -L https://kindlemodding.org/jb.sh | sh`
而 `kindlemodding.org` 托管在 **GitHub Pages（185.199.108-111.153）**，国内直连常失败 → `sh` 收到空内容 → **表现是"点了没反应"**（下载提示出现但无对话框）。

**解法：本地执行版**（只改这一行，其余与官方一致，`jb.sh` 保持官方原版并校验 SHA-256）：

```html
source_command: "sh -c 'echo DIALOGER_EXECUTED > /mnt/us/JB_TRACE.txt; JB_HEADER=\"Winterbreak2 Jailbreak\" sh /mnt/us/jb.sh > /mnt/us/JB_LOG.txt 2>&1; echo EXIT=$? >> /mnt/us/JB_TRACE.txt'"
```
把 `jb.sh`（8.7 MB，官方原版）放到 `/mnt/us/jb.sh` 即可，**不再依赖 GitHub**。模板见 `assets/dialoger-local.html`。

### 2.3 实机操作（只能人工在设备上做）
关闭飞行模式连 Wi-Fi → 打开**体验版浏览器** → 访问 `https://penguins184.xyz/wb2` → 点 **Jailbreak** → 确认下载 → 等屏幕刷日志 → `Restarting Kindle` → 自动重启。

### 2.4 验收（三件证据）
| 证据 | 位置 | 期望 |
|---|---|---|
| 越狱完成标记 | `documents/JAILBROKEN.txt` | `You are jailbroken! (jb.sh v2.4.0) … Winterbreak2 Jailbreak` |
| 漏洞链是否触发 | `JB_TRACE.txt` | `DIALOGER_EXECUTED` |
| 越狱组件 | `libkh/bin/fbink` | 存在（jb.sh 在系统补丁阶段安装） |

失败时读 `JB_LOG.txt`（jb.sh 输出）：有 `DIALOGER_EXECUTED` 无 `JAILBROKEN.txt` → 脚本执行失败；两者都没有 → 漏洞链没触发（检查载荷目录/浏览器）。

---

## 3. 阶段 2：KOReader + SimpleUI

- KOReader 包必须选**对应平台**：PW3（soft-float）用 `koreader-kindlepw2-v*.zip`；5.16.3+ 的 hard-float 机器要用 `koreader-kindlehf`。
- 解压到设备根目录：`koreader/` + `extensions/koreader/`。
- **启动方式**（无 KUAL 时）：放一个 scriptlet `documents/KOReader.sh`
  ```sh
  #!/bin/sh
  # Name: KOReader
  mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
  cd /mnt/us/koreader || exit 1
  exec sh ./koreader.sh
  ```
  （`/mnt/us` 可能是 noexec，而 KOReader 直接执行 `reader.lua`，不 remount 会失败。）
- SimpleUI：解压 `simpleui.koplugin.zip` → `koreader/plugins/simpleui.koplugin/`（目录名必须精确）。依赖 KOReader 自带 **CoverBrowser** 插件；要求 KOReader ≥ v2026.03。

### 3.1 高频坑：书库为空 / 书看不见
KOReader 的 `settings.reader.lua` 里 `home_dir` 若被设成空目录（如 `/mnt/us/Books`），书在 `documents/` 也看不见。修正（KOReader 必须先退出，否则退出时会回写覆盖）：

```
["home_dir"]         = "/mnt/us/documents"
["lock_home_folder"] = false
["lastdir"]          = "/mnt/us/documents"
```
改动前备份 `settings.reader.lua`；改完用"基本结构校验"确认仍是合法 Lua 表（`return { ... }`）。

---

## 4. 阶段 3：无线传书链路（qiaomu-send2kindle）

| 项目 | 值（本机已验证） |
|---|---|
| 技能位置 | `~/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle/` + `~/.claude/skills/qiaomu-send2kindle/` |
| 隔离运行时 | `~/Library/Application Support/Qiaomu/Kindle/runtime/`（Python 3.12 + paramiko/keyring/filelock/psutil） |
| 设备元数据 | `~/Library/Application Support/Qiaomu/Kindle/devices.json`（0600） |
| 私钥 | **仅 macOS 钥匙串**（service `ai.qiaomu.kindlesync`，account = credential_id） |
| 模式 | KOReader SSH，端口 **2222**；主机密钥指纹固定（防中间人） |

### 4.1 首次配对（需 USB，且 KOReader 必须先退出）
```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle"
"$RT" "$SK/scripts/setup_runtime.py"                 # 仅首次
"$RT" "$SK/scripts/send_to_kindle.py" pair --usb '/Volumes/Kindle' --mode koreader
# 设备端：KOReader → 工具 → SSH server 打勾启动，保持前台
"$RT" "$SK/scripts/send_to_kindle.py" connect --host <设备IP> --mode koreader --trust-new-device
```

### 4.2 状态目录被清空的恢复（无需重新配对）
钥匙串里的私钥仍在时，可只还原元数据：写 `devices.json`（结构见 `references/zh-CN/send2kindle.md`），
字段 `credential_id` 必须与钥匙串 account 一致，`fingerprint` 用之前固定的值。
然后重装运行时（`setup_runtime.py`）与 KindleUnpack（见 4.4），`status` 应为 `ok:true` 且 `credential_present:true`。

### 4.3 传书前提（三件同时成立）
1. Kindle 唤醒（休眠即断网）；2. 同一 Wi-Fi；3. **KOReader 正在运行**（SSH 随 KOReader 启停）。
`discover` 偶尔扫不到 → `send` 会先用固定 host 直连，通常仍可成功。

### 4.4 格式策略（本地增强补丁）
| 源格式 | 行为 | 收据 |
|---|---|---|
| `.epub` | 直传 | `converted:false` |
| `.azw3`（KF8） | KindleUnpack → EPUB | `converted:true`, `engine:kindleunpack-mobi8` |
| `.azw/.mobi/.prc`（MOBI7） | 解包 + 按 OPF 重打包 EPUB | `converted:true`, `engine:kindleunpack-mobi7` |
| `--mode native` + EPUB | EPUB → AZW3（原生阅读器） | `converted:true` |

转换器：**KindleUnpack**（GPL，独立安装，不随技能分发）
`~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack/lib/kindleunpack.py`
可用 `QIAOMU_KINDLEUNPACK_DIR` 覆盖。补丁细节见 `references/zh-CN/send2kindle.md`。

> 重要事实：**KOReader 不支持 AZW3/KF8**（格式注册表只有 `azw/mobi/prc`）。给 KOReader 的书一律 EPUB。

---

### 4.5 设备文件名策略（默认启用）

上传前按 **豆瓣书名** 决定设备上的文件名（用户设定）：

| 豆瓣条目 | 设备文件名 |
|---|---|
| 中文书名（如「三体全集」） | 用中文书名 `三体全集.epub` |
| 英文书名（如「Sapiens」） | 用英文书名 `Sapiens.epub` |
| 豆瓣查不到 / 网络不可用 | 回退：EPUB 元数据书名 → 源文件名 |

```bash
send 书.epub                          # 默认 --name-mode douban
send 书.epub --name-mode metadata     # 用 EPUB 元数据书名
send 书.epub --name-mode source       # 保持源文件名（旧行为）
```

实现：`name_policy.py`（豆瓣多查询 → 标题 → FAT32 合法化：去 `\ / : * ? " < > |`、
压空白、限长、保留扩展名）。重名由上传层自动加 `(2)/(3)`。收据新增
`name_source`（douban/metadata/source）、`title`、`douban_url`、`renamed_from`。

---

## 5. 阶段 4：书源质量门禁（**核心，必做**）

> 传书前先过门禁。判定为 **BLOCK** 的书不上传；**WARN** 的书要用户确认；**PASS** 才发送。

### 5.1 四条硬指标

| # | 指标 | 怎么查 | 失败含义 |
|---|---|---|---|
| 1 | **ISBN / 出版社 / 版次能对上**（豆瓣或出版社官网可查） | EPUB 元数据 `dc:identifier`(ISBN)、`dc:publisher`、`dc:date`；人工在豆瓣/出版社官网比对书名+作者+版次 | 盗版拼装、版本错配、冒名书 |
| 2 | **EPUB 结构合法**（`inspect` 不报错） | `scripts/quality_check.py`（zip 完整性、mimetype 置首、container.xml、OPF、spine、xhtml 数） | 文件损坏/伪 EPUB/转换失败品 |
| 3 | **文件大小合理**（几十 KB 的大部头基本是残缺版） | 自动：字节数 vs 章节数/是否有图；再对照书籍页数常识（如 300 页纯文字通常 ≥300 KB） | 试读版、截断本、纯文本占位 |
| 4 | **正文无脚本 / 外链跳转**（转换时会剥掉 `script/style/iframe`） | 自动扫描所有 xhtml/html：`<script>`、`<iframe>`、`on*=`、`javascript:`、外部 `href/src` | 隐藏跳转/追踪/注入，阅读时被带离正文 |

### 5.2 自动化检测
```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/quality_check.py "/绝对路径/书.epub" \
  --expect-title "书名" --expect-author "作者"
```
输出 JSON：`verdict: pass|warn|block` + 每项 `pass/warn/fail` + 细节 + 豆瓣检索链接（供人工核对指标 1）。

判定规则（脚本内置）：
- 结构不合法 / 含 script、iframe、javascript: → **block**
- 大小异常（无图且 <150 KB、或标题含 sample/excerpt/试读、或明显小于同书名常见体量）→ **warn**
- 缺 ISBN/出版社/日期 → **warn**
- 外部链接存在 → **warn**（正文导航链接除外；数量多要人工看）
- 全通过 → **pass**

### 5.2b 豆瓣自动核对（--douban，可选联网）

`scripts/douban_verify.py` 会搜索并抓取豆瓣详情页，自动比对 **书名 / 作者 / 出版社 / 出版年 / ISBN**：

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/quality_check.py "/绝对路径/书.epub" --douban
"$RT" scripts/douban_verify.py --isbn 9787208178212
"$RT" scripts/douban_verify.py --title "战略与路径" --author "黄奇帆"
```

| 比对项 | pass 条件 | 说明 |
|---|---|---|
| 书名 | 主标题（冒号前）互相包含 | 副标题差异不算错 |
| 作者 | 任一作者名互相包含（忽略【美】等前缀） | 扫描站水印（如 SoBooKs.cc）会判 warn |
| 出版社 | 互相包含 | 出版社合并/易名会 warn |
| 出版年 | 相同或相差 ≤1 年 | 版次/重印差异 |
| ISBN | 两边都有且完全一致 | 本地缺失 → warn（可用豆瓣 ISBN 作为补充依据） |

映射：豆瓣 **block 仅由书名冲突触发** → 门禁 fail → 整本 block；ISBN / 出版年 / 出版社不一致一律 **warn**（不同版次很常见）；豆瓣占位 ISBN（如 `9787001xxxxxx`）与本地校验位不合法的 ISBN 不参与一致性判断。
warn → warn；pass → pass。
豆瓣返回登录墙/风控时**降级为 warn**（提示人工核对），不会误伤书。
请求间隔 1.5 秒、浏览器 UA、15 秒超时、结果缓存 7 天（`~/Library/Application Support/Qiaomu/Kindle/douban-cache.json`）；只读公开页面。

**回填 ISBN**（让元数据更规范，且后续门禁可直接 pass）：

```bash
"$RT" scripts/backfill_isbn.py "书.epub" --douban          # 豆瓣查 ISBN 并写入 OPF
"$RT" scripts/backfill_isbn.py "书.epub" --isbn 9787...    # 或手动指定
"$RT" scripts/backfill_isbn.py "书.epub" --isbn 9787... --fix-language zh-CN   # 顺带规范语言
"$RT" scripts/backfill_isbn.py "书.epub" --douban --fill-metadata            # 回填 ISBN+出版社+日期（占位 ISBN 跳过）
"$RT" scripts/backfill_isbn.py "书.epub" --dry-run         # 只看会写什么
```

只改 OPF 元数据（插入 `urn:isbn:` 标识），不动正文/图片；重打包时 `mimetype` 仍置首且不压缩；
默认在同目录留 `书.epub.orig` 备份，写入后自动复验结构。

### 5.3 人工核对（指标 1 的最终裁决）
- 指标 1：用脚本输出的豆瓣检索链接核对 **书名 / 作者 / 出版社 / 出版年 / 页数 / ISBN** 是否与书内元数据一致；不一致即视为不可信（常见：把不同译本拼在一起、旧版内容配新版封面）。
- 结论写进传书收据（见 5.4），便于日后追溯。

### 5.4 传书收据必须包含
`ok:true` · 设备路径 · 字节数 · SHA-256（回读校验） · `converted`/`engine` · 质量门禁结论（pass/warn + 警告项）。

---

## 6. 验收与清理

- 验收：`send` 返回 `ok:true` 且 `sha256` 与源文件一致（转换时对比转换产物）；设备端 `ls` 能看到文件；KOReader 里能打开。
- 清理：删书/改名优先用精确匹配脚本（见 `assets/kindle-cleanup.py`），**先 --dry-run**；白名单保护 `KOReader.sh`（启动器）、`disable_oobe.sh`、`JAILBROKEN.txt`、`My Clippings.txt`、`dictionaries`。
- 设备 `.sdr` 侧车名跟着书名走；改名时**书与 `.sdr` 一起改**，否则阅读进度错位。

---

## 6.5 可选增强：插件 / 资讯 / 壁纸 / 回滚

以下能力合并自既有 kindle-modding-stack 技能（细节见各 `ext-*.md`），按需启用：

| 能力 | 做什么 | 参考 | 关键脚本 |
|---|---|---|---|
| 插件扩展 | SimpleUI 进阶、**微信读书**插件、SSH 服务 | `references/zh-CN/ext-plugins-weread.md` | — |
| 资讯 RSS | 「乔木精选」频道策展、"原文优先"补丁、英文源 | `references/zh-CN/ext-content-rss.md` | `scripts/apply-rss-curation.py` |
| 睡眠壁纸 | 随机名画/文字卡睡眠屏保 | `references/zh-CN/ext-wallpapers.md` | `scripts/apply-wallpapers.py`、`scripts/gen-wallpapers.py` |
| 回滚与恢复 | 单项回滚、移除传书凭据、恢复原生状态 | `references/zh-CN/ext-rollback.md` | — |
| 全栈体检 | 只读检查设备状态 | — | `scripts/verify-setup.sh` |
| 通用推送 | 任意文件/目录 SFTP 推送到设备 | — | `scripts/kindle-push.py` |

> 壁纸素材 16 张随技能分发（`assets/wallpapers/`）；微信读书插件属第三方（AGPL），不捆绑、不代登录。

## 7. 故障排查速查

| 现象 | 原因 / 处理 |
|---|---|
| 越狱点按钮没反应 | GitHub Pages 拉不到 jb.sh → 用本地执行版 dialoger（§2.2） |
| 越狱后书库空 | `home_dir` 指错目录（§3.1） |
| KOReader 打不开 | `/mnt/us` noexec → 启动器先 `mount,exec`；或 `reader.lua` 缺失 |
| KOReader 里 AZW3 打不开 | KOReader 不支持 KF8 → 先转 EPUB（§4.4） |
| 传书连不上 | KOReader 未开/设备休眠/Wi-Fi 断；`discover` 失败时直接 `send` 用固定 host |
| 技能状态目录丢失 | 钥匙串私钥还在 → 重建运行时+还原 devices.json（§4.2） |
| 系统凭据被锁 | 解锁钥匙串；无明文回退 |
| 设备时间错误 | 出厂重置后 RTC 停在旧日期，会影响 KOReader 网络/证书；设置里校正 |

---

## 8. 血统、合并说明与边界

- 本技能是**端到端流水线 + 书源质量门禁**的主线版本，已合并原 kindle-modding-stack 的全部可复用内容
  （插件/微信读书、资讯 RSS、睡眠壁纸、T1–T12 排障、回滚、许可证），以 `references/ext-*.md`、`assets/`、`scripts/` 形式保留。
- 原 kindle-modding-stack 技能已归档到项目 `archive/kindle-modding-stack-v1.0.0/`（连同 zip），不再单独维护。
- 与传书技能的分工：`qiaomu-send2kindle` 负责"送得到"（SSH/收据/转换）；本技能负责"送什么、值不值得送、送完怎么验收"。
- 冲突时以**证据**为准：`JAILBROKEN.txt`、SSH 指纹、`ok:true` 收据、quality verdict。
- 不做的事：不替用户登录第三方账号、不绕过 DRM、未经确认不删除用户数据。

---

## 9. 参考文件

| 文件 | 内容 |
|---|---|
| `references/zh-CN/jailbreak-pw3.md` | 越狱主线：方法映射、jb.sh 内部流程、验收证据、回滚 |
| `references/zh-CN/koreader-simpleui.md` | KOReader/SimpleUI 安装、启动器原理、home_dir 陷阱 |
| `references/zh-CN/send2kindle.md` | 传书链路：配对、devices.json 还原、本地补丁、转换器 |
| `references/zh-CN/book-quality.md` | **四条硬指标**判定标准、豆瓣核对清单、反例 |
| `references/zh-CN/ext-jailbreak.md` | 越狱扩展细节（官方流程与变体对比） |
| `references/zh-CN/ext-koreader.md` | KOReader 扩展细节（选包/启动器/路径修正） |
| `references/zh-CN/ext-plugins-weread.md` | 插件：SimpleUI 进阶、微信读书、SSH |
| `references/zh-CN/ext-send2kindle.md` | 传书扩展细节（架构、安装、转换） |
| `references/zh-CN/ext-content-rss.md` | 资讯 RSS：频道策展、原文优先补丁、英文源 |
| `references/zh-CN/ext-wallpapers.md` | 睡眠壁纸：机制、规格、素材来源 |
| `references/zh-CN/ext-troubleshooting.md` | T1–T12 实机排障手册（比 §7 更全） |
| `references/zh-CN/ext-rollback.md` | 回滚与恢复（单项/凭据/原生） |
| `references/zh-CN/ext-credits.md` | 第三方组件、许可证、免责声明 |
| `scripts/quality_check.py` | 书源质量检测（元数据/豆瓣、结构、体积、正文安全） |
| `scripts/douban_verify.py` | 豆瓣自动核对（多查询回退：ISBN→主标题→完整标题→标题+作者） |
| `scripts/backfill_isbn.py` | 回填 OPF 元数据：ISBN / 出版社 / 日期 / 语言（--douban、--isbn、--fill-metadata、--fix-language；自动备份+复验） |
| `scripts/apply-rss-curation.py` | 应用「乔木精选」源目录到设备 |
| `scripts/apply-wallpapers.py` | 推送壁纸包并配置 KOReader 屏保 |
| `scripts/gen-wallpapers.py` | 生成壁纸素材 |
| `scripts/kindle-push.py` | 通用 SFTP 推送（文件/目录） |
| `scripts/verify-setup.sh` | 全栈只读体检 |
| `assets/dialoger-local.html` | 本地执行版越狱载荷模板 |
| `assets/kindle-prepare-local.sh` | 填盘 + 放载荷 + 校验 |
| `assets/kindle-ssh.py` | 设备命令执行（排障） |
| `assets/kindle-cleanup.py` | 设备端精确清理（dry-run/apply） |
| `assets/KOReader.sh` | 可点击启动器的参考版本 |
| `assets/feed_config.lua`、`assets/qiaomu_sources.curated.json` | 资讯源配置与策展目录 |
| `assets/wallpapers/` | 16 张睡眠壁纸素材 |
