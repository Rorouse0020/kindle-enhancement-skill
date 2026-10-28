---
name: kindle-enhancement
display_name: Kindle Enhancement
description: |
  Set up a usable enhancement environment for a jailbroken Kindle (focus on PW3 / firmware 5.16.2.1.1): jailbreak, KOReader + SimpleUI, wireless book delivery (qiaomu-send2kindle), automatic Kindle format → EPUB conversion; and, before delivery, run a "book-source quality gate" on the ebook (ISBN/publisher/edition, EPUB structure, file size, no scripted external links in the body).
  Use when the user says "jailbreak a Kindle / install KOReader / send a book to the Kindle / check whether this book is complete and reliable / quality-control a book before sending it".
metadata:
  author: Kindle Enhancement (local build)
  version: "1.0.0"
  platform: macOS
  last_verified: "2026-10-26"
  reference_device: "Kindle Paperwhite 7th gen (PW3), firmware 5.16.2.1.1, jailbroken with WinterBreak2"
---

> **Language:** English (this file) · [中文](SKILL.md)

# Kindle Enhancement

A Kindle enhancement pipeline **verified on real hardware**: jailbreak → KOReader/SimpleUI → wireless book delivery → book-source quality gate → format conversion → acceptance.
Every step carries verification points; **if a step produced no evidence, it is not done**.

---

## 0. Core principles (read first)

1. **Evidence first**: every step must produce checkable results (`ok: true` receipt, SHA-256, on-device file listing, screen log); "it looked like it worked" is not allowed.
2. **Do not touch unknown state**: before writing to the device, confirm the firmware version, mount point, and target path; before deleting, do a dry run.
3. **Quality gate up front**: a book **passes the gate before it is uploaded**. A bad book that gets uploaded is worse than one that does not (it wastes device space, and you discover halfway through reading that it is incomplete).
4. **Rollback-able**: back up before changes (settings, plugins, books), and keep the SHA-256 and source links of official files.

---

## 1. Stage 0: Environment reconnaissance (mandatory)

```bash
# Is the device mounted + firmware version
mount | grep -i kindle
cat /Volumes/Kindle/system/version.txt          # expected: Kindle 5.16.2.1.1

# Is it already jailbroken (the search box ;log also works, but a script can verify)
ls -d /Volumes/Kindle/libkh /Volumes/Kindle/documents/JAILBROKEN.txt 2>/dev/null

# Space and update packages
df -m /Volumes/Kindle
ls /Volumes/Kindle/*.bin 2>/dev/null             # any update*.bin must be deleted first
```

Criterion: `version.txt` must be **5.16.2.1.1** (the final PW3 release). Different firmware versions require different jailbreak methods; **do not apply one across versions**.

---

## 2. Stage 1: Jailbreak (PW3 / 5.16.2.1.1 → WinterBreak2)

**Basis for the method mapping** (official guide data): in `kindlemodding.org/jailbreaks.json`, the first choice for PW3 + ≤5.16.3 is **WinterBreak2** (`registration: false`, no Amazon account required); the alternative is WinterBreak (registration required); SpiderCat/Sanctuary/AdBreak/SpringBreak/Nosebleed/Véra all **do not support PW3**.

### 2.1 Preparation (Mac side, scriptable)
1. **Full backup** of `documents/ system/ fonts/` → project `backup-<date>/` (compare file counts directory by directory).
2. **Fill the storage** (to prevent an OTA during the jailbreak): leave only **50–90 MB** free. `/mnt/us` is plain USB mass-storage mode, so the fill file can be written directly with `dd`:
   ```bash
   VOL=/Volumes/Kindle; mkdir -p "$VOL/fill_disk"; i=0
   while [ "$(df -m "$VOL" | awk 'NR==2{print $4}')" -gt 90 ]; do
     i=$((i+1)); dd if=/dev/zero of="$VOL/fill_disk/fill_$i.bin" bs=1m count=200 || break
   done
   ```
   Note: do not use an elaborate script with a "watchdog kill"; under `set -e` a failed `kill` causes a misjudgment that deletes blocks already written.
