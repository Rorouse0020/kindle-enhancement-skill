# 03 · KOReader plugins: SimpleUI / WeRead / SSH

> Goal: a phone-like home screen (SimpleUI), a Chinese book source (WeRead), and remote access (SSH).
> Prerequisite: `references/ext-koreader.md` completed and KOReader launches normally.
> General rule: the plugin directory name must be exactly **`<name>.koplugin`**, and **KOReader must be restarted** after installation for it to load.

---

## 1. SimpleUI (phone-like home screen: tiled bookshelf / news / AI text selection)

### 1.1 Version requirements

- KOReader **≥ v2026.03** (v2026.07.1 on this machine ✅)
- Depends on KOReader's built-in **CoverBrowser** plugin (enabled by default; re-enable it if turned off)

### 1.2 Download and verify (be sure to use the Release package, not the Source code zip)

```bash
cd ~/Downloads && mkdir -p simpleui && cd simpleui
TAG=v3.0.0-qiaomu.16      # subject to the latest on the Releases page
BASE=https://github.com/joeseesun/qiaomu-simpleui/releases/download/$TAG
curl -L -O $BASE/simpleui.koplugin.zip
curl -L -O $BASE/SHA256SUMS
shasum -a 256 -c SHA256SUMS        # expected: simpleui.koplugin.zip: OK
```
> Measured on this machine: `simpleui.koplugin.zip` = 2,685,672 B, sha256 `4d7b5329c86bbcdab29662dc6de32e52beca34e453c8e79723fc65871fbd1790`.

### 1.3 Installation

```bash
VOL=/Volumes/Kindle
mkdir -p "$VOL/koreader/plugins"
# Back up the old version first (if any)
[ -d "$VOL/koreader/plugins/simpleui.koplugin" ] && \
  mv "$VOL/koreader/plugins/simpleui.koplugin" "$VOL/koreader/plugins/simpleui.koplugin.bak-$(date +%Y%m%d-%H%M%S)"
unzip -q -o simpleui.koplugin.zip -d "$VOL/koreader/plugins"
ls -d "$VOL/koreader/plugins/simpleui.koplugin"                  # the directory name must match exactly
find "$VOL/koreader/plugins/simpleui.koplugin" -type f | wc -l   # 673 on this machine
grep -E 'version' "$VOL/koreader/plugins/simpleui.koplugin/_meta.lua"   # 3.0.0-qiaomu.16
```

### 1.4 Usage

Restart KOReader → the home screen becomes SimpleUI. Recommended settings:
- Settings → Home → Behavior → enable "Start with home screen"
- Add the "Tiled library" module to the home page (shows covers across subfolders)
- Long-press a file to "Hide from home and library" (display only)

AI features (optional): Tools → **Qiaomu AI → Configure with phone** → scan the code and enter the API Key (stored in `/var/local/qiaomu/ai.json`, not visible over USB).

---

## 2. WeRead plugin (Chinese books, reading within a legal subscription)

### 2.1 Notes and risks (read first)

- A third-party open-source client (author finlater) that reads books from **your own account** via the official WeRead API.
- The author states: there may be **account risk-control** risks, use at your own risk; **QR-code login must be performed by you personally**, and the API Key must not be shared externally.
- Relationship with SimpleUI: with it installed, SimpleUI automatically registers a "WeRead" shortcut entry.

### 2.2 Download and verify

```bash
cd ~/Downloads && mkdir -p weread && cd weread
TAG=v1.6.0
BASE=https://github.com/finlater/weread.koplugin/releases/download/$TAG
curl -L -O $BASE/weread.koplugin-$TAG.zip
curl -L -O $BASE/weread.koplugin-$TAG.zip.sha256
shasum -a 256 -c weread.koplugin-$TAG.zip.sha256     # expect OK
```
> Measured on this machine: `weread.koplugin-v1.6.0.zip` = 910,252 B, sha256 `647abca30fe7638d67c5c24e483409acdedaa758194f177863d1385365258d51`.

### 2.3 Installation

```bash
VOL=/Volumes/Kindle
unzip -q -o weread.koplugin-v1.6.0.zip -d "$VOL/koreader/plugins"
ls -d "$VOL/koreader/plugins/weread.koplugin"
find "$VOL/koreader/plugins/weread.koplugin" -type f | wc -l   # 91 on this machine
grep -E 'version' "$VOL/koreader/plugins/weread.koplugin/_meta.lua"   # 1.6.0
```

### 2.4 Login (3 steps, performed by you)

1. Phone **WeRead App → Me → Settings → WeRead Skill → Get API Key** (confirm it has been generated).
2. Device KOReader → **Tools → WeRead → WeChat QR-code login**.
3. Scan the QR code with WeChat + confirm on the phone; if the phone shows a **four-digit verification code**, enter it in KOReader.

After login: WeRead → Bookshelf → select a book → download chapter/full book → read it with KOReader (progress, reading time, and highlights can sync).
To update the plugin: WeRead → Settings → Update management.

---

## 3. SSH plugin (built into KOReader; the basis for book transfer and remote troubleshooting)

KOReader ships with `plugins/SSH.koplugin` + a patched `dropbear`.

| Item | Value |
|---|---|
| Port | Default **2222** (settings key `SSH_port`) |
| Public key file | `/mnt/us/koreader/settings/SSH/authorized_keys` |
| Autostart | `SSH_autostart = true` (written when pairing with send2kindle) |
| Key-only login | `SSH_key_only_auth = true` |
| How to start | KOReader → Tools → SSH server (check it); or autostart along with KOReader |
| Lifecycle | **Stops as soon as KOReader exits**; also unreachable while the device sleeps or is offline |

Verify (from the computer side):
```bash
nc -z -G 2 -w 2 <kindle-ip> 2222 && echo "SSH 在线"
```

---

## 4. General verification

```bash
VOL=/Volumes/Kindle
ls "$VOL/koreader/plugins" | grep -E 'simpleui|weread|SSH'
grep -h 'version' "$VOL/koreader/plugins"/{simpleui,weread}.koplugin/_meta.lua
```
After restarting KOReader on the device:
- Home screen = SimpleUI style
- The Tools menu shows "WeRead"
- Tools → SSH server can be checked

---

## 5. FAQ

| Symptom | Cause/Handling |
|---|---|
| Plugin doesn't appear | The directory name isn't `<name>.koplugin`, there's an extra nesting level, or KOReader wasn't restarted |
| SimpleUI errors/white screen | KOReader version < 2026.03; or CoverBrowser was turned off |
| The WeRead entry doesn't appear | The plugin wasn't loaded on restart; or the SimpleUI bottom bar is full (add it manually in the SimpleUI shortcut actions settings) |
| WeRead login fails | "WeRead Skill"/API Key not enabled on the phone; or account risk control |
| KOReader won't start after installing plugins | Move them to a `.bak` directory and eliminate them one by one (plugin conflicts); if necessary check `koreader/crash.log` |
