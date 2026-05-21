---
title: Flashscore MCP
emoji: ⚽
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
short_description: MCP server con scraping de marcadores de futbol en vivo
---

# Flashscore MCP (Cloud)

Servidor MCP (Model Context Protocol) que expone marcadores, alineaciones,
estadisticas y cuotas de futbol via streamable-http. Desplegado en
**Hugging Face Spaces** con SDK Docker (gratis, sin tarjeta).

## Endpoints

- `GET /healthz` — healthcheck publico (sin auth)
- `POST /mcp` — endpoint MCP streamable-http (requiere `Authorization: Bearer <token>`)

## Variables de entorno requeridas

Configurar en el panel del Space (Settings → Variables and secrets):

- `MCP_AUTH_TOKEN` *(secret)* — token Bearer privado para autenticar requests
- `MCP_CORS_ORIGINS` *(variable)* — origenes permitidos (default `*`)
- `FLASHSCORE_MAX_CONCURRENT_PAGES` *(variable)* — concurrencia maxima (default 2)
- `FLASHSCORE_TTL_LIVE_SECONDS` *(variable)* — TTL partidos en vivo (default 8)

## Uso desde un cliente MCP

```jsonc
{
  "servers": {
    "flashscore-cloud": {
      "type": "http",
      "url": "https://<usuario>-flashscore-mcp.hf.space/mcp",
      "headers": { "Authorization": "Bearer <MCP_AUTH_TOKEN>" }
    }
  }
}
```

## Arquitectura

- BrowserPool singleton: 1 Chromium reusado entre requests
- Cache TTL estratificado: 8s en vivo, 60s programado, 24h finalizado
- Paralelizacion con `asyncio.gather` para multi-fecha y multi-seccion
- Bloqueo de imagenes/fonts/ads via `route()` (30-50% menos bandwidth)

## Desarrollo local

```powershell
docker build -f cloud/Dockerfile -t flashscore-mcp .
docker run -p 8000:8000 -e MCP_AUTH_TOKEN=test123 flashscore-mcp
curl http://localhost:8000/healthz
```
