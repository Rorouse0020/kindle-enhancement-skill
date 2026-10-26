#!/usr/bin/env python3
"""给 Kindle 应用「随机睡眠壁纸」：推送壁纸包 + 配置 KOReader 屏保设置。

前置：Kindle 已退出 KOReader 并以 USB 挂载（KOReader 运行时不会挂载 U 盘，
      且它退出时会回写 settings.reader.lua，会把外部修改覆盖掉）。

用法: python3 tools/apply-wallpapers.py [/Volumes/Kindle]
回滚: 把生成的 settings.reader.lua.bak-wallpaper-<时间戳> 改名回去，并删除 /mnt/us/wallpapers。
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VOL = Path(sys.argv[1] if len(sys.argv) > 1 else "/Volumes/Kindle")
# 壁纸目录：默认 <skill>/wallpapers/sleep（先跑 scripts/gen-wallpapers.py 生成），可用 --images 指定
_IMAGES = None
if "--images" in sys.argv:
    _IMAGES = Path(sys.argv[sys.argv.index("--images") + 1]).expanduser()
    del sys.argv[sys.argv.index("--images"):sys.argv.index("--images") + 2]
_PKG = Path(__file__).resolve().parent.parent
_BUNDLED = _PKG / "assets" / "wallpapers"
_GENERATED = _PKG / "wallpapers" / "sleep"
LOCAL = _IMAGES or (_GENERATED if any(_GENERATED.glob("*.jpg")) else _BUNDLED)
DEST = VOL / "wallpapers"
SETTINGS = VOL / "koreader/settings.reader.lua"
KODIR = VOL / "koreader"

if not (VOL / "system/version.txt").is_file():
    raise SystemExit(f"不是 Kindle 卷：{VOL}")
print("设备固件:", (VOL / "system/version.txt").read_text(errors="replace").strip())

# ---- 1) 推送壁纸 ----
images = sorted(LOCAL.glob("*.jpg"))
if not images:
    raise SystemExit(f"本地壁纸目录为空：{LOCAL}")
DEST.mkdir(exist_ok=True)
for src in images:
    shutil.copy2(src, DEST / src.name)
total = sum((DEST / p.name).stat().st_size for p in images)
print(f"已推送 {len(images)} 张壁纸 → {DEST}（{total/1024/1024:.1f} MB）")

# ---- 2) 改 KOReader 屏保设置 ----
if not SETTINGS.is_file():
    raise SystemExit(f"找不到 {SETTINGS}（KOReader 未安装？）")
stamp = time.strftime("%Y%m%d-%H%M%S")
backup = SETTINGS.with_name(SETTINGS.name + f".bak-wallpaper-{stamp}")
shutil.copy2(SETTINGS, backup)

text = SETTINGS.read_text(encoding="utf-8")
before = text
WANT = {
    "screensaver_type": '"random_image"',
    "screensaver_dir": '"/mnt/us/wallpapers"',
    "screensaver_show_message": "false",
}
for key, value in WANT.items():
    pattern = rf'^(\s*)\["{key}"\] = [^\n]*,?$'
    line = f'    ["{key}"] = {value},'
    if re.search(pattern, text, re.M):
        text = re.sub(pattern, line, text, count=1, flags=re.M)
    else:
        # 插到 return 表的末尾（最后一个 } 之前）
        idx = text.rstrip().rfind("}")
        text = text[:idx] + line + "\n" + text[idx:]
SETTINGS.write_text(text, encoding="utf-8")
print(f"已更新屏保设置（备份：{backup.name}）")

# ---- 3) 校验 ----
ok = True
for key, value in WANT.items():
    m = re.search(rf'\["{key}"\] = ([^,\n]+)', text)
    got = m.group(1).strip() if m else None
    good = got == value
    ok = ok and good
    print(f"  {key}: {got} {'✅' if good else '❌'}")
if not ok:
    raise SystemExit("设置写入校验失败，请检查 settings.reader.lua")

# 结构粗检：可被 KOReader 解析
if not (re.match(r"^\s*(?:--[^\n]*\n\s*)*return\s*\{", text) and text.rstrip().endswith("}")):
    raise SystemExit("settings.reader.lua 结构异常，已中止（请恢复备份）")

n = len(list(DEST.glob("*.jpg")))
print(f"\n完成：/mnt/us/wallpapers 共 {n} 张；KOReader 睡眠时将显示随机壁纸（无文字覆盖层）。")
