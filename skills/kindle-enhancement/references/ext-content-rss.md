# 05 · News RSS (SimpleUI Qiaomu Picks + original-language priority + English sources)

> Goal: read AI/investment content under SimpleUI's "News"; **English sources stay in the original English**; also subscribe to any English RSS with KOReader's News downloader.
> Prerequisite: KOReader + SimpleUI installed (`references/ext-koreader.md`, `03`).

---

## 1. Mechanism (understand it before changing anything)

SimpleUI "News" reads the **Qiaomu AI RSS service** `https://rss.qiaomu.ai`:

| Endpoint | Purpose |
|---|---|
| `GET /api/entries?limit=N` | All picks (**server-side picks; local switches don't affect them**) |
| `GET /api/sources/<id>/entries?limit=N` | Entries of a single source |
| `GET /api/entry/<id>` | Article body (**original**) |
| `GET /api/entry/<id>/rewrite` | Chinese "close reading" rewritten version |
| `GET /api/sources` | Full server-side source catalog (137) |

- Source catalog: `koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json` (137 sources, fields `id/name/category/siteUrl/enabled`).
- Channels are derived from categories: **All Picks / WeChat public accounts / Podcasts / Newsletter / Blogs and news / Reader community** + one single channel per source.
- ⚠️ **The Kindle version doesn't support custom RSS subscriptions** (no OPML, no "add source"). The 137 from `/api/sources` = the 137 built into the plugin, **no additional sources can be added**.
- Request implementation: on the Kindle it uses `/usr/bin/curl`, with `--connect-to rss.qiaomu.ai:443:vps2.qiaomu.ai:443` (CDN fallback).

---

## 2. ⚠️ English sources translated into Chinese → apply the "original priority" patch

### Symptom
English sources (Ben's Bites / Import AI / Interconnects…) show Chinese translations for both titles and body on the device.

### Root cause
`features/sui_news.lua`:
- `M.title(entry)` returns `titleZh` first;
- `M.fetchArticle(id)` requests `/rewrite` (Chinese close reading) first, and if it hits, doesn't fetch the original.

### Measured comparison (same entry)
| Endpoint | Length | Chinese share |
|---|---|---|
| `/api/entry/<id>` (original) | 5,872 B | **0%** (pure English) |
| `/api/entry/<id>/rewrite` (rewritten) | 3,483 B | 40% |

### Patch (two places; back up first, **KOReader must be exited**)

```bash
VOL=/Volumes/Kindle
F="$VOL/koreader/plugins/simpleui.koplugin/features/sui_news.lua"
cp -p "$F" "$F.bak-original-$(date +%Y%m%d-%H%M%S)"
python3 - "$F" <<'PY'
import sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()

old_title='    return type(entry.titleZh) == "string" and entry.titleZh ~= "" and entry.titleZh or entry.title'
new_title='    -- [local patch] original priority: English sources show English titles\n    return entry.title or entry.titleZh'
assert old_title in s
s=s.replace(old_title,new_title,1)

old_rw='''    -- Prefer the already published Chinese reading version; do not generate AI content.
    local rewrite = M.request("/api/entry/" .. id .. "/rewrite")
    rewrite = rewrite and rewrite.rewrite
    if type(rewrite) == "table" and rewrite.stale ~= true and type(rewrite.body) == "string"
            and #rewrite.body > 0 and #rewrite.body <= 400000 then
        return { body = rewrite.body, format = "md", version = "rewrite", base_url = M.ORIGIN, media_version=1 }
    end
'''
new_rw='''    -- [local patch] original priority: no Chinese rewriting; use the *_zh close-reading channel when a Chinese summary is needed.
'''
assert old_rw in s
s=s.replace(old_rw,new_rw,1)
open(p,'w',encoding='utf-8').write(s)
print("patched")
PY
grep -c '\[local patch\]' "$F"     # expect 2
grep -c '/rewrite' "$F"            # expect 0
```
> Safety: measured across all source types, original content is still available (English newsletter 45 KB, WeChat public account 44 KB,
> `*_zh` close-reading sources whose original is the Chinese summary 8–11 KB), so removing the rewrite branch won't make anything fail to open.

---

## 3. Source catalog curation (AI + investment, 117 / 20)

Disable 20 sources unrelated to the topic (James Clear, Wait But Why, Scott Young, Dan Koe, China National Geographic (中国国家地理),
Zhihu Daily (知乎日报), Renwu (人物), Southern People Weekly (南方人物周刊), L Says (L先生说), HackerNoon Life/Writing/PM, Joe Rogan, 80,000 Hours, FS Brain Food, etc.).

```bash
python3 scripts/apply-rss-curation.py /Volumes/Kindle
```
The script will:
1. Back up and write `data/qiaomu_sources.json` (`assets/qiaomu_sources.curated.json` is the template);
2. If `settings/simpleui/news/index.json` already exists, **replace its sources list in sync**
   (the plugin uses state.sources at runtime, so without syncing it still uses the old catalog).

Verify:
```bash
python3 - <<'PY'
import json
d=json.load(open('/Volumes/Kindle/koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json',encoding='utf-8'))
s=d['sources']; print('总', len(s), '启用', len([x for x in s if x.get('enabled') is not False]))
PY
```

### Recommended channels (AI + investment)

| What you want | Channel | Representative sources |
|---|---|---|
| AI daily | **Newsletter** | Ben's Bites, TLDR AI, Import AI, Interconnects, ChinAI, One Useful Thing, Superhuman AI, AI Breakfast, The Rundown, The Neuron, Dwarkesh, Gary Marcus |
| AI + investment podcasts | **Podcasts** | All-In Chinese close reading (All-In 中文精读), Zhixing Xiaojiuguan (知行小酒馆), Mianji (面基), 42 Chapters (42章经), LateTalk (晚点聊), Zhang Xiaojun (张小珺), Lex Fridman, No Priors, Latent Space, Invest Like the Best, Acquired, Pivot, Freakonomics |
| Chinese AI/finance | **WeChat** | AI Era (新智元), Cyber Zen (赛博禅心), Kazik (卡兹克), Guizang (歸藏), Zhidx (智东西), Tencent Research Institute (腾讯研究院), Overseas Unicorn (海外独角兽), Jiazi Guangnian (甲子光年), LatePost (晚点LatePost), Wu Xiaobo Channel (吴晓波频道), Mao Bidao (猫笔刀), Huxiu (虎嗅), One Economist Article a Day (一天一篇经济学人) |
| Blogs/news | **Blogs and news** | Qiaomu Blog (乔木博客), Simon Willison, HF Papers, Reddit AI, KDnuggets, GitHub Trending |

---

## 4. Any English RSS → KOReader's News downloader

SimpleUI can only read the built-in sources; **for any English RSS, use KOReader's built-in plugin**:

```
Configuration path: /mnt/us/koreader/news/feed_config.lua
Download directory: /mnt/us/koreader/news/
Entry point:        Tools → News downloader
```

Format (full sample in `assets/feed_config.lua`, preloaded with 24 verified working English sources):
```lua
return {--do NOT change this line
 {"https://tldr.tech/api/rss/ai", limit=10, max_age="7d", download_full_article=true},
 {"https://stratechery.com/feed/", limit=8, max_age="30d", download_full_article=true},
 {"https://omny.fm/shows/odd-lots/playlists/podcast.rss", limit=5, max_age="30d", download_full_article=false},
}
```

### 24 verified English sources

| Category | Sources |
|---|---|
| AI | TLDR AI, Import AI, Interconnects, One Useful Thing, Simon Willison, Latent Space, Hugging Face Blog, Ben's Bites, The Rundown AI, OpenAI News, SemiAnalysis |
| AI/tech news | MIT Technology Review (AI), TechCrunch (AI), Hacker News |
| Investment | Stratechery, Marginal Revolution, Calculated Risk, Net Interest, Of Dollars And Data, A Wealth of Common Sense, Benedict Evans, Not Boring |
| Investment podcasts | Odd Lots, All-In Podcast |

Installation:
```bash
VOL=/Volumes/Kindle
mkdir -p "$VOL/koreader/news"
cp assets/feed_config.lua "$VOL/koreader/news/feed_config.lua"
```

Verify whether a source is usable (from the computer):
```bash
curl -sS -m 20 -L -A 'KOReader-NewsDownloader/1.0' -o /tmp/f.xml -w '%{http_code}\n' '<RSS_URL>'
grep -c '<item' /tmp/f.xml    # >0 means there are entries
```

---

## 5. ⚠️ Update failure / empty list

**Check the clock first** (this is exactly what happened on this machine): `certificate is not yet valid` → all HTTPS fails.
```bash
ssh root@<ip> -p 2222 "date"     # fix it if the year is wrong
```
For the fix and the other causes see `references/ext-troubleshooting.md` T1 / T10.
