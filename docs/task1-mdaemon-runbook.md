# 任务一：MDaemon 邮件系统部署与验收手册

## 1. 事实结论

- 任务一必须使用 Windows ECS 完成。MDaemon 是 Windows 邮件服务器软件，不能直接部署在当前 macOS 本机或现有 Ubuntu Web/Dify 服务器上。
- 推荐单独创建一台阿里云 Windows Server 抢占式 ECS，规格控制在 `2 vCPU 4 GiB` 或更低，出价 `<= 0.15 元/小时`，公网 IP 选择按使用流量。
- 邮件系统只做本机收发验证时，不需要域名 MX 解析；如果要做公网互发，必须额外配置域名 MX/SPF 和运营商/云厂商端口策略，超出任务一最低验收范围。

## 2. 关键证据

- 官方下载页：`https://www.altn.com.cn/downloads`
- 官方下载页当前显示支持系统：`Microsoft Windows 2025 | 2022 | 2019 | 2016 | 2012 | 11 | 10`
- 官方下载页当前显示：`V22及以后版本只包含64位安装程序`
- 官方下载页当前最新静态版本块：`MDaemon V25.5.2`
- 中文版 64 位安装包：`https://yc-downloads.oss-cn-shanghai.aliyuncs.com/mdaemon/md2552_zh_x64.exe`

> 上述信息核对时间：2026-04-26。

## 3. 推荐交付方案

| 项目 | 配置 |
|------|------|
| ECS 类型 | 阿里云抢占式 ECS |
| 规格 | 2 vCPU 4 GiB，不能超过 4 vCPU 8 GiB |
| 系统 | Windows Server 2022 或 Windows Server 2019 64 位 |
| 计费 | 抢占式实例，单台上限价 `<= 0.15 元/小时`，公网 IP 按使用流量 |
| 安全组 | RDP `3389` 仅放行本人公网 IP；SMTP/POP3/IMAP 如需外部客户端再放行 |
| 邮件域 | `local.test` 或 `mail.local`，仅用于本机验证 |
| 测试账户 | `alice@local.test`、`bob@local.test` |
| 隔离关键词 | `BLOCKME` |
| 邮件大小限制 | `1 MB` |

## 4. 截图清单

必须截图并放入 PPT 或提交包：

| 序号 | 截图内容 | 证明点 |
|------|----------|--------|
| 1 | 阿里云 ECS 实例规格、抢占式、上限价格、公网计费方式 | 满足资源约束 |
| 2 | Windows 系统信息 | 证明系统环境 |
| 3 | MDaemon 安装完成主界面 | 证明邮件系统部署完成 |
| 4 | MDaemon 域 `local.test` 与账户列表 | 证明账户创建完成 |
| 5 | Foxmail 账户配置页 | 证明客户端配置完成 |
| 6 | Foxmail `alice` 给 `bob` 发信成功 | 证明本地发件 |
| 7 | Foxmail `bob` 收到邮件 | 证明本地收件 |
| 8 | 内容过滤器规则页，关键词 `BLOCKME`，动作为隔离 | 证明过滤配置 |
| 9 | 发送包含 `BLOCKME` 的测试邮件 | 证明触发条件 |
| 10 | 隔离区或对应隔离目录出现邮件 | 证明隔离生效 |
| 11 | 邮件大小限制配置页，限制 `1 MB` | 证明大小限制配置 |
| 12 | 发送超过 1 MB 附件失败或被拒日志 | 证明限制生效 |
| 13 | MDaemon 日志页或日志文件关键记录 | 证明真实链路 |
| 14 | 阿里云账单/费用截图 | 用于报销 |
| 15 | 实例释放成功截图 | 证明资源释放 |

## 5. ECS 创建步骤

