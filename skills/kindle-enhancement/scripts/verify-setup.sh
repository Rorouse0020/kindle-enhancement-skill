#!/bin/bash
# Kindle 全栈体检（只读，不修改任何东西）
# 用法: bash scripts/verify-setup.sh [/Volumes/Kindle]
# 退出码: 0=全部通过 / 1=有失败项
VOL="${1:-/Volumes/Kindle}"
PASS=0; FAIL=0; WARN=0
ok(){   printf "  \033[32m✅ %-46s\033[0m %s\n" "$1" "${2:-}"; PASS=$((PASS+1)); }
bad(){  printf "  \033[31m❌ %-46s\033[0m %s\n" "$1" "${2:-}"; FAIL=$((FAIL+1)); }
warn(){ printf "  \033[33m⚠️  %-46s\033[0m %s\n" "$1" "${2:-}"; WARN=$((WARN+1)); }
hdr(){  printf "\n\033[1m== %s ==\033[0m\n" "$1"; }

hdr "0. 设备与固件"
if [ ! -d "$VOL" ]; then bad "挂载点存在" "$VOL 不存在（KOReader 运行时不会挂载，先退出 KOReader）"; echo; echo "结论: 无法继续"; exit 1; fi
ok "挂载点" "$VOL"
if [ -f "$VOL/system/version.txt" ]; then
  VER=$(cat "$VOL/system/version.txt"); ok "固件版本" "$VER"
  case "$VER" in *"5.16.2.1.1"*) ok "固件在已验证范围" "PW3 soft-float";; *) warn "固件非本包实机验证版本" "流程框架通用，但请按 jailbreaks.json 重新判定";; esac
else bad "读取 version.txt" "不是 Kindle 卷？"; fi

hdr "1. 时钟（HTTPS 与资讯的前提）"
YEAR=$(date -r "$VOL/koreader/settings.reader.lua" +%Y 2>/dev/null || echo 0)
CUR=$(date +%Y)
if [ "$YEAR" = "0" ]; then warn "无法判断设备时钟" "无 settings.reader.lua"
elif [ "$YEAR" = "$CUR" ]; then ok "设备写入时间年份" "$YEAR"
else warn "设备时钟可能不对" "文件年份=$YEAR 当前=$CUR → 见 references/ext-troubleshooting.md T1"; fi

hdr "2. 越狱"
[ -f "$VOL/documents/JAILBROKEN.txt" ] && ok "越狱标记 JAILBROKEN.txt" "$(grep -c . "$VOL/documents/JAILBROKEN.txt") 行" || bad "越狱标记 JAILBROKEN.txt" "未越狱或文件被删"
[ -f "$VOL/libkh/bin/fbink" ] && ok "越狱组件 libkh/bin/fbink" "$(du -h "$VOL/libkh/bin/fbink" | cut -f1)" || warn "libkh/bin/fbink 缺失" "越狱可能不完整"
[ -f "$VOL/jb.sh" ] && ok "jb.sh 保留（恢复用）" "$(du -h "$VOL/jb.sh" | cut -f1)" || warn "jb.sh 缺失" "可用 URL 重下"

hdr "3. KOReader"
if [ -f "$VOL/koreader/git-rev" ]; then ok "KOReader 版本" "$(cat "$VOL/koreader/git-rev")"; else bad "KOReader 未安装" "koreader/git-rev 不存在"; fi
[ -f "$VOL/koreader/reader.lua" ] && ok "reader.lua" "" || bad "reader.lua 缺失" ""
[ -f "$VOL/documents/KOReader.sh" ] && ok "启动器 documents/KOReader.sh" "" || bad "启动器缺失" "参考 assets/KOReader.sh"
if [ -f "$VOL/koreader/settings.reader.lua" ]; then
  HD=$(grep -oE '\["home_dir"\] = "[^"]*"' "$VOL/koreader/settings.reader.lua" | head -1)
  case "$HD" in *"/mnt/us/documents"*) ok "书库路径 home_dir" "$HD";; "") warn "未设置 home_dir" "默认 /mnt/us";; *) warn "书库路径不是 documents" "$HD → 见 references/ext-koreader.md";; esac
else warn "settings.reader.lua 不存在" "KOReader 还没首次运行"; fi

hdr "4. 插件"
SU="$VOL/koreader/plugins/simpleui.koplugin"
if [ -d "$SU" ]; then
  V=$(grep -oE 'version *= *"[^"]+"' "$SU/_meta.lua" | head -1)
  ok "SimpleUI" "$V ($(find "$SU" -type f | wc -l | tr -d ' ') 文件)"
