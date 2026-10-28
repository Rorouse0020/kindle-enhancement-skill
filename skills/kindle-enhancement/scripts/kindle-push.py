#!/usr/bin/env python3
"""把本地文件或目录推送到 Kindle（SFTP），复用 qiaomu-send2kindle 的凭据与主机身份校验。

用法:
    kindle-push.py <本地路径> <Kindle 绝对路径>
例:
    kindle-push.py ./unpacked/weread.koplugin /mnt/us/koreader/plugins/weread.koplugin
"""
import sys, os, stat as statmod
from pathlib import Path

import os
from pathlib import Path

_CANDIDATES = [
    os.environ.get("QIAOMU_SKILL_DIR"),
    str(Path.home() / ".claude/skills/qiaomu-send2kindle"),
    str(Path.home() / "skills/qiaomu-send2kindle"),
    str(Path.home() / "DeepSeek Harness/Kindle/skills/qiaomu-send2kindle"),
    str(Path(__file__).resolve().parent.parent.parent / "skills/qiaomu-send2kindle"),
]
SK = next((c for c in _CANDIDATES if c and (Path(c) / "scripts/kindle_transport.py").is_file()), None)
if not SK:
    raise SystemExit("找不到 qiaomu-send2kindle 技能目录；请设置 QIAOMU_SKILL_DIR（例：export QIAOMU_SKILL_DIR=~/skills/qiaomu-send2kindle）")
sys.path.insert(0, os.path.join(SK, "scripts"))

from kindle_store import ConfigStore, SystemKeys
from kindle_transport import profile_for, private_for, session

if len(sys.argv) != 3:
    raise SystemExit(__doc__)
local = Path(sys.argv[1]).expanduser().resolve()
remote = sys.argv[2]
if not local.exists():
    raise SystemExit(f"local path not found: {local}")
if not remote.startswith("/mnt/us/"):
    raise SystemExit("refuse to write outside /mnt/us")

files = []
if local.is_file():
    files.append((local, remote))
else:
    for p in sorted(local.rglob("*")):
        if p.is_file():
            files.append((p, remote.rstrip("/") + "/" + p.relative_to(local).as_posix()))

store, keys = ConfigStore(), SystemKeys()
did, device, mode, profile = profile_for(store)

def ensure_dir(sftp, path):
    parts = []
    cur = ""
    for seg in path.strip("/").split("/"):
        cur += "/" + seg
        parts.append(cur)
    for d in parts:
        try:
            if not statmod.S_ISDIR(sftp.stat(d).st_mode):
                raise SystemExit(f"not a directory on device: {d}")
        except IOError:
            sftp.mkdir(d)

uploaded = 0
with session(profile, private_for(keys, device)) as (transport, sftp, actual):
    for lp, rp in files:
        ensure_dir(sftp, os.path.dirname(rp))
        sftp.put(str(lp), rp)
        uploaded += 1
    print(f"uploaded {uploaded} file(s) -> {remote}")
    print(f"host fingerprint: {actual}")
