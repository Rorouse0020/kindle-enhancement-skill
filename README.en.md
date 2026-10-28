# Kindle Enhancement Skill

> Turn a jailbroken Kindle (primarily: Paperwhite 3 / firmware 5.16.2.1.1) into an enhanced device that **reads, delivers, and verifies**.
> End-to-end pipeline: **jailbreak → KOReader/SimpleUI → wireless delivery → book quality gate → metadata normalization → verification/rollback**.

[![Skill](https://img.shields.io/badge/agent--skill-v1.0.0-blue)]()
[![License](https://img.shields.io/badge/license-GPL--3.0-green)]()
[![Tested](https://img.shields.io/badge/tested-Kindle%20PW3%205.16.2.1.1-orange)]()

**Language:** English (this file) · [中文](README.md)

---

## What this is

This repository ships two companion Agent Skills (`SKILL.md` + scripts + references, loadable by Claude Code / Codex / any agent-skills–compatible tool):

| Skill | Purpose |
|---|---|
| **kindle-enhancement** (primary) | Jailbreak, KOReader/SimpleUI, delivery orchestration, **book quality gate**, Douban verification, metadata backfill, verification and rollback |
| **qiaomu-send2kindle** (transport, locally enhanced) | Delivers books over SSH/SFTP; local patches add **automatic AZW3/MOBI → EPUB conversion** and **Douban-title file naming** |

> Upstream: `joeseesun/qiaomu-send2kindle` (GPL-3.0). This repository contains local patches; see `skills/qiaomu-send2kindle/LOCAL_PATCHES.md`.

## Core capabilities

### 1. Jailbreak pipeline (verified on real hardware)

- Method selection follows the official `jailbreaks.json`: PW3 + ≤5.16.3 → **WinterBreak2** (no registration required).
- **Key pitfall and fix**: the official `dialoger.html` fetches `jb.sh` from GitHub Pages, which often fails (symptom: "nothing happens after tapping Jailbreak"). This project ships a **local-execution** `assets/dialoger-local.html` plus a local `jb.sh` copy, eliminating the GitHub dependency.
- Three verification artifacts: `documents/JAILBROKEN.txt`, `JB_TRACE.txt` (`DIALOGER_EXECUTED`), and `libkh/bin/fbink`.

### 2. KOReader + SimpleUI

- Correct package: PW3 (soft-float) uses `koreader-kindlepw2`.
- Launcher scriptlet (remounts `/mnt/us` as exec automatically).
- Fixes a common failure where a wrong `home_dir` makes books invisible even though they are in `documents/`.

### 3. Wireless delivery (Wi-Fi SSH)

- Pair once over USB; afterward everything runs over LAN SSH, with the private key stored only in the macOS Keychain.
- SHA-256 read-back verification; delivery counts only when `ok: true`.
- Receipts include device path, byte count, SHA-256, conversion info, and naming source.

### 4. Book quality gate (the centerpiece)

Every book is checked against **four hard criteria** before delivery: `pass` sends, `warn` needs human confirmation, `block` is refused.

| # | Criterion | Automation |
|---|---|---|
| 1 | **ISBN / publisher / edition match** (Douban) | `--douban`: search + detail-page comparison of title/author/publisher/year/ISBN |
| 2 | **Valid EPUB structure** (zip / mimetype / container / OPF / spine) | `quality_check.py` |
| 3 | **Reasonable file size** (a few dozen KB for a long book = truncated/sample) | size vs. chapters/images + sample keywords |
| 4 | **No scripts or external redirects in the body** (`script/iframe/javascript`/external links) | full spine XHTML scan |

Decision policy: **`block` is reserved for title conflicts, invalid structure, or executable content**. ISBN, publication-year, and publisher mismatches downgrade to `warn` (different editions are common), avoiding false negatives on legitimate editions.

Additional tolerance: Douban placeholder ISBNs (`9787001xxxxxx`) and locally invalid ISBN check digits are ignored during comparison; query variants automatically strip parentheses and suffixes such as "全集" (complete works) and "共N册" (N volumes).

### 5. Metadata normalization

- **ISBN / publisher / date / language backfill** via `backfill_isbn.py` (OPF only, body untouched; automatic backup + structural re-validation).
- **Device filename = Douban title**: Chinese titles for Chinese books, English titles for English books; falls back to metadata title or source filename when Douban is unavailable.

### 6. Optional enhancements

Plugins (WeRead/SSH), RSS news curation, sleep-screen wallpapers (16 public-domain/CC0 images), a T1–T12 troubleshooting manual, and rollback/recovery procedures.

## Repository layout

```
.
├── README.md / README.en.md        # Chinese / English
├── LICENSE                          # GPL-3.0 (inherited from qiaomu-send2kindle)
├── CHANGELOG.md
├── dist/                            # release packages (zip + SHA256SUMS)
└── skills/
    ├── kindle-enhancement/
    │   ├── SKILL.md                 # primary workflow (Phase 0-5), Chinese
    │   ├── SKILL.en.md              # English translation
    │   ├── scripts/
    │   │   ├── quality_check.py     # four-criteria gate (optional --douban)
    │   │   ├── douban_verify.py     # Douban verification (multi-query fallback, placeholder-ISBN detection, year matching)
    │   │   ├── backfill_isbn.py     # metadata backfill (ISBN/publisher/date/language)
    │   │   ├── name_policy.py       # device filename = Douban title
    │   │   ├── kindle-push.py       # generic SFTP push
    │   │   ├── apply-rss-curation.py / apply-wallpapers.py / gen-wallpapers.py
    │   │   └── verify-setup.sh      # read-only full-stack health check
    │   ├── references/              # jailbreak/KOReader/delivery/quality gate/troubleshooting/rollback/credits
    │   │   └── en/                  # English translations
    │   └── assets/                  # jailbreak payloads, launcher, cleanup scripts, wallpapers
    └── qiaomu-send2kindle/          # transport layer (with local patches)
```

## Installation

```bash
# 1) Install into an agent skills directory (or a project's skills/)
cp -R skills/kindle-enhancement  ~/.claude/skills/
cp -R skills/qiaomu-send2kindle  ~/.claude/skills/

# 2) Transport runtime (Python 3.10+, isolated venv)
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" "$HOME/.claude/skills/qiaomu-send2kindle/scripts/setup_runtime.py"

# 3) Format converter (installed separately, GPL, not redistributed here)
#    https://github.com/kevinhendricks/KindleUnpack
#    Extract to ~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack
#    (must contain lib/kindleunpack.py; override with QIAOMU_KINDLEUNPACK_DIR)
```

Requirements: macOS (verified), Python 3.10+, Node.js 20+ (only for native-mode EPUB→AZW3), a jailbroken Kindle with KOReader SSH.

## Usage

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/.claude/skills/kindle-enhancement"

# Quality gate before delivery (with Douban verification)
"$RT" "$SK/scripts/quality_check.py" "book.epub" --douban

# Backfill metadata (ISBN/publisher/date/language)
"$RT" "$SK/scripts/backfill_isbn.py" "book.epub" --douban --fill-metadata --fix-language en-US

# Deliver (names files by Douban title; AZW3/MOBI are converted to EPUB automatically)
"$RT" ~/.claude/skills/qiaomu-send2kindle/scripts/send_to_kindle.py send "book.epub"
```

## Field-tested

- Device: Kindle Paperwhite 3 (2015) / firmware `5.16.2.1.1` / soft-float, jailbroken with WinterBreak2.
- Verified on real hardware: jailbreak, KOReader v2026.07.1 + SimpleUI 3.0.0-qiaomu.16, SSH pairing and delivery, AZW3/MOBI7→EPUB conversion, Douban verification on multiple Chinese books, ISBN/publisher/language backfill, batch renaming and cleanup.
- Gate samples: *战略与路径* and *三体（读客版）* reach `pass`; *刘慈欣短篇科幻小说合集* stays `warn` because Douban only has a placeholder ISBN.

## Boundaries and disclaimer

- For use only with devices and books you own. No DRM circumvention, no sourcing pirated content, no logging into third-party accounts on your behalf.
- Jailbreaking may void the warranty; bricking risk is borne by the user (this skill includes backup/rollback procedures).
- Douban verification reads public pages (1.5 s rate limit, 7-day cache) and may degrade to manual verification when rate-limited.
- Third-party components and licenses: see `skills/kindle-enhancement/references/ext-credits.md` and `skills/qiaomu-send2kindle/LICENSE`.

## Credits

[KindleModding](https://kindlemodding.org/) (jailbreak process and wizard data), [KOReader](https://github.com/koreader/koreader), SimpleUI (Doctor Hetfield / qiaomu customization), [qiaomu-send2kindle](https://github.com/joeseesun/qiaomu-send2kindle), [KindleUnpack](https://github.com/kevinhendricks/KindleUnpack), weread.koplugin (finlater), and [向阳乔木](https://qiaomu.ai).

## License

GPL-3.0 (see [LICENSE](LICENSE)); wallpaper assets are public domain / CC0, detailed in `skills/kindle-enhancement/assets/wallpapers/sources.json`.
