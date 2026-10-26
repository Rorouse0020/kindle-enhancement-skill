---
name: kindle-enhancement-skill
description: |
  把一台 Kindle 做成"越狱 + KOReader + SimpleUI + 微信读书 + Wi-Fi 无线传书 + RSS 资讯 + 睡眠壁纸"的完整增强机，并附带全套排障与回滚流程。
  当用户说"越狱 Kindle""给 Kindle 装 KOReader / 插件""把电子书无线传到 Kindle""Kindle 屏保/睡眠壁纸""Kindle 资讯 RSS""Kindle 打不开 AZW3"时使用。
  本包已在 Kindle Paperwhite 3（2015，固件 5.16.2.1.1，soft-float）上逐项实机验证；其他机型按 references/01-jailbreak.md 的判定表选择对应越狱方法与安装包。
metadata:
  version: "1.0.0"
  tested_device: "Kindle Paperwhite 3 (7th gen, 2015) / firmware 5.16.2.1.1 / soft-float"
  license: "文档 CC-BY-4.0；脚本 MIT；第三方组件各自遵循原许可证（见 references/09-credits.md）"
  upstream: "kindlemodding.org · koreader · Doctor Hetfield SimpleUI · joeseesun(qiaomu) · finlater(weread)"
---

# Kindle 全栈增强 Skill

> 目标：任何人拿到这个包，按 Phase 0→5 顺序执行，就能复刻出同样一台"越狱 Kindle"。
> 每一步都写了 **命令 + 预期输出 + 失败该看哪一节**。凡标 ⚠️ 的地方都是本次实机踩过的坑。

---

## 0. 一分钟读懂：这套东西由什么组成

| 层 | 组件 | 作用 | 详细文档 |
|---|---|---|---|
| 系统层 | **WinterBreak2 越狱**（+ 本地执行变体） | 获得 root、封 OTA、装包管理器 | `references/01-jailbreak.md` |
| 阅读器 | **KOReader** v2026.07.1（kindlepw2 包） | 主力阅读器，EPUB/PDF 体验远超原生 | `references/02-koreader.md` |
| 界面 | **SimpleUI** 3.0.0-qiaomu.16 | 类手机主页、平铺书架、资讯、AI 划词 | `references/03-plugins.md` |
| 中文书 | **微信读书插件** v1.6.0 | 在 KOReader 里读微信读书书架（合法、可同步） | `references/03-plugins.md` |
| 传书 | **乔木 send2kindle + 本地补丁** | Wi-Fi 直传、SHA-256 回读校验、AZW3/MOBI 自动转 EPUB | `references/04-send2kindle.md` |
| 内容 | **资讯 RSS + 原文优先补丁 + News downloader** | AI/投资资讯，英文源保持英文 | `references/05-content-rss.md` |
| 体验 | **随机睡眠壁纸**（15 张） | 睡眠时随机显示名画/文字卡 | `references/06-wallpapers.md` |

**总耗时参考**：熟练后约 1.5–2 小时（越狱 20 min + KOReader/插件 20 min + 传书配对 15 min + 内容/壁纸 20 min + 验收）。

---

## 1. 适用性判定（**先做这一节，不要跳**）

### 1.1 本包实机验证范围

| 项目 | 值 |
|---|---|
| 机型 | Kindle Paperwhite 3（Paperwhite 第 7 代，2015），社区代号 **PW3** |
| 固件 | **5.16.2.1.1**（PW3 的最终固件） |
| 架构 | **soft-float**（hard-float 从 5.16.3 才开始） |
| 越狱方法 | WinterBreak2（官方向导对 PW3 + 5.16.2.1.1 的首选） |

### 1.2 其他机型怎么办

流程框架（备份 → 填盘 → 越狱 → KOReader → 插件 → 传书 → 内容）**通用**，但三样东西必须按你的机型重新确定：

