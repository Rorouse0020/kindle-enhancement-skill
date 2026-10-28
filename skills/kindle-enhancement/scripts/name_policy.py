#!/usr/bin/env python3
"""传书命名策略：用豆瓣书名作为设备上的文件名。

规则（用户设定）：
  * 豆瓣条目有中文书名  -> 用中文书名
  * 豆瓣条目是英文书名  -> 用英文书名
  * 豆瓣查不到 / 网络不可用 -> 回退：EPUB 元数据书名 -> 源文件名

实现要点：
  * 书名来自豆瓣详情页（douban_verify.verify 的多查询回退逻辑，带缓存与限速）。
  * 文件名做 FAT32/Kindle 合法化：去掉 \\ / : * ? " < > | 与控制字符、压缩空白、
    去首尾点号、限制长度；保留原扩展名（.epub / .azw3 等）。
  * 不改变文件内容；重名由上传层自动加 (2)/(3) 后缀。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
ILLEGAL_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')


def sanitize(title: str, ext: str, max_len: int = 100) -> str:
    name = re.sub(r"<[^>]+>", "", title or "")
    name = name.replace("\u3000", " ")
    name = ILLEGAL_RE.sub("·", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(". ")
    if not name:
        name = "untitled"
    if len(name) > max_len:
        name = name[:max_len].rstrip(". ")
    if not ext.startswith("."):
        ext = "." + ext if ext else ""
    return name + ext


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def _import_douban_verify():
    try:
        import douban_verify  # 与本文件同目录（kindle-enhancement/scripts）
        return douban_verify
    except Exception:
        return None


def resolve(epub_path, fallback_name: str, use_douban: bool = True) -> dict:
    """返回 {name, title, title_source, douban_url, script, fallback}。

    epub_path: 待上传文件（转换后通常为 EPUB）；非 EPUB 时只做元数据/文件名回退。
    fallback_name: 原文件名（含扩展名），用于取扩展名与最终回退。
    """
    ext = Path(fallback_name).suffix
    local_title = ""
    local_creators = []
    dv = _import_douban_verify()
    if dv is not None and epub_path and str(epub_path).lower().endswith(".epub"):
        try:
            meta = dv.epub_metadata(str(epub_path))
            local_title = meta.get("title") or ""
            local_creators = meta.get("creators") or []
        except Exception:
            pass

    douban = None
    if use_douban and dv is not None:
        try:
            if epub_path and str(epub_path).lower().endswith(".epub"):
                result = dv.verify(path=str(epub_path))
            else:
                result = dv.verify(title=local_title or Path(fallback_name).stem,
                                   author=(local_creators or [""])[0])
            if result.get("ok") and result.get("douban"):
                douban = result["douban"]
        except Exception:
            douban = None

    if douban and douban.get("title"):
        title = douban["title"]
        source = "douban"
    elif local_title:
        title = local_title
        source = "metadata"
    else:
        title = Path(fallback_name).stem
        source = "source"

    return {
        "name": sanitize(title, ext),
        "title": title,
        "title_source": source,
        "script": "zh" if has_cjk(title) else "latin",
        "douban_url": (douban or {}).get("url"),
        "douban_isbn": (douban or {}).get("isbn"),
        "fallback_name": fallback_name,
    }


if __name__ == "__main__":
    # 便于手工验证：name_policy.py 书.epub [--no-douban]
    import json
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: name_policy.py BOOK.epub [--no-douban]")
        raise SystemExit(2)
    out = resolve(args[0], Path(args[0]).name, use_douban="--no-douban" not in sys.argv)
    print(json.dumps(out, ensure_ascii=False, indent=2))
