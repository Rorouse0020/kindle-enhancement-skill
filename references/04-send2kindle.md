# 04 · Wi-Fi 无线传书（乔木 send2kindle + 自动格式转换）

> 目标：在电脑上说一句"把这本书发到 Kindle"，书就落到设备 `/mnt/us/documents/`，并有 SHA-256 回读收据。
> 支持：EPUB 直传；**AZW3 / AZW / MOBI / PRC 自动转 EPUB**（本地增强补丁）。
> 前提：越狱完成 + KOReader 已装 + 设备与电脑同一 Wi-Fi。

---

## 1. 架构概览

```
AI/终端 → send_to_kindle.py → 密码学身份（私钥在系统钥匙串）
        → SSH/SFTP（KOReader 的 dropbear，端口 2222）
        → 上传临时文件 → 设备端完整回读 → 校验字节数 + SHA-256 → 改名为最终文件
```
- 私钥：**只存系统凭据**（macOS Keychain，service `ai.qiaomu.kindlesync`），不落盘、不进日志。
- 设备身份：`~/Library/Application Support/Qiaomu/Kindle/devices.json`（记录主机指纹，防中间人）。
- 运行时：`~/Library/Application Support/Qiaomu/Kindle/runtime/`（隔离 venv，不改全局 Python）。

---

## 2. 安装技能本体与运行时

```bash
# 2.1 取代码（任选：官方 skills CLI 或直接解包）
npx skills add joeseesun/qiaomu-send2kindle        # 若可用
# 或：git clone / 解压 tarball 到任意目录，例如 ~/skills/qiaomu-send2kindle

cd ~/skills/qiaomu-send2kindle
python3 --version        # 必须 ≥ 3.10
python3 scripts/setup_runtime.py
# 期望输出：{"ok": true, "runtime": ".../runtime/bin/python3", "credential_store": "operating-system", ...}
```

### ⚠️ 坑：uv/pyenv 管理的 Python 建 venv 后 `sys.base_prefix=/install`

**症状**：`runtime/bin/python3` 一运行就报
`ModuleNotFoundError: No module named 'encodings'` / `Could not find platform independent libraries`。
**根因**：通过**符号链接**调用 uv 的 Python 时，venv 的 `pyvenv.cfg` 把 `home` 记成了链接所在目录，
导致 base prefix 解析失败。
**解法**：用**真实路径**的解析器创建 venv：
```bash
UV=$HOME/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/bin/python3.12
rm -rf "$HOME/Library/Application Support/Qiaomu/Kindle/runtime"
"$UV" scripts/setup_runtime.py
"$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3" -c "import paramiko,keyring,filelock,psutil;print('deps ok')"
```

---

## 3. USB 配对（一次）

前提：**退出 KOReader**（KOReader 运行时不挂载 U 盘），USB 连接 → 挂载成功。

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
"$RT" scripts/send_to_kindle.py pair --usb '/Volumes/Kindle' --mode koreader
# 期望：{"ok": true, "paired": true, "device": "kindle-xxxxxxxx", "mode": "koreader",
#        "port": 2222, "host_trust_pending": true}
```
它做的事：
1. 生成 ECDSA 密钥对，私钥写入系统钥匙串；
2. 公钥追加到 `koreader/settings/SSH/authorized_keys`（**保留**原有内容）；
3. 在 `koreader/settings.reader.lua` 写入
   `SSH_port="2222"`、`SSH_key_only_auth=true`、`SSH_autostart=true`（**先备份**原文件为 `*.qiaomu-skill-backup-*`）。

验证：
```bash
VOL=/Volumes/Kindle
cat "$VOL/koreader/settings/SSH/authorized_keys"      # 一行 ecdsa-sha2-nistp256 ... qiaomu-kindlesync
grep -E 'SSH_(port|autostart|key_only_auth)' "$VOL/koreader/settings.reader.lua"
```

---

## 4. 首次建立信任

1. 设备：启动 KOReader（SSH 随启动自启；工具 → SSH server 可确认勾选），保持 KOReader 打开、Wi-Fi 连接。
2. 电脑：先找设备 IP（弹窗只显示几秒，也可扫描端口）：
   ```bash
   seq 1 254 | xargs -P 128 -I{} sh -c 'nc -z -G 1 -w 1 192.168.31.{} 2222 2>/dev/null && echo 192.168.31.{}'
   ```
3. 建立信任（仅首次）：
   ```bash
   "$RT" scripts/send_to_kindle.py connect --host <设备IP> --mode koreader --trust-new-device
   # 期望：{"ok": true, "ready": true, "fingerprint": "<64位十六进制>"}
   ```
   之后设备身份被固定，`--trust-new-device` 不能再替换它（防中间人）。

---

## 5. 日常使用

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/skills/qiaomu-send2kindle"

"$RT" "$SK/scripts/send_to_kindle.py" status                     # 配对/模式/凭据状态
"$RT" "$SK/scripts/send_to_kindle.py" discover --mode koreader    # IP 变化后自动按身份找设备
"$RT" "$SK/scripts/send_to_kindle.py" inspect '/path/书.epub'     # 先核对标题/作者/语言
"$RT" "$SK/scripts/send_to_kindle.py" send    '/path/书.epub'     # 发送（KOReader 模式）
"$RT" "$SK/scripts/send_to_kindle.py" send    '/path/书.epub' --mode native   # 给原生阅读器（自动转 AZW3）
```

