# 03 · KOReader 插件：SimpleUI / 微信读书 / SSH

> 目标：类手机主页（SimpleUI）、中文书源（微信读书）、远程访问（SSH）。
> 前提：`references/02-koreader.md` 完成，KOReader 能正常启动。
> 通用规则：插件目录名必须严格为 **`<名字>.koplugin`**，装完**必须重启 KOReader** 才加载。

---

## 1. SimpleUI（类手机主页：平铺书架 / 资讯 / AI 划词）

### 1.1 版本要求

- KOReader **≥ v2026.03**（本机 v2026.07.1 ✅）
- 依赖 KOReader 自带 **CoverBrowser** 插件（默认启用；若关掉需重新打开）

### 1.2 下载与校验（一定要用 Release 包，不要用 Source code zip）

```bash
cd ~/Downloads && mkdir -p simpleui && cd simpleui
TAG=v3.0.0-qiaomu.16      # 以 Releases 页面最新为准
BASE=https://github.com/joeseesun/qiaomu-simpleui/releases/download/$TAG
curl -L -O $BASE/simpleui.koplugin.zip
curl -L -O $BASE/SHA256SUMS
shasum -a 256 -c SHA256SUMS        # 期望：simpleui.koplugin.zip: OK
```
> 本机实测：`simpleui.koplugin.zip` = 2,685,672 B，sha256 `4d7b5329c86bbcdab29662dc6de32e52beca34e453c8e79723fc65871fbd1790`。

### 1.3 安装

```bash
VOL=/Volumes/Kindle
mkdir -p "$VOL/koreader/plugins"
# 先备份旧版本（如果有）
[ -d "$VOL/koreader/plugins/simpleui.koplugin" ] && \
  mv "$VOL/koreader/plugins/simpleui.koplugin" "$VOL/koreader/plugins/simpleui.koplugin.bak-$(date +%Y%m%d-%H%M%S)"
unzip -q -o simpleui.koplugin.zip -d "$VOL/koreader/plugins"
ls -d "$VOL/koreader/plugins/simpleui.koplugin"                  # 目录名必须完全一致
find "$VOL/koreader/plugins/simpleui.koplugin" -type f | wc -l   # 本机 673
grep -E 'version' "$VOL/koreader/plugins/simpleui.koplugin/_meta.lua"   # 3.0.0-qiaomu.16
```

### 1.4 使用

重启 KOReader → 主页变成 SimpleUI。建议设置：
- 设置 → 主页 → 行为 → 开启「以主页启动」
- 首页添加「平铺书库」模块（跨子文件夹显示封面）
- 长按文件可「从主页和书库隐藏」（只影响显示）

AI 功能（可选）：工具 → **乔木 AI → 用手机配置** → 扫码填 API Key（存 `/var/local/qiaomu/ai.json`，USB 不可见）。

---

## 2. 微信读书插件（中文书，合法订阅内阅读）

### 2.1 说明与风险（先读）

- 第三方开源客户端（作者 finlater），通过微信读书官方 API 读取**你自己账号**的书。
- 作者声明：可能存在**账号风控**风险，使用后果自负；**扫码登录必须本人操作**，API Key 不要外发。
- 与 SimpleUI 的关系：装了它，SimpleUI 会自动注册「微信读书」快捷入口。

### 2.2 下载与校验

```bash
cd ~/Downloads && mkdir -p weread && cd weread
TAG=v1.6.0
BASE=https://github.com/finlater/weread.koplugin/releases/download/$TAG
curl -L -O $BASE/weread.koplugin-$TAG.zip
curl -L -O $BASE/weread.koplugin-$TAG.zip.sha256
shasum -a 256 -c weread.koplugin-$TAG.zip.sha256     # 期望 OK
```
> 本机实测：`weread.koplugin-v1.6.0.zip` = 910,252 B，sha256 `647abca30fe7638d67c5c24e483409acdedaa758194f177863d1385365258d51`。

### 2.3 安装

```bash
VOL=/Volumes/Kindle
unzip -q -o weread.koplugin-v1.6.0.zip -d "$VOL/koreader/plugins"
ls -d "$VOL/koreader/plugins/weread.koplugin"
find "$VOL/koreader/plugins/weread.koplugin" -type f | wc -l   # 本机 91
grep -E 'version' "$VOL/koreader/plugins/weread.koplugin/_meta.lua"   # 1.6.0
```

### 2.4 登录（3 步，本人操作）

1. 手机 **微信读书 App → 我 → 设置 → 微信读书 Skill → 获取 API Key**（确认已生成）。
2. 设备 KOReader → **工具 → 微信读书 → 微信扫码登录**。
3. 微信扫码 + 手机确认；若手机显示**四位验证码**，在 KOReader 输入。

登录后：微信读书 → 书架 → 选书 → 章节/全书下载 → 用 KOReader 阅读（进度、时长、划线可同步）。
更新插件：微信读书 → 设置 → 更新管理。

---

## 3. SSH 插件（KOReader 自带，传书与远程排障的基础）

KOReader 自带 `plugins/SSH.koplugin` + 补丁版 `dropbear`。

| 项 | 值 |
|---|---|
| 端口 | 默认 **2222**（设置键 `SSH_port`） |
| 公钥文件 | `/mnt/us/koreader/settings/SSH/authorized_keys` |
| 自启 | `SSH_autostart = true`（由 send2kindle 配对时写入） |
| 只能密钥登录 | `SSH_key_only_auth = true` |
| 启动方式 | KOReader → 工具 → SSH server（勾选）；或随 KOReader 启动自启 |
| 生命周期 | **KOReader 退出即停止**；设备休眠/断网也会不可达 |

验证（电脑侧）：
```bash
nc -z -G 2 -w 2 <kindle-ip> 2222 && echo "SSH 在线"
```

---

## 4. 通用验证

```bash
VOL=/Volumes/Kindle
ls "$VOL/koreader/plugins" | grep -E 'simpleui|weread|SSH'
grep -h 'version' "$VOL/koreader/plugins"/{simpleui,weread}.koplugin/_meta.lua
```
设备上重启 KOReader 后：
- 主页 = SimpleUI 样式
- 工具菜单出现「微信读书」
- 工具 → SSH server 可勾选

---

## 5. 常见问题

| 现象 | 原因/处理 |
|---|---|
| 插件不出现 | 目录名不是 `<名字>.koplugin`、多一层嵌套、或没重启 KOReader |
| SimpleUI 报错/白屏 | KOReader 版本 < 2026.03；或 CoverBrowser 被关掉 |
| 微信读书入口没出现 | 插件未重启加载；或 SimpleUI 底栏已满（去 SimpleUI 快捷动作设置里手动添加） |
| 微信读书登录失败 | 手机端未开通「微信读书 Skill」/API Key；或账号风控 |
| 装了插件后 KOReader 起不来 | 移到 `.bak` 目录逐个排除（插件冲突），必要时看 `koreader/crash.log` |
