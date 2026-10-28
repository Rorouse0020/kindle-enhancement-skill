# 06 · 睡眠屏保壁纸（随机名画 / 文字卡）

> 目标：设备睡眠时随机显示一张壁纸，替代系统默认的"休眠中"提示。
> 本机实测：15 张 1072×1448 灰度壁纸，KOReader 内睡眠时随机切换。
> 前提：KOReader 已装。**不需要** NiLuJe ScreensaverHack，不改系统分区。

---

## 1. 机制

KOReader 内置屏保（`frontend/ui/screensaver.lua` + `elements/screensaver_menu.lua`），支持 6 种模式：
`cover`（书名封面）｜`document_cover`（自定义图/封面）｜**`random_image`（文件夹随机）**｜
`readingprogress`（阅读进度）｜`bookstatus`（读书状态）｜`disable`（保持原屏）。

写入三个设置键即可（`koreader/settings.reader.lua`）：

```lua
["screensaver_type"] = "random_image",
["screensaver_dir"]  = "/mnt/us/wallpapers",
["screensaver_show_message"] = false,   -- 不叠加"休眠中"文字
```

取图规则：**非递归**扫描目录，最多 256 个文件（`screensaver_max_files`），
支持 jpg/png/gif/bmp/webp，忽略 `._*`；默认随机，也可开关 `screensaver_cycle_images_alphabetically` 顺序轮换。

---

## 2. 壁纸规格（重要：决定观感和残影）

| 项 | 要求 | 原因 |
|---|---|---|
| 分辨率 | **1072×1448**（PW3）；其他机型 = 设备屏幕原生分辨率 | 避免缩放模糊/黑边 |
| 色彩 | 灰度（L） | 墨水屏只有灰阶 |
| 亮度均值 | **100–250**（推荐 120–200） | 太暗会有残影；纯白背景文字卡最省电 |
| 对比度 | std ≥ 30 | 太低会"发灰看不出内容" |
| 格式 | JPEG q80–85 或 PNG | 体积小、KOReader 支持 |
| 数量 | 6–20 张 | 太少会重复，太多无意义 |

> 本机两张水墨画原始均值只有 54/72（会残影），做了两步处理：
> gamma 提亮 + 向白色混合（`Image.blend(im, white, 0.1~0.35)`），最终 144–178。

---

## 3. 素材来源（全部可自由使用）

| 来源 | 说明 |
|---|---|
| **Wikimedia Commons** | 公版/CC0 名画，API 可搜（见下） |
| **NASA images** | 公版（`images-api.nasa.gov`） |
| **自制文字卡** | PIL 生成，字体可用系统字体或设备自带中文字体 |

⚠️ Met Museum 的 `collectionapi` **搜索接口已返回 410**（对象接口仍可用）；Art Institute of Chicago 有 Cloudflare 拦截。
本包脚本用 Wikimedia + NASA，稳定可用。

生成脚本（`scripts/gen-wallpapers.py`）核心流程：
```python
# Wikimedia 搜索（必须指定文件命名空间 6）
u = "https://commons.wikimedia.org/w/api.php?" + urlencode({
    "action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":8,
    "prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1800,"format":"json"})
# 下载 thumburl → 灰度 → 中心裁剪到 1072:1448 → resize → 提亮 → 存 JPEG
```

运行：
```bash
python3 scripts/gen-wallpapers.py     # 输出到 wallpapers/sleep/
```
产物清单与作者/许可记录在同目录 `sources.json`。

---

## 4. 安装（一键）

```bash
# 前提：Kindle 已退出 KOReader 并以 USB 挂载
python3 scripts/apply-wallpapers.py /Volumes/Kindle
```
脚本做四件事：
1. 把 `wallpapers/sleep/*.jpg` 复制到 `/Volumes/Kindle/wallpapers/`；
2. 备份 `koreader/settings.reader.lua`（`*.bak-wallpaper-<时间戳>`）；
3. 写入三个 `screensaver_*` 设置并校验（含 Lua 结构合法性检查）；
4. 打印结果（不自动弹出，需你 `diskutil eject`）。

验证：
```bash
ls /Volumes/Kindle/wallpapers/*.jpg | wc -l        # 15
grep -E '\["screensaver_(type|dir|show_message)"\]' /Volumes/Kindle/koreader/settings.reader.lua
```

---

## 5. 使用与自定义

| 想做什么 | 怎么做 |
|---|---|
| 换壁纸 | 把 jpg/png（1072×1448、偏亮）丢进 `/mnt/us/wallpapers`，自动参与随机 |
| 顺序轮换（不随机） | KOReader → 设置 → 屏幕 → 睡眠屏幕 → 勾选 *Cycle images alphabetically* |
| 显示当前书封面 | 同菜单选 *Show book cover on sleep screen* |
| 恢复系统默认 | 同菜单选 *Leave screen as-is*（`screensaver_type="disable"`） |
| 完全撤销 | 恢复 `.bak-wallpaper-*`，删除 `/mnt/us/wallpapers` |

设置也可在 KOReader UI 里改：**设置 → 屏幕 → 睡眠屏幕**（改完立即生效，无需 USB）。

---

## 6. 局限（必须告诉用户）

1. **只在 KOReader 里睡眠时生效**。回到 Kindle 原生界面睡眠，仍是系统自带的"休眠中"提示。
2. 想改**原生**睡眠屏：需要 NiLuJe ScreensaverHack。本机是 **soft-float 的最终固件 5.16.2.1.1**，
   官方说明"某些最终 soft-float 版本上可能不工作"，属于有变砖风险的操作，**本包不提供**。
3. 原生折中：Kindle 设置里若有「显示封面（Display Cover）」，开启后原生睡眠显示当前书封面。
4. SimpleUI 另有 UI 背景壁纸（`simpleui_style_wallpaper` / `simpleui_style_wallpaper_enabled` /
   `simpleui_wallpaper_show_in_fm`），与睡眠屏保互相独立；需要时可指向同一张图。
