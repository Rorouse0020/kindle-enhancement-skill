#!/usr/bin/env python3
"""书源质量门禁：按 Kindle Enhancement 的四条硬指标检查一个 EPUB。

用法：
  python3 scripts/quality_check.py BOOK.epub \
      [--expect-title T] [--expect-author A] [--strict] [--douban]

输出 JSON：
  verdict: pass | warn | block
  checks: 四条硬指标（1 元数据/豆瓣、2 结构、3 体积、4 正文安全）各自的 status + 细节
  douban: 供人工核对指标 1 的检索链接

判定规则：
  * EPUB 结构非法、含 script/iframe/javascript:  -> fail（block）
  * 文件大小异常、疑似试读/残缺                      -> warn
  * 缺 ISBN/出版社/日期                              -> warn
  * 正文外部链接过多                                  -> warn
  任一 fail -> verdict=block；否则有 warn -> warn；否则 pass。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET

DC = "{http://purl.org/dc/elements/1.1/}"
OPF = "{http://www.idpf.org/2007/opf}"
CONTAINER = "{urn:oasis:names:tc:opendocument:xmlns:container}"

SUSPICIOUS_TITLE_WORDS = ("sample", "excerpt", "preview", "试读", "样章", "预览", "节选")
SCRIPT_PATTERNS = [
    (re.compile(r"<\s*script\b", re.I), "script"),
    (re.compile(r"<\s*iframe\b", re.I), "iframe"),
    (re.compile(r"<\s*object\b", re.I), "object"),
    (re.compile(r"<\s*embed\b", re.I), "embed"),
    (re.compile(r"javascript\s*:", re.I), "javascript:"),
    (re.compile(r"\son[a-z]+\s*=", re.I), "on*事件"),
]


def fail(msg):
    return {"status": "fail", "detail": msg}


def warn(msg):
    return {"status": "warn", "detail": msg}


def ok(msg):
    return {"status": "pass", "detail": msg}


def isbn_digits(value: str):
    digits = re.sub(r"[^0-9Xx]", "", value or "")
    if len(digits) == 13 and digits.isdigit():
        return digits
    if len(digits) == 10:
        return digits.upper()
    return None


def check_structure(zf: zipfile.ZipFile):
    names = zf.namelist()
    if not names:
        return fail("EPUB 为空"), {}
    if names[0] != "mimetype":
        return fail("mimetype 不是第一个条目"), {}
    if zf.read("mimetype").strip() != b"application/epub+zip":
        return fail("mimetype 内容不是 application/epub+zip"), {}
    if "META-INF/container.xml" not in names:
        return fail("缺少 META-INF/container.xml"), {}
    try:
        root = ET.fromstring(zf.read("META-INF/container.xml"))
    except ET.ParseError:
        return fail("container.xml 无法解析"), {}
    opf_path = None
    for node in root.iter():
        if node.tag.endswith("rootfile"):
            opf_path = node.attrib.get("full-path")
            break
    if not opf_path or opf_path not in names:
        return fail("container.xml 未指向有效 OPF"), {}
    try:
        pkg = ET.fromstring(zf.read(opf_path))
    except ET.ParseError:
        return fail("OPF 无法解析"), {}
    manifest = {}
    for item in pkg.iter(OPF + "item"):
        manifest[item.attrib.get("id")] = item
    spine = [ref.attrib.get("idref") for ref in pkg.iter(OPF + "itemref")]
    if not spine:
        return fail("spine 为空（没有可读章节）"), {}
    missing = [sid for sid in spine if sid not in manifest]
    if missing:
        return fail("spine 引用了不存在的 manifest 项: %s" % missing[:3]), {}
    docs = [manifest[sid] for sid in spine if sid in manifest]
    xhtml = [d for d in docs if (d.attrib.get("media-type") or "").lower()
             in ("application/xhtml+xml", "text/html")]
    if not xhtml:
        return fail("spine 中没有 XHTML 正文"), {}
    if zf.testzip() is not None:
        return fail("压缩包内有损坏条目"), {}
    return ok("结构合法：%d 个正文文档 / %d 个 manifest 项" % (len(xhtml), len(manifest))), {
        "opf": opf_path, "pkg": pkg, "manifest": manifest, "spine": spine}


def check_metadata(pkg, expect_title=None, expect_author=None):
    def first(tag):
        return next((("".join(n.itertext()) or "").strip() for n in pkg.iter(DC + tag)), "")

    md = {
        "title": first("title"),
        "creator": first("creator"),
        "publisher": first("publisher"),
        "date": first("date"),
        "language": first("language"),
        "identifiers": [(n.text or "").strip() for n in pkg.iter(DC + "identifier")],
    }
    isbn = next((d for d in (isbn_digits(i) for i in md["identifiers"]) if d), None)
    problems = []
    if not md["title"]:
        problems.append("缺书名")
    if not md["creator"]:
        problems.append("缺作者")
    if not isbn:
        problems.append("缺 ISBN（dc:identifier 中无可识别 ISBN-10/13）")
    if not md["publisher"]:
        problems.append("缺出版社")
    if not md["date"]:
        problems.append("缺出版日期/版次信息")
    if expect_title and expect_title not in md["title"]:
        problems.append("书名与期望不符（期望含 %r，实际 %r）" % (expect_title, md["title"]))
    if expect_author and expect_author not in md["creator"]:
        problems.append("作者与期望不符（期望含 %r，实际 %r）" % (expect_author, md["creator"]))
    md["isbn"] = isbn
    if problems:
        return warn("元数据待人工核对：" + "；".join(problems)), md
    return ok("元数据齐全：%s / %s / %s (%s) / ISBN %s"
              % (md["title"], md["creator"], md["publisher"], md["date"], isbn)), md


def check_size(zf, xhtml_items, total_bytes, title_digits):
    images = [n for n in zf.namelist()
              if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"))]
    text_bytes = 0
    for item in xhtml_items:
        try:
            text_bytes += len(zf.read(item))
        except Exception:
            pass
    suspicious = []
    if total_bytes < 50 * 1024:
        suspicious.append("文件 < 50 KB")
    elif total_bytes < 150 * 1024 and not images:
        suspicious.append("无图片且文件 < 150 KB")
    if title_digits.lower().find("sample") >= 0 or any(w in title_digits for w in SUSPICIOUS_TITLE_WORDS):
        suspicious.append("标题疑似试读/样章")
    detail = "%.0f KB（XHTML 未压缩 %.0f KB，图片 %d 张，章节 %d）" % (
        total_bytes / 1024.0, text_bytes / 1024.0, len(images), len(xhtml_items))
    if suspicious:
        return warn(detail + "；" + "、".join(suspicious) + "，需人工确认是否残缺/试读"), {}
    return ok(detail), {}


def check_content(zf, xhtml_items):
    scanned = 0
    counts = {
        "script": 0, "iframe": 0, "object": 0, "embed": 0,
        "javascript:": 0, "on*事件": 0, "外部链接": 0,
    }
    samples = []
    budget = 8 * 1024 * 1024
    for name in xhtml_items:
        try:
            data = zf.read(name)
        except Exception:
            continue
        if scanned > budget:
            break
        scanned += len(data)
        text = data.decode("utf-8", "replace")
        for pattern, key in SCRIPT_PATTERNS:
            hits = len(pattern.findall(text))
            if hits:
                counts[key] += hits
                if len(samples) < 5:
                    samples.append("%s: %s x%d" % (name, key, hits))
        for m in re.finditer(r'(?:href|src)\s*=\s*["\'](https?://[^"\']+)', text, re.I):
            counts["外部链接"] += 1
            if len(samples) < 5:
                samples.append("%s: 外链 %s" % (name, m.group(1)[:80]))
    risky = {k: v for k, v in counts.items()
             if v and k in ("script", "iframe", "object", "embed", "javascript:", "on*事件")}
    if risky:
        return fail("正文含可执行内容：%s" % risky), counts
    if counts["外部链接"]:
        return warn("正文含 %d 个外部链接/跳转，需人工确认是否合理" % counts["外部链接"]), counts
    return ok("正文无脚本、无 iframe、无 javascript:、无外链跳转"), counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--expect-title", default=None)
    ap.add_argument("--expect-author", default=None)
    ap.add_argument("--strict", action="store_true", help="warn 也视为不通过")
    ap.add_argument("--douban", action="store_true", help="联网到豆瓣自动核对指标 1（书名/作者/出版社/年份/ISBN）")
    args = ap.parse_args()

    path = os.path.abspath(os.path.expanduser(args.path))
    result = {"ok": True, "path": path, "verdict": None, "checks": {}}
    if not os.path.isfile(path):
        result.update(ok=False, verdict="block")
        result["checks"]["file"] = fail("文件不存在")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    size = os.path.getsize(path)
    result["bytes"] = size
    try:
        with zipfile.ZipFile(path) as zf:
            structure, ctx = check_structure(zf)
            result["checks"]["1_meta"] = None  # 占位，稍后填
            if structure["status"] == "fail":
                result["checks"]["2_structure"] = structure
                result["checks"]["4_content"] = {"status": "skip", "detail": "结构非法，跳过内容扫描"}
                result["checks"]["3_size"] = {"status": "skip", "detail": "结构非法，跳过"}
                result["checks"]["1_meta"] = warn("结构非法，无法读取元数据")
            else:
                pkg = ctx["pkg"]
                manifest = ctx["manifest"]
                xhtml_items = [manifest[sid].attrib.get("href") for sid in ctx["spine"]
                               if sid in manifest and manifest[sid].attrib.get("href")]
                opf_dir = os.path.dirname(ctx["opf"])
                xhtml_items = [os.path.normpath(os.path.join(opf_dir, h)).replace("\\", "/")
                               for h in xhtml_items]
                result["checks"]["2_structure"] = structure
                meta, md = check_metadata(pkg, args.expect_title, args.expect_author)
                result["checks"]["1_meta"] = meta
                result["metadata"] = md
                size_res, _size_info = check_size(zf, xhtml_items, size, md.get("title", ""))
                result["checks"]["3_size"] = size_res
                content, counts = check_content(zf, xhtml_items)
                result["checks"]["4_content"] = content
                result["content_counts"] = counts
    except zipfile.BadZipFile:
        result["checks"]["2_structure"] = fail("不是合法的 ZIP/EPUB 容器")
        result["checks"]["1_meta"] = warn("无法读取")
        result["checks"]["3_size"] = {"status": "skip", "detail": "结构非法"}
        result["checks"]["4_content"] = {"status": "skip", "detail": "结构非法"}
    except Exception as exc:  # noqa: BLE001 - 只报告，不吞掉原因
        result.update(ok=False, verdict="block")
        result["checks"]["2_structure"] = fail("检查过程异常: %s" % exc)

    # 指标 1 的自动化部分：豆瓣核对（可选）
    if args.douban:
        try:
            import douban_verify
            dv = douban_verify.verify(path=path)
            mapping = {"pass": "pass", "warn": "warn", "block": "fail"}
            status = mapping.get(dv.get("verdict"), "warn")
            detail = dv.get("note") or ""
            if dv.get("douban"):
                d = dv["douban"]
                detail = "豆瓣《%s》%s / %s / ISBN %s / %s 页（%s）" % (
                    d.get("title"), "/".join(d.get("authors") or []), d.get("publisher"),
                    d.get("isbn") or "未知", d.get("pages") or "?", d.get("url"))
                if dv.get("compare"):
                    bad = ["%s:%s" % (k, v["status"]) for k, v in dv["compare"].items() if v["status"] != "pass"]
                    if bad:
                        detail += "；不一致项 " + ", ".join(bad)
            elif dv.get("error"):
                detail = dv["error"]
            result["checks"]["1_douban"] = {"status": status, "detail": detail}
            result["douban"] = dv.get("douban_url") or result.get("douban")
        except Exception as exc:  # 网络/风控等不阻断流程
            result["checks"]["1_douban"] = {"status": "warn", "detail": "豆瓣核对不可用: %s" % exc}

    statuses = [c.get("status") for c in result["checks"].values() if isinstance(c, dict)]
    if "fail" in statuses:
        verdict = "block"
    elif "warn" in statuses:
        verdict = "warn"
    else:
        verdict = "pass"
    if args.strict and verdict == "warn":
        verdict = "block"
    result["verdict"] = verdict

    title = (result.get("metadata") or {}).get("title") or os.path.splitext(os.path.basename(path))[0]
    isbn = (result.get("metadata") or {}).get("isbn")
    query = isbn or title
    result["douban"] = "https://search.douban.com/book/subject_search?search_text=" + urllib.parse.quote(query)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if verdict in ("pass", "warn") else 1


if __name__ == "__main__":
    raise SystemExit(main())