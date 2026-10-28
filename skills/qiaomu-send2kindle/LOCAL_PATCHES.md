# 本地修改记录（相对上游 joeseesun/qiaomu-send2kindle v2.0.0）

> 目的：让 KOReader 模式支持「AZW3 / AZW / MOBI / PRC → 自动转 EPUB 后上传」，
> 因为 KOReader 不支持 KF8/AZW3。上游默认只做「EPUB → AZW3」（供原生阅读器）。
> 升级上游时请重放以下 3 处改动（均已加 `[local patch]` 注释标记）。

## 1. 新增 `scripts/epub_convert.py`

- 用外部 **KindleUnpack**（GPL，独立安装，不随 skill 分发）把 Kindle 专有格式转成 EPUB。
- `KINDLE_FORMATS = {'.azw3','.azw','.mobi','.prc','.kf8'}`
- KF8/AZW3：直接取 `out/mobi8/*.epub`。
- MOBI7/AZW/MOBI：KindleUnpack 产出 `book.html + Images + *.opf`，本模块重新打包为合法 EPUB
  （mimetype 置首、`META-INF/container.xml` 指向该 OPF）。
- 产物结构校验 + 源文件哈希不变校验；失败一律抛 `KindleError`，不上传。
- 转换器位置解析顺序：`$QIAOMU_KINDLEUNPACK_DIR` → `<state_root>/tools/kindleunpack`
  → `~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack`。

## 2. `scripts/kindle_convert.py` — `prepare()` 增加分支

```python
from epub_convert import KINDLE_FORMATS,convert_kindle_to_epub  # 新增导入

@contextmanager
def prepare(book,mode):
    ext=Path(book['name']).suffix.lower()
    if mode!='native' and ext in KINDLE_FORMATS:      # 新增分支
        with convert_kindle_to_epub(book,mode) as converted:yield converted
        return
    ...
```

## 3. `scripts/send_to_kindle.py` — 三处小改

1. 导入 `KINDLE_FORMATS`；`EXTENSIONS` 增加 `.prc`。
2. `inspect_book()` 的 MOBI 头校验集合增加 `.prc`。
3. `delivery_receipt()` 的 `converted` 分支区分两种方向：

```python
if converted:
    if mode == 'native':
        valid = valid and book['name'].lower().endswith('.epub') and destination.lower().endswith('.azw3')
    else:  # koreader：Kindle 格式 → EPUB
        valid = (valid and Path(book['name']).suffix.lower() in KINDLE_FORMATS
                 and destination.lower().endswith('.epub'))
else:
    valid = valid and size == book['bytes'] and digest == book['sha256']
```

## 5. 设备文件名：豆瓣书名（2026-10-28）

- `scripts/send_to_kindle.py` 新增 `--name-mode {douban,metadata,source}`（默认 `douban`）
  与 `resolve_destination_name()`：从 `skill 同级目录 kindle-enhancement/scripts/name_policy.py`
  加载命名策略（可用 `QIAOMU_KINDLE_ENHANCEMENT_SCRIPTS` 覆盖路径）。
- 收据新增 `name_source` / `title` / `douban_url` / `renamed_from`。
- 命名策略本体在 `kindle-enhancement/scripts/name_policy.py`（豆瓣多查询 → 标题 → FAT32 合法化）。

## 4. `SKILL.md`

- 新增「格式策略（本地增强补丁）」章节，并同步更新执行第 4/5 步与「失败与边界」的格式说明。

## 转换器安装

```bash
# KindleUnpack（kevinhendricks/KindleUnpack，GPL）
DEST="$HOME/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack"
# 解压 release 到 $DEST 后应存在 $DEST/lib/kindleunpack.py
```

## 回滚

删除 `scripts/epub_convert.py`，撤销上述 `[local patch]` 标记的三处改动，即可回到上游行为
（KOReader 模式只接受 EPUB）。已配对设备与凭据不受影响。

## 6. 校验尺度（2026-10-28 起，kindle-enhancement 侧）

- `douban_verify.py`：block 仅由**书名冲突**触发；ISBN/年份/出版社不一致 → warn；
  占位 ISBN（`9787001xxxxxx`）与校验位非法的本地 ISBN 不参与一致性判断。
- `quality_check.py`：相应只保留「书名冲突 / 结构非法 / 正文含可执行内容」为 block。
