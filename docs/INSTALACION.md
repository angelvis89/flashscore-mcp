# Tutorial de instalación — Flashscore MCP **Fast** (Cloud)

Este MCP corre 100% en la nube (Hugging Face Spaces). **No se instala nada localmente** — los clientes (VS Code, Claude, Codex, ChatGPT) sólo necesitan la URL HTTPS y un token Bearer.

- **Repo GitHub**: <https://github.com/angelvis89/flashscore-mcp>
- **Branch productiva**: `cloud-fast`
- **Space HF (objetivo)**: `angelvis-flashscore-mcp-fast` → `https://angelvis-flashscore-mcp-fast.hf.space/mcp`
- **Caché L3 (CDN)**: GitHub Pages del branch `data`

---

## Parte A — Despliegue en la nube (una sola vez)

### A1. Crear el Space en Hugging Face

1. Entra a <https://huggingface.co/new-space>.
2. Owner: `angelvis` · Space name: `flashscore-mcp-fast`.
3. License: MIT · **SDK: Docker** · Hardware: **CPU basic (free)**.
4. Visibility: **Public** (necesario para que VS Code/Claude lo consuman sin login HF).
5. Click **Create Space**. Queda vacío esperando el primer push del workflow.

### A2. Generar token de autenticación del MCP

En PowerShell (sólo lo usas una vez, luego se guarda en secretos):

```powershell
[Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Copia el resultado. Llámalo `MCP_AUTH_TOKEN`.

### A3. Crear un HF Access Token

1. <https://huggingface.co/settings/tokens> → **New token** → role `Write`.
2. Copia el token (`hf_...`). Llámalo `HF_TOKEN`.

### A4. Configurar GitHub Secrets

En el repo: **Settings → Secrets and variables → Actions → New repository secret**.

| Nombre | Valor |
|---|---|
| `HF_TOKEN` | `hf_...` (del paso A3) |
| `HF_SPACE_REPO_FAST` | `angelvis/flashscore-mcp-fast` |
| `MCP_AUTH_TOKEN` | base64 del paso A2 |

### A5. Habilitar GitHub Pages (CDN del caché L3)

1. Repo → **Settings → Pages**.
2. Source: **Deploy from a branch**.
3. Branch: `data` · folder: `/ (root)` → **Save**.

> El branch `data` lo crea automáticamente el workflow `precache.yml` en su primera ejecución.

### A6. Disparar el primer deploy

1. Repo → **Actions → Deploy HF Space (fast)** → **Run workflow** → branch `cloud-fast` → **Run**.
2. Espera ~3-5 min. Verifica el Space en `https://huggingface.co/spaces/angelvis/flashscore-mcp-fast` (debe quedar en **Running**).
3. Smoke test desde PowerShell:

```powershell
$tok = "PEGA_AQUI_TU_MCP_AUTH_TOKEN"
Invoke-RestMethod -Uri "https://angelvis-flashscore-mcp-fast.hf.space/health" -Headers @{ Authorization = "Bearer $tok" }
```

Debe responder `{"status":"ok"}`.

### A7. Activar el precache (opcional pero recomendado)

1. Repo → **Actions → Precache flashscore** → **Run workflow** → branch `cloud-fast`.
2. La primera vez genera `data/live.json`, `data/by_date/*.json`, `data/detail/*.json` en el branch `data`.
3. A partir de ahí corre automático cada 5 min en la ventana **12:00–04:00 UTC** (hora de partidos en Europa/Sudamérica).

---

## Parte B — Conectar desde VS Code (ya quedó listo)

Ya configuré tu `mcp.json` en este workspace. Sólo te falta:

1. Recargar VS Code: `Ctrl+Shift+P` → **Developer: Reload Window**.
2. Abrir el chat → el primer uso de una herramienta `flashscore-fast` te pedirá el token. Pega el `MCP_AUTH_TOKEN` del paso A2. VS Code lo guarda en su keychain.
3. Verifica con: *"con flashscore-fast, dame los partidos de hoy"*.

### MCPs antiguos (desactivados, no eliminados)

Hice backup automático:

- `.vscode\mcp.json.bak-pre-fast-20260522-150751` (workspace)
- `%APPDATA%\Code\User\mcp.json.bak-pre-fast-20260522-150751` (global)

Si en algún momento quieres reactivar el `flashscore` local o el `flashscore-cloud` viejo, copia el bloque correspondiente del backup al `mcp.json` activo.

---

## Parte C — Conectar desde Codex CLI

Edita `~/.codex/config.toml` y añade:

```toml
[mcp_servers.flashscore-fast]
type = "http"
url = "https://angelvis-flashscore-mcp-fast.hf.space/mcp"

[mcp_servers.flashscore-fast.headers]
Authorization = "Bearer TU_MCP_AUTH_TOKEN"
```

Reinicia Codex. Verifica con `codex mcp list`.

---

## Parte D — Conectar desde Claude Desktop

Claude Desktop **no soporta HTTP nativo todavía** — necesita el puente `mcp-remote`.

1. Instala una vez: `npm install -g mcp-remote`
2. Edita `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "flashscore-fast": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://angelvis-flashscore-mcp-fast.hf.space/mcp",
        "--header",
        "Authorization: Bearer TU_MCP_AUTH_TOKEN"
      ]
    }
  }
}
```

