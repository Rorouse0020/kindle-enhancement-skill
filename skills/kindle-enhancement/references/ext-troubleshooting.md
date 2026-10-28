# 07 · 排障手册（T1–T12，全部来自实机踩坑）

> 用法：按**症状**查编号；每条含「现象 → 根因 → 诊断命令 → 修复」。
> 通用前提变量：`VOL=/Volumes/Kindle`；SSH 命令用 `ssh root@<kindle-ip> -p 2222`（KOReader 运行时才有）。

---

## T1 ⚠️ 时钟错误 → 所有 HTTPS 失败（本机最坑的一条）

**现象**
- 资讯「更新失败」且列表为空
- `;kpm install` 失败；某些下载/联网功能异常
- curl 报：`SSL certificate problem: certificate is not yet valid`

**根因**
设备时钟停在出厂重置时的时间（本机 2023-09-18），2025/2026 年签发的证书在设备看来"尚未生效"。
**这与证书、DNS、源都没关系**——是时间不对。

**诊断**
```bash
ssh root@<ip> -p 2222 'date'                                  # 年份不对即命中
ssh root@<ip> -p 2222 "curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://www.baidu.com"   # 000 = 全站 HTTPS 失败
```

**修复（越狱后）**
```bash
NOW=$(date '+%Y-%m-%d %H:%M:%S')          # 电脑当前时间
ssh root@<ip> -p 2222 "date -s '$NOW' && hwclock -w && date"
# 验证：baidu / rss.qiaomu.ai 都应返回 200
```
**修复（未越狱）**：设置 → 设备选项 → 设备时间 → 手动设置。

**预防**：每次重置设备/换电池后先查 `date`。已写入 RTC（`hwclock -w`），正常重启会保留。

---

## T2 点 Jailbreak 完全没反应（GitHub Pages 拉不到 jb.sh）

**现象**：出现下载提示 → 之后毫无反应：无对话框、无日志、无重启。

**根因**：官方 `dialoger.html` 执行
`curl -L https://kindlemodding.org/jb.sh | sh`，而该域名是 **GitHub Pages**；
设备直连失败 → `sh` 收到空内容 → 静默退出。

**诊断**（设备上）
```bash
ssh root@<ip> -p 2222 "curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://kindlemodding.org/jb.sh"
# 000 / 403 / 超时 即命中；同时 /mnt/us/JB_TRACE.txt 不会生成
```

**修复**：改用**本地执行变体**（`references/ext-jailbreak.md` §4）
```bash
bash scripts/kindle-prepare-local.sh /Volumes/Kindle 90
# 它会放 jb.sh（官方原版，需核对 sha256）+ assets/dialoger-local.html
```
之后重试页面流程；成功会有 `JB_TRACE.txt`（`DIALOGER_EXECUTED`）与 `JB_LOG.txt`。

---

## T3 越狱日志跑到一半停住

**诊断**：插 USB 读 `/mnt/us/JB_LOG.txt` 末尾。
| 日志线索 | 含义 | 处理 |
|---|---|---|
| `Could not find chattr command` | 固件缺 chattr | 极少见；换越狱方法或升级到受支持固件 |
| `not enough space left in varlocal` | `/var/local` 空间不足 | 清理设备内多余文件后重试 |
| `Failed to setup sh_integration` | appreg 注册失败 | 重启后重试；仍失败看 T2 的本地执行版日志 |

**通用**：重启设备 → 重新走一遍（填盘 → 放载荷 → 触发）。JB 是幂等的。

---

## T4 KOReader 里书库空白 / 看不到 documents 里的书

**根因**：`home_dir` 指向空目录（本机是 `/mnt/us/Books`）且 `lock_home_folder=true`。
**诊断/修复**：`references/ext-koreader.md` §5（改 `home_dir=/mnt/us/documents`、`lock_home_folder=false`）。
> 这条同时解释"传书成功但书架看不到"。

---

## T5 AZW3 打不开：提示"格式不支持"

**根因**：KOReader 格式注册表只有 `azw`/`mobi`/`prc`，**没有 `azw3`**（KF8 解析不了）。不是文件坏、也不是 DRM。
**验证**：
```bash
VOL=/Volumes/Kindle
grep -nE 'addProvider\("(azw|azw3|mobi)' "$VOL/koreader/frontend/document/credocument.lua" | head
```
**修复**：转 EPUB（`references/ext-send2kindle.md` §6）；或改用原生阅读器读 AZW3（原生支持）。

---

## T6 DNS 返回 198.18.x.x（fake-IP）导致联网失败

**现象**：`nslookup rss.qiaomu.ai` → `198.18.7.7` 之类；设备 curl 全部 000。

**根因**：路由器（如 ImmortalWrt + 代理插件）用 **fake-IP** 劫持 DNS；代理客户端在本机（Mac）能处理，**Kindle 没有代理客户端**所以连不上。
> 但如果路由器本身在做透明代理，fake-IP 也能通 —— **先修 T1 时钟再判断**，本机就是时钟问题而非 DNS。

