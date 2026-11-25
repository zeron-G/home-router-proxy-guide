# 2026-11-25：低内存 RD15 上的可复现部署与自编译裁剪内核

> 记录者：[@cloader](https://github.com/cloader) · 最后核对：2026-11-25

## 实机与前提

| 项目 | 实机读取结果 |
|---|---|
| 机型 / 固件 | 小米 BE3600 2.5G（RD15），原厂固件 1.0.87 release |
| 内核 / 架构 | Linux 5.4.213，armv7l，32 位 |
| 系统可见内存 | MemTotal 180428 KiB，无 swap，内核无 zram |
| `/data` | 19952 KiB，部署前可用约 15 MiB |
| 原厂 OOM 策略 | `vm.panic_on_oom=2`、`kernel.panic=3`（内存耗尽即整机 panic 重启） |
| ShellCrash | 1.9.4release，stable 包 SHA-256 `4f946031a0483ed528e266143d459075489cce6c3f8f2f4681f39ca6d7448681` |
| 编译工具 | Go 1.27.3（windows/amd64 交叉编译），UPX 5.3.0 |

本文只记录这一台实机。IP、密钥、订阅、节点名称、会话令牌均未写入。

前提：`/data`、`/etc/config`、`/etc/crontabs` 需为可读写挂载。它们是只读时，写入的自启动配置在重启后会丢失。

## ShellCrash 部署中踩到的坑

以下都是本次实际发生、并已定位的问题：

1. **配置文件编码**。在 Windows 上生成的 `configs/ShellCrash.cfg` 如果不是 UTF-8，`redir_mod=Tproxy模式` 与脚本内的字面量不相等，TPROXY 分支被静默跳过：DNS 劫持规则正常，流量转发规则为 0 条，日志无报错。
2. **`firewall_mod` 丢失**。安装脚本写入的 `firewall_mod=iptables` 被后来自行覆盖的 cfg 冲掉后，`fw_start.sh` 两个分支都不会执行。
3. **扩展库路径**。`XTABLES_LIBDIR` 只写进 procd 的 `env` 不够：`afstart.sh`、`fw_stop.sh` 是由 `/etc/init.d/shellcrash start` 调起的，不继承服务实例的环境。需要在两个脚本开头直接 `export`。
4. **`.start_error` 标记**。启动连续失败后 ShellCrash 会生成 `$CRASHDIR/.start_error`，之后不再启动，重启后自启动也会被它拦住，必须手动删除。
5. **规则安装时机**。由服务拉起时，规则要等面板端口就绪后才安装，启动后约 30～40 秒才出现。过早检查会误判为失败，手动重复执行 `afstart.sh` 会造成规则叠加。
6. **停止服务残留内核**。procd 默认只结束主进程；监管脚本需要 `trap` 把 TERM 转发给内核，否则新旧内核并存。

## 内存：压缩内核的启动峰值是硬限制

观察结果（`dmesg` 的 OOM 记录，受害进程均为 CrashCore，`oom_score_adj=800`）：

| 内核 | 解压后体积 | 压缩后体积 | 启动结果 |
|---|---|---|---|
| Mihomo v1.19.28 官方 armv7，UPX LZMA 重压 | 44.4 MiB | 10.1 MiB | 成功，RSS 约 45 MiB，MemAvailable 5～7 MiB |
| Mihomo v1.19.33 官方 armv7，UPX LZMA 重压 | 46.8 MiB | 10.9 MiB | 3 次启动中 2 次成功、1 次被 OOM 杀 |
| Mihomo v1.19.34 官方 armv7，UPX LZMA 重压 | 56.1 MiB | 12.7 MiB | 2 次启动均被 OOM 杀 |

被杀时的读数：`anon-rss` 约 37 MiB 加 `shmem-rss` 约 18 MiB，合计约 56 MiB；而服务停止状态下全机 MemAvailable 约 59 MiB。

推断：UPX 压缩的内核在启动解压阶段要把整个程序解压进匿名内存，峰值约等于“解压后体积 + 十几 MiB 工作区”，与 `GOMEMLIMIT`/`GOGC` 无关（那时 Go 运行时还没起来）。解压后体积超过约 45 MiB 就进入临界状态。

另一个教训：留在 `/tmp`（内存盘）里的两个各约 11 MiB 的安装包，让可用内存少了约 22 MiB，直接导致一次校验进程被 OOM 杀。部署期间要及时清理 `/tmp`。

## 自编译裁剪内核

源码取自官方 tag v1.19.34，按 Makefile 的方式交叉编译，仅增加以下 build tags，未修改任何源码：

```
GOOS=linux GOARCH=arm GOARM=7 CGO_ENABLED=0
-tags "with_low_memory,no_tailscale,no_zerotier,no_easytier,no_fake_tcp"
-trimpath -ldflags "-X ...constant.Version=v1.19.34 -w -s -buildid="
```

没有带 `with_gvisor`（官方发布版带）。UPX 5.3.0 `--lzma --best` 压缩。

| 项目 | 数值 |
|---|---|
| 未压缩 | 35258492 字节 |
| 压缩后 | 8034260 字节，MD5 `f1547f8d521a71d3495d2d3d21993b25` |
| 运行时 RSS | 约 38.5 MiB（anon 25 MiB + shmem 13 MiB） |
| MemAvailable（代理运行中） | 约 15.7 MiB |
| `/data` 占用 | 8 MiB，部署后剩余约 7.4 MiB |

代价：不支持 Tun 模式；不支持 Tailscale、ZeroTier、EasyTier 出站和 fake-tcp 传输。本实例只用 TPROXY 和 SSR/Trojan 节点，不受影响。

## 保护措施

与 [07 文档](07-core-exit-recovery-20261010.md) 一致，另外确认了实际效果：

- `vm.panic_on_oom=0`，由开机 hook 在启动代理前设置。本次共发生 4 次 OOM，全部只杀了代理内核，整机没有重启。
- 监管脚本 `/data/ShellCrash/tools/core-supervisor.sh`：启动前清理残留内核；子进程 `oom_score_adj=800`；收到 TERM 转发给内核；内核退出后调用 `fw_stop.sh` 清理规则。
- procd：`respawn 3600 15 3`，env 中带 `XTABLES_LIBDIR`、`GOMEMLIMIT=12MiB`、`GOGC=30`。
- 开机 hook 中关闭了脚本自带的 `autoSSH` 和 `auto_clean`，保留原厂日志与系统服务，开机脚本只负责启动代理。

## 实机验证

| 检查 | 结果 |
|---|---|
| 面板接口版本 | v1.19.34 |
| 规则 | DNS 劫持 8 条、TPROXY 相关 23 条（含 TPROXY 跳转 4 条）、策略路由 1 条 |
| 国内 HTTPS | 200，直连 |
| 国外站点 | 取决于所选节点；香港节点下 YouTube 200、约 0.9 s |
| OOM 计数 | 裁剪版启动及运行期间未增加 |
| 重启 | [@cloader](https://github.com/cloader) 确认重启后自启动正常、访问正常 |

## 仍未验证

- 连续多日、多设备满载的稳定性。
- 有线转发吞吐与延迟。
- 固件升级、恢复出厂后的行为。
