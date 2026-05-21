$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ConfigPath = Join-Path $env:USERPROFILE ".codex\config.toml"

if (-not (Test-Path $PythonExe)) {
    throw "No se encontro $PythonExe. Ejecuta scripts\install.ps1 primero."
}

if (-not (Test-Path $ConfigPath)) {
    throw "No se encontro config de Codex: $ConfigPath"
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupPath = "$ConfigPath.bak-flashscore-$Stamp"
Copy-Item -LiteralPath $ConfigPath -Destination $BackupPath -Force

$Content = Get-Content -Raw -Encoding UTF8 $ConfigPath
$Block = @"

[mcp_servers.flashscore]
command = '$($PythonExe.Replace('\', '\\'))'
args = ["-m", "flashscore_mcp.server"]
cwd = '$($ProjectRoot.Replace('\', '\\'))'
enabled = true

[mcp_servers.flashscore.env]
MCP_TRANSPORT = "stdio"
SPORTS_PROVIDER = "flashscore"
FLASHSCORE_TIMEOUT_MS = "16000"
"@

if ($Content -match '(?ms)^\[mcp_servers\.flashscore\].*?(?=^\[|\z)') {
    $Content = [regex]::Replace($Content, '(?ms)^\[mcp_servers\.flashscore\].*?(?=^\[|\z)', $Block.TrimStart() + "`r`n")
} else {
    $Content = $Content.TrimEnd() + "`r`n" + $Block + "`r`n"
}

Set-Content -Path $ConfigPath -Value $Content -Encoding UTF8

Write-Host "MCP flashscore registrado en Codex."
Write-Host "Config: $ConfigPath"
Write-Host "Backup: $BackupPath"
