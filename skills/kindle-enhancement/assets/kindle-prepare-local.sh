#!/bin/bash
# Kindle PW3 —— 越狱准备（本地执行版 / rebuild）
# 与官方 WB2 的区别只有一处：dialoger.html 不再从 GitHub Pages 下载 jb.sh，
# 而是直接执行已经放在设备上的 /mnt/us/jb.sh（文件内容 = 官方原版，已校验）。
# 另外会写 JB_TRACE.txt / JB_LOG.txt 便于事后诊断。
#
# 用法: bash tools/kindle-prepare-local.sh [/Volumes/Kindle] [剩余MB]
set -u

VOL="${1:-/Volumes/Kindle}"
LEAVE_MB="${2:-90}"
CHUNK_MB=200

echo "== 目标卷: $VOL"
case "$VOL" in /Volumes/*) ;; *) echo "!! 目标不在 /Volumes 下，拒绝执行"; exit 1 ;; esac
[ -d "$VOL/documents" ] || { echo "!! $VOL/documents 不存在，不是 Kindle 卷"; exit 1; }
[ -f "$VOL/system/version.txt" ] || { echo "!! 找不到 version.txt"; exit 1; }
echo "== 固件: $(cat "$VOL/system/version.txt")"
grep -q "Kindle 5.16.2.1.1" "$VOL/system/version.txt" || { echo "!! 固件不是 5.16.2.1.1，终止"; exit 1; }

# --- 1) 放载荷 ---
mkdir -p "$VOL/winterbreak2"
cp -f "/Users/rorouse/DeepSeek Harness/Kindle/tools/dialoger-local.html" "$VOL/winterbreak2/dialoger.html"
cp -f "/Users/rorouse/DeepSeek Harness/Kindle/downloads/jb.sh" "$VOL/jb.sh"
echo "== 已放置:"
ls -l "$VOL/winterbreak2/dialoger.html" "$VOL/jb.sh" | sed 's/^/   /'

# --- 2) 清 macOS 元数据 ---
find "$VOL" -maxdepth 2 -name '._*' -type f -delete 2>/dev/null
find "$VOL" -maxdepth 2 -name '.DS_Store' -type f -delete 2>/dev/null
echo "== 已清理 ._* / .DS_Store"

# --- 3) 填满存储（防越狱途中 OTA）---
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
    echo "   块 $i 写入失败（可能已满）"; rm -f "$VOL/fill_disk/fill_$i.bin"; break
  fi
done
sync

# --- 4) 汇总 ---
echo
echo "==== 准备完成 ===="
df -m "$VOL" | tail -1 | awk '{print "可用: "$4" MB / 总计 "$2" MB"}'
[ -f "$VOL/jb.sh" ] && echo "jb.sh: ✅ $(stat -f%z "$VOL/jb.sh") bytes" || { echo "jb.sh 缺失 ❌"; exit 1; }
[ -f "$VOL/winterbreak2/dialoger.html" ] && echo "dialoger.html: ✅ $(stat -f%z "$VOL/winterbreak2/dialoger.html") bytes" || { echo "dialoger 缺失 ❌"; exit 1; }
find "$VOL" -maxdepth 1 -name 'update*.bin' | wc -l | awk '{print "根目录 update*.bin: "$1" 个（应为 0）"}'
