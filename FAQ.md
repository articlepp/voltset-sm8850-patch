# FAQ

### 重启后电压恢复成 Set 1，是不是没生效？
不是。`set_overrides` 写的是 PMIC 的 SDAM（0x7151），XBL 下次开机读它；SDAM 掉电就丢，
XBL 回落到 CDB 默认 Set 1。本项目用开机钩子重放来解决，日志见
`/data/adb/voltset/bootapply.log`。

### 为什么热重启保得住、断电就丢？
长按重启只复位 SoC，不断电池，SDAM 所在的 always-on 域仍有电；真正断电才清空。

### 会不会变砖？
本项目**只切换固件预置的 Set**，不写入任意电压值、不改分区、不改 boot，理论上不会变砖。
但深档位可能导致不稳定或重启；出问题时删掉
`/data/adb/service.d/99-voltset-bootapply.sh` 即可不再自动重放。

### 装完提示“无法启动 Root 权限请求”
重新签名后应用 UID 变了，KernelSU 授权按 UID 记录。去 KernelSU → 超级用户 →
找到 VoltSet → 允许，再打开一次 App。

### 支持哪些机型？
只支持 **SM8850** 且内核里有 `qcom_voltage_adj.ko` 的机型：
```sh
ls /vendor/lib/modules | grep voltage_adj
```
没有这个模块的机型无解——接口不存在。

### 打开 App 后电压没变？
这是设计如此：只有**应用过 Set** 之后才会自动重放，单纯查看不改硬件。

### 怎么确认真的生效？
```sh
cat /sys/kernel/debug/qcom_voltage_adj/get_overrides
```
重启后几秒读取，应该是目标档位而不是 `1`。

### 卸载后还要做什么？
删掉遗留的开机钩子：
```sh
rm /data/adb/service.d/99-voltset-bootapply.sh
```
