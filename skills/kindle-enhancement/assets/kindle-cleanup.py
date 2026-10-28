#!/usr/bin/env python3
"""在 Kindle 上：把两本新书改成中文名，并删除指定旧书及其侧车文件。

用法： python3 tools/kindle-cleanup.py [--dry-run]

安全设计
--------
* 只操作 /mnt/us/documents 下名字匹配下列前缀的条目，逐条打印动作；
* 白名单保护：KOReader.sh（启动器）、JAILBROKEN*、disable_oobe.sh、
  My Clippings*、dictionaries、以及两本新书本身，永不删除；
* 默认先 dry-run 输出计划，加 --apply 才真正执行。
"""
import os
import posixpath
import stat as statmod
import sys

SK = "/Users/rorouse/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle"
sys.path.insert(0, os.path.join(SK, "scripts"))

from kindle_store import ConfigStore, SystemKeys
from kindle_transport import profile_for, private_for, session

DOCS = "/mnt/us/documents"

RENAMES = {
    "Zhan Lue Yu Lu Jing _Huang Qi F - SoBooKs.cc.epub":
        "战略与路径：黄奇帆的十二堂经济课.epub",
    "Lang Xing Shi Dai _Di San Di Gu - SoBooKs.cc.epub":
        "狼性时代：第三帝国余波中的普通德国人.epub",
}

OLD_TITLE_PREFIXES = [
    "一如既往",
    "与自己和解",
    "掌控工作",
    "金钱的背后是人",
    "qiaomu-send-test",
]

KEEP_EXACT = {
    "KOReader.sh", "KOReader.sh.sdr",
    "JAILBROKEN.txt", "JAILBROKEN.sdr", "JAILBROKEN.mbp1", "JAILBROKEN.mbs",
    "disable_oobe.sh",
    "My Clippings.txt", "My Clippings.sdr",
    "dictionaries",
}
KEEP_PREFIXES = ["战略与路径", "狼性时代"]


def is_mac_junk(name):
    return name.startswith("._") or name == ".DS_Store"


def matches_old(name):
    return any(name.startswith(p) for p in OLD_TITLE_PREFIXES)


def main():
    apply = "--apply" in sys.argv[1:]
    store = ConfigStore()
    keys = SystemKeys()
    did, device, mode, profile = profile_for(store)
    actions = []

    with session(profile, private_for(keys, device)) as (transport, sftp, actual):
        names = sftp.listdir(DOCS)

        # 1) 改名（连同已存在的同名 .sdr 一起改）
        for old, new in RENAMES.items():
            if old in names:
                actions.append("RENAME  %s  ->  %s" % (old, new))
                if apply:
                    sftp.rename(posixpath.join(DOCS, old), posixpath.join(DOCS, new))
            sdr_old = old + ".sdr"
            if sdr_old in names:
                actions.append("RENAME  %s  ->  %s.sdr" % (sdr_old, new))
                if apply:
                    sftp.rename(posixpath.join(DOCS, sdr_old), posixpath.join(DOCS, new + ".sdr"))

        names = sftp.listdir(DOCS)

        # 2) 删除旧书及其侧车 / macOS 残留
        for name in sorted(names):
            if name in KEEP_EXACT or any(name.startswith(p) for p in KEEP_PREFIXES):
                continue
            if not (is_mac_junk(name) or matches_old(name)):
                continue
            target = posixpath.join(DOCS, name)
            try:
                attrs = sftp.stat(target)
                if statmod.S_ISDIR(attrs.st_mode):
                    actions.append("RM DIR  %s/" % name)
                    if apply:
                        for child in sftp.listdir(target):
                            sftp.remove(posixpath.join(target, child))
                        sftp.rmdir(target)
                else:
                    actions.append("RM      %s" % name)
                    if apply:
                        sftp.remove(target)
            except OSError as exc:
                actions.append("SKIP    %s (%s)" % (name, exc))

        final = sorted(sftp.listdir(DOCS))

    header = "已执行" if apply else "DRY-RUN（未做任何修改，加 --apply 才执行）"
    print("设备: %s  模式: %s  身份校验: %s...  [%s]" % (did, mode, actual[:16], header))
    print("--- 动作清单 ---")
    for a in actions:
        print("  " + a)
    print("--- 结果目录 ---")
    for n in final:
        print("  " + n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())