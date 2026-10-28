# 08 · Rollback and Recovery (choose the granularity you need)

> Principle: **restore OTA first, then reset**; every step can be rolled back on its own — don't tear everything down at once.

---

## 1. Quick Reference for Single-Item Rollback

| Change | Backup file (on device) | Rollback action |
|---|---|---|
| KOReader library path | `koreader/settings.reader.lua.bak-homefix-*` | Rename back to `settings.reader.lua` |
| Sleep screensaver | `koreader/settings.reader.lua.bak-wallpaper-*` | Same as above, plus `rm -rf /mnt/us/wallpapers` |
| News source catalog | `koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json.bak-rss-*` | Rename back to the original file |
| News "original text first" patch | `koreader/plugins/simpleui.koplugin/features/sui_news.lua.bak-original-*` | Rename back to the original file |
| SimpleUI plugin | `koreader/plugins/simpleui.koplugin.bak-*` | Delete the new directory, restore the backup directory |
| WeRead plugin | — | `rm -rf koreader/plugins/weread.koplugin` |
| send2kindle pairing (KOReader settings) | `koreader/settings.reader.lua.qiaomu-skill-backup-*` | Rename back + delete the corresponding line in `settings/SSH/authorized_keys` |
| Sleep/news as a whole | See above | You can also revert in the KOReader UI (Settings → Screen / Sleep screen) |

> All `.bak-*` files are **complete copies of the original file**; rollback = stop KOReader → rename → restart.

---

## 2. Remove send2kindle Credentials and Metadata

```bash
# Metadata
rm -f "$HOME/Library/Application Support/Qiaomu/Kindle/devices.json"
# Keychain entry (service ai.qiaomu.kindlesync, account is the credential_id)
security find-generic-password -s ai.qiaomu.kindlesync          # view
security delete-generic-password -s ai.qiaomu.kindlesync -a '<credential_id>'
# Runtime (optional)
rm -rf "$HOME/Library/Application Support/Qiaomu/Kindle/runtime"
```
Device-side public key: delete the line ending with `qiaomu-kindlesync` from `koreader/settings/SSH/authorized_keys`.

---

## 3. ⚠️ Fully Undo the Jailbreak (**order matters**)

**Wrong approach**: factory reset directly → stuck at `Update Failed` (because OTA is blocked and official firmware can't be installed).
**Correct order**:

```
① Restore OTA (mandatory)
   - Put ota.sh into /mnt/us/documents/ and tap it in the library (it will reboot)
   - Or KUAL → Rename OTA binaries → Restore
② Factory reset (Settings → Device Options → Reset → Reset to Factory Defaults)
③ Push the official firmware of the same version
   - Download the update_*.bin matching the device version (FW download table / FTVDB)
   - Put it in the root directory → Settings → Update Your Kindle
④ Done: the device returns to a clean, unjailbroken state (you can jailbreak again later)
```

Official recovery scriptlet: <https://kindlemodding.org/jailbreaking/ota.sh>
Firmware download table: <https://kindlemodding.org/firmware-and-flashing/downloading-updates.html>
FTVDB (look up packages by model and version): <https://ftvdb.com/kindle/firmware/>

---

## 4. How to Rescue a Device Already Stuck at `Update Failed`

1. Go to **FTVDB** and find the `.bin` for **your model + your current version** (or higher):
   `https://ftvdb.com/kindle/firmware/` (community naming differs from Amazon naming — mind the cross-reference table).
2. Put the `.bin` in the USB root directory (delete other `update*.bin` files first).
3. Eject the device → reboot → wait for it to install automatically.
4. Once installed it is in an unjailbroken state, and you can jailbreak again.

---

## 5. Data Recovery

```bash
# The backup is a copy of the entire visible storage; on restore, only user data is needed
VOL=/Volumes/Kindle; BK=/path/to/backup-YYYY-MM-DD
rsync -a --exclude '._*' --exclude '.DS_Store' "$BK/documents/" "$VOL/documents/"
rsync -a --exclude '._*' --exclude '.DS_Store' "$BK/fonts/"     "$VOL/fonts/"
# Books + reading progress are all in documents/ (the .sdr directory stores progress/annotations)
```
> Note: **deregistering the Amazon account wipes `documents/`** — back up before deregistering.

---

## 6. Post-Recovery Self-Check

```bash
bash scripts/verify-setup.sh /Volumes/Kindle
```
- Rolled back only one item: that item shows as missing/default, the rest remain green.
- Never jailbroken at all: a missing `JAILBROKEN.txt` is normal; skip the checks after Phase 2.
