#!/usr/bin/env python3
"""把 ISBN 回填进 EPUB 元数据（默认从豆瓣自动查询），其余内容保持不变。

做法：只在 OPF 的 <metadata> 里插入/替换一条
      <dc:identifier id="isbn">urn:isbn:978XXXXXXXXXX</dc:identifier>
（保留原有 unique-identifier，不改书名/作者/正文/图片；zip 重打包时 mimetype 仍置首且不压缩）

用法：
  python3 scripts/backfill_isbn.py BOOK.epub                 # 豆瓣查询 ISBN 后回填
  python3 scripts/backfill_isbn.py BOOK.epub --isbn 9787...  # 指定 ISBN
  python3 scripts/backfill_isbn.py BOOK.epub --dry-run       # 只看会写什么
  python3 scripts/backfill_isbn.py BOOK.epub --no-backup     # 不保留 .orig
  python3 scripts/backfill_isbn.py BOOK.epub --douban --fill-metadata  # 回填 ISBN+出版社+日期
  python3 scripts/backfill_isbn.py BOOK.epub --fix-language zh  # 顺带规范语言标签（可选）

输出 JSON：ok / isbn / source / changed / sha256_before / sha256_after / metadata
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

DC = "{http://purl.org/dc/elements/1.1/}"
OPF = "{http://www.idpf.org/2007/opf}"


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locate_opf(zf):
    container = ET.fromstring(zf.read("META-INF/container.xml"))
    for node in container.iter():
        if node.tag.endswith("rootfile"):
            path = node.attrib.get("full-path")
            if path:
                return path
    raise RuntimeError("container.xml 未指向 OPF")


def current_metadata(opf_bytes):
    pkg = ET.fromstring(opf_bytes)

    def values(tag):
        return [("".join(n.itertext()) or "").strip()
                for n in pkg.iter(DC + tag) if ("".join(n.itertext()) or "").strip()]

    isbn = None
    for ident in values("identifier"):
        digits = re.sub(r"[^0-9Xx]", "", ident)
        if len(digits) == 13 and digits.isdigit():
            isbn = digits
            break
        if len(digits) == 10:
            isbn = digits.upper()
            break
    return {
        "title": (values("title") or [""])[0],
        "creators": values("creator"),
        "publisher": (values("publisher") or [""])[0],
        "date": (values("date") or [""])[0],
        "language": values("language"),
        "isbn": isbn,
        "identifiers": values("identifier"),
    }


def inject_identifier(opf_text, isbn):
    """文本级插入，最大限度保留原 OPF 格式（DOCTYPE/注释/属性顺序）。"""
    urn = "urn:isbn:%s" % isbn
    ident_re = re.compile(r"<dc:identifier\b[^>]*>.*?</dc:identifier>", re.I | re.S)
    for match in ident_re.finditer(opf_text):
        digits = re.sub(r"[^0-9Xx]", "", match.group(0))
        if len(digits) in (10, 13):
            new_tag = '<dc:identifier id="isbn">%s</dc:identifier>' % urn
            opf_text = opf_text[:match.start()] + new_tag + opf_text[match.end():]
            changed = "replaced"
            break
    else:
        lower = opf_text.lower()
        idx = lower.rfind("</metadata>")
        if idx == -1:
            raise RuntimeError("OPF 中没有 </metadata>，无法插入")
        existing_ids = set(re.findall(r'id="([^"]+)"', opf_text))
        new_id = "isbn"
        n = 2
        while new_id in existing_ids:
            new_id = "isbn-%d" % n
            n += 1
        tag = '  <dc:identifier id="%s">%s</dc:identifier>\n' % (new_id, urn)
        opf_text = opf_text[:idx] + tag + opf_text[idx:]
        changed = "added"

    return opf_text, changed


def inject_language(opf_text, language):
    """把 dc:language 规范为指定值；没有则补一条。"""
    lang_re = re.compile(r"(<dc:language\b[^>]*>).*?(</dc:language>)", re.I | re.S)
    if lang_re.search(opf_text):
        return lang_re.sub(lambda m: m.group(1) + language + m.group(2), opf_text), "language-replaced"
    idx = opf_text.lower().rfind("</metadata>")
    if idx == -1:
        raise RuntimeError("OPF 中没有 </metadata>，无法插入语言标签")
    return opf_text[:idx] + "  <dc:language>%s</dc:language>\n" % language + opf_text[idx:], "language-added"


def rebuild_epub(src, dst, opf_path, opf_bytes):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        if "mimetype" not in zin.namelist():
            raise RuntimeError("EPUB 缺少 mimetype")
        mime_info = zipfile.ZipInfo("mimetype")
        mime_info.compress_type = zipfile.ZIP_STORED
        zout.writestr(mime_info, zin.read("mimetype"))
        for info in zin.infolist():
            if info.filename == "mimetype":
                continue
            data = opf_bytes if info.filename == opf_path else zin.read(info.filename)
            new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            new_info.compress_type = zipfile.ZIP_DEFLATED
            new_info.external_attr = info.external_attr
            zout.writestr(new_info, data)


def validate(path, expect_isbn):
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if names[0] != "mimetype":
            raise RuntimeError("mimetype 不是首个条目")
        if zf.read("mimetype").strip() != b"application/epub+zip":
            raise RuntimeError("mimetype 内容错误")
        if zf.testzip() is not None:
            raise RuntimeError("zip 有损坏条目")
        opf_path = locate_opf(zf)
        meta = current_metadata(zf.read(opf_path))
        pkg = ET.fromstring(zf.read(opf_path))
        spine = [ref.attrib.get("idref") for ref in pkg.iter(OPF + "itemref")]
        if not spine:
            raise RuntimeError("spine 为空")
    if expect_isbn and meta["isbn"] != expect_isbn:
        raise RuntimeError("回填后未读到 ISBN：%r" % meta["isbn"])
    return meta


def inject_field(opf_text, tag, value):
    """替换/插入 dc:publisher、dc:date 等简单字段。"""
    if not value:
        return opf_text, "none"
    pattern = re.compile(r"(<dc:%s\b[^>]*>).*?(</dc:%s>)" % (tag, tag), re.I | re.S)
    if pattern.search(opf_text):
        return pattern.sub(lambda m: m.group(1) + value + m.group(2), opf_text), "%s-replaced" % tag
    idx = opf_text.lower().rfind("</metadata>")
    if idx == -1:
        raise RuntimeError("OPF 中没有 </metadata>，无法插入")
    return opf_text[:idx] + "  <dc:%s>%s</dc:%s>\n" % (tag, value, tag) + opf_text[idx:], "%s-added" % tag


def douban_lookup(path):
    import douban_verify
    result = douban_verify.verify(path=path)
    if not result.get("ok") or not result.get("douban"):
        raise RuntimeError("豆瓣查询失败：%s" % (result.get("error") or result.get("note") or "无结果"))
    detail = result["douban"]
    return detail, detail.get("url") or result.get("douban_url")


def backfill(path, isbn=None, use_douban=False, language=None,
             dry_run=False, backup=True, fill_metadata=False):
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        raise RuntimeError("文件不存在: %s" % path)
    before = sha256_of(path)

    with zipfile.ZipFile(path) as zf:
        opf_path = locate_opf(zf)
        opf_bytes = zf.read(opf_path)
    meta_before = current_metadata(opf_bytes)

    import douban_verify as _dv

    source = "argument"
    douban_url = None
    douban_detail = None
    if use_douban:
        douban_detail, douban_url = douban_lookup(path)
        source = "douban"
    if not isbn:
        candidate = (douban_detail or {}).get("isbn")
        if candidate and not _dv.is_placeholder_isbn(candidate):
            isbn = candidate
        elif not fill_metadata:
            raise RuntimeError("需要 --isbn 或 --douban（且豆瓣条目需有有效 ISBN；占位 ISBN 不回填）")
    isbn = re.sub(r"[^0-9Xx]", "", isbn or "") or None
    if isbn and len(isbn) not in (10, 13):
        raise RuntimeError("ISBN 格式不合法: %r" % isbn)

    needs_isbn = bool(isbn) and meta_before.get("isbn") != isbn
    needs_lang = bool(language) and (language not in (meta_before.get("language") or []))
    pub = (douban_detail or {}).get("publisher") if fill_metadata else None
    date = (douban_detail or {}).get("pubdate") if fill_metadata else None
    needs_pub = bool(pub) and meta_before.get("publisher") != pub
    needs_date = bool(date) and not (meta_before.get("date") or "").startswith(date)

    if not any((needs_isbn, needs_lang, needs_pub, needs_date)):
        return {"ok": True, "path": path, "isbn": isbn, "source": source,
                "changed": False, "reason": "元数据已一致",
                "douban_url": douban_url, "sha256": before, "metadata": meta_before}

    opf_text = opf_bytes.decode("utf-8", "replace")
    steps = []
    new_opf_text = opf_text
    if needs_isbn:
        new_opf_text, h = inject_identifier(new_opf_text, isbn); steps.append(h)
    if needs_lang:
        new_opf_text, h = inject_language(new_opf_text, language); steps.append(h)
    if needs_pub:
        new_opf_text, h = inject_field(new_opf_text, "publisher", pub); steps.append(h)
    if needs_date:
        new_opf_text, h = inject_field(new_opf_text, "date", date); steps.append(h)
    how = "+".join(steps) or "none"
    new_opf_bytes = new_opf_text.encode("utf-8")

    result = {"ok": True, "path": path, "isbn": isbn, "source": source,
              "douban_url": douban_url, "changed": True, "how": how,
              "language": language,
              "filled": {"publisher": pub if needs_pub else None,
                         "date": date if needs_date else None},
              "sha256_before": before}
    if dry_run:
        result.update(dry_run=True, sha256_after=None,
                      metadata_after=current_metadata(new_opf_bytes))
        return result

    fd, tmp = tempfile.mkstemp(prefix=".isbn-", suffix=".epub", dir=os.path.dirname(path))
    os.close(fd)
    try:
        rebuild_epub(path, tmp, opf_path, new_opf_bytes)
        meta_after = validate(tmp, isbn)
        if backup:
            backup_path = path + ".orig"
            if not os.path.exists(backup_path):
                shutil.copy2(path, backup_path)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    after = sha256_of(path)
    result.update(sha256_after=after, backup=(path + ".orig") if backup else None,
                  metadata_after=meta_after)
    if language:
        result["language_set"] = language
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--isbn")
    ap.add_argument("--douban", action="store_true", help="从豆瓣自动查询 ISBN")
    ap.add_argument("--fill-metadata", action="store_true",
                    help="同时用豆瓣数据回填出版社与出版日期（ISBN 为占位值时跳过 ISBN）")

    ap.add_argument("--language", "--fix-language", dest="language",
                    help="顺带把 dc:language 设为该值（如 zh-CN）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()
    try:
        out = backfill(args.path, args.isbn, args.douban, args.language,
                       args.dry_run, not args.no_backup, args.fill_metadata)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())