$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot ".mcp-server.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "Estado: detenido"
    exit 0
}

$PidValue = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
$Process = if ($PidValue) { Get-Process -Id ([int]$PidValue) -ErrorAction SilentlyContinue } else { $null }

if ($Process) {
    Write-Host "Estado: activo"
    Write-Host "PID: $PidValue"
    Write-Host "URL: http://127.0.0.1:8000/mcp"
} else {
    Write-Host "Estado: detenido (PID viejo: $PidValue)"
}
