import json, os, urllib.request, urllib.parse, io
from PIL import Image, ImageOps, ImageDraw, ImageFont

W, H = 1072, 1448
from pathlib import Path as _P
BASE = _P(__file__).resolve().parent.parent
OUT, RAW = str(BASE / "wallpapers" / "sleep"), str(BASE / "wallpapers" / "raw")
os.makedirs(OUT, exist_ok=True); os.makedirs(RAW, exist_ok=True)
UA = {"User-Agent": "KindleWallpaper/1.0 (personal use)"}

def get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def commons_pick(query, want=None, idx=0):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": 6,
        "gsrlimit": 8, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1800, "format": "json"})
    d = json.loads(get(u))
    pages = list(((d.get("query") or {}).get("pages") or {}).values())
    pages.sort(key=lambda p: (p.get("imageinfo") or [{}])[0].get("width") or 0, reverse=True)
    for p in pages:
        title = p.get("title", "")[5:]
        ii = (p.get("imageinfo") or [{}])[0]
        if want and want.lower() not in title.lower(): continue
        if not (ii.get("thumburl") or ii.get("url")): continue
        if min(ii.get("width", 0), ii.get("height", 0)) < 800: continue
        return p, ii, title
    return None, None, None

def process(raw_bytes, out_path, lighten=0.85):
    img = Image.open(io.BytesIO(raw_bytes)).convert("L")
    w, h = img.size; r = W / H
    if w / h > r:
        nw = int(h * r); img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / r); img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    img = img.resize((W, H), Image.LANCZOS)
    img = img.point([min(255, int(255 * ((i / 255) ** lighten))) for i in range(256)])
    img = ImageOps.autocontrast(img, cutoff=1)
    img.save(out_path, "JPEG", quality=82, optimize=True)
    return os.path.getsize(out_path)

ART = [
    ("Hokusai Great Wave off Kanagawa", "Great Wave off Kanagawa2", 0.86),
    ("Hokusai Tsunami", "Tsunami by hokusai", 0.86),
    ("China Northern Song Palace Landscape", "Palace Landscape", 0.9),
    ("China Southern Song Bamboo Landscape", "Bamboo Landscape", 0.9),
    ("Qing Songnian Landscape handscroll", "山水 手卷", 0.9),
    ("Hiroshige famous views landscape", "Hiroshige", 0.88),
    ("Monet Water Lilies", "Water Lilies", 0.88),
    ("Caspar David Friedrich Wanderer", "Wanderer above the Sea of Fog", 0.86),
    ("Vincent van Gogh Starry Night", "Starry Night", 0.8),
    ("Hiroshige Plum Garden", "Plum", 0.88),
]
meta, n = [], 0
for q, want, light in ART:
    try:
        p, ii, title = commons_pick(q, want)
        if not p:
            print("  ✗ 未找到:", q); continue
        url = ii.get("thumburl") or ii.get("url")
        data = get(url, 90)
        n += 1
        fn = os.path.join(OUT, f"art-{n:02d}.jpg")
        kb = process(data, fn, light)
        em = ii.get("extmetadata") or {}
        lic = (em.get("LicenseShortName") or {}).get("value", "Public domain")
        artist = (em.get("Artist") or {}).get("value", "")
        import re; artist = re.sub(r"<[^>]+>", "", artist)[:60]
        meta.append({"file": f"art-{n:02d}.jpg", "title": title, "artist": artist, "license": lic})
        print(f"  ✅ {title[:46]} | {kb//1024} KB | {lic}")
    except Exception as e:
        print("  ✗", q, str(e)[:70])

# --- NASA ---
try:
    d = json.loads(get("https://images-api.nasa.gov/search?q=earth%20from%20space&media_type=image&page_size=5"))
    items = d.get("collection", {}).get("items", [])
    got = 0
    for it in items:
        nid = it["data"][0]["nasa_id"]
        try:
            asset = json.loads(get(f"https://images-api.nasa.gov/asset/{urllib.parse.quote(nid)}"))
            links = [x["href"] for x in asset["collection"]["items"] if x["href"].lower().endswith((".jpg", ".png"))]
            if not links: continue
            url = links[0].replace("~orig", "~large").replace("~medium", "~large")
            data = get(url, 90)
            n += 1
            fn = os.path.join(OUT, f"space-{n:02d}.jpg")
            kb = process(data, fn, 0.9)
            meta.append({"file": f"space-{n:02d}.jpg", "title": it["data"][0]["title"][:60], "artist": "NASA", "license": "Public domain (NASA)"})
            print(f"  ✅ NASA: {it['data'][0]['title'][:40]} | {kb//1024} KB")
            got += 1
            if got >= 2: break
        except Exception as e:
            continue
except Exception as e:
    print("  ✗ NASA:", str(e)[:60])

# --- 文字卡 ---
FONTS = ["backup-2026-10-26/fonts/方正楷体.ttf", "backup-2026-10-26/fonts/方正北魏楷书.ttf",
         "/System/Library/Fonts/Supplemental/Georgia.ttf", "/System/Library/Fonts/Supplemental/Times New Roman.ttf"]
zh_font = next((f for f in FONTS[:2] if os.path.exists(f)), None)
en_font = next((f for f in FONTS[2:] if os.path.exists(f)), None)
CARDS = [
    (zh_font, "读书随处净土\n闭门即是深山", "陈继儒《小窗幽记》"),
    (zh_font, "静以修身 俭以养德", "诸葛亮《诫子书》"),
    (en_font, "A reader lives a thousand lives\nbefore he dies.", "George R. R. Martin"),
    (en_font, "The more that you read,\nthe more things you will know.", "Dr. Seuss"),
]
for i, (font_path, text, sub) in enumerate(CARDS, 1):
    if not font_path: continue
    img = Image.new("L", (W, H), 250); d = ImageDraw.Draw(img)
    is_zh = any('\u4e00' <= ch <= '\u9fff' for ch in text)
    size = 96 if is_zh else 74
    try: f = ImageFont.truetype(font_path, size)
    except Exception: continue
    lines = text.split("\n")
    lh = int(size * 1.7); total = lh * len(lines)
    y = (H - total) // 2 - 40
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=f); tw = bb[2] - bb[0]
        d.text(((W - tw) // 2, y), ln, font=f, fill=28); y += lh
    d.line([(W//2 - 90, y + 30), (W//2 + 90, y + 30)], fill=120, width=2)
    fs = ImageFont.truetype(font_path, 34)
    bb = d.textbbox((0, 0), sub, font=fs); tw = bb[2] - bb[0]
    d.text(((W - tw)//2, y + 70), sub, font=fs, fill=110)
    fn = os.path.join(OUT, f"quote-{i:02d}.jpg")
    img.save(fn, "JPEG", quality=90, optimize=True)
    meta.append({"file": f"quote-{i:02d}.jpg", "title": text.replace("\n", " "), "artist": sub, "license": "generated locally"})
    print(f"  ✅ 文字卡 {i}: {text[:22]}")

json.dump(meta, open("wallpapers/sources.json", "w"), ensure_ascii=False, indent=1)
print(f"\n总计 {len(meta)} 张，输出目录 {OUT}")
