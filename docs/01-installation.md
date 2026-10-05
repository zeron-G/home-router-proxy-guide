# 安装、适配和持久化

> 作者：zeron-G · 最后核对：2026-10-06

## 实机前提

机型是小米 BE3600 2.5G（RD15），原厂固件 1.0.87。主人先完成 root SSH 开启，安装工作从可登录 SSH 开始。论坛帖子和 PDF 是参考资料，不作为自动执行命令的授权。

| 项目 | 实机读取结果 |
|---|---|
| 内核 / 架构 | Linux 5.4.213 / armv7l，32 位 ARM |
| 系统 | OpenWrt 18.06-SNAPSHOT，ipq53xx_32，musl armhf |
| iptables | 1.6.2，libxtables.so.12 |
| 系统可见内存 | 180428 KiB，约 176 MiB |
| `/data` | 19952 KiB 的持久化分区；完成部署后约 3976 KiB 可用 |
| 临时文件 | `/tmp` 是内存文件系统，重启会丢失 |

先通过 SSH 读取自己的情况，网关地址用实际值替换示例：

```sh
ssh -o HostKeyAlgorithms=+ssh-rsa root@192.168.0.1
uname -a
cat /etc/openwrt_release
free
df -k /data /tmp
iptables --version
ip addr
ip route
```

不要根据商品标称内存判断剩余空间；以 `free` 的 MemAvailable 和实际进程 RSS 为准。

## 先备份，暂不启动

备份网络、防火墙、DHCP、SSH 配置及当前服务状态。备份内容可能包含 Wi-Fi 密码和 SSH 私钥，权限设为仅 root 可读，并另存到私人电脑。升级、回退前仍要做新备份。本库不提供这些私人备份。

安装 ShellCrash 时先关闭自动启动，确认配置、内核和规则数据齐全以后再启动。不要让一个没有节点配置的默认服务抢先接管整个家庭网络。

## ShellCrash 和内核

本次采用 [ShellCrash 官方仓库](https://github.com/juewuy/ShellCrash) stable 安装包，得到 1.9.4release。先保存并检查官方安装脚本，再在 SSH 内运行，根据菜单把安装目录选为 `/data/ShellCrash`。可以在电脑上预下载，避免路由器临时目录同时堆积多个大文件。

运行内核是 Mihomo Meta v1.19.28，Go 1.26.5，ARMv7 UPX 文件，来自 ShellCrash 官方 update 分支的 `bin/meta/clash-linux-armv7.upx`。持久化文件为 `/data/ShellCrash/CrashCore.upx`，`/tmp/ShellCrash/CrashCore` 是运行时链接。

本次下载文件的校验值：

| 文件 | 大小 / SHA-256 |
|---|---|
| ShellCrash stable 包 | `4f946031a0483ed528e266143d459075489cce6c3f8f2f4681f39ca6d7448681` |
| ARMv7 UPX 内核 | 10185476 字节；`33d58f2103c674caaf12ac350cd351539102b6089fae0a3ce44b50fb36f86b64` |

这些值记录本次获取的文件；stable / update 分支会更新，新下载不必与它们相同，但必须重新核对来源、架构和版本。

规则数据使用小型 `Country.mmdb`、中国域名 `cn.mrs` 与 ShellCrash 的中国 IP 列表，减少资源占用。它们在本实例分别约 133 KB、535 KB、71 KB。不要把完整版巨型规则库直接塞进这个分区。

## TPROXY 适配是本机的关键步骤

内核支持 TPROXY，但原厂 iptables 用户态缺少 `libxt_TPROXY.so` 和 `libxt_socket.so`。本次从官方 OpenWrt 18.06.9 的 ARM Cortex-A7 `iptables-mod-tproxy` 1.6.2-3 包取出这两个扩展，先确认它们与系统 `libxtables.so.12` 的 ABI 匹配。

扩展放在 `/data/ShellCrash/tools/iptables/`，同时在这个目录链接原厂已有扩展。为 ShellCrash 设置：

```sh
export XTABLES_LIBDIR=/data/ShellCrash/tools/iptables
iptables -j TPROXY -h
```

只有输出含 `--on-port` 等 TPROXY 参数，才能说明用户态扩展已正确加载。不要整包覆盖原厂 iptables / libc，也不要只看到内核模块存在就认为适配完成。日后检查规则时也要带上 `XTABLES_LIBDIR`，否则会把缺少搜索路径误认为服务故障。

本实例用 TPROXY 接管 LAN 和 IoT 子网的 TCP / UDP，入口端口为 7893，mark 7892（十六进制 0x1ed4），table 100 指向 local default。只覆盖明确的下游子网，不把上级路由器网段一并接管。`routing-mark: 7894` 用于内核自己的出站连接。

原厂 `qca-nss-ecm` 会影响 bridge netfilter 参数。本次持久化修复让 `net.bridge.bridge-nf-call-iptables` 与 `ip6tables` 为 0；这属于本次实机适配，其他机型先确认拓扑和转发行为再决定是否需要。

## 服务与启动链

1. `/etc/init.d/shellcrash` 交给 procd 管理内核；持久化模板为 `/data/ShellCrash/starts/shellcrash.procd`。
2. 两份服务定义显式传入 `GOMEMLIMIT=12MiB GOGC=30`，并读取扩展路径。
3. `/data/shellcrash_init.sh` 等待 LAN 就绪、恢复主人已经启用的 SSH、重建运行环境及必要适配，再启动 ShellCrash。
4. `firewall.ShellCrash.path` 指向上述持久化 hook，`enabled=1`。大小写必须与实际 UCI 节名一致。
5. `/etc/rc.d/S99shellcrash` 存在；控制器就绪检查使用实际 LAN 绑定地址。

本实例保留原 SSH host key 和 root 密码，关闭原脚本自动开 Telnet、自动改密码及删除原厂日志目录的行为。正常重启后验证了 SSH、服务、内存参数和防火墙恢复。未验证固件升级、恢复出厂或断电损坏后的恢复。

## 配置部署顺序

准备本地节点文件、规则数据、面板及 YAML → 备份现有配置 → 核对 YAML 字段和路径 → 让现有核心通过 API 重载 → 读取 `/configs`、`/rules`、`/proxies` → 从不设客户端代理的设备测试国内和国外网站。

本机不能同时运行正常核心与另一个 `CrashCore -t` 来测试配置，额外进程会增加内存压力。使用本地 YAML 检查和现有核心 API 重载；必须运行内核测试时，先安排短暂停服窗口。
