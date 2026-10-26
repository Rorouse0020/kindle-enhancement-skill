# 05 · 资讯 RSS（SimpleUI 乔木精选 + 原文优先 + 英文源）

> 目标：在 SimpleUI 的「资讯」里读 AI/投资内容；**英文源保持英文原文**；另用 KOReader 的 News downloader 订阅任意英文 RSS。
> 前提：KOReader + SimpleUI 已装（`references/02`、`03`）。

---

## 1. 机制（先理解，再改）

SimpleUI「资讯」读取**乔木 AI RSS 服务** `https://rss.qiaomu.ai`：

| 接口 | 用途 |
|---|---|
| `GET /api/entries?limit=N` | 全部精选（**服务端精选，本地开关不影响它**） |
| `GET /api/sources/<id>/entries?limit=N` | 单个源的条目 |
| `GET /api/entry/<id>` | 文章正文（**原文**） |
| `GET /api/entry/<id>/rewrite` | 中文「精读」改写版 |
| `GET /api/sources` | 服务端完整源目录（137 个） |

- 源目录：`koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json`（137 个源，字段 `id/name/category/siteUrl/enabled`）。
- 频道由分类推导：**全部精选 / 微信公众号 / 播客 / Newsletter / 博客与资讯 / 读者社区** + 每个源的单频道。
- ⚠️ **Kindle 版不支持自定义 RSS 订阅**（无 OPML、无"添加源"）。`/api/sources` 的 137 个 = 插件内置的 137 个，**没有额外源可加**。
- 请求实现：Kindle 上用 `/usr/bin/curl`，并带 `--connect-to rss.qiaomu.ai:443:vps2.qiaomu.ai:443`（CDN 兜底）。

---

## 2. ⚠️ 英文源被翻译成中文 → 打"原文优先"补丁

### 症状
英文源（Ben's Bites / Import AI / Interconnects…）在设备上标题和正文都是中文译文。

### 根因
`features/sui_news.lua`：
- `M.title(entry)` 优先返回 `titleZh`；
- `M.fetchArticle(id)` 优先请求 `/rewrite`（中文精读），命中就不取原文。

### 实测对比（同一个条目）
| 接口 | 长度 | 中文占比 |
|---|---|---|
| `/api/entry/<id>`（原文） | 5,872 B | **0%**（纯英文） |
| `/api/entry/<id>/rewrite`（改写） | 3,483 B | 40% |

### 补丁（两处；改前先备份，**KOReader 必须退出**）

```bash
VOL=/Volumes/Kindle
F="$VOL/koreader/plugins/simpleui.koplugin/features/sui_news.lua"
cp -p "$F" "$F.bak-original-$(date +%Y%m%d-%H%M%S)"
python3 - "$F" <<'PY'
import sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()

old_title='    return type(entry.titleZh) == "string" and entry.titleZh ~= "" and entry.titleZh or entry.title'
new_title='    -- [local patch] 原文优先：英文源显示英文标题\n    return entry.title or entry.titleZh'
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
new_rw='''    -- [local patch] 原文优先：不做中文改写；需要中文摘要时用 *_zh 精读频道。
'''
assert old_rw in s
s=s.replace(old_rw,new_rw,1)
open(p,'w',encoding='utf-8').write(s)
print("patched")
PY
grep -c '\[local patch\]' "$F"     # 期望 2
grep -c '/rewrite' "$F"            # 期望 0
```
> 安全性：实测各类型源都仍有原文内容（英文 newsletter 45 KB、公众号 44 KB、
> `*_zh` 精读源原文即中文摘要 8–11 KB），删掉改写分支不会导致打不开。

---

## 3. 源目录整理（AI + 投资，117 / 20）

关闭 20 个与主题无关的源（James Clear、Wait But Why、Scott Young、Dan Koe、中国国家地理、
知乎日报、人物、南方人物周刊、L先生说、HackerNoon 生活/写作/PM、Joe Rogan、80,000 Hours、FS Brain Food 等）。

