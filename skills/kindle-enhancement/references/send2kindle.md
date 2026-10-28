# 无线传书链路参考（qiaomu-send2kindle + 本地增强）

## 1. 结构

| 项目 | 位置（本机默认） |
|---|---|
| 技能本体 | `~/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle/` 及 `~/.claude/skills/qiaomu-send2kindle/`（两份应一致） |
| 隔离运行时 | `~/Library/Application Support/Qiaomu/Kindle/runtime/`（Python 3.10+；依赖 paramiko/keyring/filelock/psutil） |
| 设备元数据 | `~/Library/Application Support/Qiaomu/Kindle/devices.json`（0600，非秘密） |
| 转换器 | `~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack/lib/kindleunpack.py`（GPL，独立安装） |
| 私钥 | **仅 macOS 钥匙串**，service `ai.qiaomu.kindlesync`，account = `credential_id` |
| 传输 | SSH/SFTP，KOReader 模式端口 **2222**；主机密钥指纹固定 |

## 2. 安装与配对

```bash
RT="$HOME/Library/Application Support/Qiaomu/Kindle/runtime/bin/python3"
SK="$HOME/DeepSeek Harness/Kindle/skills/qiaomu-send2kindle"

# 运行时（用真实路径的 Python，不要用指向 uv 的符号链接，否则 venv 的 home 会记错）
"$RT" "$SK/scripts/setup_runtime.py"

# 配对（Kindle 需 USB 连接、KOReader 已退出）
"$RT" "$SK/scripts/send_to_kindle.py" pair --usb '/Volumes/Kindle' --mode koreader
# 配对会写 koreader/settings/SSH/authorized_keys，并设置 SSH_port/SSH_autostart/SSH_key_only_auth
# 原 settings.reader.lua 会备份为 *.qiaomu-skill-backup-<ts>

# 设备端打开 KOReader（SSH 自动启动），然后首次信任
"$RT" "$SK/scripts/send_to_kindle.py" connect --host <设备IP> --mode koreader --trust-new-device
"$RT" "$SK/scripts/send_to_kindle.py" discover      # 之后按固定身份找设备
```

## 3. devices.json 结构（状态目录丢失时按此还原）

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

**恢复要点**：只要钥匙串里 `credential_id` 对应的私钥还在，就不必重新配对；还原元数据后 `status` 应返回
`ok:true, credential_present:true`。若钥匙串条目也丢失，则只能重新 USB 配对（旧身份无法恢复）。

## 4. 使用

````bash
"$RT" "$SK/scripts/send_to_kindle.py" status
"$RT" "$SK/scripts/send_to_kindle.py" inspect "/绝对路径/书.epub"   # 元数据 + 结构校验（传书前必做）
"$RT" "$SK/scripts/send_to_kindle.py" send    "/绝对路径/书.epub"    # 收据 ok:true 才算送达
"$RT" "$SK/scripts/send_to_kindle.py" send    "/绝对路径/书.epub" --mode native   # 原生阅读器（EPUB→AZW3）
````

**前提三件**：Kindle 唤醒 + 同 Wi-Fi + **KOReader 正在运行**（SSH 随 KOReader 启停；退出 KOReader 即断）。

## 5. 本地增强补丁（AZW3/MOBI → EPUB 自动转换）

上游只做 EPUB→AZW3（native）。本机新增 KOReader 模式下的**反向转换**（KOReader 不支持 KF8/AZW3）：

| 源格式 | 处理 | 收据 |
|---|---|---|
| `.epub` | 直传 | `converted:false` |
| `.azw3` | KindleUnpack → EPUB（取 `mobi8/*.epub`） | `converted:true`, `engine: kindleunpack-mobi8` |
| `.azw/.mobi/.prc` | KindleUnpack 解包 → 按 OPF 重打包 EPUB | `converted:true`, `engine: kindleunpack-mobi7` |

改动（详见技能内 `LOCAL_PATCHES.md`，均带 `[local patch]` 标记）：

1. 新增 `scripts/epub_convert.py`：转换 + 结构校验 + 源文件哈希不变校验；失败一律不上传。
2. `scripts/kindle_convert.py`：`prepare()` 增加 koreader 模式非 EPUB 的转换分支。
3. `scripts/send_to_kindle.py`：`EXTENSIONS` 增加 `.prc`、MOBI 头校验加 `.prc`、`delivery_receipt()` 支持双向转换校验。

实测：KF8（2.2 MB→1.7 MB epub）、MOBI7（公版书 580 KB→362 KB epub）、EPUB 直传回归均 `ok:true`。
DRM 文件不转换、不假装成功。

## 5.1 设备文件名（豆瓣书名）

`send` 默认 `--name-mode douban`：调用 `name_policy.py` 查豆瓣书名作为设备文件名
（中文书名用中文、英文书名用英文）；豆瓣不可用时回退 EPUB 元数据书名，再回退源文件名。
`--name-mode metadata|source` 可分别改为元数据书名/源文件名。重名自动加 `(2)`。
收据字段：`name_source`、`title`、`douban_url`、`renamed_from`。

## 6. 安全边界

- 转换产物必须是合法 EPUB（mimetype 置首、container.xml、OPF、≥1 xhtml、zip 无损坏），否则不上传。
- 源文件在转换期间变化 → 中止。
- 主机身份变化 → 立即停止认证（不提供"忽略指纹"开关）。
- 私钥只在进程内存中使用，不进 argv/日志/临时文件；无明文回退。
- `inspect` 与 `quality_check.py` 是**两道独立门禁**：前者保证"能被发送"，后者保证"值得发送"。