3. Place the payload `winterbreak2/dialoger.html` in the device **root directory**.

### 2.2 Key pitfall: GitHub Pages dependency
The official `dialoger.html` runs
`curl -L https://kindlemodding.org/jb.sh | sh`
and `kindlemodding.org` is hosted on **GitHub Pages (185.199.108-111.153)**; direct connections from mainland China often fail → `sh` receives empty content → **the symptom is "nothing happens when you tap"** (the download prompt appears but no dialog box).

**Solution: a local-execution version** (change only this one line; everything else matches the official version, and `jb.sh` stays the official original with its SHA-256 verified):

```html
source_command: "sh -c 'echo DIALOGER_EXECUTED > /mnt/us/JB_TRACE.txt; JB_HEADER=\"Winterbreak2 Jailbreak\" sh /mnt/us/jb.sh > /mnt/us/JB_LOG.txt 2>&1; echo EXIT=$? >> /mnt/us/JB_TRACE.txt'"
```
Just put `jb.sh` (8.7 MB, official original) at `/mnt/us/jb.sh`, and **GitHub is no longer a dependency**. Template: `assets/dialoger-local.html`.

### 2.3 On-device steps (can only be done manually on the device)
Turn off airplane mode and connect to Wi-Fi → open the **experimental browser** → visit `https://penguins184.xyz/wb2` → tap **Jailbreak** → confirm the download → wait for the log to scroll on screen → `Restarting Kindle` → automatic reboot.

### 2.4 Acceptance (three pieces of evidence)
| Evidence | Location | Expected |
|---|---|---|
| Jailbreak completion marker | `documents/JAILBROKEN.txt` | `You are jailbroken! (jb.sh v2.4.0) … Winterbreak2 Jailbreak` |
| Whether the exploit chain fired | `JB_TRACE.txt` | `DIALOGER_EXECUTED` |
| Jailbreak components | `libkh/bin/fbink` | Present (jb.sh installs it during the system patching phase) |

On failure, read `JB_LOG.txt` (jb.sh output): `DIALOGER_EXECUTED` present but no `JAILBROKEN.txt` → the script execution failed; neither present → the exploit chain never fired (check the payload directory/browser).

---

## 3. Stage 2: KOReader + SimpleUI

- The KOReader package must match the **corresponding platform**: PW3 (soft-float) uses `koreader-kindlepw2-v*.zip`; hard-float devices on 5.16.3+ need `koreader-kindlehf`.
- Unzip to the device root directory: `koreader/` + `extensions/koreader/`.
- **Launch method** (when there is no KUAL): place a scriptlet at `documents/KOReader.sh`
  ```sh
  #!/bin/sh
  # Name: KOReader
  mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
  cd /mnt/us/koreader || exit 1
  exec sh ./koreader.sh
  ```
  (`/mnt/us` may be mounted noexec, and KOReader executes `reader.lua` directly, so it fails without a remount.)
- SimpleUI: unzip `simpleui.koplugin.zip` → `koreader/plugins/simpleui.koplugin/` (the directory name must be exact). It depends on KOReader's built-in **CoverBrowser** plugin; requires KOReader ≥ v2026.03.

### 3.1 Common pitfall: empty library / books not visible
If `home_dir` in KOReader's `settings.reader.lua` is set to an empty directory (for example `/mnt/us/Books`), books in `documents/` are invisible too. Fix (KOReader must be closed first, otherwise it writes back and overwrites on exit):

```
["home_dir"]         = "/mnt/us/documents"
["lock_home_folder"] = false
["lastdir"]          = "/mnt/us/documents"
```
Back up `settings.reader.lua` before the change; afterward, use the "basic structure check" to confirm it is still a valid Lua table (`return { ... }`).

---

## 4. Stage 3: Wireless book-delivery chain (qiaomu-send2kindle)