1. 打开阿里云 ECS 控制台，创建实例。
2. 付费类型选择抢占式实例。
3. 实例规格选择 `2 vCPU 4 GiB`，如果价格不满足就换同级别实例族。
4. 镜像选择 `Windows Server 2022 数据中心版 64 位` 或 `Windows Server 2019 数据中心版 64 位`。
5. 公网 IP 选择按使用流量，带宽峰值可设 `5 Mbps` 到 `10 Mbps`。
6. 抢占式单台实例上限价格设置为 `0.15 元/小时` 或更低。
7. 安全组入方向：
   - `3389/TCP`：仅放行本人公网 IP。
   - `25/TCP`、`110/TCP`、`143/TCP`、`587/TCP`：本机验证不需要公网放行；需要外部客户端时再按需放行。
8. 创建后记录公网 IP、实例 ID、地域、规格、计费方式并截图。

## 6. Windows 初始化

登录 RDP 后，以管理员 PowerShell 执行：

```powershell
Set-TimeZone -Id "China Standard Time"
New-Item -ItemType Directory -Force -Path C:\tools,C:\evidence,C:\installers
Get-ComputerInfo | Select-Object OsName,OsVersion,CsTotalPhysicalMemory,CsNumberOfLogicalProcessors | Format-List
```

下载 MDaemon：

```powershell
$url = "https://yc-downloads.oss-cn-shanghai.aliyuncs.com/mdaemon/md2552_zh_x64.exe"
$out = "C:\installers\md2552_zh_x64.exe"
Invoke-WebRequest -Uri $url -OutFile $out
Get-FileHash $out -Algorithm SHA256
```

下载 Foxmail：

```powershell
Start-Process "https://www.foxmail.com/"
```

> Foxmail 下载页可能会根据地区重定向，实际安装包以官网页面为准，下载页和安装完成界面都要截图。

## 7. 安装 MDaemon

1. 右键以管理员身份运行 `C:\installers\md2552_zh_x64.exe`。
2. 选择默认安装路径，例如 `C:\MDaemon`。
3. 首次配置时创建主域：`local.test`。
4. 创建管理员账户，例如 `postmaster@local.test`。
5. 安装完成后确认 Windows 服务中存在 MDaemon 相关服务，并处于运行状态。

PowerShell 验证：

```powershell
Get-Service | Where-Object {$_.Name -like "*MDaemon*" -or $_.DisplayName -like "*MDaemon*"} | Format-Table -AutoSize
Test-NetConnection 127.0.0.1 -Port 25
Test-NetConnection 127.0.0.1 -Port 110
Test-NetConnection 127.0.0.1 -Port 143
```

## 8. 创建邮件账户

在 MDaemon 管理界面创建两个本地域账户：

| 账户 | 用途 |
|------|------|
| `alice@local.test` | 发件账户 |
| `bob@local.test` | 收件账户 |

建议设置简单但可记录的临时密码，例如 `Yuncan@2026Mail1`，任务完成后释放实例。

## 9. 配置 Foxmail 本地收发

在服务器内安装 Foxmail，并添加两个账户。

`alice@local.test` 配置：

| 项 | 值 |
|----|----|
| 邮箱地址 | `alice@local.test` |
| 用户名 | `alice@local.test` |
| 收信服务器 | `127.0.0.1` |
| 收信协议 | POP3 或 IMAP |
| POP3 端口 | `110` |
| IMAP 端口 | `143` |
| 发信服务器 | `127.0.0.1` |
| SMTP 端口 | `25` 或 `587` |
| SSL | 本机验证可关闭 |

`bob@local.test` 同理。

验证邮件：

| 发件人 | 收件人 | 主题 | 正文 |
|--------|--------|------|------|
| `alice@local.test` | `bob@local.test` | `normal mail test` | `hello bob from alice` |

预期结果：

- Foxmail 发件箱无滞留。
- `bob@local.test` 收件箱收到邮件。
- MDaemon 日志出现 SMTP 接收、投递成功记录。

## 10. 内容过滤器隔离

目标：标题或正文包含 `BLOCKME` 的邮件进入隔离，不进入正常收件箱。

