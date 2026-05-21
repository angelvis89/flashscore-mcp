$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot ".mcp-server.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "No hay PID guardado. Flashscore MCP parece detenido."
    exit 0
}

$PidValue = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $PidValue) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "PID vacio limpiado. Flashscore MCP parece detenido."
    exit 0
}

$Process = Get-Process -Id ([int]$PidValue) -ErrorAction SilentlyContinue
if ($Process) {
    Stop-Process -Id $Process.Id -Force
    Write-Host "Flashscore MCP detenido. PID: $PidValue"
} else {
    Write-Host "El PID guardado ya no existe. Flashscore MCP parece detenido."
}

Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
