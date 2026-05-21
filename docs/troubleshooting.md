# Troubleshooting

## PowerShell no permite activar el entorno

Ejecuta una sola vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Luego:

```powershell
.\.venv\Scripts\Activate.ps1
```

## `pytest` no existe

Instala dependencias de desarrollo dentro del venv:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Playwright no encuentra Chromium

```powershell
python -m playwright install chromium
```

## El provider Flashscore no devuelve datos

Prueba primero el provider mock:

```powershell
$env:SPORTS_PROVIDER="mock"
python -m flashscore_mcp.server
```

Si el mock funciona, el problema esta en la pagina viva, el selector DOM, cookies, red o bloqueo temporal.
