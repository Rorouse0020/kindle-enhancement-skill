# 01 · 越狱（WinterBreak2，含 GitHub 被墙时的本地执行变体）

> 目标：让 Kindle 可以运行第三方代码（root shell、包管理器），并自动封锁 OTA。
> 产出：`documents/JAILBROKEN.txt` + `/mnt/us/libkh/bin/fbink` + `/var/local/jailbreak.txt`
> 预计：20–30 分钟（含填盘 5–10 分钟）

---

## 1. 选对方法（先判定，不要盲试）

### 1.1 PW3 / 5.16.2.1.1 的结论

| 方法 | 覆盖固件 | 需要注册亚马逊账号 | 对本机 |
|---|---|---|---|
| **WinterBreak2** | 5.6.1.1 – 5.16.3（另接受 5.16.5） | ❌ 不需要 | ✅ **首选** |
| WinterBreak（原版） | 5.6.1.1 – 5.18.0.2 | ✅ 需要 | 备选（WB2 失败时） |
| SpiderCat / Sanctuary / Noodle / SpringBreak / AdBreak / Véra | — | — | ❌ 模型列表不含 PW3 |
| Popcorn PW3 | — | — | ⚠️ 需拆机短接（硬件越狱），最后手段 |

> 为什么 PW3 固件上限是 5.16.2.1.1：Amazon 未给 PW3 发布 5.16.3+ 的包（`s3.amazonaws.com/firmwaredownloads/update_kindle_all_new_paperwhite_5.16.3.bin` 返回 403，而 5.16.2.1.1 返回 200）。

### 1.2 其他机型怎么判

```bash
curl -s https://kindlemodding.org/jailbreaks.json   # 方法 → models/firmwares 区间
curl -s https://kindlemodding.org/models.json       # 序列号前缀 → 机型
```
规则：`机型 ∈ jb.models` 且固件落在 `[min,max]`（或 `outliers.accepted`，且不在 `denied`）；
按文件顺序**第一个匹配**即官方推荐；`registration:true` 表示**要求设备已注册**。

---

## 2. 准备

| 项 | 要求 |
|---|---|
| 电脑 | macOS/Linux + `curl`、`unzip` |
| 数据线 | 能传数据的 USB 线 |
| 设备 | **已解锁、已退出 KOReader**（KOReader 会阻止 U 盘挂载） |
| 网络 | 设备能上 Wi-Fi（越狱过程中要用浏览器） |
| 必备动作 | Phase 0 的备份 + 时钟检查（`date` 年份必须正确，否则 HTTPS 全失败） |

下载官方载荷（写进本包的是 2026-10-26 的 v1.1.0）：
```bash
cd ~/Downloads && mkdir -p kindle-jb && cd kindle-jb
curl -L -o wb2.zip https://github.com/KindleModding/Winterbreak2/releases/latest/download/wb2.zip
unzip -l wb2.zip            # 应看到 winterbreak2/dialoger.html
shasum -a 256 wb2.zip       # 记录哈希，便于与他人核对
```

---

## 3. 官方流程（推荐先试）

### 3.1 填满存储（防越狱途中被 OTA 打断）

原则：**可用空间压到 50–90 MB**，让更新包下不下来。

```bash
VOL=/Volumes/Kindle
# 先开飞行模式；删除已下载的更新包
rm -f "$VOL"/update*.bin "$VOL"/update.bin.tmp.partial

# 方式 A：官方脚本（PW3 是普通 U 盘模式，macOS 可用）
cp ~/Downloads/kindle-jb/../Filler.sh "$VOL"/ 2>/dev/null || true
cd "$VOL" && bash Filler.sh        # 选 Fill，目标留 50/100MB

# 方式 B：手动 dd（等价、确定性更好）
VOL=/Volumes/Kindle; mkdir -p "$VOL/fill_disk"; i=0
while [ "$(df -m "$VOL" | awk 'NR==2{print $4}')" -gt 90 ]; do
  i=$((i+1)); dd if=/dev/zero of="$VOL/fill_disk/fill_$i.bin" bs=1m count=200 2>/dev/null || { rm -f "$VOL/fill_disk/fill_$i.bin"; break; }
done
df -m "$VOL"
```

> ⚠️ 官方 `Filler.sh` 在 macOS 上偶发"看门狗误杀已成功的块"，导致循环提前结束；
> 用上面的 dd 循环更稳（实测写入 ~9.4 MB/s，3 GB 约 5–6 分钟）。

### 3.2 放入载荷并触发

```bash
unzip -o ~/Downloads/kindle-jb/wb2.zip -d "$VOL"     # 根目录出现 winterbreak2/
ls -d "$VOL/winterbreak2"                            # 必须存在
dot_clean "$VOL" 2>/dev/null || true                  # 清 macOS 元数据残留
diskutil eject "$VOL"                                # macOS 安全弹出
```

