# 02 · KOReader installation (including the launcher and library path fix)

> Goal: install KOReader and be able to launch it with one tap from the library; the library points to the correct `documents/`.
> Measured on this machine: **KOReader v2026.07.1** + the `koreader-kindlepw2` package (soft-float).
> Prerequisite: `references/ext-jailbreak.md` completed.

---

## 1. Choose the right package (wrong choice = crash on launch)

| Package name | Applies to | How to tell |
|---|---|---|
| `koreader-kindlepw2-*.zip` | **soft-float**: PW2/PW3/KT2/KV/KOA1, etc. (firmware < 5.16.3) | `ls /lib/ld-linux-armhf.so.3` on the device **does not exist** |
| `koreader-kindlehf-*.zip` | **hard-float**: models on 5.16.3+ | the `ls` above **exists** |
| `koreader-kindle-*.zip` / `kindle-legacy` | older models (K4/K5, etc.) | see the KOReader Wiki |

Download (replace `v2026.07.1` with the version you want):
```bash
cd ~/Downloads && mkdir -p koreader && cd koreader
curl -L -o kor.zip https://github.com/koreader/koreader/releases/download/v2026.07.1/koreader-kindlepw2-v2026.07.1.zip
unzip -l kor.zip | head -12      # expected: extensions/koreader/... and koreader/...
shasum -a 256 kor.zip            # record it so others can verify (package on this machine = 40,715,224 B)
```

> Official KOReader releases don't provide per-file signatures; if strict verification is needed, rely on the GitHub release page and check the size.

---

## 2. Installation

```bash
VOL=/Volumes/Kindle
[ -d "$VOL/documents" ] || { echo "不是 Kindle 卷"; exit 1; }
unzip -o kor.zip -d "$VOL"        # yields koreader/ and extensions/koreader/
ls -d "$VOL/koreader" "$VOL/extensions/koreader"
cat "$VOL/koreader/git-rev"        # expected: v2026.07.1
find "$VOL/koreader" -type f | wc -l   # about 2227 files on this machine
```

---

## 3. Launcher (critical)

KOReader's `koreader.sh` ultimately executes `./reader.lua`, and `/mnt/us` may be **noexec** by default.
Therefore the launcher must remount first and then launch. Place this package's `assets/KOReader.sh` in `documents/`:

```sh
#!/bin/sh
# Name: KOReader
# Author: KindleModding
# Icon: /mnt/us/koreader/resources/koreader.png
mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
cd /mnt/us/koreader || exit 1
exec sh ./koreader.sh
```
```bash
cp assets/KOReader.sh "$VOL/documents/KOReader.sh"
diskutil eject "$VOL"
```

Principle: during the jailbreak **sh_integration** was installed (the extractor registered by jb.sh), so `.sh` files in `documents/`
are indexed as "books" and run as root when tapped — this is the officially recognized way to launch scripts (the KOReader FAQ also mentions launching via a scriptlet).
`# Name:` determines the displayed name in the library, `# Icon:` determines the icon.

> Alternative: if you separately installed KUAL, you can also launch from KUAL's KOReader menu
> (`extensions/koreader/` is installed along with the package).

---

## 4. First launch

On the device: Library → **KOReader** → wait 10–30 seconds (the first run generates the cache and settings).
Success indicator: the KOReader file browser appears.

The first launch generates:
```
koreader/settings.reader.lua      # global settings
koreader/settings/                # per-plugin settings
koreader/cache/                   # cache
```

---

## 5. ⚠️ Blank library / no books visible: fix home_dir

**Symptom**: KOReader launches, but the bookshelf doesn't show the books in `documents/`.
**Root cause**: `home_dir` was set to some empty directory (`/mnt/us/Books` on this machine), and `lock_home_folder=true` locked down navigation.

Diagnose (USB or SSH both work):
```bash
VOL=/Volumes/Kindle
grep -nE '\["home_dir"\]|\["lock_home_folder"\]|\["lastdir"\]' "$VOL/koreader/settings.reader.lua"
```

Fix (**must be edited while KOReader is exited**, otherwise it writes back and overwrites on exit):

```bash
VOL=/Volumes/Kindle; S="$VOL/koreader/settings.reader.lua"
cp -p "$S" "$S.bak-homefix-$(date +%Y%m%d-%H%M%S)"
python3 - "$S" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
s=re.sub(r'^    \["home_dir"\] = "[^"]*",$','    ["home_dir"] = "/mnt/us/documents",',s,flags=re.M)
s=re.sub(r'^    \["lock_home_folder"\] = \w+,$','    ["lock_home_folder"] = false,',s,flags=re.M)
s=re.sub(r'^    \["lastdir"\] = "[^"]*",$','    ["lastdir"] = "/mnt/us/documents",',s,flags=re.M)
open(p,'w',encoding='utf-8').write(s)
PY
grep -E '\["(home_dir|lock_home_folder|lastdir)"\]' "$S"
```
After restarting KOReader the library is back to normal.

> Why this matters: `/mnt/us/documents` is also the target directory for wireless book transfer (`references/ext-send2kindle.md`).
> Once fixed, "books sent over are immediately visible"; otherwise you get "transfer succeeds but can't be seen".

---

## 6. Verification checklist

```bash
VOL=/Volumes/Kindle
cat "$VOL/koreader/git-rev"                                  # v2026.07.1
ls -l "$VOL/koreader/reader.lua" "$VOL/koreader/koreader.sh" # exists and is readable
grep -E '\["home_dir"\]' "$VOL/koreader/settings.reader.lua" # /mnt/us/documents
ls "$VOL/documents/KOReader.sh"                              # launcher exists
```
On the device: tapping KOReader enters it; the library shows the EPUB/PDF files from `documents/`.

---

## 7. FAQ

| Symptom | Handling |
|---|---|
| Tapping KOReader does nothing / flashes back | Check whether the launcher has `mount -o remount,exec`; when `/mnt/us` is noexec, `reader.lua` cannot execute |
| Black screen / garbled screen after launch | Confirm the package is `kindlepw2` (soft-float); hard-float machines use `kindlehf` |
| Empty library | §5 (home_dir) |
| A plugin is missing from the menu | The plugin directory name must be exactly `<name>.koplugin`, and **KOReader must be restarted** |
| Want to upgrade KOReader | Exit KOReader → overwrite-extract with the new zip → restart; settings and plugins are preserved |
