# 04 · Wi-Fi wireless book transfer (Qiaomu send2kindle + automatic format conversion)

> Goal: say "send this book to the Kindle" on the computer, and the book lands in the device's `/mnt/us/documents/`, with a SHA-256 read-back receipt.
> Supports: EPUB direct transfer; **AZW3 / AZW / MOBI / PRC automatically converted to EPUB** (local enhancement patch).
> Prerequisite: jailbreak complete + KOReader installed + device and computer on the same Wi-Fi.

---

## 1. Architecture overview

```
AI/terminal → send_to_kindle.py → cryptographic identity (private key in the system keychain)
        → SSH/SFTP (KOReader's dropbear, port 2222)
        → upload a temporary file → full read-back on the device → verify byte count + SHA-256 → rename to the final file
```
- Private key: **stored only in system credentials** (macOS Keychain, service `ai.qiaomu.kindlesync`), never written to disk and never logged.
- Device identity: `~/Library/Application Support/Qiaomu/Kindle/devices.json` (records the host fingerprint, prevents man-in-the-middle).
- Runtime: `~/Library/Application Support/Qiaomu/Kindle/runtime/` (isolated venv, doesn't modify the global Python).

---

## 2. Install the skill itself and the runtime

```bash
# 2.1 Get the code (either: official skills CLI or unpack directly)
npx skills add joeseesun/qiaomu-send2kindle        # if available
# or: git clone / unpack the tarball into any directory, e.g. ~/skills/qiaomu-send2kindle

cd ~/skills/qiaomu-send2kindle
python3 --version        # must be ≥ 3.10
python3 scripts/setup_runtime.py
# expected output: {"ok": true, "runtime": ".../runtime/bin/python3", "credential_store": "operating-system", ...}
```

### ⚠️ Pitfall: Python managed by uv/pyenv has `sys.base_prefix=/install` after creating a venv

**Symptom**: `runtime/bin/python3` immediately reports
`ModuleNotFoundError: No module named 'encodings'` / `Could not find platform independent libraries`.
**Root cause**: when uv's Python is invoked through a **symlink**, the venv's `pyvenv.cfg` records `home` as the directory containing the link,
causing base-prefix resolution to fail.
**Solution**: create the venv with the **real path** interpreter:
```bash
UV=$HOME/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/bin/python3.12
rm -rf "$HOME/Library/Application Support/Qiaomu/Kindle/runtime"
"$UV" scripts/setup_runtime.py
"$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3" -c "import paramiko,keyring,filelock,psutil;print('deps ok')"
```

---

## 3. USB pairing (once)

Prerequisite: **exit KOReader** (KOReader doesn't mount USB mass storage while running), connect USB → mount succeeds.

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/send_to_kindle.py pair --usb '/Volumes/Kindle' --mode koreader
# expected: {"ok": true, "paired": true, "device": "kindle-xxxxxxxx", "mode": "koreader",
#        "port": 2222, "host_trust_pending": true}
```
What it does:
1. Generates an ECDSA key pair and writes the private key to the system keychain;
2. Appends the public key to `koreader/settings/SSH/authorized_keys` (**preserving** the existing content);
3. Writes into `koreader/settings.reader.lua`
   `SSH_port="2222"`, `SSH_key_only_auth=true`, `SSH_autostart=true` (**backing up** the original file first as `*.qiaomu-skill-backup-*`).

Verify:
```bash
VOL=/Volumes/Kindle
cat "$VOL/koreader/settings/SSH/authorized_keys"      # one line: ecdsa-sha2-nistp256 ... qiaomu-kindlesync
grep -E 'SSH_(port|autostart|key_only_auth)' "$VOL/koreader/settings.reader.lua"
```

---

## 4. Establishing trust for the first time

1. Device: launch KOReader (SSH autostarts with it; Tools → SSH server confirms it's checked), keep KOReader open and Wi-Fi connected.
2. Computer: first find the device IP (the popup only shows for a few seconds; you can also scan the port):
   ```bash
   seq 1 254 | xargs -P 128 -I{} sh -c 'nc -z -G 1 -w 1 192.168.31.{} 2222 2>/dev/null && echo 192.168.31.{}'
   ```
3. Establish trust (first time only):
   ```bash
   "$RT" scripts/send_to_kindle.py connect --host <device-IP> --mode koreader --trust-new-device
   # expected: {"ok": true, "ready": true, "fingerprint": "<64-digit hex>"}
   ```
   After that the device identity is pinned, and `--trust-new-device` can no longer replace it (prevents man-in-the-middle).

---

## 5. Daily use

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/skills/qiaomu-send2kindle"

"$RT" "$SK/scripts/send_to_kindle.py" status                     # pairing/mode/credential status
"$RT" "$SK/scripts/send_to_kindle.py" discover --mode koreader    # automatically find the device by identity after the IP changes
"$RT" "$SK/scripts/send_to_kindle.py" inspect '/path/书.epub'     # check title/author/language first
"$RT" "$SK/scripts/send_to_kindle.py" send    '/path/书.epub'     # send (KOReader mode)
"$RT" "$SK/scripts/send_to_kindle.py" send    '/path/书.epub' --mode native   # for the native reader (auto-converts to AZW3)
```

**Delivery determination**: only `ok: true` counts as success; the `sha256` in the receipt must equal the source file (or the converted transfer file, in which case there is also `source_sha256`).
The book lands in `/mnt/us/documents/`, and **files with the same name are not overwritten**.

---

## 6. ⚠️ Format strategy and local patches (the core enhancement of this round)

### 6.1 Why patching is necessary

- KOReader's format registry only has `azw` / `mobi` / `prc`, **no `azw3`** (KF8 can't be parsed);
  transferring AZW3 directly to the device → "format not supported" when opening.
- The upstream skill only does "EPUB → AZW3" (for the native reader); there is no reverse direction.

### 6.2 Patch contents (three places + one new file)

| File | Change |
|---|---|
| `scripts/epub_convert.py` (new) | Uses **KindleUnpack** to convert AZW3/AZW/MOBI/PRC to EPUB; for KF8 it takes `mobi8/*.epub` directly; for MOBI7 it repackages with `book.html + Images + *.opf`; includes structural validation and validation that the source file hash is unchanged |
| `scripts/kindle_convert.py` | `prepare()` adds a branch: `mode != native` and the extension ∈ `KINDLE_FORMATS` → convert first |
| `scripts/send_to_kindle.py` | ① add `.prc` to `EXTENSIONS`; ② the MOBI magic-number check includes `.prc`; ③ `delivery_receipt()` allows `converted:true` + target `.epub` in koreader mode |
| `SKILL.md` (shipped with the skill) | Adds a "format strategy" section (so other agents can understand it) |

All changes are marked with `[local patch]` comments; replay them accordingly when upgrading upstream (see the `LOCAL_PATCHES.md` template in the skill directory).

### 6.3 Install the converter KindleUnpack (GPL, installed separately, not distributed with the skill)

```bash
DEST="$HOME/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack"
mkdir -p "$DEST"
curl -L https://codeload.github.com/kevinhendricks/KindleUnpack/tar.gz/HEAD | tar -xz -C "$DEST" --strip-components=1
ls "$DEST/lib/kindleunpack.py"        # must exist
# the location can be overridden with the environment variable: QIAOMU_KINDLEUNPACK_DIR
```

### 6.4 Behavior matrix

| What you send | Behavior | Key receipt fields |
|---|---|---|
| `.epub` | Direct transfer | `converted:false`, `sha256`=source file |
| `.azw3` (KF8) | KindleUnpack converts to EPUB | `converted:true`, `engine:"kindleunpack-mobi8"` |
| `.azw`/`.mobi`/`.prc` (MOBI7) | Unpack + repackage per OPF | `converted:true`, `engine:"kindleunpack-mobi7"` |
| `.pdf`/`.txt`/... | Direct transfer (natively supported by KOReader) | `converted:false` |
| `--mode native` + `.epub` | Convert locally to AZW3 | `converted:true`, target `.azw3` |

**Measured records** (this machine):
- KF8: `掌控工作.azw3` 2,266,201 B → EPUB 1,757,077 B;
- MOBI7: Gutenberg's *Pride and Prejudice* 580,884 B → EPUB 362,840 B;
- Regression: EPUB direct transfer 2,124 B, `converted:false`.

---

## 7. Troubleshooting

| Symptom | Root cause | Handling |
|---|---|---|
| `{"ok": false, "code": "local"}` | Restricted runtime environment: keychain inaccessible / application directory not writable (e.g., running in a container sandbox) | Run in a normal terminal; unlock the keychain; grant Python Full Disk Access |
| `discover` can't find the device | KOReader not open / SSH server not checked / different Wi-Fi | Open KOReader → Tools → SSH server; confirm the same subnet |
| `network` / `sftp` errors | Device asleep, IP changed, firewall | Wake the device; relocate with `discover`; confirm the router has no client isolation |
| `host-key` error | The device host key changed (device replaced/reinstalled) | Do **not** disable verification; re-pair over USB |
| `credential-missing` | The private key in the keychain is gone | Re-pair over USB (no replacement identity is generated automatically) |
| `converter-missing` | KindleUnpack isn't installed | See §6.3 |
| Conversion fails | The file has DRM | **Do not decrypt**; use the native reader instead or find a DRM-free version |
| Sent over but KOReader can't see it | KOReader `home_dir` is wrong | `references/ext-koreader.md` §5 |
| Receipt `scanPending` (native mode) | Native indexing not finished | Check the device first; don't blindly resend |
