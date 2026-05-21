$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Desktop = [Environment]::GetFolderPath("Desktop")
$WScript = New-Object -ComObject WScript.Shell

function New-Shortcut {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string]$Description
    )

    $ShortcutPath = Join-Path $Desktop $Name
    $Shortcut = $WScript.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = $Description
    $Shortcut.IconLocation = "powershell.exe,0"
    $Shortcut.Save()
    Write-Host "Creado: $ShortcutPath"
}

New-Shortcut `
    -Name "Activar Flashscore MCP.lnk" `
    -ScriptPath (Join-Path $PSScriptRoot "start-flashscore-mcp.ps1") `
    -Description "Activa o reactiva el servidor MCP de Flashscore"

New-Shortcut `
    -Name "Detener Flashscore MCP.lnk" `
    -ScriptPath (Join-Path $PSScriptRoot "stop-flashscore-mcp.ps1") `
    -Description "Pausa o detiene el servidor MCP de Flashscore"
