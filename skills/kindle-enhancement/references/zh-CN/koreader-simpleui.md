# KOReader + SimpleUI 参考（Kindle / PW3）

## 1. 选包

| 设备平台 | 包名 |
|---|---|
| PW3 / PW2 / KV / KT2 等 soft-float（无 `/lib/ld-linux-armhf.so.3`） | `koreader-kindlepw2-v*.zip` |
| 5.16.3+ hard-float（PW4/KT4 之后多数） | `koreader-kindlehf-v*.zip` |
| 很老的 K4/K5 | `koreader-kindle-v*.zip` / `koreader-kindle-legacy-v*.zip` |

包结构：`koreader/`（主程序，含 `reader.lua`、`koreader.sh`、`dropbear`、`plugins/`）+ `extensions/koreader/`（KUAL 菜单）。

## 2. 安装（无 KUAL 时）

1. 解压到设备根目录：`unzip -q -o koreader-kindlepw2-*.zip -d /Volumes/Kindle`
2. 放启动器 scriptlet 到 `documents/KOReader.sh`：
   ```sh
   #!/bin/sh
   # Name: KOReader
   # Icon: /mnt/us/koreader/resources/koreader.png
   mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
   cd /mnt/us/koreader || exit 1
   exec sh ./koreader.sh
   ```
   原因：`/mnt/us` 可能是 noexec，而 KOReader 直接执行 `reader.lua`；scriptlet 由越狱装的 shell integration 运行（可点击）。
3. 插件放 `koreader/plugins/<name>.koplugin/`（目录名必须精确，不能多一层）。
4. macOS 解压后清理 `._*` / `.DS_Store`。

## 3. SimpleUI（乔木定制版）

- 要求 KOReader **≥ v2026.03**；Release 用 `simpleui.koplugin.zip`（不要用 GitHub 源码 zip），并用官方 `SHA256SUMS` 校验。
- 目录：`koreader/plugins/simpleui.koplugin/`；依赖自带 **CoverBrowser** 插件启用。
- 首启后建议：设置 → 主页 → 行为 → 以主页启动；首页加"平铺书库"。
- AI 功能需「工具 → 乔木 AI → 用手机配置」扫码填 API Key（存 `/var/local/qiaomu/ai.json`，USB 不可见）。

## 4. 高频坑：书库空 / 书看不见

KOReader 的书库根目录来自 `settings.reader.lua` 的 `home_dir`。若被设成空目录（如 `/mnt/us/Books`），
即使书在 `documents/` 里也**不显示**。

修复（**必须先退出 KOReader**，否则退出时会回写覆盖编辑）：

```
["home_dir"]         = "/mnt/us/documents"
["lock_home_folder"] = false
["lastdir"]          = "/mnt/us/documents"
```

改动前备份 `settings.reader.lua`；改完确认仍是合法 Lua 表（`return { … }`，无 BOM/CRLF 问题）。
`/mnt/us/documents` 同时是无线传书目标目录，所以修好后新书即时可见。

## 5. 格式支持（实测 v2026.07.1）

| 支持 | 不支持 |
|---|---|
| EPUB/EPUB3、PDF、DjVu、FB2/FB3、TXT、HTML(Z)、CHM、DOC/DOCX、MOBI/AZW/PRC（老式 KF7，无 DRM） | **AZW3/KFX（KF8）**、任何 DRM |

依据：`frontend/document/credocument.lua` 只注册了 `azw`/`mobi`/`prc`，没有 `azw3`。
→ 给 KOReader 的书必须 **EPUB**；AZW3 转 EPUB 见 `references/zh-CN/send2kindle.md` §5。

## 6. 设置备份与回滚

- 备份：`settings.reader.lua`、`settings/`（含 `simpleui/`）；插件目录整份备份。
- 回滚：把备份放回原处、删除对应插件目录即可；书/批注/阅读记录不受影响。
- 插件异常：读 `koreader/crash.log` 末尾按时间定位。

## 7. 时钟

出厂重置后 RTC 可能停在旧日期（实测显示 2023-09-18），会导致 KOReader 的网络/证书相关功能异常（OTA、AI、资讯）。
在 `设置 → 设备选项 → 设备时间` 校正，或连 Wi-Fi 等待自动同步。