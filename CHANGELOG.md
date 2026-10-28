# Changelog

## v1.0.1 — 2026-10-28

Documentation default changed to English; Chinese remains available as a mirror.

### Changed

- **English is now the default documentation language**: `README.md`, `SKILL.md`, and `references/*.md`
- Chinese mirrors moved to `README.zh-CN.md`, `SKILL.zh-CN.md`, and `references/zh-CN/*.md`
- Cross-links updated so each language points to files in its own language tree

## v1.0.0 — 2026-10-28

First public release, verified end-to-end on a Kindle Paperwhite 3 (firmware 5.16.2.1.1, soft-float).

### Added

- **kindle-enhancement (primary skill)**
  - Jailbreak pipeline: WinterBreak2 selection, local-execution payload that removes the GitHub Pages dependency, three verification artifacts
  - KOReader + SimpleUI installation, launcher scriptlet, `home_dir` fix
  - Wireless delivery orchestration: SSH pairing, SHA-256 read-back receipts, recovery without re-pairing when the state directory is lost
  - **Book-source quality gate** with four hard criteria (metadata/Douban, structure, size, body safety)
  - **Douban automation**: multi-query fallback (ISBN → main title → full title → stripped "complete works / N volumes" variants → title + author), placeholder-ISBN detection, local ISBN check-digit validation, edition-year matching
  - **Metadata backfill**: `backfill_isbn.py` fills ISBN / publisher / date / language (`--fill-metadata`, `--fix-language`); OPF-only edits, automatic `.orig` backup, structural re-validation
  - **Device filename policy**: `name_policy.py` names files after the Douban title (Chinese titles for Chinese books, English titles for English books), FAT32 sanitization, automatic numbering on collisions
  - Optional enhancements: WeRead plugin, RSS news curation, sleep wallpapers, rollback, T1–T12 troubleshooting (merged from the earlier kindle-modding-stack iteration)
- **qiaomu-send2kindle (transport, locally enhanced)**
  - Automatic AZW3/AZW/MOBI/PRC → EPUB conversion via KindleUnpack (two paths: direct mobi8 extraction, mobi7 repackaging)
  - `--name-mode douban|metadata|source` naming policy
  - Receipts now include `name_source` / `title` / `douban_url` / `renamed_from`
- **Release packages**: skill-only ZIP, companion ZIP, full repository ZIP, and `SHA256SUMS`

### Fixed

- Douban search handles ISBN poorly → multi-query fallback
- Titles with parentheses or "complete works" suffixes failed to match → query variants
- Douban placeholder ISBNs (`9787001xxxxxx`) were treated as conflicts → detected and ignored
- Multi-author EPUBs (with scan-site watermarks such as `SoBooKs.cc`) failed author comparison → compare all creators
- Edition-specific ISBN/year differences caused false blocks → downgraded to `warn`; `block` is reserved for title conflicts, invalid structure, or unsafe body content
- `backfill_isbn.py` could not fix language alone when the ISBN already matched → split change detection
- Device filenames fell back to pinyin (upload used the source filename) → default to Douban titles

### Known limitations

- Douban has no official API; when pages change or rate limiting kicks in, this check degrades to `warn` (manual review)
- Some Douban ebook entries only have placeholder ISBNs (e.g., *刘慈欣短篇科幻小说合集*), so no real ISBN can be backfilled
- Format conversion depends on a separately installed KindleUnpack (GPL, not redistributed here)
- Native mode (EPUB→AZW3 receiver) has not been fully validated on real hardware
