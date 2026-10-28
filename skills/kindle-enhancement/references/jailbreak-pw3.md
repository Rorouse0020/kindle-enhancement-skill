# Jailbreak Reference: Kindle PW3 / Firmware 5.16.2.1.1 (WinterBreak2)

## 1. Method Mapping (Official Data)

Source: `https://kindlemodding.org/jailbreaks.json` + the filtering logic of `jailbreakFinder.js` (the model is in `models`, the firmware falls within the `min~max` range, `outliers` are exceptions).

Match results for **PW3 + 5.16.2.1.1** (in file order):

| Order | Method | Coverage | Requires registration |
|---|---|---|---|
| 1 | **WinterBreak2** | 5.6.1.1 – 5.16.3 | ❌ Not required |
| 2 | WinterBreak | 5.6.1.1 – 5.18.0.2 | ✅ Required |

Methods that do not support PW3: SpiderCat, Sanctuary, AdBreak, SpringBreak, Nosebleed, Véra.

## 2. Prerequisite Facts (Confirmed by Testing)

- The **final firmware for the PW3 is 5.16.2.1.1**: `update_kindle_all_new_paperwhite_5.16.2.1.1.bin` on AWS S3 returns 200, while 5.16.3/5.16.4/5.16.5 all return 403.
- Because hard-float only starts with **5.16.3**, the PW3 is forever **soft-float** → KOReader uses the `koreader-kindlepw2` package.
- The device can be jailbroken while **unregistered** (WB2 does not require an account); but OOBE must be bypassed (see §5).

## 3. Preparation Steps (Automatable on the Mac Side)

1. **Back up**: copy `documents/ system/ fonts/` in full to the project directory, and verify directory by directory that the file counts match.
2. **Fill up storage** (to prevent an OTA download during the jailbreak):
   ```bash
   VOL=/Volumes/Kindle; mkdir -p "$VOL/fill_disk"; i=0
   while [ "$(df -m "$VOL" | awk 'NR==2{print $4}')" -gt 90 ]; do
     i=$((i+1)); dd if=/dev/zero of="$VOL/fill_disk/fill_$i.bin" bs=1m count=200 || break
   done
   ```
   Target: leave **50–90 MB** free. The PW3 is in USB mass-storage mode (not MTP), so scripts/`dd` work directly.
   ⚠️ Do not write "a loop with a kill watchdog + `set -e`": if `kill` fails, the script misjudges and deletes blocks that were already written (this project has hit that).
3. **Place the payload**: put `winterbreak2/dialoger.html` in the device **root directory** (extract the contents of `wb2.zip`; `winterbreak2/` appears in the root).
4. Clear `update*.bin` / `update.bin.tmp.partial` from the root directory.

## 4. Exploit Chain and jb.sh (Understand It Before Troubleshooting)

```
Experimental Browser → https://penguins184.xyz/wb2
  → tap Jailbreak → /wb2p returns an attachment, with the script embedded in the Content-Disposition filename
  → com.lab126.pillow customDialog loads the device-local
    /mnt/us/winterbreak2/dialoger.html
  → dialoger uses nativeBridge(com.lab126.transfer, request_upload) to execute shell commands
  → official: curl -L https://kindlemodding.org/jb.sh | sh     ← GitHub Pages, often fails in China
  → local: sh /mnt/us/jb.sh                                     ← recommended
```

**Key actions of jb.sh v2.4.0**: stop the OTA service → unpack to `/tmp/kmc` → copy to `/var/local/kmc` →
symlink `/var/local/mkk/{su,gandalf}` → install `/mnt/us/libkh/bin/fbink` → delete the old hotfix →
register hotfix/emergency/sh_integration (appreg.db) → install the kindlet keystore → turn off ads →
system patches → write `documents/JAILBROKEN.txt` and `/var/local/jailbreak.txt` → `reboot`.

Platform detection: if `/lib/ld-linux-armhf.so.3` exists → kindlehf, otherwise **kindlepw2** (the PW3 is the latter).
No DRM, no network required; the script itself is 8.7 MB, and self-extraction relies on the device's built-in `base64/xz/tar`.

## 5. OOBE and Registration

- After a factory reset the device stays at initial setup, and **without registration there is no browser**.
- Official bypass (captive portal): connect to a public Wi-Fi that requires web authentication → in the authentication page's browser address bar enter `;demo` → when the demo mode prompt appears you **must tap NO** → tap Home to enter the system.
- Registration failure troubleshooting (measured): if the device region is "中文（中国）" it connects to the discontinued amazon.cn (now returns 503), and a US account will inevitably report "email or password incorrect"; switch to **English (United States)** and confirm the account country is United States.
- After jailbreaking you can run the official `disable_oobe.sh` (tap it in `documents/`) to permanently disable OOBE; otherwise you must redo the demo trick on every reboot.

## 6. Acceptance and Rollback

Acceptance evidence (all three required):

1. `documents/JAILBROKEN.txt` = `You are jailbroken! / (jb.sh v2.4.0) / … Winterbreak2 Jailbreak`
2. `JB_TRACE.txt` (only in the local-execution version) = `DIALOGER_EXECUTED`
3. `libkh/bin/fbink` exists

Rollback (completely uninstall the jailbreak): restore OTA (the `ota.sh` scriptlet) → factory reset → flash the **same-version** official firmware (put it in the root → Settings → Update Your Kindle).
⚠️ Do not factory reset while OTA is blocked; you will be stuck unable to update (requires FTVDB same-version firmware recovery).