3. Reinicia Claude Desktop (cerrar desde la bandeja, no sólo la ventana).
4. En el chat, el icono de herramientas (🔌) debe mostrar `flashscore-fast`.

---

## Parte E — Conectar desde ChatGPT (Custom GPTs / Actions)

ChatGPT aún no consume MCP directo — se conecta vía **Actions** con OpenAPI.

1. Abre <https://chat.openai.com/gpts/editor>.
2. Configure → **Create new action**.
3. **Authentication**: API Key · Auth Type **Bearer** · pega `MCP_AUTH_TOKEN`.
4. En **Schema** pega el spec OpenAPI mínimo:

```yaml
openapi: 3.1.0
info:
  title: Flashscore MCP Fast
  version: "1.0"
servers:
  - url: https://angelvis-flashscore-mcp-fast.hf.space
paths:
  /tools/get_live_scores:
    post:
      operationId: getLiveScores
      summary: Marcadores en vivo
      responses:
        "200": { description: OK }
  /tools/get_matches_by_date:
    post:
      operationId: getMatchesByDate
      summary: Partidos por fecha
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                date: { type: string, example: "2026-05-22" }
      responses:
        "200": { description: OK }
  /tools/get_match_full_detail:
    post:
      operationId: getMatchFullDetail
      summary: Detalle completo (stats+events+odds+lineups)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                match_id: { type: string }
      responses:
        "200": { description: OK }
```

5. **Privacy policy**: pon la URL del repo (`https://github.com/angelvis89/flashscore-mcp`).
6. Guarda. Prueba el GPT con *"dame los partidos del día"*.

---

## Parte F — Otros clientes (Cursor, Continue.dev, Cline, Zed…)

Todos los clientes MCP modernos aceptan transporte `http` con bearer. Patrón genérico:

```json
{
  "name": "flashscore-fast",
  "transport": "http",
  "url": "https://angelvis-flashscore-mcp-fast.hf.space/mcp",
  "headers": { "Authorization": "Bearer TU_MCP_AUTH_TOKEN" }
}
```

---

## Parte G — Herramientas expuestas

| Tool | Para qué sirve |
|---|---|
| `get_live_scores` | Marcadores en vivo (cache L1 ~10s) |
| `get_matches_by_date` | Partidos por fecha YYYY-MM-DD |
| `get_match_detail` | Datos básicos de un partido |
| `get_match_statistics` | Estadísticas (posesión, tiros, etc.) |
| `get_match_events` | Goles, tarjetas, cambios |
| `get_match_odds` | Cuotas 1X2 + Over/Under |
| `get_match_full_detail` | **Todo en paralelo** (6 secciones en ~15 s) |
| `search_matches` | Buscar por texto |
| `watch_match` | Suscribirse a updates de un partido |
| `get_cache_status` / `get_poller_status` | Diagnóstico |
| `refresh_live_cache` | Forzar refresh |
| `start_live_poller` / `stop_live_poller` | Control del poller |

---

## Parte H — Mantenimiento y troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| Space en estado `Build error` | Falta secret `HF_TOKEN` o nombre Space mal | Revisar paso A4 |
| `401 Unauthorized` | Token mal pegado | Verificar bearer en el cliente |
| `503 Service Unavailable` | Space dormido (free tier) | Primer request lo despierta (15-30 s) |
| Respuestas viejas | Caché L3 sin refrescar | Disparar `Precache flashscore` manual |
| Workflow `precache` excede 2000 min/mes | Ventana muy amplia | Editar cron en `.github/workflows/precache.yml` |

### Logs

- **Space**: <https://huggingface.co/spaces/angelvis/flashscore-mcp-fast> → tab **Logs**.
- **Actions**: <https://github.com/angelvis89/flashscore-mcp/actions>.
- **Cliente VS Code**: `Output` → canal **MCP**.

### Rotar el token

1. Generar nuevo con el comando del paso A2.
2. Actualizar secret `MCP_AUTH_TOKEN` en GitHub.
3. Re-run del workflow `Deploy HF Space (fast)`.
4. Actualizar el bearer en cada cliente.

---

## Anexo — Arquitectura

```
┌──────────────────┐   git push    ┌───────────────────────┐
│ Branch cloud-fast│ ────────────▶ │ GitHub Actions        │
└──────────────────┘               │  - deploy-hfspace-fast│
                                   │  - precache (cron */5)│
                                   └──┬──────────────────┬─┘
                                      │                  │
                                      ▼                  ▼
                              ┌──────────────┐   ┌────────────────┐
                              │ HF Space FAST│   │ Branch `data`  │
                              │ FastMCP HTTP │◀──│ GitHub Pages CDN│
                              └──────┬───────┘   └────────────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │ Clientes MCP (VS Code, Claude, Codex...) │
              └──────────────────────────────────────────┘
```

- **Hot path** (live): Cliente → Space → Playwright → respuesta (~5-15 s)
- **Warm path** (cacheado): Cliente → Space → consulta CDN Pages → respuesta (~300 ms)
- **Cold path** (no cacheado): Cliente → Space → Playwright (~15-25 s)