1. **越狱方法**：按官方向导的机器可读数据判定
   ```bash
   curl -s https://kindlemodding.org/jailbreaks.json   # 各方法的 models / firmwares 区间
   curl -s https://kindlemodding.org/models.json       # 序列号前缀 → 机型 & 最后固件
   curl -s https://kindlemodding.org/jailbreakFinder.js # 向导筛选逻辑（fillResults）
   ```
   判定规则：`机型 ∈ jb.models` 且 `固件 ∈ [min,max]`（或 in `outliers.accepted`，且不在 `denied`），
   文件顺序中的**第一个匹配**即官方推荐；同时注意 `registration:true` 表示该越狱**要求设备已注册**。
2. **KOReader 安装包**：看 `koreader-<平台>-vX.zip` 里平台是否匹配
   - `kindlepw2` → soft-float（PW2/PW3/KT2/KV/KOA1 等，**本机用的就是这个**）
   - `kindlehf` → hard-float（5.16.3+）
   - `kindle` / `kindle-legacy` → 更老机型
   判定设备是否 hard-float：设备上 `ls /lib/ld-linux-armhf.so.3`，存在即 hard-float。
3. **插件兼容性**：SimpleUI 要求 KOReader ≥ **2026.03**；微信读书插件同样要求较新 KOReader。

**拿到别人机器时的第一条命令**（USB 挂载后）：
```bash
VOL=/Volumes/Kindle            # macOS；Linux 一般是 /media/$USER/Kindle
cat "$VOL/system/version.txt"  # → Kindle 5.16.2.1.1 (409747 002)
```

### 1.3 不适用/不建议的情况

- 固件比 jailbreaks.json 覆盖上限还新 → 等新越狱，**不要**尝试降级（未越狱无法降级）。
- 2025/2026 年的新款（KT7 等）→ 社区标注 "None Available"。
- 设备是借来的/不是自己的：越狱会失去保修、有变砖风险，**必须先确认机主同意**。
- 只想要"能看 EPUB"：先去 Kindle 商店/官方 Send to Kindle 路线，越狱不是唯一解。

---

## 2. 硬性安全规则（违反会变砖或丢数据）

1. **先备份**：整盘 `documents/`（书、笔记、clippings、自定义字体）。本包流程第 0 阶段强制。
2. **不要升级固件**：越狱后升级可能清掉越狱；本机 5.16.2.1.1 已是终版。
3. **不要在 OTA 被封锁的状态下出厂重置**：会卡在无法更新（`Update Failed`）。重置前先跑 `ota.sh` 恢复 OTA。
4. **越狱过程中不要断电/拔线**。
5. **DRM 不解密**：本包所有转换只处理**无 DRM** 文件；书源请用合法渠道（`references/05-content-rss.md`）。
6. **每个改动都留备份**：本包所有脚本都会生成 `.bak-*` 文件，回滚见 `references/08-rollback.md`。
7. **不要向亚马逊客服提及设备被改装**。

---

## 3. 阶段总览

| Phase | 目标 | 通过标准（Checkpoint） | 文档 |
|---|---|---|---|
| **0** | 环境、备份、体检（固件/机型/时钟/空间） | 备份 344+ 文件校验一致；`date` 年份正确 | 本文件 §4 |
| **1** | 越狱（WinterBreak2 / 本地执行变体） | `documents/JAILBROKEN.txt` 出现；`libkh/bin/fbink` 存在 | `references/01-jailbreak.md` |
| **2** | KOReader + SimpleUI + 微信读书 | `koreader/git-rev`=v2026.07.1；插件目录版本正确；能启动 KOReader | `references/02-koreader.md`、`03-plugins.md` |
| **3** | Wi-Fi 无线传书 | `send` 返回 `ok:true` 且 sha256 回读一致 | `references/04-send2kindle.md` |
| **4** | 资讯 RSS + 睡眠壁纸 | 资讯有文章（英文源显示英文）；睡眠出现随机壁纸 | `references/05-content-rss.md`、`06-wallpapers.md` |
| **5** | 验收、维护、回滚 | 跑通 `scripts/verify-setup.sh` 全绿 | 本文件 §5、`references/08-rollback.md` |

---

## 4. Phase 0：环境准备与体检

### 4.1 前置条件

