# Wireless Delivery Pipeline Reference (qiaomu-send2kindle + Local Enhancements)

## 1. Structure

| Item | Location (local default) |
|---|---|
| Skill itself | `~/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle/` and `~/.claude/skills/qiaomu-send2kindle/` (the two copies should match) |
| Isolated runtime | `~/Library/Application Support/Qiaomu/Kindle/runtime/` (Python 3.10+; depends on paramiko/keyring/filelock/psutil) |
| Device metadata | `~/Library/Application Support/Qiaomu/Kindle/devices.json` (0600, not secret) |
| Converter | `~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack/lib/kindleunpack.py` (GPL, installed separately) |
| Private key | **macOS Keychain only**, service `ai.qiaomu.kindlesync`, account = `credential_id` |
| Transport | SSH/SFTP, KOReader mode port **2222**; host key fingerprint pinned |

## 2. Installation and Pairing

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle"

# Runtime (use the real-path Python, not a symlink pointing at uv, otherwise the venv's home is recorded wrongly)
"$RT" "$SK/scripts/setup_runtime.py"

# Pairing (the Kindle must be connected via USB and KOReader must be exited)
"$RT" "$SK/scripts/send_to_kindle.py" pair --usb '/Volumes/Kindle' --mode koreader
# Pairing writes koreader/settings/SSH/authorized_keys and sets SSH_port/SSH_autostart/SSH_key_only_auth
# The original settings.reader.lua is backed up as *.qiaomu-skill-backup-<ts>

# Open KOReader on the device (SSH starts automatically), then trust for the first time
"$RT" "$SK/scripts/send_to_kindle.py" connect --host <device IP> --mode koreader --trust-new-device
"$RT" "$SK/scripts/send_to_kindle.py" discover      # afterwards, find the device by its fixed identity
```

## 3. devices.json Structure (Restore by This When the State Directory Is Lost)

```json
{
  "version": 2,
  "default_mode": "koreader",
  "devices": {
    "<device-id>": {
      "credential_id": "<keychain account>",
      "profiles": {
        "koreader": {"host": "192.168.31.209", "port": 2222, "paired": true,
                     "pending_trust": false, "fingerprint": "<64 hex>"}
      }
    }
  },
  "active_device": "<device-id>"
}
```

**Restore key points**: as long as the private key corresponding to `credential_id` is still in the Keychain, there is no need to re-pair; after restoring the metadata, `status` should return
`ok:true, credential_present:true`. If the Keychain entry is also lost, the only option is to re-pair over USB (the old identity cannot be recovered).

## 4. Usage

````bash
"$RT" "$SK/scripts/send_to_kindle.py" status
"$RT" "$SK/scripts/send_to_kindle.py" inspect "/absolute/path/book.epub"   # metadata + structure validation (mandatory before sending)
"$RT" "$SK/scripts/send_to_kindle.py" send    "/absolute/path/book.epub"    # only counts as delivered if the receipt says ok:true
"$RT" "$SK/scripts/send_to_kindle.py" send    "/absolute/path/book.epub" --mode native   # native reader (EPUB→AZW3)
````

**Three prerequisites**: the Kindle is awake + on the same Wi-Fi + **KOReader is running** (SSH starts and stops with KOReader; exiting KOReader disconnects it).

## 5. Local Enhancement Patch (Automatic AZW3/MOBI → EPUB Conversion)

Upstream only does EPUB→AZW3 (native). This machine adds the **reverse conversion** in KOReader mode (KOReader does not support KF8/AZW3):

| Source format | Handling | Receipt |
|---|---|---|
| `.epub` | direct transfer | `converted:false` |
| `.azw3` | KindleUnpack → EPUB (takes `mobi8/*.epub`) | `converted:true`, `engine: kindleunpack-mobi8` |
| `.azw/.mobi/.prc` | KindleUnpack unpack → repack EPUB per the OPF | `converted:true`, `engine: kindleunpack-mobi7` |

Changes (see `LOCAL_PATCHES.md` in the skill for details; all carry the `[local patch]` marker):

1. New `scripts/epub_convert.py`: conversion + structure validation + source-file hash-unchanged validation; on any failure nothing is uploaded.
2. `scripts/kindle_convert.py`: `prepare()` gains a conversion branch for non-EPUB files in koreader mode.
3. `scripts/send_to_kindle.py`: `EXTENSIONS` gains `.prc`, MOBI header validation adds `.prc`, and `delivery_receipt()` supports validation of both conversion directions.

Measured: KF8 (2.2 MB→1.7 MB epub), MOBI7 (public-domain book 580 KB→362 KB epub), and the EPUB direct-transfer regression all returned `ok:true`.
DRM files are not converted, and no success is faked.

## 5.1 Device Filename (Douban Book Title)

`send` defaults to `--name-mode douban`: it calls `name_policy.py` to look up the Douban title as the device filename
(Chinese titles in Chinese, English titles in English); if Douban is unavailable it falls back to the EPUB metadata title, then to the source filename.
`--name-mode metadata|source` switches to the metadata title/source filename respectively. Duplicate names automatically get `(2)`.
Receipt fields: `name_source`, `title`, `douban_url`, `renamed_from`.

## 6. Security Boundaries

- The conversion output must be a valid EPUB (mimetype first, container.xml, OPF, ≥1 xhtml, zip not corrupted), otherwise it is not uploaded.
- If the source file changes during conversion → abort.
- If the host identity changes → stop authentication immediately (there is no "ignore fingerprint" switch).
- The private key is used only in process memory and never enters argv/logs/temp files; there is no plaintext fallback.
- `inspect` and `quality_check.py` are **two independent gates**: the former ensures "it can be sent", the latter ensures "it is worth sending".
