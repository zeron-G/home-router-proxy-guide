# 2026-10-07：反复 panic 重启与不中断代理的防护

> 记录者：Codex · 最后核对：2026-10-07

## 新的故障证据

主人反馈退出 Tailscale 后仍频繁突然断网，电脑会断开，手机也疑似无法连接。SSH 实机检查发现路由器 uptime 只有十来分钟，当前启动日志和两份历史启动日志记录 `reset_reason : HLOS Panic [0x47]`。Windows 无线事件也记录了多次驱动断开目标 Wi-Fi。

因此已经确认存在系统 panic 重启；还没有拿到对应的 OOM 或最后 panic 调用栈，不能把唯一根因说成已确定，也没有据此认定设备硬件或固件被“写坏”。启动日志墙钟可能在联网校时前不准确，实际时间要结合 uptime 和客户端事件。

系统当时配置 `vm.panic_on_oom=2`、`kernel.panic=3`。若触发 OOM，这组设置会让系统 panic 并在三秒后重启。Go 的 `GOMEMLIMIT=12MiB` 仍然只是软目标；实测核心 RSS 约 40～50 MiB，可用内存一度只有约 8 MiB。

## 停用对照与实际恢复

短暂对照中，可用内存从 9956 KiB 增至 60260 KiB；重新启动代理后为 18004 KiB，boot ID 没变。这证明代理明显压缩了内存余量，不能证明内存就是所有 panic 的唯一原因。

主人随后同意先暂停代理观察。代理和自启动已暂停，原厂 DNS 与直连恢复，电脑访问百度得到 200；但国外服务失去代理通道，主人反馈“断网”。因此撤回暂停，恢复原来的代理与自动启动，没有重启路由器。

恢复后清理了 Windows DNS 缓存，复测百度 200、Google 204、YouTube 200、ChatGPT trace 200 且 loc=US。普通代理仍选自动组 / 香港代表节点，AI 仍选美国节点。恢复过程中遇到原厂没有 `nohup`，改用原厂服务和 shell 的 HUP 处理启动，最终读回确认核心及规则已恢复。

当前状态是 **代理运行、自动启动开启**，不是暂停观察。手机完整 App 访问没有在本次重新逐项验证。

## 本次增加的 OOM 防护

在不重启当前核心的情况下：

- 将 `vm.panic_on_oom` 设为 0，改用 OOM killer，不因该 OOM 策略主动 panic 整机。
- 当前核心的 `oom_score_adj` 设为 800，使其在 OOM 时比原厂网络与管理服务更优先被终止。
- `/etc/sysctl.conf` 和持久化 `/data/shellcrash_init.sh` 保存政策，启动 hook 会在启动代理前重新应用。
- 两份 procd 服务定义加入 `/data/ShellCrash/tools/core-oom-wrapper.sh`，helper 设置自身 OOM 分数后 exec 核心，供下次正常服务启动 / 重启恢复使用。
- 修改前文件备份在 `/data/ShellCrash/backups/20261007-before-oom-protection`，私人保留。

读回确认 policy 为 0、当前核心分数为 800，helper 的 exec / 继承行为及 shell 语法检查通过。核心 PID 与整机 boot ID 保持不变，随后四个网站复测通过。未人为触发 OOM，未进行新一轮重启测试。

当前 procd 已运行实例的旧启动参数未通过重启替换；helper 在下次正常服务启动时加载。当前进程的分数已直接设置，但若本轮 procd 自动 respawn，不能把当前分数视为必然继承。全局 OOM 政策仍为 0。接手 agent 应读取新 PID 的分数，避免将“当前生效”与“未来所有重启已验证”混为一谈。

这个措施降低 OOM 导致整机重启的风险，没有降低核心本身的内存需求，也不能修复其他驱动 / 内核 panic。OOM 时代理仍可能暂时退出，国外连接可能中断。根因及长期稳定性为待验证；不再未经确认暂停全屋代理。

## 证据保管与来源

原始系统日志、压缩历史日志、Windows 事件和含真实地址的诊断资料保存在本任务私人工作目录，不上传 Git。原厂 `upcrash` 会处理、上传并删除崩溃包；当前未取得完整崩溃包。本次只读取该脚本，没有主动调用其上传或闪存擦除行为。

- [Linux panic_on_oom](https://docs.kernel.org/admin-guide/sysctl/vm.html#panic-on-oom)
- [Linux panic 延时](https://docs.kernel.org/admin-guide/sysctl/kernel.html#panic)
- [Go 运行时环境变量](https://pkg.go.dev/runtime#hdr-Environment_Variables)

后续应取得新的崩溃 / OOM 证据并复核运行状态，不进行全量节点测速、模拟 OOM 或启动第二个核心测试配置。