| 需要 | 说明 |
|---|---|
| 电脑 | macOS / Linux（本包脚本以 macOS 为主，Windows 需 WSL 或手工等价操作） |
| USB | **能传数据的线**（很多充电线不能） |
| Python | ≥3.10（`send2kindle` 运行时）；`curl`、`unzip` |
| Wi-Fi | 设备与电脑同一局域网；设备能访问外网（越狱、RSS、传书都需要） |

### 4.2 体检命令（全部只读）

```bash
VOL=/Volumes/Kindle
mount | grep -i kindle                  # 必须看到挂载点
cat "$VOL/system/version.txt"           # 固件
ls -A "$VOL"                            # documents/ fonts/ system/ ...
df -m "$VOL"                            # 可用空间
```

### 4.3 ⚠️ 第一条必查：设备时钟

设备时钟错误时，**所有 HTTPS 都会失败**（`SSL certificate problem: certificate is not yet valid`），表现为：资讯"更新失败"、`;kpm` 下载失败、传送异常。出厂重置后时钟常停留在很久以前。

判定与修复（越狱后可用 root SSH；未越狱则在「设置 → 设备选项 → 设备时间」手工设置）：
```bash
ssh root@<kindle-ip> -p 2222 'date'                    # 年份不对就要修
ssh root@<kindle-ip> -p 2222 "date -s 'YYYY-MM-DD HH:MM:SS' && hwclock -w"
```
详见 `references/07-troubleshooting.md` T1。

### 4.4 备份（强制）

```bash
BK="/path/to/backup-$(date +%F)"
rsync -a --exclude '.Spotlight-V100' --exclude '.fseventsd' --exclude '.Trashes' "$VOL/" "$BK/"
for d in documents system fonts .active_content_sandbox; do
  echo "$d 源=$(find "$VOL/$d" -type f 2>/dev/null | wc -l) 备份=$(find "$BK/$d" -type f 2>/dev/null | wc -l)"
done
```
> ⚠️ 大文件（如几十 MB 的 azw3）复制时偶发"file truncated while reading"或卡住，改用**逐文件 + 看门狗**方式（见 `references/07-troubleshooting.md` T7）。

---

## 5. Phase 5：验收与日常维护

### 5.1 一键体检

```bash
bash scripts/verify-setup.sh "$VOL"
```
检查项：固件、越狱标记、KOReader 版本、插件版本、SSH 配对配置、传书设置、资讯补丁、壁纸数量、时钟。
**全绿 = 复刻成功。**

### 5.2 日常维护清单

| 周期 | 动作 |
|---|---|
| 每次重置/换电池后 | 先查时钟（§4.3），再查越狱标记是否还在 |
| 想换壁纸 | 把 jpg/png（1072×1448，偏亮）丢进 `/mnt/us/wallpapers` |
| 想加英文 RSS | 编辑 `/mnt/us/koreader/news/feed_config.lua`（格式见 `assets/feed_config.lua`） |
| 升级 KOReader | 换包重装即可，插件与设置保留；升级后重跑 `scripts/verify-setup.sh` |
| 想彻底还原 | `references/08-rollback.md` |

### 5.3 备份要留什么

| 文件 | 为什么 |
|---|---|
| 整盘 `documents/` | 书、笔记、`.sdr` 阅读进度 |
| `koreader/settings.reader.lua` 及 `*.bak-*` | 屏保、home_dir、SSH 等设置 |
| `koreader/settings/simpleui/` | SimpleUI 布局与资讯状态 |
| `send2kindle` 的 `devices.json` + 钥匙串条目 | 配对身份（丢了要重新 USB 配对） |

---

## 6. 任务索引（想做什么 → 看哪里）

| 我想… | 去哪 |
|---|---|
| 越狱一台 PW3 / 判断别的机型怎么越狱 | `references/01-jailbreak.md` |
| 官方 dialoger 拉不到 jb.sh（GitHub 被墙） | `references/01-jailbreak.md` §4 本地执行变体 |
| 装 KOReader / 启动不了 / 黑屏 | `references/02-koreader.md` |
| 装 SimpleUI / 微信读书 / 插件不生效 | `references/03-plugins.md` |
| 手机般无线传书 / 传过去看不见 / AZW3 打不开 | `references/04-send2kindle.md` |
| 配资讯 RSS / 英文被翻译 / 英文源太少 | `references/05-content-rss.md` |
| 睡眠壁纸 / 想自己加图 | `references/06-wallpapers.md` |
| 任何报错 | `references/07-troubleshooting.md`（按症状查 T1–T12） |
| 回滚 / 修砖 / 恢复出厂 | `references/08-rollback.md` |
| 第三方许可证与致谢 | `references/09-credits.md` |

