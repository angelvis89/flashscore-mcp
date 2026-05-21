# GUÍA COMPLETA: CREAR UN MCP SERVER PARA DATOS EN TIEMPO REAL
## Caso de uso: Flashscore.pe — Resultados de fútbol en vivo
> Generado el 21 de mayo de 2026 | Basado en la especificación oficial MCP 2025-11-25

---

## ¿QUÉ ES MCP?

**Model Context Protocol (MCP)** es un protocolo abierto creado por Anthropic que estandariza cómo los modelos de IA (Claude, GPT, Gemini, etc.) se conectan a fuentes de datos externas, herramientas y servicios. Funciona como un "puente" entre el LLM y el mundo exterior.

**Componentes principales:**
- **MCP Host**: La app que contiene el LLM (ej. Claude Desktop, tu app Python)
- **MCP Client**: Se conecta al server; vive dentro del Host
- **MCP Server**: El programa que TÚ creas, que expone Tools/Resources al modelo
- **Transport**: El canal de comunicación (stdio, SSE, Streamable HTTP)

---

## MAPA DE DOCUMENTACIÓN OFICIAL

### LECTURA OBLIGATORIA (en orden)

| Orden | Descripción | URL |
|-------|-------------|-----|
| 1 | ¿Qué es MCP? Introducción oficial | https://modelcontextprotocol.io/docs/getting-started/intro.md |
| 2 | Arquitectura: Host, Client, Server | https://modelcontextprotocol.io/docs/learn/architecture.md |
| 3 | Entender qué es un MCP Server | https://modelcontextprotocol.io/docs/learn/server-concepts.md |
| 4 | **Guía: Build an MCP Server (Python)** | https://modelcontextprotocol.io/docs/develop/build-server.md |
| 5 | SDKs oficiales disponibles | https://modelcontextprotocol.io/docs/sdk.md |
| 6 | Definir Tools en el servidor | https://modelcontextprotocol.io/specification/2025-11-25/server/tools.md |
| 7 | Definir Resources (datos que expones) | https://modelcontextprotocol.io/specification/2025-11-25/server/resources.md |
| 8 | **Transports: SSE y Streamable HTTP** ⭐ | https://modelcontextprotocol.io/specification/2025-11-25/basic/transports.md |
| 9 | Progreso y notificaciones en tiempo real | https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress.md |
| 10 | Tasks: operaciones asíncronas largas | https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks.md |
| 11 | Conectar a servidor remoto desde Claude | https://modelcontextprotocol.io/docs/develop/connect-remote-servers.md |
| 12 | Conectar a servidor local (Claude Desktop) | https://modelcontextprotocol.io/docs/develop/connect-local-servers.md |
| 13 | MCP Inspector (testear tu server) | https://modelcontextprotocol.io/docs/tools/inspector.md |
| 14 | Debugging | https://modelcontextprotocol.io/docs/tools/debugging.md |
| 15 | Security Best Practices | https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices.md |

### LECTURA COMPLEMENTARIA

| Descripción | URL |
|-------------|-----|
| Lifecycle (conexión/desconexión) | https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle.md |
| Cancellation de requests | https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation.md |
| Ping/keepalive | https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/ping.md |
| Pagination de resultados | https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination.md |
| Logging desde el server | https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging.md |
| Schema Reference completo | https://modelcontextprotocol.io/specification/2025-11-25/schema.md |
| Especificación técnica índice | https://modelcontextprotocol.io/specification/2025-11-25/index.md |
| Changelog versión 2025-11-25 | https://modelcontextprotocol.io/specification/2025-11-25/changelog.md |
| Ejemplos de servidores oficiales | https://modelcontextprotocol.io/examples.md |
| Clientes compatibles con MCP | https://modelcontextprotocol.io/clients.md |
| MCP Tasks (extension async) | https://modelcontextprotocol.io/extensions/tasks/overview.md |
| Build an MCP Client | https://modelcontextprotocol.io/docs/develop/build-client.md |
| Client Best Practices | https://modelcontextprotocol.io/docs/develop/clients/client-best-practices.md |
| Authorization (OAuth 2.1) | https://modelcontextprotocol.io/docs/tutorials/security/authorization.md |
| Indice completo de toda la doc | https://modelcontextprotocol.io/llms.txt |

