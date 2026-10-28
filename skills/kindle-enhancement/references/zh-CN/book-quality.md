# 书源质量门禁（四条硬指标）

> **核心原则：传上去一本坏书，比传不上去更糟。**
> 劣质书浪费设备空间与阅读时间，读到一半才发现残缺/错版/被篡改，代价远高于多花 1 分钟做门禁。
> 凡判定 **BLOCK** 的书一律不发送；**WARN** 必须先向用户说明并由其确认；**PASS** 才进入发送流程。

---

## 指标 1：ISBN / 出版社 / 版次能对上（豆瓣或出版社官网可查）

**为什么重要**：盗版拼装、旧版冒充新版、不同译本强行合并，都会在这里露馅。

**怎么查**

1. 读 EPUB 元数据（`quality_check.py` 会输出）：
   - `dc:identifier` 中的 ISBN-10/13（注意 `urn:isbn:` 前缀、`calibre:` 之类无效标识）
   - `dc:publisher`（出版社）、`dc:date`（出版年/版次）、`dc:title`/`dc:creator`
2. 用脚本输出的**豆瓣检索链接**核对：书名、作者、出版社、出版年、页数、ISBN 是否**全部**一致。
3. 出版社官网/电商详情页二次核对（尤其 ISBN 与版次）。

**判定**
- 元数据齐全 + 豆瓣对上 → **PASS**
- 缺 ISBN/出版社/日期其一，或书名作者与期望不符 → **WARN**（人工核对后决定）
- **书名与豆瓣条目明显冲突 → BLOCK**（认错书/拼装本）
- ISBN、出版年、出版社不一致 → **WARN**（很常见：不同版次、不同印次、套装/单册）
- 豆瓣占位 ISBN（`9787001xxxxxx` 等）或本地 ISBN 校验位不合法 → 该项 **WARN** 并忽略比对
- 判定原则：**block 只保留给"书名对不上"和"内容不安全"**；其余不一致降级为 warn，避免误杀正版的其他版次
- 常见可疑特征：`creator` 是 "SoBooKs.cc" 这类扫描站水印名；书名带"精校版/全译版"却无版本信息；同一 ISBN 对应不同封面/书名。