| Item | Value (verified on this machine) |
|---|---|
| Skill location | `~/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle/` + `~/.claude/skills/qiaomu-send2kindle/` |
| Isolated runtime | `~/Library/Application Support/Qiaomu/Kindle/runtime/` (Python 3.12 + paramiko/keyring/filelock/psutil) |
| Device metadata | `~/Library/Application Support/Qiaomu/Kindle/devices.json` (0600) |
| Private key | **macOS Keychain only** (service `ai.qiaomu.kindlesync`, account = credential_id) |
| Mode | KOReader SSH, port **2222**; host key fingerprint pinned (anti-man-in-the-middle) |

### 4.1 First-time pairing (requires USB, and KOReader must be closed first)
```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle"
"$RT" "$SK/scripts/setup_runtime.py"                 # first time only
"$RT" "$SK/scripts/send_to_kindle.py" pair --usb '/Volumes/Kindle' --mode koreader
# on device: KOReader → Tools → SSH server, check to start it, keep it in the foreground
"$RT" "$SK/scripts/send_to_kindle.py" connect --host <device IP> --mode koreader --trust-new-device
```

### 4.2 Recovering from a wiped state directory (no re-pairing needed)
When the private key is still in the Keychain, only the metadata needs restoring: write `devices.json` (structure in `references/send2kindle.md`); the `credential_id` field must match the Keychain account, and `fingerprint` must use the previously pinned value.
Then reinstall the runtime (`setup_runtime.py`) and KindleUnpack (see 4.4); `status` should report `ok:true` and `credential_present:true`.

### 4.3 Prerequisites for delivery (all three at once)
1. The Kindle is awake (sleep cuts the network); 2. same Wi-Fi; 3. **KOReader is running** (SSH starts and stops with KOReader).
`discover` occasionally fails to find the device → `send` first tries a direct connection to the pinned host, which usually still succeeds.

### 4.4 Format strategy (local enhancement patch)
| Source format | Behavior | Receipt |
|---|---|---|
| `.epub` | Direct transfer | `converted:false` |
| `.azw3` (KF8) | KindleUnpack → EPUB | `converted:true`, `engine:kindleunpack-mobi8` |
| `.azw/.mobi/.prc` (MOBI7) | Unpack + repack EPUB according to the OPF | `converted:true`, `engine:kindleunpack-mobi7` |
| `--mode native` + EPUB | EPUB → AZW3 (native reader) | `converted:true` |

Converter: **KindleUnpack** (GPL, installed independently, not distributed with the skill)
`~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack/lib/kindleunpack.py`
Can be overridden with `QIAOMU_KINDLEUNPACK_DIR`. Patch details in `references/send2kindle.md`.

> Important fact: **KOReader does not support AZW3/KF8** (its format registry only has `azw/mobi/prc`). Books destined for KOReader are always EPUB.

---

### 4.5 Device filename policy (enabled by default)

Before upload, the on-device filename is decided by the **Douban book title** (user setting):

| Douban entry | Device filename |
|---|---|
| Chinese title (for example 「三体全集」) | Use the Chinese title `三体全集.epub` |
| English title (for example 「Sapiens」) | Use the English title `Sapiens.epub` |
| Not found on Douban / network unavailable | Fallback: EPUB metadata title → source filename |

```bash
send 书.epub                          # default --name-mode douban
send 书.epub --name-mode metadata     # use the EPUB metadata title
send 书.epub --name-mode source       # keep the source filename (old behavior)
```

Implementation: `name_policy.py` (multiple Douban queries → title → FAT32 legalization: strip `\ / : * ? " < > |`,
collapse whitespace, limit length, preserve the extension). Duplicate names get `(2)/(3)` appended automatically by the upload layer. The receipt gains
`name_source` (douban/metadata/source), `title`, `douban_url`, `renamed_from`.

---

## 5. Stage 4: Book-source quality gate (**core, mandatory**)

> Run the gate before delivery. Books judged **BLOCK** are not uploaded; **WARN** books need user confirmation; only **PASS** books are sent.

