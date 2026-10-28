# Book Source Quality Gate (Four Hard Metrics)

> **Core principle: sending a bad book is worse than not sending it.**
> A poor-quality book wastes device space and reading time; discovering missing content/a misprinted edition/tampering halfway through costs far more than spending an extra minute on the gate.
> Any book judged **BLOCK** is never sent; **WARN** must first be explained to the user and confirmed by them; only **PASS** enters the send flow.

---

## Metric 1: ISBN / Publisher / Edition Can Be Matched (Verifiable on Douban or the Publisher's Website)

**Why it matters**: pirated assemblies, old editions posing as new ones, and forcibly merged translations all show up here.

**How to check**

1. Read the EPUB metadata (`quality_check.py` prints it):
   - ISBN-10/13 in `dc:identifier` (watch for the `urn:isbn:` prefix and invalid identifiers such as `calibre:`)
   - `dc:publisher` (publisher), `dc:date` (publication year/edition), `dc:title`/`dc:creator`
2. Cross-check using the **Douban search link** printed by the script: whether title, author, publisher, publication year, page count, and ISBN are **all** consistent.
3. Second check on the publisher's website/e-commerce detail page (especially ISBN and edition).

**Verdict**
- Metadata complete + matches Douban → **PASS**
- Missing any one of ISBN/publisher/date, or title/author not as expected → **WARN** (decide after manual verification)
- **Title clearly conflicts with the Douban entry → BLOCK** (wrong book/assembled copy)
- ISBN, publication year, or publisher inconsistent → **WARN** (very common: different editions, different printings, boxed set vs. single volume)
- Douban placeholder ISBN (`9787001xxxxxx` etc.) or a local ISBN with an invalid checksum → **WARN** for that item and skip the comparison
- Decision principle: **reserve block only for "title doesn't match" and "content unsafe"**; downgrade all other inconsistencies to warn, to avoid killing legitimate other editions
- Common suspicious signs: `creator` is a scan-site watermark name like "SoBooKs.cc"; the title says "精校版/全译版" but there is no version information; the same ISBN corresponds to different covers/titles.