### 1.1 自动核对（`--douban`，推荐）

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/quality_check.py "/绝对路径/书.epub" --douban
"$RT" scripts/douban_verify.py --isbn 9787208178212
"$RT" scripts/douban_verify.py --title "战略与路径" --author "黄奇帆"
```

原理：豆瓣公开页面（`book.douban.com/j/subject_suggest` 搜索 + `/subject/<id>/` 详情页），
自动比对书名、作者、出版社、出版年、ISBN，输出 `pass/warn/block`。

| 比对项 | 判定 |
|---|---|
| 书名 | 主标题（冒号前）互相包含 → pass |
| 作者 | 任一作者互相包含（去【】前缀） → pass；扫描站水印 → warn |
| 出版社 | 互相包含 → pass；不同 → warn |
| 出版年 | 相同或 ±1 年 → pass；否则 warn/fail |
| ISBN | 双方都有且一致 → pass；本地缺 → warn（可用豆瓣 ISBN 反补） |

降级策略：豆瓣登录墙/风控/网络失败 → **warn + 提示人工**，不阻断、不误判。
请求间隔 1.5 s、UA 伪装、15 s 超时、缓存 7 天；只读公开页面，不登录。

**回填 ISBN（让指标 1 直接达标）**

```bash
"$RT" scripts/backfill_isbn.py "书.epub" --douban
"$RT" scripts/backfill_isbn.py "书.epub" --isbn 9787208178212   # 手动指定
"$RT" scripts/backfill_isbn.py "书.epub" --isbn 9787... --fix-language zh-CN  # 顺带规范语言标签
"$RT" scripts/backfill_isbn.py "书.epub" --douban --fill-metadata            # ISBN+出版社+出版日期（占位 ISBN 自动跳过）
```

脚本只在 OPF 插入 `<dc:identifier id="isbn">urn:isbn:…</dc:identifier>`，正文/图片不动；
默认备份 `书.epub.orig`，写入后复验结构（mimetype 置首、container、OPF、spine）。
回填后 `quality_check.py` 的 `1_meta` 与 `1_douban` 均可 pass。

**实测样本**（2026-10-27）：
- 《战略与路径》→ 命中 `subject/36139006`，作者/出版社/年份一致，ISBN 9787208178212（本地缺失 → warn）
- 《狼性时代》→ 命中 `subject/36692833`，作者/出版社/年份一致，ISBN 9787513944441（本地缺失 → warn，`creator` 为 SoBooKs.cc）

---

## 指标 2：EPUB 结构合法（inspect 不报错）

**自动化**（`scripts/quality_check.py` 指标 2，以及 `send_to_kindle.py inspect`）：

- zip 可打开且 `testzip()` 无损坏条目
- `mimetype` 是**第一个**条目且内容为 `application/epub+zip`
- `META-INF/container.xml` 存在且能解析，rootfile 指向实际存在的 OPF
- OPF 能解析；`spine` 非空，所有 `itemref` 都能在 `manifest` 找到
- spine 中至少一个 XHTML/HTML 正文

**判定**：任一不满足 → **BLOCK**（损坏/伪 EPUB/转换失败品，传上去也打不开）。

---

## 指标 3：文件大小合理（几十 KB 的大部头基本是残缺版）

**自动化启发式**（脚本指标 3）：

- `< 50 KB` → 高度可疑
- `< 150 KB` 且**无图片** → 可疑（纯文字小册子除外）
- 标题含 `sample / excerpt / preview / 试读 / 样章 / 节选 / 预览` → 可疑
- 输出"正文 KB / 图片数 / 章节数"供人工判断

**人工标尺**（经验值，中文书）：
| 类型 | 合理区间 |
|---|---|
| 200–300 页纯文字 | 300 KB – 1.5 MB |
| 400+ 页 | 1 – 3 MB |
| 图文混排/画册 | 5 – 50 MB |
| 学术书/含大量脚注 | 1.5 – 5 MB |

**判定**：明显低于上述区间 → **WARN**（让用户确认是不是试读/截断本）；若同时缺 ISBN 或章节数极少 → 升级为 **BLOCK**。

---

## 指标 4：正文无脚本 / 外链跳转（转换时会剥掉 script/style/iframe）

**自动化扫描**（脚本指标 4，扫描全部 spine XHTML）：

| 命中 | 含义 | 处置 |
|---|---|---|
| `<script>`、`<iframe>`、`<object>`、`<embed>` | 可执行/嵌入内容 | **BLOCK** |
| `javascript:` 伪协议、`on*=` 事件属性 | 点击劫持/追踪 | **BLOCK** |
| 外部 `http(s)://` 的 `href/src` | 正文被带离/资源外链 | **WARN**（数量多或指向可疑域名 → BLOCK） |

**为什么要挡**：转换器（KindleUnpack / 内置 AZW3 writer）会剥离 `script/style/iframe`，但剥离后可能留下空白章节或跳转失效；
更严重的是这类文件常见于"网页抓取拼装本"，正文质量极低。

**判定**：含可执行内容 → **BLOCK**；仅少量外链 → **WARN** 并抽查外链目标。

---

## 门禁结论与记录

`scripts/quality_check.py` 输出：

```json
{
  "ok": true,
  "verdict": "pass | warn | block",
  "checks": {
    "1_meta":      {"status": "pass|warn|fail", "detail": "..."},
    "2_structure": {"status": "...", "detail": "..."},
    "3_size":      {"status": "...", "detail": "..."},
    "5_content":   {"status": "...", "detail": "..."}
  },
  "metadata": {"title": "...", "creator": "...", "publisher": "...", "date": "...", "isbn": "..."},
  "content_counts": {"script": 0, "iframe": 0, "外部链接": 2, "...": 0},
  "douban": "https://search.douban.com/book/subject_search?search_text=..."
}
```

**门禁 → 发送 → 收据**，三步都要留痕。发送收据必须额外带上门禁结论，例如：

```
ok:true · /mnt/us/documents/书名.epub · 1,017,049 B · sha256=c531… · converted:false
quality: pass（结构/大小/内容 自动通过，ISBN 9787… 已核对豆瓣）
```

## 反例（本项目真实踩过的坑）

| 场景 | 现象 | 教训 |
|---|---|---|
| AZW3 直接发给 KOReader | 点击提示"格式不支持" | 指标 2 合格 ≠ 阅读器支持；**格式匹配**要单独判（KOReader 不支持 KF8） |
| `home_dir` 指向空目录 | 书在 `documents` 但书架空 | 门禁过了还要验"设备侧可见" |
| SoBooKs 来源的文件 | 元数据 `creator` 是扫描站名 | 指标 1 判 WARN，需人工核对 ISBN/出版社 |