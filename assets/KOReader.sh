#!/bin/sh
# Name: KOReader
# Author: KindleModding
# Icon: /mnt/us/koreader/resources/koreader.png
# 启动 KOReader（越狱后由 shell integration 运行；先确保 /mnt/us 可执行）
mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
cd /mnt/us/koreader || exit 1
exec sh ./koreader.sh
