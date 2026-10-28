#!/usr/bin/env python3
"""豆瓣自动核对：把 EPUB 元数据与豆瓣书目比对（指标 1 的自动化部分）。

数据来源（公开页面，非官方 API）：
  * 搜索建议  https://book.douban.com/j/subject_suggest?q=<关键词/ISBN>   -> JSON
  * 详情页    https://book.douban.com/subject/<id>/                      -> HTML

限制与礼貌：
  * 每次请求间隔 1.5 秒，带浏览器 UA，15 秒超时；结果缓存 7 天（状态目录）。
  * 豆瓣可能返回登录墙/风控（403/302）——这时报告 douban-unavailable，
    由调用方降级为 warn（人工核对），**绝不**因此判定书有问题。
  * 只读取公开页面字段，不登录、不写豆瓣。

用法：
  python3 douban_verify.py BOOK.epub [--json]
  python3 douban_verify.py --isbn 9787208178212
  python3 douban_verify.py --title "战略与路径" [--author 黄奇帆]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
SUGGEST = "https://book.douban.com/j/subject_suggest?q=%s"
SUBJECT = "https://book.douban.com/subject/%s/"
DC = "{http://purl.org/dc/elements/1.1/}"
OPF = "{http://www.idpf.org/2007/opf}"
CACHE_TTL = 7 * 24 * 3600

# 豆瓣部分条目（尤其自出版/电子书）的 ISBN 是占位值，不能用于一致性判断
PLACEHOLDER_ISBN = {"9787001000000", "9787001000001", "9780000000000", "9780000000001"}


def isbn10_valid(isbn):
    s = (isbn or "").upper()
    if len(s) != 10 or not s[:9].isdigit() or not (s[9].isdigit() or s[9] == "X"):
        return False
    total = sum((10 - i) * int(c) for i, c in enumerate(s[:9]))
    total += 10 if s[9] == "X" else int(s[9])
    return total % 11 == 0


def isbn13_valid(isbn):
    s = isbn or ""
    if len(s) != 13 or not s.isdigit():
        return False
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(s[:12]))
    return (10 - total % 10) % 10 == int(s[12])


def isbn_valid(isbn):
    return isbn10_valid(isbn) or isbn13_valid(isbn)


def is_placeholder_isbn(isbn):
    isbn = (isbn or "").strip()
    if not isbn:
        return False
    if isbn in PLACEHOLDER_ISBN:
        return True
    if re.match(r"^9787001\d{6}$", isbn):   # 中文在线/豆瓣电子书占位段
        return True
    if len(set(isbn.rstrip("0"))) <= 1:       # 几乎全 0
        return True
    return False
_LAST_REQUEST = [0.0]


class DoubanUnavailable(RuntimeError):
    pass


def _cache_path():
    base = os.path.expanduser("~/Library/Application Support/Qiaomu/Kindle")
    return os.path.join(base, "douban-cache.json")


def _load_cache():
    try:
        with open(_cache_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_cache(cache):
    try:
        os.makedirs(os.path.dirname(_cache_path()), exist_ok=True)
        with open(_cache_path(), "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False)
    except Exception:
        pass


def _get(url, cache, key, allow_cache=True):
    now = time.time()
    if allow_cache and key in cache:
        item = cache[key]
        if now - item.get("ts", 0) < CACHE_TTL:
            return item.get("body")
    wait = 1.5 - (time.time() - _LAST_REQUEST[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "replace")
    except Exception as exc:  # 风控/网络/超时
        raise DoubanUnavailable(str(exc)) from None
    finally:
        _LAST_REQUEST[0] = time.time()
    if "sec.douban.com" in body[:2000] or "检测到有异常请求" in body:
        raise DoubanUnavailable("anti-bot")
    cache[key] = {"ts": now, "body": body}
    return body


def normalize(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[\s\u3000]+", "", text)
    text = re.sub(r"[（(].*?[)）]", "", text)
    text = re.sub(r"[：:·・,，。.!！?？\-—_/|]", "", text)
    return text.lower()


def split_titles(title):
    parts = re.split(r"[：:]", title or "", maxsplit=1)
    return [p.strip() for p in parts if p.strip()]


def epub_metadata(path):
    with zipfile.ZipFile(path) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        opf_path = next((n.attrib.get("full-path") for n in container.iter()
                         if n.tag.endswith("rootfile")), None)
        pkg = ET.fromstring(zf.read(opf_path))
        def all_values(tag):
            return [("".join(n.itertext()) or "").strip()
                    for n in pkg.iter(DC + tag) if ("".join(n.itertext()) or "").strip()]

        def first(tag):
            values = all_values(tag)
            return values[0] if values else ""

        ids = [(n.text or "").strip() for n in pkg.iter(DC + "identifier")]
    isbn = None
    for ident in ids:
        digits = re.sub(r"[^0-9Xx]", "", ident)
        if len(digits) == 13 and digits.isdigit():
            isbn = digits
            break
        if len(digits) == 10:
            isbn = digits.upper()
            break
    return {
        "title": first("title"),
        "creator": first("creator"),
        "creators": all_values("creator"),
        "publisher": first("publisher"),
        "date": first("date"),
        "isbn": isbn,
        "identifiers": ids,
    }


def suggest(query, cache):
    body = _get(SUGGEST % urllib.parse.quote(query), cache, "suggest:" + query)
    try:
        data = json.loads(body)
    except ValueError:
        raise DoubanUnavailable("suggest-not-json") from None
    return data if isinstance(data, list) else []


def pick_candidate(results, title=None, author=None, isbn=None, local_year=None):
    if not results:
        return None
    if isbn:
        for item in results:
            if isbn in json.dumps(item, ensure_ascii=False):
                return item
    best, best_score = None, -1
    for item in results:
        score = 0
        cand_title = normalize(item.get("title", ""))
        if title:
            local_parts = [normalize(p) for p in split_titles(title)]
            if any(p and (p in cand_title or cand_title in p) for p in local_parts):
                score += 3
        if author:
            local_author = normalize(author)
            cand_author = normalize(item.get("author_name", ""))
            if local_author and cand_author:
                short = re.sub(r"[\[\]【】]", "", local_author)
                if any(tok and tok in cand_author for tok in re.split(r"[,，;；/]", short) if len(tok) >= 2):
                    score += 2
        if item.get("type") == "b":
            score += 1
        if local_year and item.get("year"):
            try:
                cand_year = int(str(item["year"])[:4])
                if cand_year == int(local_year):
                    score += 2
                elif abs(cand_year - int(local_year)) > 2:
                    score -= 1
            except (TypeError, ValueError):
                pass
        if score > best_score:
            best, best_score = item, score
    return best


def subject_detail(subject_id, cache):
    body = _get(SUBJECT % subject_id, cache, "subject:" + subject_id)
    def info(label):
        # 兼容两种结构：<span class="pl">作者</span>: xxx<br/> 与 <span class="pl">作者:</span> xxx<br/>
        pattern = (r'<span class="pl">\s*' + label +
                   r'\s*[:：]?\s*</span>\s*[:：]?\s*(.*?)<br\s*/?>')
        m = re.search(pattern, body, re.S)
        if not m:
            return ""
        value = re.sub(r"<[^>]+>", " ", m.group(1))
        return re.sub(r"\s+", " ", html.unescape(value)).strip()
    title = ""
    m = re.search(r"<title>\s*(.*?)\s*</title>", body, re.S)
    if m:
        title = re.sub(r"\s*\(豆瓣\)\s*$", "", html.unescape(m.group(1))).strip()
    authors = []
    raw_author = info("作者")
    for chunk in re.split(r"/", raw_author):
        name = re.sub(r"\[.*?\]|【.*?】", "", chunk).strip()
        if name and name not in authors:
            authors.append(name)
    return {
        "id": str(subject_id),
        "url": SUBJECT % subject_id,
        "title": title,
        "authors": authors,
        "publisher": info("出版社"),
        "pubdate": info("出版年"),
        "isbn": re.sub(r"[^0-9Xx]", "", info("ISBN")),
        "pages": info("页数"),
    }


def compare(local, remote):
    checks = {}

    def add(name, status, detail):
        checks[name] = {"status": status, "detail": detail}

    # 书名
    local_titles = [normalize(p) for p in split_titles(local.get("title", ""))]
    remote_title = normalize(remote.get("title", ""))
    title_ok = any(p and (p == remote_title or p in remote_title or remote_title in p)
                   for p in local_titles)
    add("title", "pass" if title_ok else "fail",
        "本地=%r 豆瓣=%r" % (local.get("title"), remote.get("title")))

    # 作者（本地可能有多位，含扫描站水印；任一真实作者匹配即通过）
    local_authors = [normalize(a) for a in (local.get("creators") or [local.get("creator", "")]) if a]
    remote_authors = [normalize(a) for a in remote.get("authors") or []]
    author_ok = False
    for la in local_authors:
        if not la:
            continue
        for ra in remote_authors:
            if ra and (ra in la or la in ra):
                author_ok = True
                break
            for tok in re.split(r"[,，;；/]", la):
                if len(tok) >= 2 and tok in ra:
                    author_ok = True
                    break
            if author_ok:
                break
        if author_ok:
            break
    add("author", "pass" if author_ok else "warn",
        "本地=%r 豆瓣=%r" % (local.get("creators") or local.get("creator"), remote.get("authors")))

    # 出版社
    lp, rp = normalize(local.get("publisher", "")), normalize(remote.get("publisher", ""))
    pub_ok = bool(lp and rp and (lp in rp or rp in lp))
    add("publisher", "pass" if pub_ok else "warn",
        "本地=%r 豆瓣=%r" % (local.get("publisher"), remote.get("publisher")))

    # 出版年（允许 ±1 年：版次不同）
    ly = re.search(r"(19|20)\d{2}", local.get("date", "") or "")
    ry = re.search(r"(19|20)\d{2}", remote.get("pubdate", "") or "")
    if ly and ry:
        delta = abs(int(ly.group(0)) - int(ry.group(0)))
        add("year", "pass" if delta == 0 else "warn",
            "本地=%s 豆瓣=%s（差 %d 年，可能是不同版次）" % (ly.group(0), ry.group(0), delta))
    else:
        add("year", "warn", "本地=%r 豆瓣=%r" % (local.get("date"), remote.get("pubdate")))

    # ISBN
    li, ri = (local.get("isbn") or ""), (remote.get("isbn") or "")
    if li and not isbn_valid(li):
        add("isbn", "warn", "本地 ISBN 校验位不合法（%s），忽略比对；豆瓣为 %s" % (li, ri or "无"))
    elif ri and is_placeholder_isbn(ri):
        add("isbn", "warn", "豆瓣 ISBN 为占位值（%s），忽略一致性判断；本地=%s" % (ri, li or "无"))
    elif li and ri:
        add("isbn", "pass" if li == ri else "warn",
            "本地=%s 豆瓣=%s（不一致，可能为不同版次/不同 ISBN）" % (li, ri))
    elif ri and not li:
        add("isbn", "warn", "本地缺 ISBN；豆瓣为 %s（可用 backfill_isbn.py 回填）" % ri)
    else:
        add("isbn", "warn", "本地与豆瓣均无 ISBN")

    if "fail" in [c["status"] for c in checks.values()]:
        verdict = "block"
    elif "warn" in [c["status"] for c in checks.values()]:
        verdict = "warn"
    else:
        verdict = "pass"
    return checks, verdict


def verify(path=None, isbn=None, title=None, author=None):
    cache = _load_cache()
    local = {"title": title or "", "creator": author or "", "publisher": "",
             "date": "", "isbn": isbn}
    if path:
        try:
            local = epub_metadata(path)
        except Exception as exc:
            return {"ok": False, "error": "无法读取 EPUB 元数据: %s" % exc, "verdict": "warn"}

    title = local.get("title") or ""
    main_title = re.split(r"[：:]", title, maxsplit=1)[0].strip()
    no_paren = re.sub(r"[（(][^）)]*[）)]", "", title).strip()
    stripped = re.sub(r"(全集|套装|共\s*\d+\s*册|第[一二三四五六七八九十\d]+[册卷部])", "", no_paren).strip()
    queries = []
    for q in (local.get("isbn"), main_title, no_paren, stripped, title,
              (main_title + " " + (local.get("creator") or "")).strip(),
              (stripped + " " + (local.get("creator") or "")).strip()):
        q = (q or "").strip()
        if q and q not in queries:
            queries.append(q)
    if not queries:
        return {"ok": False, "error": "缺少可用于检索的书名/ISBN", "verdict": "warn"}

    try:
        results = []
        used = None
        for q in queries:
            results = suggest(q, cache)
            if results:
                used = q
                break
        local_year = None
        m_year = re.search(r"(19|20)\d{2}", local.get("date") or "")
        if m_year:
            local_year = m_year.group(0)
        candidate = pick_candidate(results, local.get("title"), local.get("creator"),
                                  local.get("isbn"), local_year) if results else None
        if not candidate:
            _save_cache(cache)
            return {"ok": True, "query": queries[0], "tried": queries, "local": local,
                    "douban": None, "verdict": "warn",
                    "note": "豆瓣未搜到候选条目（已尝试 ISBN/主标题/完整标题/标题+作者）—— 需人工核对"}
        detail = subject_detail(candidate.get("id"), cache)
        _save_cache(cache)
    except DoubanUnavailable as exc:
        _save_cache(cache)
        return {"ok": False, "query": queries[0], "local": local,
                "verdict": "warn", "code": "douban-unavailable",
                "error": "豆瓣不可用或触发风控（%s）；请人工核对" % exc}

    checks, verdict = compare(local, detail)
    return {"ok": True, "query": used or queries[0], "tried": queries,
            "local": local, "douban": detail,
            "compare": checks, "verdict": verdict,
            "douban_url": detail.get("url")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?")
    ap.add_argument("--isbn")
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--json", action="store_true", default=True)
    args = ap.parse_args()
    result = verify(args.path, args.isbn, args.title, args.author)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("verdict") in ("pass", "warn") else 1


if __name__ == "__main__":
    raise SystemExit(main())