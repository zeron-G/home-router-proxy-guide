# 掉线、资源限制和恢复经验

> 作者：zeron-G · 最后核对：2026-10-06

## 实际发生了什么

最初启动全部 106 个节点的健康检查和自动选择测试后，出现可用内存降至约 1 MiB、负载接近 15.8 的情况，随后 SSH 和管理请求中断，主人的已有 SSH 会话也掉线。设备后来恢复 / 重启，才继续排障。

这些观察支持“内存和并发检查造成明显资源压力”的判断，但没有保存到足够的 OOM / panic 证据，不能把掉线的唯一原因说成已经证明。操作中让大量节点同时检查，是本次需要避免重复的失误。未写入 mtd、未刷固件、未恢复出厂。

## 采取的修正

- 订阅改用本地文件，停止一次性 URL 的重复更新。
- 原节点文件备份；按主人要求缩减为香港、日本、美国 54 节点。
- URLTest 只使用三个代表节点，lazy 模式，900 秒间隔。
- 使用较小的中国规则库；平时日志等级保持 warning。
- 两份 procd 服务定义均显式设置 `GOMEMLIMIT=12MiB GOGC=30`。
- 检查真实核心 `/proc/<PID>/environ`，避免只改了交互式 shell 环境而服务没有继承。
- 修复 SSH、自启动、iptables 扩展路径和控制器就绪地址，正常重启后重新检查。

`GOMEMLIMIT` 是 Go 运行时软目标，不是整个进程的硬 RSS 上限，二进制映射等不在它的完整覆盖范围。2026-10-06 的一次检查中核心 RSS 为 50208 KiB（约 49 MiB），系统 MemAvailable 约 8988 KiB，仍然余量较小。降低 GOGC 也会增加垃圾回收工作；不能把这组参数当成通用最佳值。[Go 官方说明](https://pkg.go.dev/runtime#hdr-Environment_Variables)

## 日常检查命令

```sh
uptime
free
df -k /data
pidof CrashCore
grep -E 'VmRSS|Threads' /proc/$(pidof CrashCore)/status
tr '\0' '\n' </proc/$(pidof CrashCore)/environ | grep -E '^GOMEMLIMIT=|^GOGC='
export XTABLES_LIBDIR=/data/ShellCrash/tools/iptables
iptables-save | grep shellcrash
ip rule show
ip route show table 100
uci -q get firewall.ShellCrash.path
uci -q get firewall.ShellCrash.enabled
```

用 `iptables-save` 前设置扩展目录；不要只根据 `ps` 显示的巨大虚拟内存就判断 RSS。日志先短时间采集，再恢复 warning，不持续写入闪存。

## SSH 断开时

先判断 Wi-Fi、LAN 网关网页、SSH 端口是否还响应，确认电脑连接了目标路由器。保留时间、负载、内存、核心 PID 和日志，不盲目开启更多测试进程。

本次在原厂网页管理权限仍可用时，参考主人提供的对应固件帖子恢复 SSH。相关历史漏洞与固件强绑定，帖子里的命令不能当通用恢复脚本。本库不附会话令牌、认证密码或可直接批量执行的漏洞脚本。

如果连 LAN 管理也完全无响应，远程无法可靠发出重启；由主人给设备断电约十秒再上电，不按 Reset。正常重启、恢复出厂和刷机是不同操作，不能相互替代。

## 回退分流配置

修改前保留日期化备份，例如：

```sh
cp /data/ShellCrash/yamls/config.yaml /data/ShellCrash/backups/config-before-change.yaml
chmod 600 /data/ShellCrash/backups/config-before-change.yaml
```

配置错误时恢复最近可用的 YAML，并通过核心 API 或 ShellCrash 管理命令重载。通过 API 操作需要认证密钥，不要把密钥写进 Git、截图或公开命令历史。

必要时从 LAN SSH 执行 `/data/ShellCrash/start.sh stop` 停止代理并撤销其规则，再检查普通上网是否恢复；这会中断正在使用代理的连接。在本次原厂网络配置不变的部署方式下，可用来隔离代理层故障。未针对所有异常状态逐项验证停止后的恢复，所以实际仍需查看防火墙和 DNS 状态。

不要执行无目标的 `iptables -F`、删除网络配置、启动第二个核心做 `-t`，也不要为了修一个游戏把全屋全部 UDP 都改为直连。

## 升级与长期限制

固件升级可能重置 SSH、启动 hook 或用户态 ABI；本次只验证一次正常重启。升级前下载私人备份，记录版本、文件校验、实际路由，并安排恢复窗口。

这台设备在代理工作时剩余内存有限，尚无连续多日、全屋下载和游戏同时运行的稳定性证据。出现再次掉线或明显延迟时，先检查资源和实际连接，再决定减少功能或把代理迁到资源更多的设备。