**诊断**
```bash
ssh root@<ip> -p 2222 "nslookup rss.qiaomu.ai"                       # 198.18.x.x = fake-ip
ssh root@<ip> -p 2222 "curl -sS -m 10 --resolve rss.qiaomu.ai:443:<真实IP> -o /dev/null -w '%{http_code}\n' https://rss.qiaomu.ai/api/entries?limit=1"
```
真实 IP 可用公共 DoH 取：
```bash
curl -s 'https://223.5.5.5/resolve?name=rss.qiaomu.ai&type=A'
```

**修复（任选）**
1. 路由器：把 `+.qiaomu.ai` 加入 fake-IP 过滤 / 改 redir-host；
2. 让设备走代理（在路由器上按设备 IP 设规则）；
3. 临时验证：`--resolve` 直连真实 IP（Cloudflare IP 会变，不适合长期）。

---

## T7 USB 插上但电脑不认（无挂载点）

**根因**：**KOReader 正在运行** → 它会 `SIGSTOP volumd`，Kindle 不会以 U 盘方式出现。
**判断**：`nc -z -G 2 -w 2 <ip> 2222` 返回成功 = KOReader 在跑。
**修复**：KOReader → 菜单 → 退出 → 退出 KOReader，回到原生界面，USB 自动挂载。
> 同理：KOReader 运行时改 `settings.reader.lua` 会被它退出时回写覆盖 —— **改设置前必须退出 KOReader**。

---

## T8 rsync 备份卡住 / "file truncated while reading"

**现象**：`rsync -a` 长时间无进展；或大 azw3 报 truncated。
**根因**：Kindle FAT 卷偶发读卡顿（尤其中文长文件名、大文件）。
**修复**：改**逐文件 + 看门狗**：
```bash
SRC=/Volumes/Kindle/system; DST=/path/backup/system; mkdir -p "$DST"
while IFS= read -r -d '' f; do
  rel="${f#$SRC/}"; mkdir -p "$DST/$(dirname "$rel")"
  ( cp -p "$f" "$DST/$rel" & p=$!; ( sleep 10; kill -9 $p 2>/dev/null ) & w=$!
    wait $p 2>/dev/null; r=$?; kill $w 2>/dev/null; exit $r ) || echo "跳过: $rel"
done < <(find "$SRC" -print0)
```
备份完必须**比对文件数**（每个顶层目录源 vs 备份）。

---

## T9 启动器点了没反应 / KOReader 启动即退出

**根因**：`/mnt/us` 可能是 **noexec**，`reader.lua` 无法执行。
**修复**：启动器里先 remount：
```sh
mount -o remount,exec /mnt/us 2>/dev/null || mount -o exec /mnt/us 2>/dev/null
cd /mnt/us/koreader && exec sh ./koreader.sh
```
（见 `assets/KOReader.sh`）

---

## T10 资讯「更新失败」/ 列表为空（非 T1 情况）

按顺序：
1. **T1 时钟**（最常见）。
2. 补丁与配置是否在：`grep -c 'local patch' .../features/sui_news.lua` 应为 2；
   `ls .../news/feed_config.lua`、`data/qiaomu_sources.json` 是否可解析（`python3 -m json.tool`）。
3. 设备上直接测接口：
   ```bash
   ssh root@<ip> -p 2222 "curl -sS -m 15 -H 'X-Rss-List: reader-v1' -o /tmp/n.json -w '%{http_code}\n' 'https://rss.qiaomu.ai/api/entries?limit=10'"
   ```
   200 → 服务正常，问题在本机设置；000 → 查 T1 / T6。
4. 重启 KOReader（插件与配置在启动时加载）。

---

## T11 微信读书插件不出现 / 登录失败

| 现象 | 处理 |
|---|---|
| 工具菜单没有「微信读书」 | KOReader < 2026.03；或没重启 KOReader；目录名不是 `weread.koplugin` |
| 扫码登录失败 | 手机端未开通「微信读书 Skill」/未生成 API Key；或账号被风控 |
| 登录后 SimpleUI 底栏没入口 | 底栏已满 → SimpleUI 快捷动作设置里手动添加 |

---

## T12 睡眠壁纸不生效

| 现象 | 检查 |
|---|---|
| 睡眠仍是"休眠中" | 是否在 **KOReader 内**睡眠？（只在 KOReader 生效） |
| 显示 KOReader logo | `screensaver_dir` 为空/路径错；或目录里没有 KOReader 认的图片格式 |
| 设置被重置 | 改设置时 KOReader 在运行（T7），被回写覆盖 → 退出后再改 |
| 图片很暗/残影 | 图片亮度 < 100 → 提亮（`references/ext-wallpapers.md` §2） |

---

## 通用排查顺序（牢记）

```
1) 时钟对不对？        date
2) 网络通不通？        curl 一个 HTTPS 站点
3) 文件在不在？        ls / cat
4) 版本对不对？        git-rev / _meta.lua
5) 插件/设置加载了吗？ 重启 KOReader 再试
6) 日志说了什么？      koreader/crash.log 末尾、JB_LOG.txt
```