### 1.1 Automatic Verification (`--douban`, Recommended)

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/quality_check.py "/absolute/path/book.epub" --douban
"$RT" scripts/douban_verify.py --isbn 9787208178212
"$RT" scripts/douban_verify.py --title "战略与路径" --author "黄奇帆"
```

How it works: Douban public pages (the `book.douban.com/j/subject_suggest` search plus the `/subject/<id>/` detail page),
automatically comparing title, author, publisher, publication year, and ISBN, and outputting `pass/warn/block`.

| Comparison item | Verdict |
|---|---|
| Title | Main titles (before the colon) contain each other → pass |
| Author | Any author contains the other (after stripping the 【】 prefix) → pass; scan-site watermark → warn |
| Publisher | Mutual containment → pass; different → warn |
| Publication year | Same or ±1 year → pass; otherwise warn/fail |
| ISBN | Both present and identical → pass; missing locally → warn (can be backfilled from the Douban ISBN) |

Degradation strategy: Douban login wall/risk control/network failure → **warn + prompt for manual check**; no blocking, no false judgement.
Request interval 1.5 s, UA spoofing, 15 s timeout, 7-day cache; read-only public pages, no login.

**Backfilling ISBN (makes Metric 1 pass directly)**

```bash
"$RT" scripts/backfill_isbn.py "book.epub" --douban
"$RT" scripts/backfill_isbn.py "book.epub" --isbn 9787208178212   # specify manually
"$RT" scripts/backfill_isbn.py "book.epub" --isbn 9787... --fix-language zh-CN  # also normalize the language tag
"$RT" scripts/backfill_isbn.py "book.epub" --douban --fill-metadata            # ISBN+publisher+publication date (placeholder ISBNs skipped automatically)
```

The script only inserts `<dc:identifier id="isbn">urn:isbn:…</dc:identifier>` into the OPF; the body text/images are untouched;
by default it backs up to `book.epub.orig`, and after writing it re-validates the structure (mimetype first, container, OPF, spine).
After backfilling, both `1_meta` and `1_douban` in `quality_check.py` can pass.

**Measured samples** (2026-10-27):
- 《战略与路径》 → hits `subject/36139006`, author/publisher/year consistent, ISBN 9787208178212 (missing locally → warn)
- 《狼性时代》 → hits `subject/36692833`, author/publisher/year consistent, ISBN 9787513944441 (missing locally → warn, `creator` is SoBooKs.cc)

---

## Metric 2: EPUB Structure Valid (inspect Reports No Errors)

**Automation** (`scripts/quality_check.py` Metric 2, plus `send_to_kindle.py inspect`):

- The zip can be opened and `testzip()` reports no corrupt entries
- `mimetype` is the **first** entry and its content is `application/epub+zip`
- `META-INF/container.xml` exists and parses, and the rootfile points to an OPF that actually exists
- The OPF parses; `spine` is non-empty, and every `itemref` is found in the `manifest`
- At least one XHTML/HTML body in the spine

**Verdict**: if any one fails → **BLOCK** (corrupt/fake EPUB/failed conversion — it won't open even if sent).

---

## Metric 3: File Size Reasonable (A Massive Book of a Few Dozen KB Is Basically a Truncated Version)

**Automated heuristics** (script Metric 3):

- `< 50 KB` → highly suspicious
- `< 150 KB` and **no images** → suspicious (except text-only pamphlets)
- Title contains `sample / excerpt / preview / 试读 / 样章 / 节选 / 预览` → suspicious
- Outputs "body KB / image count / chapter count" for manual judgement

**Manual yardstick** (empirical values, Chinese books):
| Type | Reasonable range |
|---|---|
| 200–300 pages, text only | 300 KB – 1.5 MB |
| 400+ pages | 1 – 3 MB |
| Illustrated/text-image mixed, picture books | 5 – 50 MB |
| Academic books/with many footnotes | 1.5 – 5 MB |

**Verdict**: clearly below the ranges above → **WARN** (have the user confirm it isn't a sample/truncated copy); if ISBN is also missing or the chapter count is extremely low → escalate to **BLOCK**.

---

## Metric 4: No Scripts / External Link Redirects in the Body (Conversion Strips script/style/iframe)

**Automated scan** (script Metric 4, scanning all spine XHTML):

| Match | Meaning | Action |
|---|---|---|
| `<script>`, `<iframe>`, `<object>`, `<embed>` | executable/embedded content | **BLOCK** |
| `javascript:` pseudo-protocol, `on*=` event attributes | clickjacking/tracking | **BLOCK** |
| External `http(s)://` `href/src` | body taken off-device/external resources | **WARN** (many of them, or pointing to suspicious domains → BLOCK) |

**Why block these**: the converter (KindleUnpack / the built-in AZW3 writer) strips `script/style/iframe`, but after stripping it may leave blank chapters or broken navigation;
more seriously, such files are commonly "web-scraped assembled copies" with extremely low body quality.

**Verdict**: contains executable content → **BLOCK**; only a few external links → **WARN** and spot-check the link targets.

---

## Gate Conclusion and Record

`scripts/quality_check.py` outputs:

```json
{
  "ok": true,
  "verdict": "pass | warn | block",
  "checks": {
    "1_meta":      {"status": "pass|warn|fail", "detail": "..."},
    "2_structure": {"status": "...", "detail": "..."},
    "3_size":      {"status": "...", "detail": "..."},
    "5_content":   {"status": "...", "detail": "..."}
  },
  "metadata": {"title": "...", "creator": "...", "publisher": "...", "date": "...", "isbn": "..."},
  "content_counts": {"script": 0, "iframe": 0, "外部链接": 2, "...": 0},
  "douban": "https://search.douban.com/book/subject_search?search_text=..."
}
```

**Gate → send → receipt**, all three steps must leave a trail. The send receipt must additionally carry the gate conclusion, for example:

```
ok:true · /mnt/us/documents/book-title.epub · 1,017,049 B · sha256=c531… · converted:false
quality: pass (structure/size/content auto-passed, ISBN 9787… verified against Douban)
```

## Counterexamples (Real Pitfalls Hit by This Project)

| Scenario | Symptom | Lesson |
|---|---|---|
| AZW3 sent directly to KOReader | tapping it says "format not supported" | Passing Metric 2 ≠ reader support; **format matching** must be judged separately (KOReader does not support KF8) |
| `home_dir` points to an empty directory | books are in `documents` but the shelf is empty | after the gate passes you must still verify "visible on the device side" |
| Files from SoBooKs | metadata `creator` is a scan-site name | Metric 1 gives WARN; manual ISBN/publisher verification required |
