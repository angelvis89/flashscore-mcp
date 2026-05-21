$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PidFile = Join-Path $ProjectRoot ".mcp-server.pid"
$OutLog = Join-Path $ProjectRoot "mcp-server.out.log"
$ErrLog = Join-Path $ProjectRoot "mcp-server.err.log"

if (-not (Test-Path $PythonExe)) {
    throw "No se encontro Python del entorno virtual: $PythonExe. Ejecuta scripts\install.ps1 primero."
}

if (Test-Path $PidFile) {
    $OldPid = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($OldPid) {
        $OldProcess = Get-Process -Id ([int]$OldPid) -ErrorAction SilentlyContinue
        if ($OldProcess) {
            Write-Host "Flashscore MCP ya esta activo. PID: $OldPid"
            exit 0
        }
    }
}

$env:MCP_TRANSPORT = "streamable-http"
$env:SPORTS_PROVIDER = "flashscore"
$env:FLASHSCORE_TIMEOUT_MS = "16000"

$Process = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList @("-m", "flashscore_mcp.server") `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru

$Process.Id | Set-Content -Path $PidFile -Encoding ASCII
Start-Sleep -Seconds 3

$Running = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
if (-not $Running) {
    $ErrorText = if (Test-Path $ErrLog) { Get-Content -Raw $ErrLog } else { "" }
    throw "No se pudo iniciar Flashscore MCP. $ErrorText"
}

Write-Host "Flashscore MCP activo."
Write-Host "PID: $($Process.Id)"
Write-Host "URL: http://127.0.0.1:8000/mcp"