---

## REPOSITORIOS Y EJEMPLOS CLAVE (GitHub)

| Descripción | URL |
|-------------|-----|
| SDK Python oficial | https://github.com/modelcontextprotocol/python-sdk |
| SDK TypeScript oficial | https://github.com/modelcontextprotocol/typescript-sdk |
| Especificación con schemas JSON | https://github.com/modelcontextprotocol/specification |
| MCP Server + WebSocket tiempo real (Python) | https://github.com/virajsharma2000/mcp-websocket |
| FastMCP + WebSocket bidireccional (FastAPI) | https://github.com/thecodekitchen/fastmcp_websockets_example |
| Servidores de ejemplo oficiales | https://github.com/modelcontextprotocol/servers |
| FastMCP (wrapper más simple para Python) | https://github.com/jlowin/fastmcp |

---

## ARQUITECTURA PARA FLASHSCORE.PE (DATOS EN VIVO)

### El problema técnico
Flashscore.pe usa JavaScript dinámico + WebSockets internos para actualizar marcadores.
**No tiene API pública oficial.** Por lo tanto, la estrategia correcta es:
[Flashscore.pe (web live)]
↓ (scraping async con Playwright)
[MCP Server Python] ←→ [LLM / AI Client]
↓
Tools expuestas:
- get_live_matches()
- get_match_detail(match_id)
- subscribe_live_updates(match_id)

text

### Opciones de transporte según el caso

| Caso | Transport recomendado |
|------|-----------------------|
| Desarrollo local / Claude Desktop | stdio |
| Servidor remoto / producción | Streamable HTTP o SSE |
| Push de datos en tiempo real | SSE (Server-Sent Events) |
| Scraping con polling cada N segundos | Streamable HTTP + asyncio |

---

## IMPLEMENTACIÓN: MCP SERVER FLASHSCORE (Python)

### Instalación

```bash
pip install mcp httpx beautifulsoup4 playwright asyncio
playwright install chromium
```

### Estructura del proyecto
flashscore-mcp/
├── server.py # MCP Server principal
├── scraper.py # Lógica de scraping Flashscore
├── models.py # Dataclasses para Match, Score, etc.
├── requirements.txt
└── README.md

text

### Código base: server.py

```python
import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("flashscore-mcp")

# ── TOOL: Listar tools disponibles ──────────────────────────────────
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_live_matches",
            description="Obtiene todos los partidos de fútbol en vivo desde Flashscore.pe",
            inputSchema={
                "type": "object",
                "properties": {
                    "league": {
                        "type": "string",
                        "description": "Filtrar por liga (ej: 'Liga 1', 'Premier League'). Opcional."
                    }
                }
            }
        ),
        types.Tool(
            name="get_match_detail",
            description="Obtiene el marcador y detalles de un partido específico por su ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {
                        "type": "string",
                        "description": "ID único del partido en Flashscore"
                    }
                },
                "required": ["match_id"]
            }
        ),
        types.Tool(
            name="subscribe_live_updates",
            description="Suscribe a actualizaciones en tiempo real de un partido (polling cada 10s)",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Tiempo máximo de suscripción en segundos",
                        "default": 60
                    }
                },
                "required": ["match_id"]
            }
        )
    ]

# ── HANDLER: Ejecutar tools ─────────────────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_live_matches":
        data = await scrape_live_matches(arguments.get("league"))
        return [types.TextContent(type="text", text=str(data))]

    elif name == "get_match_detail":
        data = await scrape_match_detail(arguments["match_id"])
        return [types.TextContent(type="text", text=str(data))]

    elif name == "subscribe_live_updates":
        results = []
        duration = arguments.get("duration_seconds", 60)
        match_id = arguments["match_id"]
        for _ in range(duration // 10):
            data = await scrape_match_detail(match_id)
            results.append(str(data))
            await asyncio.sleep(10)
        return [types.TextContent(type="text", text="\n".join(results))]

    raise ValueError(f"Tool desconocida: {name}")

# ── SCRAPER: Playwright async ───────────────────────────────────────
async def scrape_live_matches(league_filter: str = None) -> list[dict]:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.flashscore.pe/", wait_until="networkidle")
        await page.wait_for_selector(".event__match", timeout=10000)
        matches = await page.query_selector_all(".event__match--live")
        results = []
        for match in matches:
            try:
                home = await (await match.query_selector(".event__participant--home")).inner_text()
                away = await (await match.query_selector(".event__participant--away")).inner_text()
                score = await (await match.query_selector(".event__score")).inner_text()
                results.append({
                    "home": home.strip(),
                    "away": away.strip(),
                    "score": score.strip()
                })
            except Exception:
                continue
        await browser.close()
        if league_filter:
            results = [m for m in results if league_filter.lower() in str(m).lower()]
        return results

async def scrape_match_detail(match_id: str) -> dict:
    from playwright.async_api import async_playwright
    url = f"https://www.flashscore.pe/partido/{match_id}/"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        try:
            score = await (await page.query_selector(".detailScore__wrapper")).inner_text()
            minute = await (await page.query_selector(".smv__timeBox")).inner_text()
            return {"match_id": match_id, "score": score.strip(), "minute": minute.strip()}
        except Exception as e:
            return {"match_id": match_id, "error": str(e)}
        finally:
            await browser.close()

# ── ENTRYPOINT stdio ────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(stdio_server(app))
```

