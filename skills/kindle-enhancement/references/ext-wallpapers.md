# 06 · Sleep Screen Wallpapers (Random Fine Art / Text Cards)

> Goal: display a random wallpaper when the device sleeps, replacing the system's default "going to sleep" prompt.
> Verified on this device: 15 grayscale 1072×1448 wallpapers, switched randomly on sleep inside KOReader.
> Prerequisite: KOReader is installed. NiLuJe ScreensaverHack is **not** needed, and no system partition is modified.

---

## 1. Mechanism

KOReader has a built-in screensaver (`frontend/ui/screensaver.lua` + `elements/screensaver_menu.lua`) with 6 modes:
`cover` (book cover) | `document_cover` (custom image/cover) | **`random_image` (random from folder)** |
`readingprogress` (reading progress) | `bookstatus` (reading status) | `disable` (keep the current screen).

Writing three settings keys is enough (`koreader/settings.reader.lua`):

```lua
["screensaver_type"] = "random_image",
["screensaver_dir"]  = "/mnt/us/wallpapers",
["screensaver_show_message"] = false,   -- do not overlay the "going to sleep" text
```

Image selection rule: scans the directory **non-recursively**, up to 256 files (`screensaver_max_files`),
supports jpg/png/gif/bmp/webp, ignores `._*`; random by default, or enable `screensaver_cycle_images_alphabetically` to rotate in order.

---

## 2. Wallpaper Specs (important: determines appearance and ghosting)

| Item | Requirement | Reason |
|---|---|---|
| Resolution | **1072×1448** (PW3); other models = the device's native screen resolution | Avoids scaling blur/black bars |
| Color | Grayscale (L) | E-ink only has grayscale |
| Mean brightness | **100–250** (120–200 recommended) | Too dark causes ghosting; a pure white background text card saves the most power |
| Contrast | std ≥ 30 | Too low looks "washed out and illegible" |
| Format | JPEG q80–85 or PNG | Small size, supported by KOReader |
| Count | 6–20 images | Too few repeats, too many is meaningless |

> On this device, two ink-wash paintings had an original mean of only 54/72 (would ghost), so two steps were applied:
> gamma brightening + blending toward white (`Image.blend(im, white, 0.1~0.35)`), ending at 144–178.

---

## 3. Material Sources (all freely usable)

| Source | Description |
|---|---|
| **Wikimedia Commons** | Public domain/CC0 fine art, searchable via API (see below) |
| **NASA images** | Public domain (`images-api.nasa.gov`) |
| **Self-made text cards** | Generated with PIL; fonts can be system fonts or the device's built-in Chinese fonts |

⚠️ The Met Museum `collectionapi` **search endpoint now returns 410** (the object endpoint still works); the Art Institute of Chicago has a Cloudflare block.
The scripts in this package use Wikimedia + NASA, which are stable and usable.

Generation script (`scripts/gen-wallpapers.py`) core flow:
```python
# Wikimedia search (you must specify file namespace 6)
u = "https://commons.wikimedia.org/w/api.php?" + urlencode({
    "action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":8,
    "prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1800,"format":"json"})
# download thumburl → grayscale → center-crop to 1072:1448 → resize → brighten → save as JPEG
```

Run:
```bash
python3 scripts/gen-wallpapers.py     # outputs to wallpapers/sleep/
```
The asset manifest and author/license records are in `sources.json` in the same directory.

---

## 4. Installation (one command)

```bash
# Prerequisite: Kindle has exited KOReader and is mounted over USB
python3 scripts/apply-wallpapers.py /Volumes/Kindle
```
The script does four things:
1. Copies `wallpapers/sleep/*.jpg` to `/Volumes/Kindle/wallpapers/`;
2. Backs up `koreader/settings.reader.lua` (`*.bak-wallpaper-<timestamp>`);
3. Writes the three `screensaver_*` settings and validates them (including a Lua structural validity check);
4. Prints the result (does not auto-eject; you need to run `diskutil eject`).

Verification:
```bash
ls /Volumes/Kindle/wallpapers/*.jpg | wc -l        # 15
grep -E '\["screensaver_(type|dir|show_message)"\]' /Volumes/Kindle/koreader/settings.reader.lua
```

---

## 5. Usage and Customization

| What you want to do | How to do it |
|---|---|
| Change wallpapers | Drop jpg/png (1072×1448, on the bright side) into `/mnt/us/wallpapers`; they join the random pool automatically |
| Rotate in order (not random) | KOReader → Settings → Screen → Sleep screen → check *Cycle images alphabetically* |
| Show the current book cover | In the same menu, choose *Show book cover on sleep screen* |
| Restore the system default | In the same menu, choose *Leave screen as-is* (`screensaver_type="disable"`) |
| Undo completely | Restore `.bak-wallpaper-*`, delete `/mnt/us/wallpapers` |

Settings can also be changed in the KOReader UI: **Settings → Screen → Sleep screen** (takes effect immediately, no USB needed).

---

## 6. Limitations (must tell the user)

1. **Only takes effect when sleeping inside KOReader**. When sleeping on the native Kindle interface, the system's own "going to sleep" prompt still appears.
2. To change the **native** sleep screen you need NiLuJe ScreensaverHack. This device runs **the final soft-float firmware 5.16.2.1.1**,
   and the official notes say it "may not work on some final soft-float builds"; this carries a bricking risk, so **this package does not provide it**.
3. Native compromise: if the Kindle settings have "Display Cover", enabling it makes the native sleep screen show the current book cover.
4. SimpleUI has a separate UI background wallpaper (`simpleui_style_wallpaper` / `simpleui_style_wallpaper_enabled` /
   `simpleui_wallpaper_show_in_fm`), independent of the sleep screensaver; point it at the same image if desired.
