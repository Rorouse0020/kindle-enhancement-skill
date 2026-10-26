#!/usr/bin/env python3
"""通过已配对的 SSH 身份在 Kindle 上执行一条命令（复用 qiaomu-send2kindle 的凭据与主机身份校验）。

用法: kindle-ssh.py '<远程命令>'
"""
import sys, os

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

cmd = " ".join(sys.argv[1:])
if not cmd:
    raise SystemExit("usage: kindle-ssh.py '<command>'")

store = ConfigStore()
keys = SystemKeys()
did, device, mode, profile = profile_for(store)

with session(profile, private_for(keys, device)) as (transport, sftp, actual):
    ch = transport.open_session(timeout=10)
    ch.settimeout(30)
    ch.exec_command(cmd)
    out = bytearray()
    while True:
        data = ch.recv(8192)
        if not data:
            break
        out.extend(data)
        if len(out) > 2_000_000:
            break
    rc = ch.recv_exit_status()
    sys.stdout.write(out.decode("utf-8", "replace"))
    sys.stdout.write(f"\n[exit {rc}]\n")