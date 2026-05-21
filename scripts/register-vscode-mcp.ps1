$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$UserMcpPath = Join-Path $env:APPDATA "Code\User\mcp.json"
$WorkspaceMcpDir = Join-Path $ProjectRoot ".vscode"
$WorkspaceMcpPath = Join-Path $WorkspaceMcpDir "mcp.json"

if (-not (Test-Path $PythonExe)) {
    throw "No se encontro $PythonExe. Ejecuta scripts\install.ps1 primero."
}

if (-not (Test-Path $UserMcpPath)) {
    throw "No se encontro mcp.json de VS Code: $UserMcpPath"
}

function ConvertTo-PrettyJson {
    param([object]$Value)
    return ($Value | ConvertTo-Json -Depth 20)
}

function Set-FlashscoreServer {
    param([object]$Config)

    $ConfigProperties = @($Config.PSObject.Properties.Name)
    if (-not $ConfigProperties.Contains("servers") -or $null -eq $Config.servers) {
        $Config | Add-Member -MemberType NoteProperty -Name "servers" -Value ([pscustomobject]@{})
    }

    $Server = [ordered]@{
        type = "stdio"
        command = $PythonExe
        args = @("-m", "flashscore_mcp.server")
        cwd = $ProjectRoot
        env = [ordered]@{
            MCP_TRANSPORT = "stdio"
            SPORTS_PROVIDER = "flashscore"
            FLASHSCORE_TIMEOUT_MS = "16000"
        }
    }

    $ServerProperties = @($Config.servers.PSObject.Properties.Name)
    if ($ServerProperties.Contains("flashscore")) {
        $Config.servers.PSObject.Properties.Remove("flashscore")
    }

    $Config.servers | Add-Member -MemberType NoteProperty -Name "flashscore" -Value $Server

    $ConfigProperties = @($Config.PSObject.Properties.Name)
    if (-not $ConfigProperties.Contains("inputs")) {
        $Config | Add-Member -MemberType NoteProperty -Name "inputs" -Value @()
    }

    return $Config
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupPath = "$UserMcpPath.bak-flashscore-$Stamp"
Copy-Item -LiteralPath $UserMcpPath -Destination $BackupPath -Force

$UserConfig = Get-Content -Raw -Encoding UTF8 $UserMcpPath | ConvertFrom-Json
$UserConfig = Set-FlashscoreServer -Config $UserConfig
ConvertTo-PrettyJson $UserConfig | Set-Content -Path $UserMcpPath -Encoding UTF8

if (-not (Test-Path $WorkspaceMcpDir)) {
    New-Item -ItemType Directory -Path $WorkspaceMcpDir | Out-Null
}

if (Test-Path $WorkspaceMcpPath) {
    Copy-Item -LiteralPath $WorkspaceMcpPath -Destination "$WorkspaceMcpPath.bak-flashscore-$Stamp" -Force
    $WorkspaceConfig = Get-Content -Raw -Encoding UTF8 $WorkspaceMcpPath | ConvertFrom-Json
} else {
    $WorkspaceConfig = [pscustomobject]@{
        servers = [pscustomobject]@{}
        inputs = @()
    }
}

$WorkspaceConfig = Set-FlashscoreServer -Config $WorkspaceConfig
ConvertTo-PrettyJson $WorkspaceConfig | Set-Content -Path $WorkspaceMcpPath -Encoding UTF8

Write-Host "MCP flashscore registrado en VS Code Usuario y Workspace."
Write-Host "Usuario: $UserMcpPath"
Write-Host "Workspace: $WorkspaceMcpPath"
Write-Host "Backup usuario: $BackupPath"