设备上操作：
1. 连 Wi-Fi（能真正打开网页）。
2. 打开**体验版浏览器**（菜单 → Experimental Browser；或 设置 → 设备选项 → 高级选项）。
3. 访问 **`https://penguins184.xyz/wb2`** → 点 **Jailbreak** → 若出现下载提示，**确认下载**。
4. 若 10–30 秒无反应：按 Home 回主页等待（漏洞链的对话框是在主页/下载通知层渲染的）。

### 3.3 预期表现

屏幕开始刷日志（`Stopping OTA`、`Installing libkh binaries`…）→ 出现 `Restarting Kindle` → 自动重启。
重启后书库出现 **JAILBROKEN** 条目。

---

## 4. ⚠️ 本地执行变体（GitHub Pages 被墙时的关键解法）

### 4.1 症状与根因

**症状**：点了 Jailbreak → 出现下载提示 → 之后**毫无反应**，没有日志、没有对话框、没有重启。

**根因**（读官方载荷即可确认）：`winterbreak2/dialoger.html` 执行的是
```html
source_command: "sh -c 'curl -L https://kindlemodding.org/jb.sh | JB_HEADER=\"Winterbreak2 Jailbreak\" sh'"
```
而 `kindlemodding.org` 托管在 **GitHub Pages（185.199.108-111.153）**。设备直连拉不到时，
`sh` 收到空内容 → 静默退出 → 表现为"点了没反应"。

### 4.2 解法

保留官方 `jb.sh` 原版（**必须核对哈希**），只把"URL 下载"改成"执行设备本地文件"：

```bash
cd ~/Downloads/kindle-jb
curl -L -o jb.sh https://kindlemodding.org/jb.sh
shasum -a 256 jb.sh          # 本机实测：cfe16df16effaa3be04dcddc63b542db57b6146820936d4098f8326d58fbbc02（8,691,170 B，v2.4.0）
```

然后把本包 `assets/dialoger-local.html` 放到设备的 `winterbreak2/dialoger.html`，并放 `jb.sh` 到根目录：
```bash
VOL=/Volumes/Kindle
cp assets/dialoger-local.html "$VOL/winterbreak2/dialoger.html"
cp ~/Downloads/kindle-jb/jb.sh "$VOL/jb.sh"
```
或者直接用脚本一次做完（含填盘）：
```bash
bash scripts/kindle-prepare-local.sh /Volumes/Kindle 90
```

本地执行版的命令等价于：
```
sh -c 'echo DIALOGER_EXECUTED > /mnt/us/JB_TRACE.txt;
       JB_HEADER="Winterbreak2 Jailbreak" sh /mnt/us/jb.sh > /mnt/us/JB_LOG.txt 2>&1;
       echo EXIT=$? >> /mnt/us/JB_TRACE.txt'
```
其中 `JB_TRACE.txt` / `JB_LOG.txt` 是**诊断文件**：失败时插 USB 就能看到卡在哪一步。

### 4.3 为什么不需要注册、也不依赖网络

- WB2 的官方向导数据里 `registration:false`；页面本身只负责触发漏洞链，脚本完全在本机执行。
- 唯一必需的网络访问是**打开 `penguins184.xyz/wb2` 页面**（Cloudflare）。若该页面都打不开，换网络（手机热点）后重试。

---

## 5. 验证（三项都要过）

```bash
VOL=/Volumes/Kindle
cat "$VOL/documents/JAILBROKEN.txt"
# 期望：
# You are jailbroken!
# (jb.sh v2.4.0)
# https://kindlemodding.org
# https://hackerdude.tech
#
# Winterbreak2 Jailbreak

ls -l "$VOL/libkh/bin/fbink"        # 期望存在（约 1.38 MB）
cat "$VOL/JB_TRACE.txt"             # 本地执行版：DIALOGER_EXECUTED + EXIT=0
```
设备上再确认：搜索框输入 `;log` 回车，能弹出文字 = 已越狱。

---

## 6. 越狱后收尾

```bash
VOL=/Volumes/Kindle
df -m "$VOL"
rm -rf "$VOL/fill_disk"                    # 回收空间（确认 OTA 已封后再删）
rm -f "$VOL"/update*.bin                   # 清掉任何更新包
ls -A "$VOL/documents" | head              # 放 disable_oobe.sh（未注册设备必做）
```
- `disable_oobe.sh`（官方 scriptlet，见 `assets/` 或 `https://kindlemodding.org/jailbreaking/disable_oobe.sh`）：
  放进 `documents/`，在书库点一次 → 删除 OOBE 标记并重启，之后重启不再回初始设置。
- 保留 `jb.sh`（8.7 MB）：OTA 更新/重置恢复流程会用到，删了也能重新下载。

---

## 7. 失败分支

| 现象 | 去查 |
|---|---|
| 点 Jailbreak 完全无反应 | 本文 §4（本地执行变体） |
| 有日志但中途停住 | `references/07-troubleshooting.md` T2、T3 |
| 浏览器打不开页面 | T5（网络/DNS） |
| 卡在 `Update Failed` | `references/08-rollback.md` §3 |
| 重启后没出现 JAILBROKEN | 重跑一次；仍无则看 `JB_LOG.txt` 末尾 |
