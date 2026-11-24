# Changelog

## v6
- 修复：自动补的默认目标会触发“漂移修复”，导致仅打开 App 就改电压
- 新增 `last-set.from-user` 标记，修复只在用户态生效

## v5
- 新增启动时自动补目标（无记录 → 默认 Set 6）
- 新增启动时漂移修复、bootapply 写入 5 次重试
- 新增 `/sdcard/Download/voltset-diag.txt` 诊断输出

## v4
- 新增远程诊断文件（未发布）

## v3
- 新增开机钩子（`service.d` + 等待 CE 解锁 + 后台执行 + 日志）
- 后端新增 `bootapply` 动作

## v2
- 新增应用 Set 后记录 `last-set`

## v1
- 私有 mount namespace 挂载 debugfs，修复兼容性检测
