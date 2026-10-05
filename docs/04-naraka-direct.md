# 永劫无间 Steam 版直连

> 作者：zeron-G · 配置变更：2026-10-06

主人最初怀疑代理影响永劫无间，并确认是 Steam 版。本次按当时的直连要求把游戏及相关网易服务域名放在规则列表顶部，目标策略为 DIRECT，同时加入 DNS fake-IP 例外。随后主人确认游戏正常，原先的问题是没有登录，并要求不用继续修复。停止进一步排查，已有直连规则保留；不能将游戏恢复归因于这次规则修改。

## 当前域名列表

```text
yjwujian.cn
narakathegame.com
narakabladepoint.com
neteasegames.com
netease.com
netease.im
easebar.com
163.com
126.net
127.net
nease.net
static163.net
```

这是本次采用的排障覆盖集，不是官方承诺的完整游戏服务器名单。`yjwujian.cn` 也出现在 [v2fly 的网易域名清单](https://github.com/v2fly/domain-list-community/blob/master/data/netease) 中；其他相关域名用于覆盖发行商登录、站点及资源服务。网易 / 163 的后缀较广，因此这些服务也会走直连。

每个域名对应：

```yaml
rules:
  - DOMAIN-SUFFIX,yjwujian.cn,DIRECT
  # 游戏例外必须放在 AI / 中国规则 / MATCH 之前
dns:
  fake-ip-filter:
    - '+.yjwujian.cn'
```

完整 12 条规则和 DNS 例外在配置模板里。规则由上到下匹配，使用 `Rule` 模式才生效。[Mihomo 规则说明](https://wiki.metacubex.one/config/rules/)

## 本次实施记录

原配置先备份为 `/data/ShellCrash/backups/config-before-naraka-20261006.yaml`，权限 600。新配置写入持久化 YAML，现有核心 API 重载返回 204；读取 `/configs` 与 `/rules` 确认模式为 rule，前 12 条都是 DIRECT，总规则数 58。

之后查询 `www.narakathegame.com`、`www.yjwujian.cn`，两者都有真实 DNS 答复，没有返回 fake-IP。通过不设置客户端代理的电脑访问游戏官网得到 HTTP 200，核心日志明确显示 `narakathegame.com` 命中 DIRECT。

这一步完成的是“相关域名的直连规则已经加载并命中”。网站请求只能验证域名路径，不能代替 Steam 游戏进入大厅、匹配或对局测试；观察窗口没有捕获到实际游戏会话。

## 在另一台机器上如何编辑

本库提供只编辑本地 YAML 的工具，不会登录路由器，也不会下载订阅：

```sh
python -m pip install -r requirements.txt
python scripts/apply-naraka-direct.py original.yaml updated.yaml
```

输入和输出必须是不同文件，输出存在时工具会拒绝覆盖。脚本保留其他规则 / 字段，只把这些域名的规则移到顶部并设置 DIRECT，补齐 DNS 例外；重复处理不会增加重复项。自行审阅 diff、备份后再部署到路由器。

## 玩家如何验证

1. 连接目标路由器 LAN / Wi-Fi，退出游戏；客户端若另开了 VPN 或本地 Clash，先确认不会覆盖路由器测试。
2. Windows 可执行 `ipconfig /flushdns` 清除旧解析，再重新打开 Steam 版游戏。
3. 尝试进入大厅、匹配并完成一局；记录连接错误、卡住阶段、延迟。
4. 面板连接页 / 短时 info 日志查看游戏域名和策略链；应该命中 DIRECT。
5. 如果仍有游戏流量命中普通代理，结合游戏进程的连接、实际域名或服务器地址补精准规则，再重复验证。

路由器看不到 PC 上的进程归属。给路由器写 `PROCESS-NAME,NarakaBladepoint.exe,DIRECT` 不能可靠区分转发的游戏流量。纯 IP / UDP 游戏会话、Steam 平台登录和新 CDN 也可能不匹配这份域名列表。需要观察实际流量后处理，避免猜测端口范围或把整台电脑永久全直连。

## 验证状态

规则加载、DNS 例外和官网 DIRECT 请求已检查。主人反馈游戏正常，先前问题为未登录，已停止继续排查；没有采集完整对局遥测，也不把正常状态归功于代理配置修改。