```bash
python3 scripts/apply-rss-curation.py /Volumes/Kindle
```
脚本会：
1. 备份并写入 `data/qiaomu_sources.json`（`assets/qiaomu_sources.curated.json` 为模板）；
2. 若 `settings/simpleui/news/index.json` 已存在，**同步替换其中的 sources 列表**
   （插件运行时以 state.sources 为准，不同步就仍用旧目录）。

验证：
```bash
python3 - <<'PY'
import json
d=json.load(open('/Volumes/Kindle/koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json',encoding='utf-8'))
s=d['sources']; print('总', len(s), '启用', len([x for x in s if x.get('enabled') is not False]))
PY
```

### 推荐频道（AI + 投资）

| 想看 | 频道 | 代表源 |
|---|---|---|
| AI 每日 | **Newsletter** | Ben's Bites、TLDR AI、Import AI、Interconnects、ChinAI、One Useful Thing、Superhuman AI、AI Breakfast、The Rundown、The Neuron、Dwarkesh、Gary Marcus |
| AI + 投资播客 | **Podcasts** | All-In 中文精读、知行小酒馆、面基、42章经、晚点聊、张小珺、Lex Fridman、No Priors、Latent Space、Invest Like the Best、Acquired、Pivot、Freakonomics |
| 中文 AI/财经 | **WeChat** | 新智元、赛博禅心、卡兹克、歸藏、智东西、腾讯研究院、海外独角兽、甲子光年、晚点LatePost、吴晓波频道、猫笔刀、虎嗅、一天一篇经济学人 |
| 博客/资讯 | **Blogs and news** | 乔木博客、Simon Willison、HF Papers、Reddit AI、KDnuggets、GitHub Trending |

---

## 4. 任意英文 RSS → KOReader 的 News downloader

SimpleUI 只能读内置源，**任意英文 RSS 用 KOReader 自带插件**：

```
配置路径：/mnt/us/koreader/news/feed_config.lua
下载目录：/mnt/us/koreader/news/
入口：    工具 → News downloader（新闻下载器）
```

格式（完整样例见 `assets/feed_config.lua`，已预置 24 个实测可用的英文源）：
```lua
return {--do NOT change this line
 {"https://tldr.tech/api/rss/ai", limit=10, max_age="7d", download_full_article=true},
 {"https://stratechery.com/feed/", limit=8, max_age="30d", download_full_article=true},
 {"https://omny.fm/shows/odd-lots/playlists/podcast.rss", limit=5, max_age="30d", download_full_article=false},
}
```

### 24 个已验证英文源

| 分类 | 源 |
|---|---|
| AI | TLDR AI、Import AI、Interconnects、One Useful Thing、Simon Willison、Latent Space、Hugging Face Blog、Ben's Bites、The Rundown AI、OpenAI News、SemiAnalysis |
| AI/科技新闻 | MIT Technology Review (AI)、TechCrunch (AI)、Hacker News |
| 投资 | Stratechery、Marginal Revolution、Calculated Risk、Net Interest、Of Dollars And Data、A Wealth of Common Sense、Benedict Evans、Not Boring |
| 投资播客 | Odd Lots、All-In Podcast |

安装：
```bash
VOL=/Volumes/Kindle
mkdir -p "$VOL/koreader/news"
cp assets/feed_config.lua "$VOL/koreader/news/feed_config.lua"
```

验证源是否可用（电脑端）：
```bash
curl -sS -m 20 -L -A 'KOReader-NewsDownloader/1.0' -o /tmp/f.xml -w '%{http_code}\n' '<RSS_URL>'
grep -c '<item' /tmp/f.xml    # >0 即有条目
```

---

## 5. ⚠️ 更新失败 / 列表为空

**先查时钟**（本机实际遇到的就是这个）：`certificate is not yet valid` → 所有 HTTPS 失败。
```bash
ssh root@<ip> -p 2222 "date"     # 年份不对就修
```
修复与其余原因见 `references/07-troubleshooting.md` T1 / T10。
