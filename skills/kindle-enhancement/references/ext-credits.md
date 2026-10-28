# 09 · Third-Party Components, Licenses, and Disclaimer

This package is **process documentation + glue scripts**, and contains no Kindle firmware or Amazon content.
The components below are published by their respective authors; please comply with their licenses. This package does not redistribute them (except for a small number of scripts/configs written by this package's author).

---

## 1. Component List

| Component | Author/Source | License | Role in this process |
|---|---|---|---|
| **WinterBreak2** (wb2.zip) | Scam.Net, Penguins184 / KindleModding | See its repository | Browser-triggered jailbreak payload |
| **jb.sh** (jailbreak script) | KindleModding | See kindlemodding.org | Performs the actual jailbreak (v2.4.0, sha256 measured on this device `cfe16df1…fbbc02`) |
| **KOReader** | KOReader team | **AGPL-3.0** | Reader |
| **SimpleUI** (simpleui.koplugin) | Doctor Hetfield (upstream); customized by joeseesun (qiaomu edition) | **GPL-3.0** | Phone-like home screen / news / AI text selection |
| **WeRead plugin** (weread.koplugin) | finlater | See its repository | Read WeRead inside KOReader |
| **Qiaomu send2kindle** | joeseesun | See its repository (includes THIRD_PARTY_NOTICES) | Wi-Fi book transfer + APK converter (Node) |
| **KindleUnpack** | Kevin Hendricks et al. | **GPL-3.0** | AZW3/MOBI → EPUB conversion (installed separately, not bundled) |
| **Kindle-Filler-Disk** | bastianmarin et al. | See its repository | Fill storage to prevent OTA |
| **PEKI / MRPI / Hotfix / ota.sh / disable_oobe.sh** | KindleModding | See its repository | Optional: KUAL, jailbreak persistence, OTA recovery, OOBE disable |
| Wallpaper materials | Wikimedia Commons (public domain/CC0), NASA (public domain) | Individual licenses, recorded in `wallpapers/sources.json` | Sleep screensaver |

---

## 2. Content Owned by This Package

- Documentation: CC-BY-4.0 (please credit the source when quoting)
- Scripts (`scripts/*`, `assets/dialoger-local.html`, `assets/KOReader.sh`, `assets/feed_config.lua`):
  MIT

---

## 3. Disclaimer

1. **Jailbreaking carries risk**: in theory it may brick the device, void the warranty, and affect account security. Assess it yourself and **proceed at your own risk**.
2. **No assistance with piracy**: this package does not include or point to any pirated book sources (Z-Library / LibGen / Telegram bots, etc.).
   All format conversion is only for files that are **DRM-free** and legally owned by the user; this package **does not decrypt DRM**.
3. **Account risk**: the WeRead plugin is a third-party client, and its author states that account risk control is possible; login must be performed by the user personally,
   and the API Key / Cookie should not be given to anyone (including AI assistants).
4. **Compliance**: the Amazon Terms of Service, local laws, and device warranty policies are for the user to confirm.
5. **No warranty**: this package is provided "as is"; versions, URLs, and server-side endpoints may change over time, so consult the official pages before executing anything.

---

## 4. Key Upstream Links

| Purpose | Link |
|---|---|
| KindleModding Wiki (jailbreak hub) | https://kindlemodding.org/jailbreaking/ |
| Jailbreak wizard | https://kindlemodding.org/jailbreak-wizard.html |
| Prevent auto-update (fill disk) | https://kindlemodding.org/jailbreaking/prevent-auto-update/ |
| What's Next / package manager | https://kindlemodding.org/jailbreaking/whats-next/ |
| OTA recovery scriptlet | https://kindlemodding.org/jailbreaking/ota.sh |
| OOBE disable scriptlet | https://kindlemodding.org/jailbreaking/disable_oobe.sh |
| Firmware download table / FTVDB | https://kindlemodding.org/firmware-and-flashing/downloading-updates.html ｜ https://ftvdb.com/kindle/firmware/ |
| KOReader | https://github.com/koreader/koreader |
| SimpleUI (qiaomu edition) | https://github.com/joeseesun/qiaomu-simpleui |
| WeRead plugin | https://github.com/finlater/weread.koplugin |
| send2kindle | https://github.com/joeseesun/qiaomu-send2kindle |
| KindleUnpack | https://github.com/kevinhendricks/KindleUnpack |
| Fill disk script | https://github.com/bastianmarin/Kindle-Filler-Disk |
