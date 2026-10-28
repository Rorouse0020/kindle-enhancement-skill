# 01 · Jailbreak (WinterBreak2, including a local-execution variant for when GitHub is blocked)

> Goal: let the Kindle run third-party code (root shell, package manager) and automatically block OTA.
> Outputs: `documents/JAILBROKEN.txt` + `/mnt/us/libkh/bin/fbink` + `/var/local/jailbreak.txt`
> Estimated: 20–30 minutes (including 5–10 minutes to fill the disk)

---

## 1. Choose the right method (decide first, don't guess)

### 1.1 Conclusion for the PW3 / 5.16.2.1.1

| Method | Covered firmware | Requires an Amazon account registration | For this device |
|---|---|---|---|
| **WinterBreak2** | 5.6.1.1 – 5.16.3 (also accepts 5.16.5) | ❌ Not required | ✅ **First choice** |
| WinterBreak (original) | 5.6.1.1 – 5.18.0.2 | ✅ Required | Fallback (when WB2 fails) |
| SpiderCat / Sanctuary / Noodle / SpringBreak / AdBreak / Véra | — | — | ❌ The model list doesn't include the PW3 |
| Popcorn PW3 | — | — | ⚠️ Requires opening the device and shorting pins (hardware jailbreak), last resort |

> Why the PW3 firmware ceiling is 5.16.2.1.1: Amazon never published a 5.16.3+ package for the PW3 (`s3.amazonaws.com/firmwaredownloads/update_kindle_all_new_paperwhite_5.16.3.bin` returns 403, while 5.16.2.1.1 returns 200).

### 1.2 How to judge other models

```bash
curl -s https://kindlemodding.org/jailbreaks.json   # method → models/firmwares ranges
curl -s https://kindlemodding.org/models.json       # serial-number prefix → model
```
Rule: `model ∈ jb.models` and the firmware falls within `[min,max]` (or `outliers.accepted`, and is not in `denied`);
the **first match** in file order is the official recommendation; `registration:true` means **the device is required to be registered**.

---

## 2. Preparation

| Item | Requirement |
|---|---|
| Computer | macOS/Linux + `curl`, `unzip` |
| Cable | A USB cable capable of data transfer |
| Device | **Unlocked and KOReader exited** (KOReader blocks USB mass-storage mounting) |
| Network | The device can reach Wi-Fi (the browser is needed during the jailbreak) |
| Required action | The Phase 0 backup + clock check (`date` year must be correct, otherwise all HTTPS fails) |

Download the official payload (what is bundled in this package is v1.1.0 from 2026-10-26):
```bash
cd ~/Downloads && mkdir -p kindle-jb && cd kindle-jb
curl -L -o wb2.zip https://github.com/KindleModding/Winterbreak2/releases/latest/download/wb2.zip
unzip -l wb2.zip            # should show winterbreak2/dialoger.html
shasum -a 256 wb2.zip       # record the hash so others can verify it
```

---

## 3. Official procedure (try this first)

### 3.1 Fill up storage (to prevent OTA from interrupting the jailbreak)

Principle: **squeeze free space down to 50–90 MB** so the update package can't download.

```bash
VOL=/Volumes/Kindle
# Turn on airplane mode first; delete any downloaded update packages
rm -f "$VOL"/update*.bin "$VOL"/update.bin.tmp.partial

# Option A: official script (the PW3 is in normal USB mass-storage mode, works on macOS)
cp ~/Downloads/kindle-jb/../Filler.sh "$VOL"/ 2>/dev/null || true
cd "$VOL" && bash Filler.sh        # choose Fill, leave 50/100MB as the target

# Option B: manual dd (equivalent, more deterministic)
VOL=/Volumes/Kindle; mkdir -p "$VOL/fill_disk"; i=0
while [ "$(df -m "$VOL" | awk 'NR==2{print $4}')" -gt 90 ]; do
  i=$((i+1)); dd if=/dev/zero of="$VOL/fill_disk/fill_$i.bin" bs=1m count=200 2>/dev/null || { rm -f "$VOL/fill_disk/fill_$i.bin"; break; }
done
df -m "$VOL"
```

> ⚠️ On macOS the official `Filler.sh` occasionally has a "watchdog kills an already-successful block" issue, causing the loop to end early;
> the dd loop above is more reliable (measured write speed ~9.4 MB/s, about 5–6 minutes for 3 GB).

### 3.2 Place the payload and trigger it

```bash
unzip -o ~/Downloads/kindle-jb/wb2.zip -d "$VOL"     # winterbreak2/ appears in the root directory
ls -d "$VOL/winterbreak2"                            # must exist
dot_clean "$VOL" 2>/dev/null || true                  # clear macOS metadata residue
diskutil eject "$VOL"                                # safe eject on macOS
```

