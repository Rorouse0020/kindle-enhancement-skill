# 07 · Troubleshooting Guide (T1–T12, all from real-device experience)

> How to use: look up the number by **symptom**; each entry covers "symptom → root cause → diagnostic command → fix".
> Common prerequisite variable: `VOL=/Volumes/Kindle`; SSH commands use `ssh root@<kindle-ip> -p 2222` (only available while KOReader is running).

---

## T1 ⚠️ Wrong clock → all HTTPS failures (the nastiest one on this device)

**Symptom**
- News shows "update failed" and the list is empty
- `;kpm install` fails; some download/network features misbehave
- curl reports: `SSL certificate problem: certificate is not yet valid`

**Root cause**
The device clock is stuck at the time of the factory reset (2023-09-18 on this device), so certificates issued in 2025/2026 appear "not yet valid" to the device.
**This has nothing to do with certificates, DNS, or the feed source** — the time is simply wrong.

**Diagnosis**
```bash
ssh root@<ip> -p 2222 'date'                                  # if the year is wrong, this is it
ssh root@<ip> -p 2222 "curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://www.baidu.com"   # 000 = all HTTPS fails
```

**Fix (after jailbreak)**
```bash
NOW=$(date '+%Y-%m-%d %H:%M:%S')          # current time on the computer
ssh root@<ip> -p 2222 "date -s '$NOW' && hwclock -w && date"
# verify: baidu / rss.qiaomu.ai should both return 200
```
**Fix (not jailbroken)**: Settings → Device Options → Device Time → Set Manually.

**Prevention**: check `date` first after every device reset or battery replacement. It has been written to the RTC (`hwclock -w`), so a normal reboot preserves it.

---

## T2 Tapping Jailbreak does nothing at all (GitHub Pages can't fetch jb.sh)

**Symptom**: a download prompt appears → then nothing: no dialog, no log, no reboot.

**Root cause**: the official `dialoger.html` runs
`curl -L https://kindlemodding.org/jb.sh | sh`, and that domain is **GitHub Pages**;
a direct connection from the device fails → `sh` receives empty content → it exits silently.

**Diagnosis** (on the device)
```bash
ssh root@<ip> -p 2222 "curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://kindlemodding.org/jb.sh"
# 000 / 403 / timeout means this is it; also /mnt/us/JB_TRACE.txt will not be created
```

**Fix**: switch to the **local-execution variant** (`references/ext-jailbreak.md` §4)
```bash
bash scripts/kindle-prepare-local.sh /Volumes/Kindle 90
# it places jb.sh (the official original, verify sha256) + assets/dialoger-local.html
```
Then retry the page flow; on success you will get `JB_TRACE.txt` (`DIALOGER_EXECUTED`) and `JB_LOG.txt`.

---

## T3 The jailbreak log stops halfway

**Diagnosis**: plug in USB and read the end of `/mnt/us/JB_LOG.txt`.
| Log clue | Meaning | Action |
|---|---|---|
| `Could not find chattr command` | Firmware lacks chattr | Very rare; use a different jailbreak method or upgrade to supported firmware |
| `not enough space left in varlocal` | `/var/local` is out of space | Clean up extra files on the device and retry |
| `Failed to setup sh_integration` | appreg registration failed | Reboot and retry; if it still fails, see the local-execution log in T2 |

**General**: reboot the device → go through it again (fill disk → place payload → trigger). JB is idempotent.

---

## T4 KOReader library is blank / books in documents are not visible

**Root cause**: `home_dir` points to an empty directory (`/mnt/us/Books` on this device) and `lock_home_folder=true`.
**Diagnosis/fix**: `references/ext-koreader.md` §5 (set `home_dir=/mnt/us/documents`, `lock_home_folder=false`).
> This also explains "book transfer succeeded but the bookshelf doesn't show it".

---

## T5 AZW3 won't open: "format not supported"

**Root cause**: KOReader's format registry only has `azw`/`mobi`/`prc`, **there is no `azw3`** (it cannot parse KF8). The file is not corrupt, and it's not DRM.
**Verify**:
```bash
VOL=/Volumes/Kindle
grep -nE 'addProvider\("(azw|azw3|mobi)' "$VOL/koreader/frontend/document/credocument.lua" | head
```
**Fix**: convert to EPUB (`references/ext-send2kindle.md` §6); or use the native reader for AZW3 (supported natively).

---

## T6 DNS returns 198.18.x.x (fake-IP), causing network failures

**Symptom**: `nslookup rss.qiaomu.ai` → something like `198.18.7.7`; all device curl requests return 000.

**Root cause**: the router (e.g., ImmortalWrt + a proxy plugin) hijacks DNS with **fake-IP**; the proxy client on this machine (Mac) can handle it, but **the Kindle has no proxy client**, so it cannot connect.
> However, if the router itself is doing transparent proxying, fake-IP can still work — **fix the T1 clock first before judging**; on this device it was a clock problem, not DNS.

