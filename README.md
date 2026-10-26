# Kindle Enhancement Skill

A practical guide and helper toolkit for turning a compatible Kindle into a customizable reading device with KOReader, an enhanced home screen, Wi-Fi book delivery, RSS news, and sleep wallpapers.

The project brings the setup sequence, configuration files, troubleshooting notes, and rollback instructions together in one place. It is designed for readers following the guide themselves and AI agents using [`SKILL.md`](SKILL.md) as the workflow entry point.

**Baseline:** v1.0.0 · development records dated 26 October 2026. The detailed guides are primarily in Chinese; this README provides an English overview.

**Downloads:** [Complete v1.0.0 toolkit ZIP](https://github.com/Rorouse0020/kindle-enhancement-skill/raw/refs/tags/v1.0.0/dist/kindle-enhancement-skill-v1.0.0.zip) · [SHA-256 checksums](https://github.com/Rorouse0020/kindle-enhancement-skill/blob/v1.0.0/SHA256SUMS.txt) · [Original development ZIP](https://github.com/Rorouse0020/kindle-enhancement-skill/raw/refs/tags/v1.0.0/archives/kindle-modding-stack-v1.0.0.zip). The complete toolkit ZIP contains the current README, guides, helper scripts, assets, and licenses. The original ZIP is preserved unchanged as a historical snapshot.

> **Compatibility:** The supplied development records document a Kindle Paperwhite 3 (7th generation, 2015), firmware **5.16.2.1.1**, using the **soft-float** KOReader package. Other models, firmware versions, and computer platforms require their own compatibility checks. This repository is a guided toolkit; installation includes device-side actions and separately installed upstream components.

## Why this project exists

A Kindle enhancement setup spans several projects, device settings, and computer tools. Instructions that work individually can still leave an unusable setup: the reader may not launch, transferred books may be invisible, HTTPS requests may fail, or settings may disappear after restarting KOReader.

This project connects those steps and records how to diagnose the failures encountered during development.

| Problem | What the toolkit provides |
|---|---|
| Unclear model, firmware, or package compatibility | A compatibility-first workflow and links to the upstream jailbreak selector. |
| The device cannot retrieve the jailbreak script | A documented local-script execution variant, with preparation and hash checking. |
| KOReader fails to launch or shows an empty library | Launcher setup, executable-mount guidance, and library-path corrections. |
| USB transfer is inconvenient, or delivery is hard to confirm | A separate sender integration with USB pairing, SSH/SFTP delivery, and read-back SHA-256 receipts. |
| Existing AZW3/MOBI books do not open in the documented reader setup | A documented conversion path for DRM-free files using a local sender patch and KindleUnpack. |
| News updates fail or English articles appear as Chinese rewrites | Clock/TLS troubleshooting, source curation, and a documented original-language patch. |
| Settings are overwritten or an installation needs to be reversed | Guidance on exiting KOReader before edits, backing up affected files, and rolling back individual changes. |

## What you can build

| Capability | Included material | Dependencies and limits |
|---|---|---|
| **Compatible-device jailbreak preparation** | WinterBreak2 guide, local dialoger asset, and preparation helper. | Check the device against upstream guidance first. Jailbreak payloads are obtained separately. |
| **KOReader reading environment** | Package-selection guidance, launcher, and library configuration. | The recorded setup used KOReader **v2026.07.1**, `kindlepw2` build. |
| **Enhanced home screen** | SimpleUI installation and configuration guide. | The recorded setup used **3.0.0-qiaomu.16**. AI lookup is optional and requires separate provider configuration. |
| **WeRead integration / 微信读书** | Plugin installation and account-setup guide. | The recorded setup used `weread.koplugin` **v1.6.0**. Requires the user's own account and manual login. |
| **Wi-Fi book delivery and remote helpers** | Sender setup guide, paired SSH command helper, and recursive SFTP uploader. | Requires **qiaomu-send2kindle**, its Python runtime, completed pairing, and an awake Kindle running KOReader with SSH enabled. |
| **DRM-free format conversion** | Documentation for the local AZW3/AZW/MOBI/PRC-to-EPUB sender enhancement. | The patched sender implementation and KindleUnpack are **outside this package**; see the limitation below. |
| **RSS reading** | A source-catalog preset with **137 entries: 117 enabled and 20 disabled**, plus **24 English feed entries** for KOReader News downloader. | Catalog counts describe the bundled files. Feed availability and the SimpleUI news service can change. The original-language patch is a separate documented edit. |
| **Random sleep wallpapers** | **15 bundled grayscale images**, wallpaper configuration helper, and optional generator. | Images target **1072 × 1448**. Random wallpapers apply while sleeping inside KOReader. |
| **Diagnostics and recovery** | A read-only setup checker, a troubleshooting index, and component rollback instructions. | Automated checks cover files and configuration; manual device checks are also required. |

## Requirements

- **A compatible Kindle:** identify the model and installed firmware before selecting a jailbreak or reader build.
- **A computer:** the recorded workflow used macOS. Linux users must adapt platform-specific commands and credential paths; Windows/WSL deployment is not established by the supplied records.
- **Host tools:** Python **3.10 or later**, Bash, `curl`, `unzip`, and standard filesystem tools. Git is needed if cloning the repository. Preparation uses `shasum` or `sha256sum`.
- **A USB data cable and a verified backup:** preserve books, notes, reading progress, fonts, and settings before device changes.
- **Networking:** the computer and Kindle need a mutually reachable local network for wireless delivery. Downloads, account services, and news require access to their respective internet services.
- **Separate component downloads:** obtain KOReader, plugins, the sender, and any required jailbreak assets from the upstream sources linked in the guides.

Optional features have additional requirements: **KindleUnpack plus the patched sender** for the documented reverse conversion, **Pillow and suitable fonts** for regenerating wallpapers, and the relevant account or API credentials for WeRead and AI features. Applying the bundled wallpapers does not require Pillow.

## Getting started

```bash
git clone https://github.com/Rorouse0020/kindle-enhancement-skill.git
cd kindle-enhancement-skill

# Read compatibility checks, backup instructions, and the phase overview first.
less SKILL.md
```

Begin with **Phase 0** in `SKILL.md`. Confirm the target device, select compatible upstream components, and complete the backup before running any preparation or installation helper. An already enhanced device can enter at the relevant phase after checking its existing state.

For a USB-mounted device, the setup checker provides an initial inventory:

```bash
# macOS example: exit KOReader, connect USB, and confirm the actual mount path.
bash scripts/verify-setup.sh /Volumes/Kindle
```

On an unmodified Kindle, missing-component failures are expected. This command inspects the current setup; it does not install components or determine whether a jailbreak is safe for a particular model.

### Deployment sequence

| Phase | Work | Completion check | Guide |
|---|---|---|---|
| **0 — Prepare** | Identify the device and firmware; select packages; back up data; check time and storage. | Backup is usable, compatibility is established, and the device date/time is correct. | [`SKILL.md`](SKILL.md) |
| **1 — Jailbreak** | Follow the applicable jailbreak path, including local-script preparation if needed. | Check the documented completion markers and required components. | [Jailbreak guide](references/01-jailbreak.md) |
| **2 — Reader and plugins** | Install KOReader, configure the launcher/library, then add the selected plugins. | KOReader launches on the device and opens a book; installed plugins are accessible. | [KOReader](references/02-koreader.md), [plugins](references/03-plugins.md) |
| **3 — Wireless delivery** | Install the separate sender/runtime, pair over USB, and establish device trust. | Send a test book, confirm the successful read-back receipt, and open it on the Kindle. | [Wireless delivery](references/04-send2kindle.md) |
| **4 — Content and appearance** | Apply the chosen news configuration and wallpapers. | Fetch and open an article; check original-language behavior if patched; verify a wallpaper during KOReader sleep. | [RSS](references/05-content-rss.md), [wallpapers](references/06-wallpapers.md) |
| **5 — Verify and maintain** | Review the setup checker, perform device checks, and retain recovery copies. | Resolve failures, assess warnings, and confirm the selected features on the device. | [Troubleshooting](references/07-troubleshooting.md), [rollback](references/08-rollback.md) |

Keep KOReader running for its SSH-based wireless connection. Exit KOReader before USB-based configuration edits: the documented setup may not expose USB storage while KOReader is running, and KOReader can overwrite external settings changes when it exits.

## Helper scripts

Run helpers from a terminal with the dependencies required by that operation. Review the linked guide before executing a script that writes to the device.

| Script | Purpose | Effect / prerequisite |
|---|---|---|
| [`verify-setup.sh`](scripts/verify-setup.sh) | Inspect installed files, settings, host runtime, and storage. | Read-only checks; requires a mounted Kindle. |
| [`kindle-prepare-local.sh`](scripts/kindle-prepare-local.sh) | Prepare the local jailbreak script and dialoger, then create storage filler files. | **Writes to the device and fills storage.** Use only after backup and compatibility checks. |
| [`kindle-ssh.py`](scripts/kindle-ssh.py) | Execute a remote command using the sender's paired identity. | Requires the sender/runtime and a reachable SSH server. Its effect depends on the command. |
| [`kindle-push.py`](scripts/kindle-push.py) | Upload a file or directory through SFTP. | Writes to device storage; requires the sender/runtime and pairing. |
| [`apply-rss-curation.py`](scripts/apply-rss-curation.py) | Apply the bundled source catalog and update existing news state. | Writes catalog/state files; backs up existing affected files. Does not apply the original-language code patch. |
| [`apply-wallpapers.py`](scripts/apply-wallpapers.py) | Copy images and configure random sleep wallpapers. | Writes images/settings; backs up the existing settings file. Exit KOReader first. |
| [`gen-wallpapers.py`](scripts/gen-wallpapers.py) | Regenerate wallpaper assets from external images and text cards. | Writes local files; needs Pillow, internet access, and suitable local fonts. |

The SSH and SFTP helpers locate the separate sender through `QIAOMU_SKILL_DIR` or their documented fallback locations. Run them with a Python environment containing the sender's dependencies; setting the path alone does not install those dependencies.

### What a passing setup check means

`verify-setup.sh` returns **0 when it records no failures** and **1 when it records a failure**. Warnings can remain with exit code 0.

Its clock check infers a possible problem from a settings-file timestamp; it does not read the live device clock. It also does not prove that KOReader launches, an account can log in, a feed loads, a transfer opens successfully, or a wallpaper appears. Complete the corresponding device checks before calling the deployment successful.

## Repository contents

```text
kindle-enhancement-skill/
├── README.md                 # Project overview and starting point
├── SKILL.md                  # Detailed workflow for readers and agents
├── manifest.json             # Package metadata and recorded component baseline
├── CHANGELOG.md              # Version history
├── LICENSE                   # MIT terms for authored scripts
├── LICENSE-DOCS              # CC BY 4.0 documentation terms
├── SHA256SUMS.txt             # Checksums for both downloadable ZIP files
├── dist/                     # Complete toolkit ZIP for distribution
├── archives/                 # Unchanged original development ZIP
├── references/               # Nine setup, troubleshooting, and recovery guides
├── scripts/                  # Seven helper scripts
└── assets/                   # Launcher, dialoger, feed presets, and wallpapers
```

The original development bundle is named `kindle-modding-stack-v1.0.0.zip`; this repository uses the publication name **kindle-enhancement-skill**. Archive contents and repository revisions should be checked separately when reproducing a setup.

The distribution ZIP extracts into a `kindle-enhancement-skill/` folder with the source, guides, and assets above. The `dist/` and `archives/` directories and repository-level checksum file are kept outside that ZIP to avoid nested archives and a self-referencing checksum.

## Known limits

- **The conversion implementation is a separate dependency.** This package describes a local modification to qiaomu-send2kindle, but does not include the patched sender source or an installable patch artifact. Cloning the upstream sender alone does not reproduce that enhancement. Start with direct EPUB delivery unless you have the documented patched implementation and KindleUnpack. KFX conversion and DRM removal are outside the documented workflow.
- **Host portability is incomplete.** Some helpers use macOS credential paths and BSD command syntax. The wallpaper generator also refers to local font locations. Review and adapt these before using another host; regeneration can produce fewer images when fonts or downloads are unavailable.
- **The upstream versions are a recorded baseline.** They are not a claim about the latest releases or compatibility with future firmware and plugins. Recheck upstream instructions before installing or upgrading.
- **Some features depend on external services.** RSS feeds, the SimpleUI news backend, WeRead, and optional AI providers can change independently of this repository.
- **Wallpapers are scoped to KOReader sleep.** The package does not install a system-wide native Kindle screensaver replacement.

## Device changes and private data

Back up first. Jailbreaking changes device software and can leave a device unusable if the procedure fails. Follow the selected guide's power, storage, and firmware precautions. Before a factory reset on an OTA-blocked device, consult the [rollback guide](references/08-rollback.md) for restoring the required update state.

Use books and accounts you are entitled to access. Format conversion in this workflow is limited to **DRM-free** files. WeRead is a third-party integration; complete authentication yourself and consider its upstream account-risk notes.

Keep personal books, clippings, device backups, serial numbers, pairing records, private keys, cookies, and API credentials out of Git commits, release archives, and issue reports. Review diagnostic output before sharing it.

## Maintenance and contributions

For a bug report, include the model, firmware, relevant component versions, reproduction steps, and redacted output. Clearly distinguish a proposed setup from one tested on hardware. Use the [troubleshooting guide](references/07-troubleshooting.md) to identify the affected layer.

When updating a component, record the version change in [`CHANGELOG.md`](CHANGELOG.md), check any local modifications against the new upstream source, and verify the affected workflow on the device. Retain a known working configuration and its recovery instructions.

## Upstream projects and licensing

This toolkit connects work from [KindleModding](https://kindlemodding.org/jailbreaking/), [KOReader](https://github.com/koreader/koreader), [SimpleUI upstream](https://github.com/doctorhetfield-cmd/simpleui.koplugin), [qiaomu SimpleUI](https://github.com/joeseesun/qiaomu-simpleui), [qiaomu-send2kindle](https://github.com/joeseesun/qiaomu-send2kindle), [WeRead for KOReader](https://github.com/finlater/weread.koplugin), [KindleUnpack](https://github.com/kevinhendricks/KindleUnpack), and [Kindle-Filler-Disk](https://github.com/bastianmarin/Kindle-Filler-Disk).

Authored scripts use **MIT** terms and documentation uses **CC BY 4.0**; see [`LICENSE`](LICENSE) and [`LICENSE-DOCS`](LICENSE-DOCS). Wallpaper assets and third-party components retain their respective terms. See the [credits and component notices](references/09-credits.md) and [wallpaper source records](assets/wallpapers/sources.json). Upstream reader/plugin binaries, Kindle firmware, and personal reading content are not bundled with this toolkit.
