# 2026-10-10：代理退出后的全屋断网恢复

> 记录者：Codex · 最后核对：2026-10-10

## 现场与原因

主人反馈路由器已无法使用，随后用电脑的“以太网 2”连接 LAN。实测网口链路、DHCP 地址、管理页面及 root SSH 均有响应，上联路由器与公网 IP 能 ping 通。整机 uptime 为两天多，boot ID 与 10 月 7 日最后一次检查相同。

当时 Mihomo 核心没有进程，面板端口关闭，procd 实例为 `running=false`；但 DNS 重定向至 1053 和 TPROXY 转发规则仍在。客户端 DNS 实测超时。这确认本次全屋访问失败有一条明确链路：**代理核心退出 → 劫持规则残留 → 请求进入没有服务监听的端口**。

核心最初为什么退出仍不明确：当前内核日志和已轮转的系统日志没有对应 OOM / 最后退出记录。10 月 7 日的 OOM 防护没有覆盖核心退出后的规则清理，本次补足该缺口。不能将这次失联说成已经确认固件刷坏或硬件死亡，也不能凭本次恢复认定所有无线故障已排除。

## 本次修复

先保留原服务定义、wrapper、iptables 状态及系统日志，再使用 ShellCrash 原有 `fw_stop.sh` 清理失效规则。通过指定有线网卡地址、直接查询路由器 DNS 的客户端测试确认百度返回 200。

随后修改当前和持久化两份 procd 服务定义，以及 `/data/ShellCrash/tools/core-oom-wrapper.sh`：

- procd 管理一个小型 shell 父进程；实际核心作为子进程运行，子进程 `oom_score_adj=800`，父进程实测为 0。
- 父进程等待核心退出，退出后调用原有 `fw_stop.sh` 清理 DNS / TPROXY 规则和策略路由，使基础联网回退直连。
- 设置显式 `respawn 3600 15 3`，通过 procd 读回确认阈值、延迟和重试参数已实际加载；连续快速失败不会无限循环。
- 每次恢复都调用原有 `afstart.sh` 的就绪检查与规则安装流程；移除原服务中重复的 `afstart.sh &` 调用。
- `/tmp/ShellCrash/core-supervisor.log` 保留有界的启动 / 退出记录，便于后续区分退出码与真实 OOM 证据。

分流、节点订阅和面板密钥没有改动。代理与自动启动当前均开启。变更前私人备份在 `/data/ShellCrash/backups/20261010-before-recovery`；原始日志不上传 Git。

## 实机验证

恢复后以及恢复机制测试后，都以电脑的有线网卡为源地址，直接查询这台路由器的 DNS，并通过 curl 绑定该源地址访问。路由选择和 TPROXY 计数同时核对，排除电脑另外连接的 Wi-Fi 绕路。

| 检查 | 结果 |
|---|---|
| 百度 HTTPS | 200，国内直连 |
| Google generate_204 | 204 |
| YouTube HTTPS | 200 |
| ChatGPT trace | 200，loc=US |
| 代理、DNS、面板监听 | 三个端口恢复 |
| 新核心的 OOM 分数 | 800；父进程为 0 |
| procd 运行与重试参数 | 实际读回为运行中，延迟 15 秒，retry=3 |
| 主人使用反馈 | 确认国内和国外都恢复了 |

为验证退出处理，进行一次明确标记的受控测试：只向已核实的核心 PID 发送 SIGKILL，没有模拟内存耗尽，也没有启动第二个核心。核心退出后，ShellCrash 的跳转规则与策略路由清空，在等待恢复时百度仍返回 200。15 秒后 procd 自动启动新核心，新进程分数仍为 800，DNS / TPROXY 规则重新安装，四站测试再次通过。整机 boot ID 不变。

日志中的这一次 `status=137` 是人为恢复测试，**不是实际 OOM 证据**。手机完整 App 登录、无线覆盖、长时间满载、重试耗尽和下次整机启动没有在本轮重新验证。核心恢复的等待期间国外访问会短暂中断；如果核心持续失败，基础直连可用不代表国外代理已经恢复。

## 仍需核实

运行内存余量仍约 15 MiB。此次修复处理的是核心退出后的恢复和规则清理，没有解决核心所有退出原因，也没有扩大这台设备的物理内存。接手 agent 应先读取当前状态与新日志，不能把短时通过等同于永久稳定。

procd 参数参考：[OpenWrt 18.06 procd shell 接口](https://raw.githubusercontent.com/openwrt/openwrt/openwrt-18.06/package/system/procd/files/procd.sh)。OOM 政策参考：[Linux panic_on_oom](https://docs.kernel.org/admin-guide/sysctl/vm.html#panic-on-oom)。本机实际读回及上述受控测试是本次恢复机制的验证依据。

## 同日补查：确认系统有 OOM 杀进程记录

主人追问是否是内存耗尽后，再进行只读检查，发现 `/proc/vmstat` 中 **`oom_kill 12`**。本次 boot ID 仍相同，说明本次启动以来已经发生过 OOM 杀进程，不再仅是“内存不足的风险推测”。Linux 5.4 的该计数在 OOM killer 处理受害进程时增加；普通的受控 SIGKILL 不会增加此计数。

补查时可用内存多次只有约 4.5～7.2 MiB，核心 RSS 约 42 MiB，内核不可回收 slab 约 56～58 MiB，无 swap。核心 PID 与受控恢复后的进程相同，监督日志没有新的自然退出记录；两次计数检查仍为 12。

该计数不能单独说明被杀的是哪个 PID，也没有事件时间，不能把 12 全部归到代理核心或那次断网。当前仍缺少对应 `Killed process ... (CrashCore)` 的记录。更新后的判断是：**系统确实经历 OOM，内存压力是掉线的重要嫌疑；具体核心退出是否由 OOM 造成尚未逐次证实**。

此前自动恢复修复解决退出后的清理与重试，尚未解决内存耗尽本身。本次补查没有修改设置、停止服务或重启。新的资源快照保存在私人工作目录，供后续核对。

计数语义来源：[Linux 5.4 OOM killer](https://github.com/torvalds/linux/blob/v5.4/mm/oom_kill.c#L801-L836)、[vmstat 计数名称](https://github.com/torvalds/linux/blob/v5.4/mm/vmstat.c#L1141-L1143)。`GOMEMLIMIT` 的软限制语义见 [Go runtime 文档](https://pkg.go.dev/runtime#hdr-Environment_Variables)，不能把 12 MiB 参数当成整个进程的硬 RSS 上限。
