$ErrorActionPreference = "Stop"

$PythonExe = "C:\Users\User\miniconda3\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Comando fallo con codigo $LASTEXITCODE"
    }
}

Invoke-Checked { & $PythonExe -m venv .venv }
.\.venv\Scripts\Activate.ps1
Invoke-Checked { python -m pip install --upgrade pip }
Invoke-Checked { python -m pip install -e ".[dev]" }
Invoke-Checked { python -m playwright install chromium }

Write-Host "Instalacion completada."
