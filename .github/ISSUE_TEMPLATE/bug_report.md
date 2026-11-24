---
name: Bug report
about: 报告“不生效 / 重启恢复 / 检测失败”
title: "[bug] "
labels: bug
---

## 机型与内核
```
（贴 uname -r 与 ro.product.model）
```

## 驱动是否存在
```
ls /vendor/lib/modules | grep voltage_adj
```

## 诊断文件
把 `/sdcard/Download/voltset-diag.txt` 的内容贴在这里（每次打开 App 会刷新）。

## 开机日志
```
cat /data/adb/voltset/bootapply.log
```

## 现象
（例如：重启后 `get_overrides` 回到 1；或检测仍显示 UNSUPPORTED）
