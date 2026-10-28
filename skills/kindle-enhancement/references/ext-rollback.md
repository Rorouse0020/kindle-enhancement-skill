# 08 · 回滚与恢复（按需选择粒度）

> 原则：**先恢复 OTA，再重置**；每步都能单独回滚，不要一次全拆。

---

## 1. 单项回滚速查

| 改动 | 备份文件（设备上） | 回滚动作 |
|---|---|---|
| KOReader 书库路径 | `koreader/settings.reader.lua.bak-homefix-*` | 改名回 `settings.reader.lua` |
| 睡眠屏保 | `koreader/settings.reader.lua.bak-wallpaper-*` | 同上，并 `rm -rf /mnt/us/wallpapers` |
| 资讯源目录 | `koreader/plugins/simpleui.koplugin/data/qiaomu_sources.json.bak-rss-*` | 改名回原文件 |
| 资讯"原文优先"补丁 | `koreader/plugins/simpleui.koplugin/features/sui_news.lua.bak-original-*` | 改名回原文件 |
| SimpleUI 插件 | `koreader/plugins/simpleui.koplugin.bak-*` | 删新目录，恢复备份目录 |
| WeRead 插件 | — | `rm -rf koreader/plugins/weread.koplugin` |
| send2kindle 配对（KOReader 设置） | `koreader/settings.reader.lua.qiaomu-skill-backup-*` | 改名回去 + 删除 `settings/SSH/authorized_keys` 中对应行 |
| 睡眠/资讯整体 | 见上 | 也可在 KOReader UI 里改回（设置 → 屏幕 / 睡眠屏幕） |

> 所有 `.bak-*` 都是**原文件的完整副本**，回滚 = 停 KOReader → 改名 → 重启。

---

## 2. 移除 send2kindle 的凭据与元数据

```bash
# 元数据
rm -f "$HOME/Library/Application Support/Qiaomu/Kindle/devices.json"
# 钥匙串条目（service ai.qiaomu.kindlesync，account 为 credential_id）
security find-generic-password -s ai.qiaomu.kindlesync          # 查看
security delete-generic-password -s ai.qiaomu.kindlesync -a '<credential_id>'
# 运行时（可选）
rm -rf "$HOME/Library/Application Support/Qiaomu/Kindle/runtime"
```
设备侧公钥：从 `koreader/settings/SSH/authorized_keys` 删除以 `qiaomu-kindlesync` 结尾的那一行。

---

## 3. ⚠️ 完整撤销越狱（**顺序不能错**）

**错误做法**：直接出厂重置 → 卡在 `Update Failed`（因为 OTA 被封锁、无法安装官方固件）。
**正确顺序**：

```
① 恢复 OTA（必须）
   - 把 ota.sh 放进 /mnt/us/documents/，在书库点一下（会重启）
   - 或 KUAL → Rename OTA binaries → Restore
② 出厂重置（设置 → 设备选项 → 重置 → 恢复出厂设置）
③ 推入同版本官方固件
   - 下载与设备同版本的 update_*.bin（FW 下载表 / FTVDB）
   - 放根目录 → 设置 → 更新您的 Kindle
④ 完成：设备回到未越狱的干净状态（之后可重新越狱）
```

官方恢复 scriptlet：<https://kindlemodding.org/jailbreaking/ota.sh>
固件下载表：<https://kindlemodding.org/firmware-and-flashing/downloading-updates.html>
FTVDB（按机型和版本查包）：<https://ftvdb.com/kindle/firmware/>

---

## 4. 已经卡在 `Update Failed` 怎么救

1. 去 **FTVDB** 找**你机型 + 你当前版本**（或更高）的 `.bin`：
   `https://ftvdb.com/kindle/firmware/`（社区命名与亚马逊命名不同，注意对照表）。
2. 把 `.bin` 放到 USB 根目录（先删掉其它 `update*.bin`）。
3. 弹出设备 → 重启 → 等它自动安装。
4. 装完即为未越狱状态，可重新越狱。

---

## 5. 数据恢复

```bash
# 备份是整盘可见存储的副本；恢复时只还原用户数据即可
VOL=/Volumes/Kindle; BK=/path/to/backup-YYYY-MM-DD
rsync -a --exclude '._*' --exclude '.DS_Store' "$BK/documents/" "$VOL/documents/"
rsync -a --exclude '._*' --exclude '.DS_Store' "$BK/fonts/"     "$VOL/fonts/"
# 书+阅读进度都在 documents/（.sdr 目录保存进度/批注）
```
> 注意：**注销亚马逊账号会清空 `documents/`**，注销前先备份。

---

## 6. 恢复后的自检

```bash
bash scripts/verify-setup.sh /Volumes/Kindle
```
- 只回滚了某一项：对应项会显示缺失/默认值，其余仍绿。
- 完全未越狱：`JAILBROKEN.txt` 缺失属正常，跳过 Phase 2 之后的检查。
