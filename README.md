# Flashscore Live MCP

Servidor MCP profesional para exponer marcadores deportivos en vivo a clientes compatibles con Model Context Protocol.

> Estado: implementacion inicial. El proveedor `FlashscorePlaywrightProvider` es experimental porque Flashscore no ofrece una API publica oficial para este caso.

## Arquitectura

```text
Cliente MCP
  -> tools/resources MCP
  -> cache TTL en memoria
  -> proveedor deportivo
  -> Flashscore.pe via Playwright experimental
```

La regla principal es que las tools leen cache y refrescan de forma controlada. Para datos cada segundo, configura `FLASHSCORE_REFRESH_SECONDS=1`, pero usa ese modo solo en pruebas internas. Para uso serio o comercial, cambia el proveedor por una fuente autorizada o por un adaptador propio.

Los scripts de ejecucion arrancan con `SPORTS_PROVIDER=flashscore`. Para pruebas sin red puedes usar `mock`:

```powershell
$env:SPORTS_PROVIDER="mock"
```

## Tools MCP

- `get_live_scores(sport, league, live_only, force_refresh)`: devuelve partidos actuales.
- `get_match_detail(match_id, force_refresh)`: devuelve detalle resumido por ID.
- `get_matches_by_date(date, sport, league, force_refresh)`: partidos por fecha.
- `search_matches(query, date_from, date_to, sport, league)`: busqueda por equipo/liga/texto.
- `get_match_full_detail(match_id, sections, force_refresh)`: resumen, estadisticas, alineaciones, cuotas, H2H y previa.
- `get_match_statistics(match_id, force_refresh)`: estadisticas visibles.
- `get_match_odds(match_id, force_refresh)`: cuotas visibles y pick mas probable estimado.
- `get_match_events(match_id, force_refresh)`: eventos/timeline visible.
- `watch_match(match_id, duration_seconds, interval_seconds)`: observa un partido por polling.
- `get_cache_status()`: inspecciona claves, edad y estado stale del cache.
- `refresh_live_cache(sport, league, live_only)`: fuerza un refresco unico.
- `start_live_poller(sport, league, live_only, interval_seconds)`: mantiene snapshots en background.
- `stop_live_poller()`: detiene el poller.
- `get_poller_status()`: muestra el estado del poller.

## Resources MCP

- `sports://football/live`
- `sports://match/{match_id}`

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

Si PowerShell bloquea `Activate.ps1`, revisa [docs/troubleshooting.md](docs/troubleshooting.md).

Verificacion local:

```powershell
python -m pytest -q
python -m ruff check .
```

## Ejecucion local por stdio

```powershell
$env:MCP_TRANSPORT="stdio"
python -m flashscore_mcp.server
```

Configuracion ejemplo para un cliente MCP local:

```json
{
  "mcpServers": {
    "flashscore-live": {
      "command": "C:\\Users\\User\\Desktop\\Crear MCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "flashscore_mcp.server"],
      "cwd": "C:\\Users\\User\\Desktop\\Crear MCP",
      "env": {
        "MCP_TRANSPORT": "stdio",
        "SPORTS_PROVIDER": "flashscore"
      }
    }
  }
}
```

En Claude Desktop, pega la configuracion en `%APPDATA%\Claude\claude_desktop_config.json` y reinicia la aplicacion. Hay mas detalle en [docs/clientes-windows.md](docs/clientes-windows.md).

## Ejecucion HTTP

```powershell
$env:MCP_TRANSPORT="streamable-http"
python -m flashscore_mcp.server
```

Por defecto FastMCP expone Streamable HTTP en `/mcp`; en local normalmente queda en `http://127.0.0.1:8000/mcp` cuando se usa el servidor HTTP del SDK. Pruebalo con MCP Inspector:

```powershell
npx -y @modelcontextprotocol/inspector
```

## Variables

Copia `.env.example` y exporta las variables que necesites:

- `MCP_TRANSPORT`: `stdio` o `streamable-http`.
- `SPORTS_PROVIDER`: `mock` o `flashscore`.
- `FLASHSCORE_BASE_URL`: URL base.
- `FLASHSCORE_HEADLESS`: `true` o `false`.
- `FLASHSCORE_TIMEOUT_MS`: timeout de navegador.
- `FLASHSCORE_REFRESH_SECONDS`: intervalo objetivo de refresco.
- `FLASHSCORE_CACHE_TTL_SECONDS`: vida del cache.
- `FLASHSCORE_MAX_WATCH_SECONDS`: limite para `watch_match`.

## Notas legales y tecnicas

Flashscore/Livesport protege su contenido y puede limitar automatizaciones. Este proyecto no intenta evadir sistemas anti-bot; usa frecuencia conservadora, cache y fallback stale. Si vas a redistribuir datos, monetizar o exponer el servicio a terceros, usa una fuente autorizada como proveedor deportivo con licencia.

## Smoke tests reales

```powershell
$env:PYTHONPATH="src"
$env:SPORTS_PROVIDER="flashscore"
.\.venv\Scripts\python.exe scripts\smoke_official_flashscore.py
```

Este test valida un dia pasado, la pagina principal de hoy, un dia futuro y detalle enriquecido de un partido.

## Fuentes base

- MCP: https://modelcontextprotocol.io/docs/develop/build-server
- Python SDK: https://py.sdk.modelcontextprotocol.io/
- Transportes: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

## Documentacion local

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/clientes-windows.md](docs/clientes-windows.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/TUTORIAL-USO.md](docs/TUTORIAL-USO.md)

## Accesos directos

En el Escritorio:

- `Activar Flashscore MCP.lnk`
- `Detener Flashscore MCP.lnk`

El MCP tambien queda registrado en `C:\Users\User\.codex\config.toml` como `flashscore`.
