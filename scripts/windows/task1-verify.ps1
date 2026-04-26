$ErrorActionPreference = "Continue"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evidenceDir = "C:\evidence"
$outputFile = Join-Path $evidenceDir "task1-verify-$timestamp.txt"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

function Write-Section {
    param([string]$Title)
    "`n===== $Title =====" | Tee-Object -FilePath $outputFile -Append
}

function Write-Data {
    param([object]$Data)
    $Data | Out-String | Tee-Object -FilePath $outputFile -Append
}

Write-Section "任务一验收采集"
Write-Data "采集时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"

Write-Section "系统信息"
Write-Data (Get-ComputerInfo | Select-Object OsName,OsVersion,CsName,CsTotalPhysicalMemory,CsNumberOfLogicalProcessors)

Write-Section "MDaemon 服务状态"
$services = Get-Service | Where-Object {
    $_.Name -like "*MDaemon*" -or $_.DisplayName -like "*MDaemon*" -or
    $_.Name -like "*WorldClient*" -or $_.DisplayName -like "*WorldClient*"
}
if ($services) {
    Write-Data ($services | Sort-Object DisplayName | Format-Table Name,DisplayName,Status,StartType -AutoSize)
} else {
    Write-Data "未发现名称包含 MDaemon 或 WorldClient 的 Windows 服务。请确认安装路径和服务名称。"
}

Write-Section "本机邮件端口连通性"
$ports = @(25, 110, 143, 587)
foreach ($port in $ports) {
    $result = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
    Write-Data ([PSCustomObject]@{
        Host = "127.0.0.1"
        Port = $port
        TcpTestSucceeded = $result.TcpTestSucceeded
    })
}

Write-Section "MDaemon 常见目录"
$paths = @("C:\MDaemon", "C:\MDaemon\Logs", "C:\MDaemon\Queues", "C:\MDaemon\Users", "C:\MDaemon\App")
foreach ($path in $paths) {
    if (Test-Path $path) {
        $item = Get-Item $path
        Write-Data ([PSCustomObject]@{
            Path = $path
            Exists = $true
            LastWriteTime = $item.LastWriteTime
        })
    } else {
        Write-Data ([PSCustomObject]@{
            Path = $path
            Exists = $false
            LastWriteTime = $null
        })
    }
}

Write-Section "MDaemon 最新日志概览"
$logDir = "C:\MDaemon\Logs"
if (Test-Path $logDir) {
    $logs = Get-ChildItem $logDir -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 20 FullName,Length,LastWriteTime
    Write-Data ($logs | Format-Table -AutoSize)

    $keywordHits = Select-String -Path (Join-Path $logDir "*") -Pattern "BLOCKME","size","exceed","larger","quarantine","content filter" -SimpleMatch -ErrorAction SilentlyContinue |
        Select-Object -First 80 Path,LineNumber,Line
    Write-Section "关键词/隔离/大小限制日志线索"
    if ($keywordHits) {
        Write-Data ($keywordHits | Format-List)
    } else {
        Write-Data "未在日志中检索到 BLOCKME、size、quarantine、content filter 等关键词。若刚完成测试，请刷新日志或手动截图 MDaemon 控制台日志。"
    }
} else {
    Write-Data "日志目录不存在: $logDir"
}

Write-Section "生成 2MB 大附件测试文件"
$largeFile = Join-Path $evidenceDir "large-2mb.bin"
if (-not (Test-Path $largeFile)) {
    fsutil file createnew $largeFile 2097152 | Out-Null
}
Write-Data (Get-Item $largeFile | Select-Object FullName,Length,LastWriteTime)

Write-Section "采集结果"
Write-Data "验收输出文件: $outputFile"
Write-Data "请同时保留 MDaemon 控制台、Foxmail 收发、隔离区、大小限制失败提示、阿里云账单和释放实例截图。"

Write-Host "验收采集完成: $outputFile"

