#!/usr/bin/env python3
"""把整理过的「乔木精选」源目录应用到已挂载的 Kindle（SimpleUI 资讯）。

做法：
1) 备份设备上的 data/qiaomu_sources.json 和 settings/simpleui/news/index.json（若存在）
2) 写入 curated 目录（关闭与 AI/投资无关的 20 个源，其余保持启用）
3) 若 index.json 已存在（用户之前打开过资讯），同步替换其中的 sources 列表
   —— 插件运行时以 state.sources 为准，不改它就会继续用旧目录
4) 打印前后对比

用法：python3 tools/apply-rss-curation.py [/Volumes/Kindle]
回滚：把生成的 *.bak-rss-<时间戳> 文件改名回去即可。
"""
import json
import shutil
import sys
import time
from pathlib import Path

VOL = Path(sys.argv[1] if len(sys.argv) > 1 else "/Volumes/Kindle")
# 模板随包分发（也可用第二个参数指定）
CURATED = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "assets" / "qiaomu_sources.curated.json"

DATA = VOL / "koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json"
STATE = VOL / "koreader/settings/simpleui/news/index.json"

if not (VOL / "system/version.txt").is_file():
    raise SystemExit(f"不是 Kindle 卷：{VOL}")
version = (VOL / "system/version.txt").read_text(errors="replace").strip()
print(f"设备固件: {version}")
if not CURATED.is_file():
    raise SystemExit(f"缺少整理后的目录文件：{CURATED}")

curated = json.loads(CURATED.read_text(encoding="utf-8"))
enabled = [s for s in curated["sources"] if s.get("enabled") is not False]
disabled = [s for s in curated["sources"] if s.get("enabled") is False]

stamp = time.strftime("%Y%m%d-%H%M%S")

if DATA.is_file():
    backup = DATA.with_name(DATA.name + f".bak-rss-{stamp}")
    shutil.copy2(DATA, backup)
    DATA.write_text(json.dumps(curated, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已更新源目录: {DATA}")
    print(f"  备份: {backup.name}")
else:
    print(f"警告：设备上找不到 {DATA}（SimpleUI 未安装？）")

if STATE.is_file():
    backup = STATE.with_name(STATE.name + f".bak-rss-{stamp}")
    shutil.copy2(STATE, backup)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    before = len(state.get("sources") or [])
    state["sources"] = [
        {"id": s["id"], "name": s["name"], "category": s.get("category", ""),
         "siteUrl": s.get("siteUrl", ""), **({"enabled": False} if s.get("enabled") is False else {})}
        for s in curated["sources"]
    ]
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    print(f"已同步资讯状态里的源列表: {STATE}（原有 {before} 个 → 现在 {len(state['sources'])} 个）")
    print(f"  备份: {backup.name}")
else:
    print("资讯状态文件尚不存在（首次打开资讯时会自动按新目录初始化）")

print()
print(f"结果：启用 {len(enabled)} 个源 / 关闭 {len(disabled)} 个源")
print("已关闭:", "、".join(s["name"] for s in disabled))