配置路径按 MDaemon 中文界面版本可能略有差异，通常在：

```text
安全 / 安全设置 -> 内容过滤器
```

新增规则：

| 项 | 值 |
|----|----|
| 规则名 | `隔离 BLOCKME 关键词邮件` |
| 条件 1 | 邮件主题包含 `BLOCKME` |
| 条件 2 | 邮件正文包含 `BLOCKME` |
| 条件关系 | 任一条件命中即可 |
| 动作 | 隔离邮件，或移动到隔离目录 |
| 记录日志 | 开启 |

测试邮件：

| 发件人 | 收件人 | 主题 | 正文 |
|--------|--------|------|------|
| `alice@local.test` | `bob@local.test` | `BLOCKME quarantine test` | `this message should be quarantined` |

预期结果：

- `bob@local.test` 正常收件箱不出现该邮件。
- MDaemon 隔离区或隔离目录出现该邮件。
- MDaemon 日志出现内容过滤器命中记录。

## 11. 限制邮件大小并验证

目标：限制最大邮件大小为 `1 MB`，发送超过限制的邮件被拒绝或退回。

配置路径按版本可能略有差异，通常在：

```text
设置 -> 默认域和服务器 -> 服务器设置
```

或：

```text
账户设置 / 域设置 -> 邮件大小限制
```

配置项：

| 项 | 值 |
|----|----|
| 最大邮件大小 | `1024 KB` 或 `1 MB` |
| 适用范围 | 全局或 `local.test` 域 |
| 日志 | 开启 SMTP 日志 |

生成 2 MB 测试附件：

```powershell
fsutil file createnew C:\evidence\large-2mb.bin 2097152
Get-Item C:\evidence\large-2mb.bin | Select-Object FullName,Length
```

测试邮件：

| 发件人 | 收件人 | 主题 | 附件 |
|--------|--------|------|------|
| `alice@local.test` | `bob@local.test` | `large mail test` | `C:\evidence\large-2mb.bin` |

预期结果：

- Foxmail 发送失败、收到退信，或 MDaemon SMTP 阶段拒绝。
- MDaemon 日志出现邮件大小超过限制的记录。

## 12. 验收命令

把本仓库脚本复制到 Windows ECS 后执行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
powershell -ExecutionPolicy Bypass -File C:\path\to\task1-verify.ps1
```

脚本会输出：

- 系统版本、CPU、内存。
- MDaemon 服务状态。
- 本机邮件端口连通性。
- MDaemon 目录和日志文件概览。
- 2 MB 附件测试文件。
- 结果文件：`C:\evidence\task1-verify-*.txt`

## 13. 提交材料目录建议

```text
task1-md/
├── 01-ecs-spec-price.png
├── 02-windows-system.png
├── 03-mdaemon-installed.png
├── 04-domain-accounts.png
├── 05-foxmail-account.png
├── 06-normal-send.png
├── 07-normal-receive.png
├── 08-content-filter-rule.png
├── 09-quarantine-test-mail.png
├── 10-quarantine-result.png
├── 11-size-limit-rule.png
├── 12-size-limit-reject.png
├── 13-mdaemon-logs.png
├── 14-billing.png
├── 15-instance-released.png
└── task1-verify-output.txt
```

## 14. 未完成项与风险

| 项 | 状态 | 处理方式 |
|----|------|----------|
| 真实 ECS 创建 | 需要阿里云账号操作 | 按第 5 节创建并截图 |
| MDaemon/Foxmail 真实安装 | 需要 Windows ECS 桌面环境 | 按第 6-11 节操作 |
| 真实运行日志 | 需要部署后采集 | 运行 `scripts/windows/task1-verify.ps1` 并截图 |
| 公网收发邮件 | 非最低验收必需 | 如需公网互发，再补 MX/SPF、安全组和端口策略 |
| 抢占式回收 | 存在中断风险 | 完成每一步立即截图，最后及时释放实例 |