On the device:
1. Connect to Wi-Fi (such that web pages actually open).
2. Open the **Experimental Browser** (Menu → Experimental Browser; or Settings → Device Options → Advanced Options).
3. Visit **`https://penguins184.xyz/wb2`** → tap **Jailbreak** → if a download prompt appears, **confirm the download**.
4. If nothing happens for 10–30 seconds: press Home to return to the home screen and wait (the exploit chain's dialog is rendered on the home screen / download notification layer).

### 3.3 Expected behavior

The screen starts logging (`Stopping OTA`, `Installing libkh binaries`…) → `Restarting Kindle` appears → automatic reboot.
After the reboot a **JAILBROKEN** entry appears in the library.

---

## 4. ⚠️ Local-execution variant (the key workaround when GitHub Pages is blocked)

### 4.1 Symptoms and root cause

**Symptom**: tap Jailbreak → a download prompt appears → afterwards **nothing at all**, no logs, no dialog, no reboot.

**Root cause** (confirmable by reading the official payload): `winterbreak2/dialoger.html` executes
```html
source_command: "sh -c 'curl -L https://kindlemodding.org/jb.sh | JB_HEADER=\"Winterbreak2 Jailbreak\" sh'"
```
And `kindlemodding.org` is hosted on **GitHub Pages (185.199.108-111.153)**. When the device can't pull it directly,
`sh` receives empty content → exits silently → presents as "tapped it and nothing happened".

### 4.2 Solution

Keep the original official `jb.sh` (**the hash must be verified**), and only change "download from URL" to "execute a local file on the device":

```bash
cd ~/Downloads/kindle-jb
curl -L -o jb.sh https://kindlemodding.org/jb.sh
shasum -a 256 jb.sh          # measured on this machine: cfe16df16effaa3be04dcddc63b542db57b6146820936d4098f8326d58fbbc02 (8,691,170 B, v2.4.0)
```

Then place this package's `assets/dialoger-local.html` as the device's `winterbreak2/dialoger.html`, and put `jb.sh` in the root directory:
```bash
VOL=/Volumes/Kindle
cp assets/dialoger-local.html "$VOL/winterbreak2/dialoger.html"
cp ~/Downloads/kindle-jb/jb.sh "$VOL/jb.sh"
```
Or do it all at once with the script (including filling the disk):
```bash
bash scripts/kindle-prepare-local.sh /Volumes/Kindle 90
```

The local-execution version's command is equivalent to:
```
sh -c 'echo DIALOGER_EXECUTED > /mnt/us/JB_TRACE.txt;
       JB_HEADER="Winterbreak2 Jailbreak" sh /mnt/us/jb.sh > /mnt/us/JB_LOG.txt 2>&1;
       echo EXIT=$? >> /mnt/us/JB_TRACE.txt'
```
Here `JB_TRACE.txt` / `JB_LOG.txt` are **diagnostic files**: when it fails, plug in USB and you can see which step it got stuck at.

### 4.3 Why no registration is needed and it doesn't depend on the network

- In WB2's official wizard data, `registration:false`; the page itself only triggers the exploit chain, and the script runs entirely on the device.
- The only required network access is **opening the `penguins184.xyz/wb2` page** (Cloudflare). If even that page won't open, switch networks (phone hotspot) and retry.

---

## 5. Verification (all three must pass)

```bash
VOL=/Volumes/Kindle
cat "$VOL/documents/JAILBROKEN.txt"
# Expected:
# You are jailbroken!
# (jb.sh v2.4.0)
# https://kindlemodding.org
# https://hackerdude.tech
#
# Winterbreak2 Jailbreak

ls -l "$VOL/libkh/bin/fbink"        # expected to exist (about 1.38 MB)
cat "$VOL/JB_TRACE.txt"             # local-execution version: DIALOGER_EXECUTED + EXIT=0
```
Then confirm on the device: type `;log` in the search box and press Enter; if text pops up = jailbroken.

---

## 6. Post-jailbreak cleanup

```bash
VOL=/Volumes/Kindle
df -m "$VOL"
rm -rf "$VOL/fill_disk"                    # reclaim space (delete only after confirming OTA is blocked)
rm -f "$VOL"/update*.bin                   # remove any update packages
ls -A "$VOL/documents" | head              # place disable_oobe.sh (required for unregistered devices)
```
- `disable_oobe.sh` (official scriptlet, see `assets/` or `https://kindlemodding.org/jailbreaking/disable_oobe.sh`):
  place it in `documents/`, tap it once in the library → it deletes the OOBE flag and reboots; after that, reboots no longer return to initial setup.
- Keep `jb.sh` (8.7 MB): it is used by the OTA update/reset recovery flow; if deleted, it can be downloaded again.

---

## 7. Failure branches

| Symptom | Where to look |
|---|---|
| Tapping Jailbreak does nothing at all | §4 of this document (local-execution variant) |
| Logs appear but it stalls midway | `references/ext-troubleshooting.md` T2, T3 |
| The browser can't open the page | T5 (network/DNS) |
| Stuck at `Update Failed` | `references/ext-rollback.md` §3 |
| No JAILBROKEN after reboot | Run it again; if it's still absent, check the end of `JB_LOG.txt` |
