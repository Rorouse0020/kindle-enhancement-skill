#!/bin/bash
# Kindle 越狱准备（本地执行变体）—— 放入官方 jb.sh + 本地执行版 dialoger + 填满存储
#
# 为什么需要"本地执行"：
#   官方 dialoger.html 执行 `curl -L https://kindlemodding.org/jb.sh | sh`，
#   而该域名是 GitHub Pages；设备直连失败时 sh 收到空内容 → 静默无反应。
#   本脚本把官方 jb.sh 放到设备本地，并替换 dialoger 让它执行 `sh /mnt/us/jb.sh`。
#
# 用法: bash kindle-prepare-local.sh [/Volumes/Kindle] [剩余MB=90]
#   环境变量: JB_SH=<本地 jb.sh 路径>   跳过下载（离线时用）
#             SKIP_HASH=1               跳过哈希校验（不推荐）
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ASSETS="$(dirname "$HERE")/assets"
VOL="${1:-/Volumes/Kindle}"
LEAVE_MB="${2:-90}"
CHUNK_MB=200

# 官方 jb.sh v2.4.0（本包实机验证过的版本）的 SHA-256；上游更新后哈希会变，
# 此时请自行到 https://kindlemodding.org/jb.sh 下载并核对，或用 JB_SH 指定。
JB_SHA256="cfe16df16effaa3be04dcddc63b542db57b6146820936d4098f8326d58fbbc02"

echo "== 目标卷: $VOL"
case "$VOL" in /Volumes/*|/media/*|/mnt/*) ;; *) echo "!! 目标路径看起来不是挂载卷，拒绝执行"; exit 1 ;; esac
[ -d "$VOL/documents" ] || { echo "!! $VOL/documents 不存在（不是 Kindle 卷，或 KOReader 正在运行导致未挂载）"; exit 1; }
[ -f "$VOL/system/version.txt" ] || { echo "!! 找不到 version.txt"; exit 1; }
echo "== 固件: $(cat "$VOL/system/version.txt")"

# ---- 1) 准备 jb.sh ----
JB="${JB_SH:-$ASSETS/jb.sh}"
if [ ! -f "$JB" ]; then
  echo "== 本地没有 jb.sh，尝试下载 https://kindlemodding.org/jb.sh ..."
  curl -fsSL -m 120 -o "$ASSETS/jb.sh" https://kindlemodding.org/jb.sh || { echo "!! 下载失败；请手动下载后用 JB_SH=<路径> 重跑"; exit 1; }
  JB="$ASSETS/jb.sh"
fi
if [ "${SKIP_HASH:-0}" != "1" ]; then
  GOT=$( (shasum -a 256 "$JB" 2>/dev/null || sha256sum "$JB") | cut -d' ' -f1 )
  if [ "$GOT" != "$JB_SHA256" ]; then
    echo "!! jb.sh 哈希不匹配（可能是上游更新）"
    echo "   期望: $JB_SHA256"
    echo "   实际: $GOT"
    echo "   确认来源可信后可设置 SKIP_HASH=1 继续；否则中止。"
    exit 1
  fi
  echo "== jb.sh 哈希校验通过"
fi

# ---- 2) 放载荷 ----
mkdir -p "$VOL/winterbreak2"
cp -f "$ASSETS/dialoger-local.html" "$VOL/winterbreak2/dialoger.html"
cp -f "$JB" "$VOL/jb.sh"
echo "== 已放置: winterbreak2/dialoger.html + jb.sh（$(du -h "$VOL/jb.sh" | cut -f1)）"

# ---- 3) 清 macOS 元数据 ----
find "$VOL" -maxdepth 2 -name '._*' -type f -delete 2>/dev/null
echo "== 已清理 ._* / .DS_Store"

# ---- 4) 填满存储（防 OTA 打断越狱）----
mkdir -p "$VOL/fill_disk"
i=0
while :; do
  free=$(df -m "$VOL" | awk 'NR==2{print $4}')
  [ -z "$free" ] && { echo "!! 读不到可用空间"; exit 1; }
  [ "$free" -le "$LEAVE_MB" ] && { echo "== 填满完成，可用 ${free} MB"; break; }
  i=$((i+1))
  if dd if=/dev/zero of="$VOL/fill_disk/fill_$i.bin" bs=1m count=$CHUNK_MB 2>/dev/null; then
    echo "   块 $i 完成，可用 $(df -m "$VOL" | awk 'NR==2{print $4}') MB"
  else
    echo "   块 $i 写入失败（接近写满）"; rm -f "$VOL/fill_disk/fill_$i.bin"; break
  fi
done
sync

# ---- 5) 汇总 ----
echo
echo "==== 准备完成 ===="
df -m "$VOL" | tail -1 | awk '{print "可用: "$4" MB / 总计 "$2" MB"}'
if [ -f "$VOL/jb.sh" ]; then echo "jb.sh: OK ($(stat -f%z "$VOL/jb.sh" 2>/dev/null || stat -c%s "$VOL/jb.sh") bytes)"; else echo "jb.sh 缺失"; exit 1; fi
if [ -f "$VOL/winterbreak2/dialoger.html" ]; then echo "dialoger.html: OK"; else echo "dialoger 缺失"; exit 1; fi
echo
echo "下一步：安全弹出（macOS: diskutil eject \"$VOL\"）"
echo "       设备上：连 Wi-Fi → 体验版浏览器 → https://penguins184.xyz/wb2 → 点 Jailbreak → 确认下载"
echo "       若 10-30 秒无反应，按 Home 回主页等待。"
