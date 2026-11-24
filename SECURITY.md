# Security

## 不会随本仓库分发的东西

- **签名私钥**（`*.jks` / `*.keystore`）：由使用者自行生成并保管。私钥泄露意味着
  他人可以签发能覆盖安装的"更新"，请勿提交到任何仓库。
- **预编译 APK**：只通过 Releases 分发，不进入 Git 历史。
- **原版 APK 与上游内核模块**：属于上游发布物，请从其官方渠道获取。

## 本项目的权限面

改造后的后端脚本以 root 运行，会读写：

- `/sys/kernel/debug/qcom_voltage_adj/*`（仅在私有 mount namespace 内）
- `/data/adb/voltset/`（运行状态、日志、钩子）
- `/data/adb/service.d/99-voltset-bootapply.sh`（开机重放钩子）
- `/sdcard/Download/voltset-diag.txt`（诊断报告）

诊断文件包含机型、内核版本、电压索引，**不包含**账号、序列号或用户数据。
如需报告问题，请先自行检查该文件内容。

## 报告问题

请开 issue 并附上：
1. `uname -r` 与机型
2. `ls /vendor/lib/modules | grep voltage_adj` 输出
3. `/sdcard/Download/voltset-diag.txt` 内容
4. `cat /data/adb/voltset/bootapply.log`
