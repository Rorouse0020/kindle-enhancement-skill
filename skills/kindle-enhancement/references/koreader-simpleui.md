# KOReader + SimpleUI Reference (Kindle / PW3)

## 1. Choosing a Package

| Device platform | Package name |
|---|---|
| PW3 / PW2 / KV / KT2 and other soft-float devices (no `/lib/ld-linux-armhf.so.3`) | `koreader-kindlepw2-v*.zip` |
| 5.16.3+ hard-float (most devices after PW4/KT4) | `koreader-kindlehf-v*.zip` |
| Very old K4/K5 | `koreader-kindle-v*.zip` / `koreader-kindle-legacy-v*.zip` |

Package structure: `koreader/` (main program, containing `reader.lua`, `koreader.sh`, `dropbear`, `plugins/`) + `extensions/koreader/` (KUAL menu).

## 2. Installation (Without KUAL)

1. Extract to the device root directory: `unzip -q -o koreader-kindlepw2-*.zip -d /Volumes/Kindle`
2. Put the launcher scriptlet at `documents/KOReader.sh`:
   ```sh
   #!/bin/sh
   # Name: KOReader
   # Icon: /mnt/us/koreader/resources/koreader.png
   mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
   cd /mnt/us/koreader || exit 1
   exec sh ./koreader.sh
   ```
   Reason: `/mnt/us` may be mounted noexec, while KOReader executes `reader.lua` directly; the scriptlet is run by the shell integration installed by the jailbreak (and is clickable).
3. Put plugins in `koreader/plugins/<name>.koplugin/` (the directory name must be exact, with no extra level).
4. After extracting on macOS, clean up `._*` / `.DS_Store`.

## 3. SimpleUI (Qiaomu Custom Build)

- Requires KOReader **≥ v2026.03**; for the Release use `simpleui.koplugin.zip` (do not use the GitHub source zip), and verify it with the official `SHA256SUMS`.
- Directory: `koreader/plugins/simpleui.koplugin/`; it depends on the bundled **CoverBrowser** plugin being enabled.
- After the first launch we recommend: Settings → Home → Behavior → Start with home screen; add a "tiled bookshelf" to the home page.
- The AI features require Tools → Qiaomu AI → Configure with phone, then scan the QR code to fill in the API Key (stored at `/var/local/qiaomu/ai.json`, not visible over USB).

## 4. Common Pitfall: Empty Library / Books Not Visible

KOReader's library root comes from `home_dir` in `settings.reader.lua`. If it is set to an empty directory (e.g. `/mnt/us/Books`),
then even if the books are in `documents/` they **will not show up**.

Fix (**you must exit KOReader first**, otherwise it writes back on exit and overwrites your edit):

```
["home_dir"]         = "/mnt/us/documents"
["lock_home_folder"] = false
["lastdir"]          = "/mnt/us/documents"
```

Back up `settings.reader.lua` before changing it; after changing it, confirm it is still a valid Lua table (`return { … }`, no BOM/CRLF issues).
`/mnt/us/documents` is also the wireless delivery target directory, so once fixed, new books are visible immediately.

## 5. Format Support (Tested on v2026.07.1)

| Supported | Not supported |
|---|---|
| EPUB/EPUB3, PDF, DjVu, FB2/FB3, TXT, HTML(Z), CHM, DOC/DOCX, MOBI/AZW/PRC (old-style KF7, no DRM) | **AZW3/KFX (KF8)**, any DRM |

Basis: `frontend/document/credocument.lua` registers only `azw`/`mobi`/`prc`, not `azw3`.
→ Books for KOReader must be **EPUB**; for AZW3-to-EPUB conversion see `references/send2kindle.md` §5.

## 6. Settings Backup and Rollback

- Backup: `settings.reader.lua`, `settings/` (including `simpleui/`); back up plugin directories in full.
- Rollback: put the backup back in place and delete the corresponding plugin directory; books/annotations/reading progress are unaffected.
- Plugin failure: read the end of `koreader/crash.log` and locate the issue by timestamp.

## 7. Clock

After a factory reset the RTC may be stuck at an old date (observed showing 2023-09-18), which can break KOReader's network/certificate-related features (OTA, AI, news).
Correct it in `Settings → Device options → Device time`, or connect to Wi-Fi and wait for automatic sync.