else bad "SimpleUI 未安装" "koreader/plugins/simpleui.koplugin"; fi
WR="$VOL/koreader/plugins/weread.koplugin"
if [ -d "$WR" ]; then ok "微信读书插件" "$(grep -oE 'version *= *"[^"]+"' "$WR/_meta.lua" | head -1)"; else warn "微信读书插件未安装" "可选"; fi
[ -d "$VOL/koreader/plugins/SSH.koplugin" ] && ok "SSH 插件（自带）" "" || warn "SSH.koplugin 缺失" "传书需要它"

hdr "5. 无线传书配置"
if [ -f "$VOL/koreader/settings/SSH/authorized_keys" ]; then
  N=$(grep -c 'qiaomu-kindlesync' "$VOL/koreader/settings/SSH/authorized_keys" 2>/dev/null)
  [ "${N:-0}" -ge 1 ] && ok "已配对公钥" "$N 条 qiaomu-kindlesync" || warn "authorized_keys 无 send2kindle 公钥" "重新 pair"
else warn "未配对" "settings/SSH/authorized_keys 不存在"; fi
grep -qE '\["SSH_autostart"\] = true' "$VOL/koreader/settings.reader.lua" 2>/dev/null && ok "SSH 自启" "SSH_autostart=true" || warn "SSH 未设自启" "可在 KOReader 工具→SSH server 手动开"
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
[ -x "$RT" ] && ok "send2kindle 运行时" "$("$RT" -c 'import sys;print(sys.version.split()[0])' 2>/dev/null)" || warn "运行时缺失" "python3 scripts/setup_runtime.py"
[ -f "$HOME/Library/Application Support/Qiaomu/Kindle/devices.json" ] && ok "设备身份元数据" "devices.json" || warn "无设备元数据" "尚未配对"

hdr "6. 资讯 RSS"
F="$VOL/koreader/plugins/simpleui.koplugin/features/sui_news.lua"
if [ -f "$F" ]; then
  P=$(grep -c 'local patch' "$F"); R=$(grep -c '/rewrite' "$F")
  [ "$P" -ge 2 ] && [ "$R" -eq 0 ] && ok "原文优先补丁" "标记 $P 处 / rewrite $R 次" || warn "原文优先补丁未生效" "标记 $P / rewrite $R（见 references/ext-content-rss.md）"
else warn "找不到 sui_news.lua" ""; fi
SRC="$VOL/koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json"
if [ -f "$SRC" ]; then
  ON=$(grep -o '"enabled": *false' "$SRC" | wc -l | tr -d ' ')
  ok "资讯源目录" "关闭 $ON 个源（其余启用）"
fi
[ -f "$VOL/koreader/news/feed_config.lua" ] && ok "英文 RSS 配置 feed_config.lua" "$(grep -cE '^\s*\{"https?://' "$VOL/koreader/news/feed_config.lua") 条源" || warn "无 feed_config.lua" "News downloader 可用默认"

hdr "7. 睡眠壁纸"
if [ -d "$VOL/wallpapers" ]; then ok "壁纸目录" "$(ls "$VOL/wallpapers"/*.jpg 2>/dev/null | wc -l | tr -d ' ') 张"; else warn "无壁纸目录" "/mnt/us/wallpapers"; fi
ST=$(grep -oE '\["screensaver_type"\] = "[^"]*"' "$VOL/koreader/settings.reader.lua" 2>/dev/null | head -1)
case "$ST" in *random_image*) ok "屏保模式" "$ST";; "") warn "未配置屏保" "默认'休眠中'提示";; *) warn "屏保模式非随机图" "$ST";; esac
SD=$(grep -oE '\["screensaver_dir"\] = "[^"]*"' "$VOL/koreader/settings.reader.lua" 2>/dev/null | head -1)
[ -n "$SD" ] && ok "壁纸目录设置" "$SD" || warn "未设置 screensaver_dir" ""

hdr "8. 安全状态"
C=$(ls "$VOL"/update*.bin 2>/dev/null | wc -l | tr -d ' ')
[ "$C" = "0" ] && ok "根目录无更新包" "" || bad "存在 update*.bin" "$C 个，请删除（防 OTA 意外安装）"
[ -d "$VOL/fill_disk" ] && warn "填充分区仍存在" "越狱完成后应删除以回收空间" || ok "无填充分区" ""
DF=$(df -m "$VOL" | awk 'NR==2{print $4}'); ok "可用空间" "${DF} MB"

echo
printf "\033[1m结论: 通过 %d / 警告 %d / 失败 %d\033[0m\n" "$PASS" "$WARN" "$FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