### Configuración en Claude Desktop (claude_desktop_config.json)

```json
{
  "mcpServers": {
    "flashscore": {
      "command": "python",
      "args": ["/ruta/absoluta/a/flashscore-mcp/server.py"]
    }
  }
}
```

---

## VARIANTE CON SSE (para servidor remoto)

Si quieres exponer tu MCP Server en red (producción, GCP, etc.):

```python
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

sse = SseServerTransport("/messages/")

async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await app.run(
            streams, streams,[1]
            app.create_initialization_options()
        )

starlette_app = Starlette(routes=[Route("/sse", endpoint=handle_sse)])

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8080)
```

Conectar desde cliente:
http://localhost:8080/sse

text

---

## TESTING CON MCP INSPECTOR

```bash
# Instalar y conectar a servidor stdio
npx @modelcontextprotocol/inspector python server.py

# Conectar a servidor SSE remoto
npx @modelcontextprotocol/inspector --url http://localhost:8080/sse
```

Documentación: https://modelcontextprotocol.io/docs/tools/inspector.md

---

## CONSIDERACIONES LEGALES Y TÉCNICAS

| Aspecto | Detalle |
|---------|---------|
| **Scraping Flashscore** | No tiene API pública; scraping puede violar ToS. Usar con responsabilidad. |
| **Rate limiting** | Añadir delays entre requests (mínimo 2-3 segundos) |
| **Headless detection** | Usar `--disable-blink-features=AutomationControlled` en Playwright |
| **User-Agent** | Simular browser real para evitar bloqueos |

---

## ALTERNATIVA LEGAL: API-FOOTBALL

```python
# api-football.com — plan gratuito: 100 req/día
@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_live_matches":
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://v3.football.api-sports.io/fixtures",
                params={"live": "all"},
                headers={"x-apisports-key": "TU_API_KEY"}
            )
            return [types.TextContent(type="text", text=response.text)]
```

- Registro: https://www.api-football.com/documentation-v3
- Alternativa gratuita: https://www.football-data.org/

---

## RECURSOS ADICIONALES

| Recurso | URL |
|---------|-----|
| Registro oficial MCP (publicar tu server) | https://modelcontextprotocol.io/registry/quickstart.md |
| Extensiones MCP disponibles | https://modelcontextprotocol.io/extensions/overview.md |
| Roadmap oficial MCP | https://modelcontextprotocol.io/development/roadmap.md |
| Índice de todos los SEPs | https://modelcontextprotocol.io/seps/index.md |
| Índice completo de toda la documentación | https://modelcontextprotocol.io/llms.txt |

---

*Puedes pegar este archivo completo en el contexto de Claude, GPT-4 o Gemini
y pedirle que implemente o extienda el servidor directamente.*
