# 来源与使用方式

- [ShellCrash 官方项目](https://github.com/juewuy/ShellCrash)：安装器、服务管理、内核与面板获取入口。
- [ShellCrash stable 安装包](https://raw.githubusercontent.com/juewuy/ShellCrash/stable/ShellCrash.tar.gz)：本次采用的源，版本和文件校验记录在安装文档。
- [ShellCrash update 分支](https://github.com/juewuy/ShellCrash/tree/update)：本次 ARMv7 UPX 内核来源。
- [Mihomo 官方项目](https://github.com/MetaCubeX/mihomo)：内核项目。
- [Mihomo 规则](https://wiki.metacubex.one/config/rules/)、[DNS](https://wiki.metacubex.one/config/dns/)、[代理集合](https://wiki.metacubex.one/config/proxy-providers/)：配置语法核对。
- [Go runtime 环境变量](https://pkg.go.dev/runtime#hdr-Environment_Variables)：GOMEMLIMIT 软目标和 GOGC 的含义。
- [OpenWrt 18.06.9 官方下载目录](https://downloads.openwrt.org/releases/18.06.9/)：本次补齐匹配 iptables ABI 的扩展来源。
- [v2fly 网易域名清单](https://github.com/v2fly/domain-list-community/blob/master/data/netease)：游戏及网易域名核对来源之一，不作为完整服务器列表。
- [论坛参考一](https://www.right.com.cn/forum/thread-8485993-1-1.html)、[对应 RD15 固件参考](https://www.right.com.cn/forum/forum.php?mod=viewthread&tid=8321180)：主人提供帖子及其 PDF，用于理解 SSH / 原厂固件操作背景。本库不重新分发帖子全文或 PDF。

本教程的大部分部署参数和故障经过来自本次实机命令、配置读回、HTTP / DNS 检查及主人反馈。把“现场观察”“技术判断”“尚待实测”分开记录，避免将第三方资料里的步骤写成自己已经完成的操作。
