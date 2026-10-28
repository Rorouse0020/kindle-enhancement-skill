# 02 · KOReader 安装（含启动器与书库路径修正）

> 目标：装好 KOReader 并能从书库一键启动；书库指向正确的 `documents/`。
> 本机实测：**KOReader v2026.07.1** + `koreader-kindlepw2` 包（soft-float）。
> 前提：已完成 `references/zh-CN/ext-jailbreak.md`。

---

## 1. 选对安装包（选错 = 启动即崩）

| 包名 | 适用 | 判定方法 |
|---|---|---|
| `koreader-kindlepw2-*.zip` | **soft-float**：PW2/PW3/KT2/KV/KOA1 等（固件 < 5.16.3） | 设备上 `ls /lib/ld-linux-armhf.so.3` **不存在** |
| `koreader-kindlehf-*.zip` | **hard-float**：5.16.3+ 的机型 | 上一条 `ls` **存在** |
| `koreader-kindle-*.zip` / `kindle-legacy` | 更老机型（K4/K5 等） | 见 KOReader Wiki |

下载（把 `v2026.07.1` 换成你要的版本）：
```bash
cd ~/Downloads && mkdir -p koreader && cd koreader
curl -L -o kor.zip https://github.com/koreader/koreader/releases/download/v2026.07.1/koreader-kindlepw2-v2026.07.1.zip
unzip -l kor.zip | head -12      # 期望：extensions/koreader/... 与 koreader/...
shasum -a 256 kor.zip            # 记录，便于他人核对（本机包 = 40,715,224 B）
```

> KOReader 官方 release 不提供逐文件签名；如需严格校验，以 GitHub release 页面为准并核对大小。

---

## 2. 安装

```bash
VOL=/Volumes/Kindle
[ -d "$VOL/documents" ] || { echo "不是 Kindle 卷"; exit 1; }
unzip -o kor.zip -d "$VOL"        # 得到 koreader/ 与 extensions/koreader/
ls -d "$VOL/koreader" "$VOL/extensions/koreader"
cat "$VOL/koreader/git-rev"        # 期望：v2026.07.1
find "$VOL/koreader" -type f | wc -l   # 本机约 2227 个文件
```

---

## 3. 启动器（关键）

KOReader 的 `koreader.sh` 最终执行 `./reader.lua`，而 `/mnt/us` 默认可能是 **noexec**。
因此启动器必须先 remount 再启动。把本包 `assets/KOReader.sh` 放到 `documents/`：

```sh
#!/bin/sh
# Name: KOReader
# Author: KindleModding
# Icon: /mnt/us/koreader/resources/koreader.png
mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
cd /mnt/us/koreader || exit 1
exec sh ./koreader.sh
```
```bash
cp assets/KOReader.sh "$VOL/documents/KOReader.sh"
diskutil eject "$VOL"
```

原理：越狱时装了 **sh_integration**（jb.sh 注册的 extractor），所以 `documents/` 里的 `.sh`
会被当"书"索引，点击即以 root 运行 —— 这是官方认可的脚本启动方式（KOReader FAQ 也提到可用 scriptlet 启动）。
`# Name:` 决定书库显示名，`# Icon:` 决定图标。

> 备选：若你另外装了 KUAL，也可从 KUAL 的 KOReader 菜单启动
> （`extensions/koreader/` 已随包安装）。

---

## 4. 首次启动

设备上：书库 → **KOReader** → 等待 10–30 秒（首次生成 cache 与 settings）。
成功标志：出现 KOReader 文件浏览器。

首次启动会生成：
```
koreader/settings.reader.lua      # 全局设置
koreader/settings/                # 各插件设置
koreader/cache/                   # 缓存
```

---

## 5. ⚠️ 书库空白/看不到书：修正 home_dir

**症状**：KOReader 能启动，但书架看不到 `documents/` 里的书。
**根因**：`home_dir` 被设成了某个空目录（本机是 `/mnt/us/Books`），且 `lock_home_folder=true` 锁死了导航。

诊断（USB 或 SSH 均可）：
```bash
VOL=/Volumes/Kindle
grep -nE '\["home_dir"\]|\["lock_home_folder"\]|\["lastdir"\]' "$VOL/koreader/settings.reader.lua"
```

修复（**必须在 KOReader 退出时改**，否则它退出时会回写覆盖）：

```bash
VOL=/Volumes/Kindle; S="$VOL/koreader/settings.reader.lua"
cp -p "$S" "$S.bak-homefix-$(date +%Y%m%d-%H%M%S)"
python3 - "$S" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
s=re.sub(r'^    \["home_dir"\] = "[^"]*",$','    ["home_dir"] = "/mnt/us/documents",',s,flags=re.M)
s=re.sub(r'^    \["lock_home_folder"\] = \w+,$','    ["lock_home_folder"] = false,',s,flags=re.M)
s=re.sub(r'^    \["lastdir"\] = "[^"]*",$','    ["lastdir"] = "/mnt/us/documents",',s,flags=re.M)
open(p,'w',encoding='utf-8').write(s)
PY
grep -E '\["(home_dir|lock_home_folder|lastdir)"\]' "$S"
```
重启 KOReader 后书库即正常。

> 为什么重要：`/mnt/us/documents` 也是无线传书的目标目录（`references/zh-CN/ext-send2kindle.md`）。
> 修好后"传过去的书立刻可见"，否则会出现"传成功但看不到"。

---

## 6. 验证清单

```bash
VOL=/Volumes/Kindle
cat "$VOL/koreader/git-rev"                                  # v2026.07.1
ls -l "$VOL/koreader/reader.lua" "$VOL/koreader/koreader.sh" # 存在且可读
grep -E '\["home_dir"\]' "$VOL/koreader/settings.reader.lua" # /mnt/us/documents
ls "$VOL/documents/KOReader.sh"                              # 启动器存在
```
设备上：点 KOReader 能进入；书库能看到 `documents/` 的 EPUB/PDF。

---

## 7. 常见问题

| 现象 | 处理 |
|---|---|
| 点 KOReader 无反应/闪回 | 检查启动器是否有 `mount -o remount,exec`；`/mnt/us` noexec 时 `reader.lua` 无法执行 |
| 启动后黑屏/花屏 | 确认包是 `kindlepw2`（soft-float）；hard-float 机器用 `kindlehf` |
| 书库空 | §5（home_dir） |
| 菜单里没有某插件 | 插件目录名必须严格为 `<名字>.koplugin`，且需**重启 KOReader** |
| 想升级 KOReader | 退出 KOReader → 用新 zip 覆盖解压 → 重启；设置与插件保留 |