### 5.1 Four hard metrics

| # | Metric | How to check | Meaning of failure |
|---|---|---|---|
| 1 | **ISBN / publisher / edition can be matched** (checkable on Douban or the publisher's official website) | EPUB metadata `dc:identifier` (ISBN), `dc:publisher`, `dc:date`; manually compare title + author + edition on Douban/the publisher's website | Pirated compilation, version mismatch, impersonated book |
| 2 | **EPUB structure is valid** (`inspect` reports no errors) | `scripts/quality_check.py` (zip integrity, mimetype first, container.xml, OPF, spine, xhtml count) | Corrupted file / fake EPUB / failed conversion output |
| 3 | **File size is reasonable** (a multi-hundred-page book of a few dozen KB is basically an incomplete version) | Automatic: byte count vs. chapter count / whether there are images; then compare against common sense for the book's page count (for example, 300 pages of plain text is usually ≥300 KB) | Sample/preview version, truncated copy, plain-text placeholder |
| 4 | **No scripts / external-link redirects in the body** (conversion strips `script/style/iframe`) | Automatic scan of all xhtml/html: `<script>`, `<iframe>`, `on*=`, `javascript:`, external `href/src` | Hidden redirects/tracking/injection that carry you away from the body text while reading |

### 5.2 Automated detection
```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/quality_check.py "/absolute/path/book.epub" \
  --expect-title "书名" --expect-author "作者"
```
Outputs JSON: `verdict: pass|warn|block` + `pass/warn/fail` per item + details + a Douban search link (for manual verification of metric 1).

Decision rules (built into the script):
- Invalid structure / contains script, iframe, or javascript: → **block**
- Abnormal size (no images and <150 KB, or the title contains sample/excerpt/preview, or clearly smaller than the usual size for the same title) → **warn**
- Missing ISBN/publisher/date → **warn**
- External links present → **warn** (except in-body navigation links; if there are many, inspect manually)
- Everything passes → **pass**

### 5.2b Douban automatic verification (--douban, optional network access)

`scripts/douban_verify.py` searches for and fetches the Douban detail page, automatically comparing **title / author / publisher / publication year / ISBN**:

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/quality_check.py "/absolute/path/book.epub" --douban
"$RT" scripts/douban_verify.py --isbn 9787208178212
"$RT" scripts/douban_verify.py --title "战略与路径" --author "黄奇帆"
```

| Compared field | pass condition | Notes |
|---|---|---|
| Title | Main titles (the part before the colon) contain one another | Subtitle differences are not an error |
| Author | Any author name contains the other (ignoring prefixes such as 【美】) | Scanner-site watermarks (for example SoBooKs.cc) yield warn |
| Publisher | Contain one another | Publisher mergers/renames yield warn |
| Publication year | Same or within ≤1 year | Edition/reprint differences |
| ISBN | Present on both sides and exactly identical | Missing locally → warn (the Douban ISBN may be used as supplementary evidence) |

Mapping: a Douban **block is triggered only by a title conflict** → gate fail → the whole book is blocked; any ISBN / publication-year / publisher mismatch is always **warn** (different editions are very common); Douban placeholder ISBNs (such as `9787001xxxxxx`) and locally checksum-invalid ISBNs do not participate in the consistency decision.
warn → warn; pass → pass.
When Douban returns a login wall / bot protection, **degrade to warn** (prompting manual verification); a book is never wrongly rejected.
Request interval 1.5 seconds, browser UA, 15-second timeout, results cached for 7 days (`~/Library/Application Support/Qiaomu/Kindle/douban-cache.json`); only public pages are read.

**Backfilling ISBN** (to make metadata more standard so that later gate runs can pass directly):

```bash
"$RT" scripts/backfill_isbn.py "书.epub" --douban          # look up the ISBN on Douban and write it into the OPF
"$RT" scripts/backfill_isbn.py "书.epub" --isbn 9787...    # or specify it manually
"$RT" scripts/backfill_isbn.py "书.epub" --isbn 9787... --fix-language zh-CN   # also normalize the language
"$RT" scripts/backfill_isbn.py "书.epub" --douban --fill-metadata            # backfill ISBN+publisher+date (placeholder ISBNs skipped)
"$RT" scripts/backfill_isbn.py "书.epub" --dry-run         # only show what would be written
```

Only OPF metadata is changed (inserting a `urn:isbn:` identifier); the body text/images are untouched; on repack, `mimetype` is still first and uncompressed;
by default a `书.epub.orig` backup is left in the same directory, and the structure is automatically re-verified after writing.

### 5.3 Manual verification (the final arbiter for metric 1)
- Metric 1: use the Douban search link printed by the script to check whether **title / author / publisher / publication year / page count / ISBN** match the in-book metadata; any mismatch counts as untrustworthy (common cases: stitching different translations together, old-version content with a new-version cover).
- Write the conclusion into the delivery receipt (see 5.4) for later traceability.

### 5.4 The delivery receipt must include
`ok:true` · device path · byte count · SHA-256 (read-back verification) · `converted`/`engine` · quality-gate verdict (pass/warn + warning items).

---

## 6. Acceptance and cleanup

- Acceptance: `send` returns `ok:true` and `sha256` matches the source file (when converting, compare against the conversion output); an on-device `ls` shows the file; it opens in KOReader.
- Cleanup: for deleting/renaming books, prefer the exact-match scripts (see `assets/kindle-cleanup.py`), **`--dry-run` first**; the allowlist protects `KOReader.sh` (launcher), `disable_oobe.sh`, `JAILBROKEN.txt`, `My Clippings.txt`, `dictionaries`.
- The device-side `.sdr` sidecar name follows the book filename; when renaming, **rename the book and the `.sdr` together**, otherwise reading progress gets misaligned.

---

## 6.5 Optional enhancements: plugins / feeds / wallpapers / rollback

The following capabilities are merged from the existing kindle-modding-stack skill (details in the respective `ext-*.md`); enable them as needed:

| Capability | What it does | Reference | Key scripts |
|---|---|---|---|
| Plugin extensions | Advanced SimpleUI, **WeRead** plugin, SSH service | `references/ext-plugins-weread.md` | — |
| News RSS | Curation of the "Qiaomu Picks" channel, "original-text-first" patch, English sources | `references/ext-content-rss.md` | `scripts/apply-rss-curation.py` |
| Sleep wallpapers | Random famous-painting / text-card sleep screensaver | `references/ext-wallpapers.md` | `scripts/apply-wallpapers.py`, `scripts/gen-wallpapers.py` |
| Rollback and recovery | Per-item rollback, remove delivery credentials, restore native state | `references/ext-rollback.md` | — |
| Full-stack health check | Read-only inspection of device state | — | `scripts/verify-setup.sh` |
| Generic push | SFTP any file/directory to the device | — | `scripts/kindle-push.py` |

> 16 wallpaper assets ship with the skill (`assets/wallpapers/`); the WeRead plugin is third-party (AGPL) and is not bundled, nor does it log in on the user's behalf.

## 7. Troubleshooting quick reference

| Symptom | Cause / handling |
|---|---|
| Tapping the button during jailbreak does nothing | GitHub Pages cannot fetch jb.sh → use the local-execution dialoger (§2.2) |
| Library empty after jailbreak | `home_dir` points at the wrong directory (§3.1) |
| KOReader will not open | `/mnt/us` is noexec → the launcher does `mount,exec` first; or `reader.lua` is missing |
| AZW3 will not open in KOReader | KOReader does not support KF8 → convert to EPUB first (§4.4) |
| Cannot connect for delivery | KOReader not running / device asleep / Wi-Fi down; if `discover` fails, use `send` directly with the pinned host |
| Skill state directory lost | The Keychain private key is still there → rebuild the runtime + restore devices.json (§4.2) |
| System credentials locked | Unlock the Keychain; there is no plaintext fallback |
| Device clock wrong | After a factory reset the RTC can sit on an old date, which affects KOReader networking/certificates; correct it in settings |

---

## 8. Lineage, merge notes, and boundaries

- This skill is the mainline version of the **end-to-end pipeline + book-source quality gate**, and has absorbed all reusable content from the original kindle-modding-stack
  (plugins/WeRead, news RSS, sleep wallpapers, T1–T12 troubleshooting, rollback, licenses), kept in the form of `references/ext-*.md`, `assets/`, and `scripts/`.
- The original kindle-modding-stack skill is archived at project `archive/kindle-modding-stack-v1.0.0/` (together with the zip) and is no longer maintained separately.
- Division of labor with the delivery skill: `qiaomu-send2kindle` is responsible for "getting it there" (SSH/receipt/conversion); this skill is responsible for "what to send, whether it is worth sending, and how to accept it afterward".
- When in conflict, **evidence** wins: `JAILBROKEN.txt`, the SSH fingerprint, the `ok:true` receipt, the quality verdict.
- What this skill does not do: log in to third-party accounts on the user's behalf, bypass DRM, or delete user data without confirmation.

---

## 9. Reference files

| File | Content |
|---|---|
| `references/jailbreak-pw3.md` | Jailbreak mainline: method mapping, jb.sh internals, acceptance evidence, rollback |
| `references/koreader-simpleui.md` | KOReader/SimpleUI installation, launcher mechanics, the home_dir trap |
| `references/send2kindle.md` | Delivery chain: pairing, devices.json restoration, local patches, converter |
| `references/book-quality.md` | **Four hard metrics** decision criteria, Douban checklists, counterexamples |
| `references/ext-jailbreak.md` | Jailbreak extension details (official flow vs. variants) |
| `references/ext-koreader.md` | KOReader extension details (package selection/launcher/path fixes) |
| `references/ext-plugins-weread.md` | Plugins: advanced SimpleUI, WeRead, SSH |
| `references/ext-send2kindle.md` | Delivery extension details (architecture, installation, conversion) |
| `references/ext-content-rss.md` | News RSS: channel curation, original-text-first patch, English sources |
| `references/ext-wallpapers.md` | Sleep wallpapers: mechanism, specs, asset sources |
| `references/ext-troubleshooting.md` | T1–T12 real-device troubleshooting manual (more complete than §7) |
| `references/ext-rollback.md` | Rollback and recovery (per-item/credentials/native) |
| `references/ext-credits.md` | Third-party components, licenses, disclaimers |
| `scripts/quality_check.py` | Book-source quality check (metadata/Douban, structure, size, body safety) |
| `scripts/douban_verify.py` | Douban automatic verification (multi-query fallback: ISBN→main title→full title→title+author) |
| `scripts/backfill_isbn.py` | Backfill OPF metadata: ISBN / publisher / date / language (--douban, --isbn, --fill-metadata, --fix-language; automatic backup + re-verification) |
| `scripts/apply-rss-curation.py` | Apply the "Qiaomu Picks" source catalog to the device |
| `scripts/apply-wallpapers.py` | Push the wallpaper pack and configure the KOReader screensaver |
| `scripts/gen-wallpapers.py` | Generate wallpaper assets |
| `scripts/kindle-push.py` | Generic SFTP push (files/directories) |
| `scripts/verify-setup.sh` | Full-stack read-only health check |
| `assets/dialoger-local.html` | Local-execution jailbreak payload template |
| `assets/kindle-prepare-local.sh` | Fill the disk + place the payload + verify |
| `assets/kindle-ssh.py` | Device command execution (troubleshooting) |
| `assets/kindle-cleanup.py` | Exact on-device cleanup (dry-run/apply) |
| `assets/KOReader.sh` | Reference version of the tappable launcher |
| `assets/feed_config.lua`, `assets/qiaomu_sources.curated.json` | News source config and curated catalog |
| `assets/wallpapers/` | 16 sleep wallpaper assets |