**送达判定**：仅 `ok: true` 算成功；收据里的 `sha256` 必须等于源文件（或转换后的传输文件，此时另有 `source_sha256`）。
书落在 `/mnt/us/documents/`，**同名文件不覆盖**。

---

## 6. ⚠️ 格式策略与本地补丁（本次核心增强）

### 6.1 为什么必须补

- KOReader 的格式注册表只有 `azw` / `mobi` / `prc`，**没有 `azw3`**（KF8 解析不了）；
  直接把 AZW3 传到设备 → 打开时提示"格式不支持"。
- 上游技能只会"EPUB → AZW3"（给原生阅读器），没有反方向。

### 6.2 补丁内容（三处 + 一个新文件）

| 文件 | 改动 |
|---|---|
| `scripts/epub_convert.py`（新增） | 用 **KindleUnpack** 把 AZW3/AZW/MOBI/PRC 转 EPUB；KF8 直接取 `mobi8/*.epub`；MOBI7 用 `book.html + Images + *.opf` 重打包；含结构校验与源文件哈希不变校验 |
| `scripts/kindle_convert.py` | `prepare()` 增加分支：`mode != native` 且扩展名 ∈ `KINDLE_FORMATS` → 先转换 |
| `scripts/send_to_kindle.py` | ① `EXTENSIONS` 加 `.prc`；② MOBI 魔数校验含 `.prc`；③ `delivery_receipt()` 允许 koreader 模式下 `converted:true` + 目标 `.epub` |
| `SKILL.md`（技能自带） | 加"格式策略"章节（便于其他 agent 读懂） |

所有改动都带 `[local patch]` 注释标记，上游升级时按此重放（见技能目录 `LOCAL_PATCHES.md` 模板）。

### 6.3 安装转换器 KindleUnpack（GPL，独立安装，不随技能分发）

```bash
DEST="$HOME/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack"
mkdir -p "$DEST"
curl -L https://codeload.github.com/kevinhendricks/KindleUnpack/tar.gz/HEAD | tar -xz -C "$DEST" --strip-components=1
ls "$DEST/lib/kindleunpack.py"        # 必须存在
# 可用环境变量覆盖位置：QIAOMU_KINDLEUNPACK_DIR
```

### 6.4 行为矩阵

| 你发送 | 行为 | 收据关键字段 |
|---|---|---|
| `.epub` | 直传 | `converted:false`，`sha256`=源文件 |
| `.azw3`（KF8） | KindleUnpack 转 EPUB | `converted:true`，`engine:"kindleunpack-mobi8"` |
| `.azw`/`.mobi`/`.prc`（MOBI7） | 解包 + 按 OPF 重打包 | `converted:true`，`engine:"kindleunpack-mobi7"` |
| `.pdf`/`.txt`/... | 直传（KOReader 原生支持） | `converted:false` |
| `--mode native` + `.epub` | 本地转 AZW3 | `converted:true`，目标 `.azw3` |

**实测记录**（本机）：
- KF8：`掌控工作.azw3` 2,266,201 B → EPUB 1,757,077 B；
- MOBI7：古登堡《Pride and Prejudice》580,884 B → EPUB 362,840 B；
- 回归：EPUB 直传 2,124 B，`converted:false`。

---

## 7. 排障

| 症状 | 根因 | 处理 |
|---|---|---|
| `{"ok": false, "code": "local"}` | 运行环境受限：钥匙串不可访问 / 应用目录不可写（例如在容器沙盒里跑） | 在普通终端运行；解锁钥匙串；给 Python 完全磁盘访问 |
| `discover` 找不到设备 | KOReader 没开 / SSH server 没勾 / 不同 Wi-Fi | 打开 KOReader → 工具 → SSH server；确认同一网段 |
| `network` / `sftp` 报错 | 设备休眠、IP 变了、防火墙 | 唤醒设备；`discover` 重新定位；确认路由无客户端隔离 |
| `host-key` 报错 | 设备主机密钥变了（换机/重装） | **不要**关闭校验；重新 USB 配对 |
| `credential-missing` | 钥匙串里私钥丢了 | 重新 USB 配对（不会自动生成替代身份） |
| `converter-missing` | 没装 KindleUnpack | 见 §6.3 |
| 转换失败 | 文件带 DRM | **不解密**，改走原生阅读器或找 DRM-free 版本 |
| 传过去 KOReader 看不到 | KOReader `home_dir` 错 | `references/02-koreader.md` §5 |
| 收据 `scanPending`（native 模式） | 原生索引未完成 | 先看设备，不要盲目重发 |
