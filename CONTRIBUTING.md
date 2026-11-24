# Contributing

欢迎提交补丁与机型反馈，尤其是**其它内核构建**上的验证结果。

## 提交前自检

```sh
sh -n assets/backend/voltset.sh        # 语法
gcc -O2 -static -s -o /tmp/vsetns src/vsetns.c   # 能编译
bash tools/verify.sh path/to/built.apk           # 七层机制是否都在包里
```

## 代码约定

- 后端脚本必须保持 `#!/system/bin/sh` 且仅使用 toybox 已有的命令
- 新增逻辑必须能在**没有 root 之外依赖**的情况下失败退让（脚本里到处是 `|| :`，别删）
- 任何会改变电压的行为都必须有开关或标记，避免"只是打开 App 就改硬件"

## 报告机型兼容性

请提供第四节四项信息（见 SECURITY.md），并说明：
- 是热重启丢、还是断电丢
- `get_overrides` 重启后是 `1` 还是目标值
