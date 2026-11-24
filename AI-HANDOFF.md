# AI / 工程师交接上下文（VoltSet v6 · SM8850）

> 这份文件的目的是：让另一个 AI 或工程师在**不读聊天记录**的情况下，快速理解
> 做了什么、为什么这么做、哪些路已经试过且失败、当前状态和下一步。
> 读顺序建议：本文 → README.md → voltset-vs-upstream.patch → assets/backend/voltset.sh

---

## 0. 一句话现状

在 REDMI K100 Pro Max（SM8850）上，VoltSet 原版因 debugfs 未挂载而判 UNSUPPORTED；
已通过「私有 mount namespace 挂 debugfs」解决检测，并加了 6 层机制让写入的 Set 在重启后
自动恢复。**离线验证全部通过，真机开机重放尚未闭环。**

---

## 1. 环境事实（实测，非推测）

| 项 | 值 |
|---|---|
| 设备 | REDMI K100 Pro Max，代号 M098FE / songyuan，slot `_b` |
| SoC | SM8850（骁龙 8 Elite Gen 5），2×Oryon 4.608 GHz + 6×3.6288 GHz |
| 内核（用户机） | `6.12.69-android16-6-g0a1dc0413ec7-ab16271006-4k`，页 4096 |
| 内核（另一台对照机） | `6.12.69-android16-6-g43b5ab7e247d-abogki561813157-4k`（**不同构建**） |
| Root | KernelSU，进程 context `u:r:ksu:s0`，管理器 `me.weishu.kernelsu`，SUSFS 可用 |
| 驱动 | `qcom_voltage_adj.ko` 在 `/vendor/lib/modules/`，**已随系统加载** |
| 关键事实 | init **不挂载 debugfs**；手动挂载后节点 `get_overrides`/`set_overrides` 立刻出现 |
| 运行时状态目录 | `/data/adb/voltset/`（App 卸载不清理） |
| 开机钩子目录 | `/data/adb/service.d/`（同目录已存在第三方脚本，证明机制可用） |

目标应用：VoltSet `io.voltset.sm8850` 0.2.0（https://github.com/rfj53005-gif/VoltSet）

---

## 2. 时间线：做过什么、什么失败了（重要，别重走）

### 2.1 已放弃：BOOT_COMPLETED 接收器
**目标**：给 APK 加开机广播接收器，最“正统”的持久化方式。
**为什么放弃**：本机 aapt2 是 Debian 的 2.19（2019 年），`aapt2 link` 读不了 API 36 的
框架资源，报 `RES_TABLE_TYPE_RES_TABLE_TYPE_TYPE entry offsets overlap actual entry data`；
换成系统 aapt2 后只缺 `--no-compile-sdk-metadata`，做过滤包装器后仍失败于框架 APK 解析。
用 API 23 的 android.jar 亦不可行（缺 `dataExtractionRules` 等新属性）。
**结论**：改清单 + 注入 smali 这条路在 ARM64 上缺少可用工具链，放弃。
**替代**：改后端 shell 脚本，由 App 在运行时自己安装 `/data/adb/service.d` 钩子。
好处是清单/资源/dex 一个字节不动，风险极低。

### 2.2 已放弃：纯 shell 的 `unshare -m`
**现象**：`unshare -m` 后挂载 debugfs，退出后**外部 `/proc/mounts` 仍能看到**（传播泄漏）。
**原因**：Android 的 `/` 是 shared 传播，新建 namespace 的挂载会向上传播。
**解决**：必须在 namespace 内再 `mount("/", MS_REC|MS_PRIVATE)`；而 toybox 的 `mount`
不支持 `--make-rprivate`（会报 `bad /etc/fstab`），所以只能写 C 调 `mount(2)`。
**验证**：加 `MS_PRIVATE` 后 `outside` 计数从 1 变 0。

### 2.3 踩坑：APK 重打包
`extractNativeLibs=false` 要求 `lib/**/*.so` 保持 `ZIP_STORED`，用 `unzip/zip` 重打会压缩，
安装报 `INSTALL_FAILED_INVALID_APK: Failed to extract native libraries, res=-2`。
改用 Python `zipfile` 逐条复制并指定压缩类型解决（`tools/repack.py`）。
另外：只删 `META-INF` 里的签名文件，**不要整个删 META-INF**（含 androidx 元数据）。

### 2.4 踩坑：重装导致 root 失效
重新签名后重装，应用 UID 从 10276 变 10483/10486，KernelSU 授权按 uid+签名记录，
于是 `sys_execve su` 被拒，App 报“无法启动 Root 权限请求”。**这不是包的问题**，
任何重签 APK 都要重新点一次允许。同一把密钥覆盖升级则 UID 不变、授权保留。

### 2.5 踩坑：`service.d` 在 CE 存储解锁前执行
`/data/user/0/...` 是文件级加密的，钩子早期访问必然失败。改为后台等待 bundle 出现
（最多 30 分钟），整体 `&` 放后台不阻塞开机。

### 2.6 踩坑：自愈逻辑把用户改回默认值
L3 补默认 `6 6` 后，L4 立刻认为“漂移”并重写，导致**只打开 App 看一眼电压就被改**。
解决：加标记文件 `last-set.from-user`，L4 只在有标记时修复。

### 2.7 踩坑：`set_override` 忘记写 `last-set`
早期版本只加了钩子，没在应用时记录目标，导致钩子第一行 `[ -f last-set ]` 就退出——
这是另一台机器“还是会恢复”的真实原因（钩子正常安装、但无目标可重放）。