**Diagnosis**
```bash
ssh root@<ip> -p 2222 "nslookup rss.qiaomu.ai"                       # 198.18.x.x = fake-ip
ssh root@<ip> -p 2222 "curl -sS -m 10 --resolve rss.qiaomu.ai:443:<real-IP> -o /dev/null -w '%{http_code}\n' https://rss.qiaomu.ai/api/entries?limit=1"
```
You can get the real IP from a public DoH:
```bash
curl -s 'https://223.5.5.5/resolve?name=rss.qiaomu.ai&type=A'
```

**Fix (choose one)**
1. Router: add `+.qiaomu.ai` to the fake-IP filter / switch to redir-host;
2. Route the device through the proxy (set a rule by device IP on the router);
3. Temporary verification: `--resolve` directly to the real IP (Cloudflare IPs change, so not suitable long-term).

---

## T7 USB is plugged in but the computer doesn't recognize it (no mount point)

**Root cause**: **KOReader is running** → it sends `SIGSTOP volumd`, so the Kindle does not appear as a USB drive.
**Check**: `nc -z -G 2 -w 2 <ip> 2222` returning success = KOReader is running.
**Fix**: KOReader → Menu → Exit → Exit KOReader, return to the native interface, and USB mounts automatically.
> Likewise: editing `settings.reader.lua` while KOReader is running gets overwritten when it exits — **you must exit KOReader before changing settings**.

---

## T8 rsync backup hangs / "file truncated while reading"

**Symptom**: `rsync -a` makes no progress for a long time; or a large azw3 reports truncated.
**Root cause**: occasional read stalls on the Kindle FAT volume (especially long Chinese filenames and large files).
**Fix**: switch to **file-by-file + watchdog**:
```bash
SRC=/Volumes/Kindle/system; DST=/path/backup/system; mkdir -p "$DST"
while IFS= read -r -d '' f; do
  rel="${f#$SRC/}"; mkdir -p "$DST/$(dirname "$rel")"
  ( cp -p "$f" "$DST/$rel" & p=$!; ( sleep 10; kill -9 $p 2>/dev/null ) & w=$!
    wait $p 2>/dev/null; r=$?; kill $w 2>/dev/null; exit $r ) || echo "skipped: $rel"
done < <(find "$SRC" -print0)
```
After backing up you must **compare file counts** (source vs. backup, for each top-level directory).

---

## T9 Launcher does nothing when tapped / KOReader exits immediately on start

**Root cause**: `/mnt/us` may be **noexec**, so `reader.lua` cannot execute.
**Fix**: remount first in the launcher:
```sh
mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
cd /mnt/us/koreader && exec sh ./koreader.sh
```
(see `assets/KOReader.sh`)

---

## T10 News "update failed" / empty list (not a T1 case)

In order:
1. **T1 clock** (most common).
2. Are the patch and config present: `grep -c 'local patch' .../features/sui_news.lua` should be 2;
   do `ls .../news/feed_config.lua` and `data/qiaomu_sources.json` parse (`python3 -m json.tool`).
3. Test the endpoint directly on the device:
   ```bash
   ssh root@<ip> -p 2222 "curl -sS -m 15 -H 'X-Rss-List: reader-v1' -o /tmp/n.json -w '%{http_code}\n' 'https://rss.qiaomu.ai/api/entries?limit=10'"
   ```
   200 → the service is fine, the problem is local settings; 000 → check T1 / T6.
4. Restart KOReader (plugins and config load at startup).

---

## T11 WeRead plugin doesn't appear / login fails

| Symptom | Action |
|---|---|
| No "WeRead" in the tools menu | KOReader < 2026.03; or KOReader wasn't restarted; or the directory name isn't `weread.koplugin` |
| QR code login fails | "WeRead Skill" not enabled on the phone / no API Key generated; or the account is flagged by risk control |
| No entry in the SimpleUI bottom bar after login | The bottom bar is full → add it manually in SimpleUI's shortcut actions settings |

---

## T12 Sleep wallpaper doesn't take effect

| Symptom | Check |
|---|---|
| Sleep still shows "going to sleep" | Are you sleeping **inside KOReader**? (only effective there) |
| Shows the KOReader logo | `screensaver_dir` is empty/wrong path; or the directory has no image format KOReader recognizes |
| Settings get reset | KOReader was running when you changed settings (T7), so it was overwritten → exit first, then change |
| Image is very dark / ghosting | Image brightness < 100 → brighten it (`references/ext-wallpapers.md` §2) |

---

## General troubleshooting order (memorize this)

```
1) Is the clock right?          date
2) Is the network up?           curl an HTTPS site
3) Are the files there?         ls / cat
4) Is the version right?        git-rev / _meta.lua
5) Are plugins/settings loaded? restart KOReader and retry
6) What do the logs say?        end of koreader/crash.log, JB_LOG.txt
```
