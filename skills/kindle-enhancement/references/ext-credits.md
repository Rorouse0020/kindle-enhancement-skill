# 09 · 第三方组件、许可证与免责声明

本包是**流程文档 + 胶水脚本**，本身不包含任何 Kindle 固件或亚马逊内容。
下列组件由各自作者发布，请遵守其许可证；本包不重新分发它们（除少量脚本/配置由本包作者编写）。

---

## 1. 组件清单

| 组件 | 作者/来源 | 许可证 | 在本流程中的作用 |
|---|---|---|---|
| **WinterBreak2**（wb2.zip） | Scam.Net、Penguins184 / KindleModding | 见其仓库 | 浏览器触发式越狱载荷 |
| **jb.sh**（越狱脚本） | KindleModding | 见 kindlemodding.org | 实际执行越狱（v2.4.0，本机实测 sha256 `cfe16df1…fbbc02`） |
| **KOReader** | KOReader 团队 | **AGPL-3.0** | 阅读器 |
| **SimpleUI**（simpleui.koplugin） | Doctor Hetfield（上游）；joeseesun 定制（qiaomu 版） | **GPL-3.0** | 类手机主页 / 资讯 / AI 划词 |
| **微信读书插件**（weread.koplugin） | finlater | 见其仓库 | 在 KOReader 内读微信读书 |
| **乔木 send2kindle** | joeseesun | 见其仓库（含 THIRD_PARTY_NOTICES） | Wi-Fi 传书 + APK 转换器（Node） |
| **KindleUnpack** | Kevin Hendricks 等 | **GPL-3.0** | AZW3/MOBI → EPUB 转换（独立安装，不随包分发） |
| **Kindle-Filler-Disk** | bastianmarin 等 | 见其仓库 | 填满存储防 OTA |
| **PEKI / MRPI / Hotfix / ota.sh / disable_oobe.sh** | KindleModding | 见其仓库 | 可选：KUAL、越狱保留、OTA 恢复、OOBE 关闭 |
| 壁纸素材 | Wikimedia Commons（公版/CC0）、NASA（公版） | 各自许可，记录在 `wallpapers/sources.json` | 睡眠屏保 |

---

## 2. 本包自有内容

- 文档：CC-BY-4.0（引用请注明来源）
- 脚本（`scripts/*`、`assets/dialoger-local.html`、`assets/KOReader.sh`、`assets/feed_config.lua`）：
  MIT

---

## 3. 免责声明

1. **越狱有风险**：理论上可能变砖、失去保修、影响账号安全。请自行评估，**自担风险**。
2. **不协助盗版**：本包不包含、不指导任何盗版书源（Z-Library / LibGen / Telegram 机器人等）。
   所有格式转换仅针对**无 DRM** 且用户合法拥有的文件；本包**不解密 DRM**。
3. **账号风险**：微信读书插件为第三方客户端，作者声明存在账号风控可能；登录须本人操作，
   API Key / Cookie 不应交给任何人（包括 AI 助手）。
4. **合规**：Amazon 服务条款、所在地法律与设备保修政策由使用者自行确认。
5. **不做担保**：本包按"现状"提供；版本、URL 与服务端接口可能随时间变化，执行前请以官方页面为准。

---

## 4. 关键上游链接

| 用途 | 链接 |
|---|---|
| KindleModding Wiki（越狱总站） | https://kindlemodding.org/jailbreaking/ |
| 越狱向导 | https://kindlemodding.org/jailbreak-wizard.html |
| 防自动更新（填盘） | https://kindlemodding.org/jailbreaking/prevent-auto-update/ |
| What's Next / 包管理器 | https://kindlemodding.org/jailbreaking/whats-next/ |
| OTA 恢复 scriptlet | https://kindlemodding.org/jailbreaking/ota.sh |
| OOBE 关闭 scriptlet | https://kindlemodding.org/jailbreaking/disable_oobe.sh |
| 固件下载表 / FTVDB | https://kindlemodding.org/firmware-and-flashing/downloading-updates.html ｜ https://ftvdb.com/kindle/firmware/ |
| KOReader | https://github.com/koreader/koreader |
| SimpleUI（qiaomu 版） | https://github.com/joeseesun/qiaomu-simpleui |
| 微信读书插件 | https://github.com/finlater/weread.koplugin |
| send2kindle | https://github.com/joeseesun/qiaomu-send2kindle |
| KindleUnpack | https://github.com/kevinhendricks/KindleUnpack |
| 填盘脚本 | https://github.com/bastianmarin/Kindle-Filler-Disk |
