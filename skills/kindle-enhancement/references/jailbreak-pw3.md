# 越狱参考：Kindle PW3 / 固件 5.16.2.1.1（WinterBreak2）

## 1. 方法映射（官方数据）

来源：`https://kindlemodding.org/jailbreaks.json` + `jailbreakFinder.js` 的筛选逻辑（模型在 `models` 中、固件落在 `min~max` 区间、`outliers` 例外）。

对 **PW3 + 5.16.2.1.1** 的匹配结果（按文件顺序）：

| 顺序 | 方法 | 覆盖范围 | 需要注册 |
|---|---|---|---|
| 1 | **WinterBreak2** | 5.6.1.1 – 5.16.3 | ❌ 不需要 |
| 2 | WinterBreak | 5.6.1.1 – 5.18.0.2 | ✅ 需要 |

不支持 PW3 的方法：SpiderCat、Sanctuary、AdBreak、SpringBreak、Nosebleed、Véra。

## 2. 前置事实（实测确认）

- PW3 的**最终固件就是 5.16.2.1.1**：AWS S3 上 `update_kindle_all_new_paperwhite_5.16.2.1.1.bin` 返回 200，而 5.16.3/5.16.4/5.16.5 均 403。
- 因 hard-float 从 **5.16.3** 才开始，PW3 永远是 **soft-float** → KOReader 用 `koreader-kindlepw2` 包。
- 设备可**未注册**越狱（WB2 不要求账号）；但 OOBE 需要绕过（见 §5）。

## 3. 准备步骤（Mac 侧可自动化）

1. **备份**：`documents/ system/ fonts/` 整盘复制到项目目录，逐目录核对文件数一致。
2. **填满存储**（防越狱途下载 OTA）：
   ```bash
   VOL=/Volumes/Kindle; mkdir -p "$VOL/fill_disk"; i=0
   while [ "$(df -m "$VOL" | awk 'NR==2{print $4}')" -gt 90 ]; do
     i=$((i+1)); dd if=/dev/zero of="$VOL/fill_disk/fill_$i.bin" bs=1m count=200 || break
   done
   ```
   目标：剩 **50–90 MB**。PW3 是 USB 大容量模式（非 MTP），脚本/`dd` 直接可用。
   ⚠️ 不要写"带 kill 看门狗的循环 + `set -e`"：`kill` 失败会让脚本误判并把已写好的块删掉（本项目踩过）。
3. **放载荷**：`winterbreak2/dialoger.html` 放到设备**根目录**（解压 `wb2.zip` 的内容，根目录出现 `winterbreak2/`）。
4. 清掉根目录 `update*.bin` / `update.bin.tmp.partial`。

## 4. 漏洞链与 jb.sh（理解后才能排障）

```
体验版浏览器 → https://penguins184.xyz/wb2
  → 点 Jailbreak → /wb2p 返回附件，Content-Disposition 文件名内嵌脚本
  → com.lab126.pillow customDialog 加载设备本地
    /mnt/us/winterbreak2/dialoger.html
  → dialoger 用 nativeBridge(com.lab126.transfer, request_upload) 执行 shell 命令
  → 官方: curl -L https://kindlemodding.org/jb.sh | sh     ← GitHub Pages，国内常失败
  → 本地: sh /mnt/us/jb.sh                                  ← 推荐
```

**jb.sh v2.4.0 关键动作**：停 OTA 服务 → 解包到 `/tmp/kmc` → 拷到 `/var/local/kmc` →
软链 `/var/local/mkk/{su,gandalf}` → 装 `/mnt/us/libkh/bin/fbink` → 删旧 hotfix →
注册 hotfix/emergency/sh_integration（appreg.db）→ 装 kindlet keystore → 关广告 →
系统补丁 → 写 `documents/JAILBROKEN.txt` 与 `/var/local/jailbreak.txt` → `reboot`。

判定平台：`/lib/ld-linux-armhf.so.3` 存在 → kindlehf，否则 **kindlepw2**（PW3 属后者）。
无 DRM、无需联网的脚本本体 8.7 MB，自解压依赖设备自带 `base64/xz/tar`。

## 5. OOBE 与注册

- 出厂重置后设备停在初始设置，**不注册就没有浏览器**。
- 官方绕过（captive portal）：连需要网页认证的公共 Wi-Fi → 认证页浏览器地址栏输入 `;demo` → 弹 demo 模式提示时**必须点 NO** → 点 Home 进系统。
- 注册失败排查（实测）：设备区域若为「中文（中国）」会连已关停的 amazon.cn（现返回 503），美国账号必然报"邮箱或密码不正确"；改选 **English (United States)** 并确认账号国家为 United States。
- 越狱后可跑官方 `disable_oobe.sh`（`documents/` 里点一下）永久关闭 OOBE；不跑则每次重启要重做 demo 技巧。

## 6. 验收与回滚

验收证据（三个都要）：

1. `documents/JAILBROKEN.txt` = `You are jailbroken! / (jb.sh v2.4.0) / … Winterbreak2 Jailbreak`
2. `JB_TRACE.txt`（本地执行版才有）= `DIALOGER_EXECUTED`
3. `libkh/bin/fbink` 存在

回滚（彻底卸载越狱）：恢复 OTA（`ota.sh` scriptlet）→ 出厂重置 → 刷**同版本**官方固件（放根目录 → 设置 → 更新您的 Kindle）。
⚠️ 不要在 OTA 被封锁状态直接出厂重置，会卡在无法更新（需 FTVDB 同版本固件恢复）。