---

## 3. 文件地图

| 文件 | 作用 | 是否核心 |
|---|---|---|
| `assets/backend/voltset.sh` | 全部改造都在这里（7 层） | ★核心 |
| `assets/backend/bin/vsetns.c` | 私有挂载工具，12 行 | ★核心 |
| `tools/vsetns` | 已编译 aarch64 静态二进制 | 构建产物 |
| `tools/repack.py` | 重打包，保持 `.so` STORED | 工具 |
| `tools/build.sh` | 一键构建 | 工具 |
| `tools/vset.jks` | 签名密钥，升级必须同一把 | 工具 |
| `orig/voltset-0.2.0-original.apk` | 构建输入 | 输入 |
| `voltset-vs-upstream.patch` | 相对上游的 diff | 参考 |
| `extras/SM8850-降压-工作记录.md` | 降压链路与可压空间分析 | 背景 |
| `extras/cdb_patch.py` + `apply_pdp_cdb.sh` | 改 `pdp_cdb` 默认 Set 的工具 | **未执行** |

---

## 4. 七层机制与设计理由

见 README 第一节表格。三条最容易被误解的：

1. **L1 的价值不是“能挂载”，而是“挂载不可见”**——否则检测里 `DEBUGFS` 会暴露。
2. **L3/L4 必须成对理解**：L3 保证钩子永远有目标，L4 保证目标被意外改回时能修复；
   两者靠 `last-set.from-user` 标记解耦，避免“自动补的默认值”触发修复。
3. **L5 的时序**：`service.d` → 等 CE 解锁 → 调后端 `bootapply` → 后端脚本顶部会再次走 L1
   的 shim（因为开机时节点不可见），所以在钩子里不需要自己挂 debugfs。

---

## 5. 已验证 / 未验证（判断能不能交付的关键）

**已验证（离线）**
- `sh -n` 语法；APK 内脚本与包内脚本 SHA-256 一致；签名有效
- 五场景逻辑仿真（继承当前值 / 默认 6 / 自定义默认 / 用户态修复 / 一致不写）
- 私有 namespace 实测：内部可见、外部 `leak 0`（在真机上跑过）
- 后端脚本在真机上以 root 手动执行，输出 `DEBUGFS=/sys/kernel/debug`、`ADJ_AVAILABLE=1`

**未验证**
- v6 真机安装后的完整链路（钩子写入 → 重启 → 重放）
- 不同内核构建（如 `g43b5ab7e247d`）上的行为
- VoltSet 自带 SCMI 读表模块在异构内核上的加载（大概率失败，只影响读电压显示）

---

## 6. 复现与验证命令

```sh
# 环境前提
zcat /proc/config.gz | grep DEBUG_FS          # 需 =y
ls /vendor/lib/modules | grep voltage_adj     # 需有 .ko（没有则本方案无效）
mount -t debugfs debugfs /sys/kernel/debug && \
  cat /sys/kernel/debug/qcom_voltage_adj/get_overrides   # 手动验证接口存在

# 构建
bash tools/build.sh

# 装机后
cat /data/adb/voltset/last-set
ls -l /data/adb/service.d/99-voltset-bootapply.sh
cat /data/adb/voltset/bootapply.log
cat /sdcard/Download/voltset-diag.txt          # 远程诊断汇总
grep -c ' /sys/kernel/debug ' /proc/mounts     # 应为 0
```

---

## 7. 不该做的事（已知风险）

1. **不要改 `pdp_cdb` 分区**，除非先 dump 分析校验字段并确认 fastboot 可用（`extras/` 里有工具，未验证）
2. **不要用不同密钥签名后覆盖安装**——必然要求卸载，root 授权与设置全丢
3. **不要把 L4 的“用户标记”去掉**——会退回“看一眼就改电压”的行为
4. **不要在无 `qcom_voltage_adj` 的机型上硬套**——接口不存在，任何用户态方案都无效
5. **不要同时用 CDT 与 OEM Set 做深压**——`CDT Key 7` 的 SLT+ACD 会与 Set 叠加，实际降压量不可控

---

## 8. 下一步建议（按收益排序）

1. **真机闭环**：装 v6 → 应用 Set → 重启 → 读 `get_overrides`，确认不是 1
2. **异构内核适配**：拿到对照机的 `uname -r`、`voltset-diag.txt`、`bootapply.log`，
   判断是“驱动不存在 / 挂载失败 / 被 XBL 覆盖”中的哪一种
3. **若要彻底不依赖钩子**：改 `pdp_cdb` 里 CFDB 目录的 OVERRIDE 条目（4 字节），
   使其指向目标 Set。前置工作是确认头部 8 字节是否为校验字段（`extras/cdb_patch.py info` 会尝试识别）

---

## 9. 上游与出处

- VoltSet：https://github.com/rfj53005-gif/VoltSet
- 4.61 GHz 不可持续 / 峰值约 20 W：https://meeco.kr/mini/40775092
  、https://wylsa.com/goryachee-nekuda-qualcomm-predstavila-flagmanskij-snapdragon-8-elite-gen-5/
- 极客湾 SM8850 能效分析：https://www.c114.net.cn/industry/24235.html
- `pdp_cdb` / `OEM_VOLTAGE_ADJUSTMENTS` **无公开规范**，文中相关结论均来自设备实测
  与 VoltSet 自带解析器源码（`app/.../PdpCdbParser.kt`）
