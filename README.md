# VoltSet SM8850 patch — pass the compatibility check and keep your undervolt across reboots

**TL;DR (English)** — On some SM8850 (Snapdragon 8 Elite Gen 5) devices, `init` never mounts
debugfs, so VoltSet's `qcom_voltage_adj` compatibility check fails with `UNSUPPORTED`. This
project patches the backend shell script (no manifest / resources / dex changes) to mount
debugfs inside a private mount namespace, and adds six more layers so that the selected
voltage Set is re-applied after a reboot. Tested on a REDMI K100 Pro Max (M098FE), kernel
`6.12.69-android16-6-g0a1dc0413ec7`. **Modifying PMIC voltage can damage your device — use at
your own risk.**

---

## 问题是什么

VoltSet（[上游](https://github.com/rfj53005-gif/VoltSet)）通过内核的 `qcom_voltage_adj`
接口切换 CPU 电压档位（Set）。这个接口只以 debugfs 节点形式存在：

```
/sys/kernel/debug/qcom_voltage_adj/{get_overrides,set_overrides}
```

但部分 SM8850 机型的 `init` **根本不挂载 debugfs**，于是：

- 驱动 `qcom_voltage_adj.ko` 明明已经加载（`/proc/modules` 可见）
- 节点却不存在 → VoltSet 判 `[UNSUPPORTED] 不支持本机 OEM Set 调压`

另一个问题是**持久性**：写入的 Set 索引只进 PMIC 的 SDAM（0x7151），XBL 下次开机读它；
一旦 SDAM 掉电清空，就回落到 CDB 里的默认 Set 1，表现为“重启后电压恢复原状”。

## 做了什么

改造**只发生在后端 shell 脚本**（`assets/backend/voltset.sh`），不碰 `AndroidManifest.xml`、
不改 `resources.arsc`、不注入 dex，因此不会破坏 App 本身。

| 层 | 机制 | 解决什么 |
|---|---|---|
| L1 | 私有 mount namespace 挂 debugfs | 过检测；且挂载对其它进程不可见 |
| L2 | 应用 Set 后记录 `last-set` + 用户标记 | 重启后忘记档位 |
| L3 | 打开 App 时自动补齐 `last-set` | 装完没应用过，钩子无目标 |
| L4 | 打开 App 时检测漂移并修复（限用户态） | 被意外改回后自动恢复 |
| L5 | 开机钩子 `service.d` 重放 | 开机后自动恢复档位 |
| L6 | 写入 5 次重试 + 回读校验 | 驱动晚就绪导致静默失败 |
| L7 | 每次打开生成诊断文件 | 远程定位问题 |

### L1 为什么必须用 C

`unshare -m` 单独使用会泄漏：Android 的 `/` 是 shared 传播，namespace 内的挂载会传播回父
namespace。必须在 namespace 内再执行 `mount("/", MS_REC|MS_PRIVATE)`，而 toybox 的 `mount`
不支持 `--make-rprivate`，只能落到 `mount(2)` 系统调用 —— 这就是 `vsetns` 存在的理由。

实测：只 `unshare -m` 时外部 `/proc/mounts` 计数为 1，加 `MS_PRIVATE` 后为 0。

### L3/L4 为什么需要一个标记

L3 会写入一个默认目标（Set 6）。如果没有 `last-set.from-user` 标记，L4 会立刻认为“当前值
与记录不一致 = 漂移”，结果就是**只打开 App 看一眼，电压就被自动改掉**。标记保证“查看不改硬件”。

---

## 前置条件（缺一不可）

1. SoC 为 **SM8850**，且内核里有 `qcom_voltage_adj.ko`
   ```sh
   ls /vendor/lib/modules | grep voltage_adj
   ```
2. Root（KernelSU / Magisk / APatch），并且存在 `/data/adb/service.d`
3. 内核 `CONFIG_DEBUG_FS=y`
   ```sh
   zcat /proc/config.gz | grep DEBUG_FS
   ```

驱动不存在的机型**无解**：接口不存在，任何用户态方案都碰不到 PMIC 的调压入口。

---

## 构建

需要：`gcc`（aarch64 静态）、`python3`、`zipalign`、`apksigner`、VoltSet 0.2.0 原始 APK。

```sh
gcc -O2 -static -s -o vsetns src/vsetns.c

python3 tools/repack.py \
    /path/to/voltset-0.2.0-original.apk \
    assets/backend/voltset.sh \
    vsetns \
    unsigned.apk

zipalign -f -p 4 unsigned.apk aligned.apk
apksigner sign --ks your.jks --out signed.apk aligned.apk
apksigner verify signed.apk
```

**唯一的坑**：APK 声明了 `extractNativeLibs=false`，所以 `lib/**/*.so` 必须保持
`ZIP_STORED`。用 `unzip/zip` 重打包会压缩它们，安装时报
`INSTALL_FAILED_INVALID_APK: Failed to extract native libraries, res=-2`。
`repack.py` 逐条复制原包条目并保持压缩类型，因此不会触发这个问题。

签名密钥请**自备**：用不同密钥签名的包无法覆盖安装，必须卸载重装，
而重装会改变应用 UID，导致 KernelSU 的 root 授权失效（需要重新授权）。

---

## 安装

```sh
# 从官方包换过来（签名不同，必须先卸载）
pm uninstall io.voltset.sm8850
pm install signed.apk

# 或者：从本项目旧版本升级（同一密钥），不需要卸载
pm install -r signed.apk
```

装完：打开 App → 授权 root → **再打开一次** → 应用想要的 Set。

---

## 验证

```sh
cat /data/adb/voltset/last-set                          # 记录的目标，如 "6 6"
ls -l /data/adb/service.d/99-voltset-bootapply.sh       # 开机钩子
cat /data/adb/voltset/bootapply.log                     # 重放日志
cat /sys/kernel/debug/qcom_voltage_adj/get_overrides    # 重启后应为目标档位
grep -c ' /sys/kernel/debug ' /proc/mounts              # 应为 0（无可见挂载）
```

诊断汇总在 `/sdcard/Download/voltset-diag.txt`，每次打开 App 刷新，方便远程排查。

---

## 已知限制

1. 装完必须打开 App 一次，钩子才会写入
2. 应用过一次 Set 之后才会产生用户态标记，L4 才开始生效
3. 开机后长时间不解锁（>30 分钟），本次开机不重放
4. 卸载 App 后钩子仍留在 `service.d`，彻底不用时需手动删除
5. 不同内核构建的行为可能不同（本项目只在 `g0a1dc0413ec7` 上验证过）

## 免责声明

修改 PMIC 电压属于硬件级操作。虽然本项目只切换固件预置的 Set（不会写入任意电压值），
但仍可能导致不稳定、重启，极端情况下损坏硬件。**风险自负**。
本项目与 Qualcomm、小米、REDMI 及 VoltSet 上游作者均无关联。

## License

衍生自 VoltSet（Apache License 2.0），修改说明见 [NOTICE](NOTICE)，许可证全文见 [LICENSE](LICENSE)。
