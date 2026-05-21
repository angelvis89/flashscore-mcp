# Tutorial de uso - Flashscore MCP

## 1. Usarlo desde Codex

El MCP queda registrado como:

```text
flashscore
```

Reinicia VS Code/Codex para que lea `C:\Users\User\.codex\config.toml`.

Luego puedes pedir cosas como:

```text
Usa el MCP flashscore y dame los partidos de hoy.
```

```text
Busca en flashscore los partidos de Cienciano entre hoy y mañana.
```

```text
Con el MCP flashscore, abre el detalle del partido K8bh3OkJ y dame cuotas, estadísticas y previa.
```

## 2. Tools disponibles

- `get_live_scores`: partidos en vivo.
- `get_matches_by_date`: partidos por fecha `YYYY-MM-DD`.
- `search_matches`: busqueda por equipo, liga o texto.
- `get_match_full_detail`: detalle completo del partido.
- `get_match_statistics`: estadisticas visibles.
- `get_match_odds`: cuotas visibles y pick estimado por cuota menor.
- `get_match_events`: eventos o resumen visible.
- `start_live_poller`: refresco en background.
- `stop_live_poller`: detener refresco.
- `get_cache_status`: ver cache.

## 3. Usarlo desde VS Code / Copilot Chat local

El MCP tambien queda registrado globalmente en:

```text
C:\Users\User\AppData\Roaming\Code\User\mcp.json
```

Y para este proyecto en:

```text
C:\Users\User\Desktop\Crear MCP\.vscode\mcp.json
```

Debe aparecer en VS Code como:

```text
flashscore
```

Si ya tenias VS Code abierto:

1. Presiona `Ctrl+Shift+P`.
2. Ejecuta `Developer: Reload Window`.
3. Abre `Personalizaciones del agente > Servidores MCP`.
4. Verifica que aparezca `flashscore`.
5. Si aparece detenido, pulsa iniciar desde la interfaz de VS Code.

Ejemplos en Copilot Chat / agente local:

```text
Usa el MCP flashscore y lista los partidos de hoy.
```

```text
Usa flashscore para buscar partidos de Alianza Lima esta semana.
```

```text
Con flashscore, dame el detalle completo del partido K8bh3OkJ incluyendo cuotas y estadisticas.
```

## 4. Accesos directos del Escritorio

Se crean dos accesos:

- `Activar Flashscore MCP`: levanta el servidor HTTP local.
- `Detener Flashscore MCP`: detiene el servidor HTTP local.

El modo HTTP queda en:

```text
http://127.0.0.1:8000/mcp
```

Codex normalmente usa el modo `stdio`, por lo que puede aparecer aunque no tengas el HTTP iniciado. Los accesos sirven para reactivarlo manualmente o conectarlo desde clientes que pidan URL.

## 5. Pruebas

Desde PowerShell en el proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
$env:PYTHONPATH="src"
$env:SPORTS_PROVIDER="flashscore"
.\.venv\Scripts\python.exe scripts\smoke_official_flashscore.py
```

## 6. Detener manualmente

```powershell
.\scripts\stop-flashscore-mcp.ps1
```

## 7. Reactivar manualmente

```powershell
.\scripts\start-flashscore-mcp.ps1
```