---

## 7. 脚本清单

| 脚本 | 作用 | 典型用法 |
|---|---|---|
| `scripts/verify-setup.sh` | 一键体检（只读） | `bash scripts/verify-setup.sh /Volumes/Kindle` |
| `scripts/kindle-ssh.py` | 用已配对身份在设备上执行命令 | `python3 scripts/kindle-ssh.py 'ls /mnt/us'` |
| `scripts/kindle-push.py` | 递归推送文件/目录到设备 | `python3 scripts/kindle-push.py ./dir /mnt/us/target` |
| `scripts/kindle-prepare-local.sh` | 越狱准备（放本地 jb.sh + dialoger + 填盘） | `bash scripts/kindle-prepare-local.sh /Volumes/Kindle 90` |
| `scripts/apply-rss-curation.py` | 应用整理后的资讯源目录（117/20） | `python3 scripts/apply-rss-curation.py /Volumes/Kindle` |
| `scripts/apply-wallpapers.py` | 推送壁纸 + 配置随机睡眠屏保 | `python3 scripts/apply-wallpapers.py /Volumes/Kindle` |
| `scripts/gen-wallpapers.py` | 生成壁纸素材（公版名画/NASA/文字卡） | `python3 scripts/gen-wallpapers.py` |

`scripts/kindle-ssh.py` / `kindle-push.py` 依赖 `send2kindle` 的凭据模块（见 `references/04-send2kindle.md` §2），
需要先完成配对；未配对时只能用 USB 直接读写挂载点。

---

## 8. 已知限制（先告诉用户，避免预期落差）

1. **KOReader 不支持 AZW3/KFX**（KF8 解析不了）；本包用"自动转 EPUB"解决。带 DRM 的文件**无法**转换。
2. **睡眠壁纸只在 KOReader 内睡眠时生效**；原生界面的睡眠屏需要 NiLuJe ScreensaverHack，本机是 soft-float 最终固件，官方标注"可能不工作"，本包**不安装**。
3. **未注册设备**：KOReader/传书/资讯全部可用；但 Kindle 商店、Kindle Unlimited、官方 Send to Kindle、云同步不可用。
4. **第三方账号风险**：微信读书插件是第三方客户端，作者声明可能有账号风控；登录必须本人操作。
5. **平台差异**：`send2kindle` 的系统凭据后端 macOS 已实机验证，Windows/Linux 未实机验收。
6. **不协助盗版**：本包不包含、不指导 Z-Library/LibGen/Telegram 机器人等渠道。

---

## 9. 参考来源

- KindleModding 官方 Wiki：<https://kindlemodding.org/jailbreaking/>
- 越狱向导（判定方法）：<https://kindlemodding.org/jailbreak-wizard.html>
- KOReader 官方：<https://github.com/koreader/koreader> ｜ Kindle 安装说明见其 Wiki
- SimpleUI（上游）：<https://github.com/doctorhetfield-cmd/simpleui.koplugin>；本机使用 <https://github.com/joeseesun/qiaomu-simpleui>
- 乔木无线传书：<https://github.com/joeseesun/qiaomu-send2kindle>
- 微信读书插件：<https://github.com/finlater/weread.koplugin>
- 填盘脚本：<https://github.com/bastianmarin/Kindle-Filler-Disk>
- KindleUnpack（AZW3→EPUB）：<https://github.com/kevinhendricks/KindleUnpack>

---

## 10. 变更记录

| 版本 | 日期 | 内容 |
|---|---|---|
| 1.0.0 | 2026-10-26 | 首版：在 PW3 / 5.16.2.1.1 上完成越狱、KOReader、SimpleUI、微信读书、无线传书、资讯 RSS（原文优先 + 英文源）、睡眠壁纸，并记录 12 类实机故障的定位与修复 |
