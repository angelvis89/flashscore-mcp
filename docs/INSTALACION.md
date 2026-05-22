# Tutorial de instalación — Flashscore MCP **Fast** (Cloud)

Versión optimizada del MCP que reutiliza **el mismo Space que ya tenías** (`angelvis/flashscore-mcp`), sólo que ahora con el código rápido del branch `cloud-fast`. **No hay que crear Space nuevo.**

- **Repo GitHub**: <https://github.com/angelvis89/flashscore-mcp>
- **Branch productivo**: `cloud-fast`
- **Space HF (reutilizado)**: `angelvis/flashscore-mcp` → `https://angelvis-flashscore-mcp.hf.space/mcp`
- **Caché L3 (CDN)**: GitHub Pages del branch `data`

### Qué cambió respecto al cloud viejo

| | Cloud viejo | **Cloud Fast (este)** |
|---|---|---|
| BrowserPool reusable | ❌ Lanzaba Chromium en cada request | ✅ Singleton, warm-up al arranque |
| 6 secciones del detalle | Secuencial (~90 s) | **Paralelo `asyncio.gather` (~15 s)** |
| `fetch_match_detail` | Iteraba 7 días pasados | **URL canónica directa** |
| `storage_state` (cookies) | Aceptaba cookies en cada request | **Persistido, salta el banner** |
| Caché L3 | No existía | **JSON precacheado en GitHub Pages, ~300 ms** |
| `wait_for_timeout` fijos | 2200 ms x 6 | Espera por selector real |

**Resultado**: consultas que tardaban **~60 s** ahora tardan **~5–15 s** en caliente y **~300 ms** si están en caché L3.

---

## Parte A — Migrar el Space existente (una sola vez)

### A1. Generar token de autenticación del MCP

En PowerShell:

```powershell
[Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Copia el resultado. Llámalo `MCP_AUTH_TOKEN`. (Si quieres reutilizar el bearer del cloud viejo `+Dqwt4bWWlr6sFl0kyX266VE3/zwlJhYDtnmGQtFgXU=`, también vale — pero recomiendo rotarlo.)

### A2. Verificar GitHub Secrets

En el repo: **Settings → Secrets and variables → Actions**. Necesitas estos tres (probablemente ya tienes los dos primeros del despliegue anterior):

| Nombre | Valor |
|---|---|
| `HF_TOKEN` | Tu token HF con scope `Write` (<https://huggingface.co/settings/tokens>) |
| `HF_SPACE_REPO` | `angelvis/flashscore-mcp` (el Space existente) |
| `MCP_AUTH_TOKEN` | El bearer del paso A1 |

> Si tu secret se llama `HF_SPACE_REPO_FAST`, renómbralo a `HF_SPACE_REPO` o crea uno nuevo con ese nombre.

### A3. Configurar variables en el Space HF

Ve a <https://huggingface.co/spaces/angelvis/flashscore-mcp/settings> → **Variables and secrets**:

| Nombre | Tipo | Valor |
|---|---|---|
| `MCP_AUTH_TOKEN` | **Secret** | El mismo bearer del paso A1 |
| `FLASHSCORE_STATIC_CACHE_URL` | Variable | `https://angelvis89.github.io/flashscore-mcp` |

### A4. Habilitar GitHub Pages (CDN del caché L3)

1. Repo → **Settings → Pages**.
2. Source: **Deploy from a branch**.
3. Branch: `data` · folder: `/ (root)` → **Save**.

> El branch `data` lo crea automáticamente el workflow `precache.yml` en su primera corrida.

### A5. Disparar el primer deploy FAST

1. Repo → **Actions → deploy-hfspace-fast** → **Run workflow** → branch `cloud-fast` → **Run**.
2. Espera ~3–5 min. El Space `angelvis/flashscore-mcp` se reconstruye con el código nuevo.
3. Verifica en <https://huggingface.co/spaces/angelvis/flashscore-mcp> que quede en estado **Running**.
4. Smoke test:

```powershell
$tok = "PEGA_AQUI_TU_MCP_AUTH_TOKEN"
Invoke-RestMethod -Uri "https://angelvis-flashscore-mcp.hf.space/health" -Headers @{ Authorization = "Bearer $tok" }
```

Debe devolver `{"status":"ok"}`.

### A6. Activar el precache (recomendado)

1. Repo → **Actions → Precache flashscore** → **Run workflow** → branch `cloud-fast`.
2. Genera `data/live.json`, `data/by_date/*.json`, `data/detail/*.json` en el branch `data`.
3. A partir de ahí corre automático cada 5 min en la ventana **12:00–04:00 UTC**.

---

## Parte B — Conectar desde VS Code (ya quedó listo)

Tu `mcp.json` ya tiene los dos servidores activos: `flashscore` (local) + `flashscore-fast` (HTTP cloud).

1. Recarga VS Code: `Ctrl+Shift+P` → **Developer: Reload Window**.
2. El primer uso de `flashscore-fast` te pedirá el token → pega el `MCP_AUTH_TOKEN`. VS Code lo guarda en su keychain.
3. Verifica con: *"usa flashscore-fast para darme los partidos de hoy"*.

### Cuándo usar cada uno

| MCP | Cuándo |
|---|---|
| `flashscore-fast` | **Por defecto.** Es el rápido, corre en la nube, soporta paralelización y caché L3. |
| `flashscore` (local) | Sólo si la nube está caída o necesitas debuggear cambios sin desplegar. |

---

## Parte C — Conectar desde Codex CLI

Edita `~/.codex/config.toml`:

```toml
[mcp_servers.flashscore-fast]
type = "http"
url = "https://angelvis-flashscore-mcp.hf.space/mcp"

[mcp_servers.flashscore-fast.headers]
Authorization = "Bearer TU_MCP_AUTH_TOKEN"
```

Reinicia Codex. Verifica con `codex mcp list`.

---

## Parte D — Conectar desde Claude Desktop

Claude Desktop **no soporta HTTP nativo** todavía — necesita el puente `mcp-remote`.

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
        "https://angelvis-flashscore-mcp.hf.space/mcp",
        "--header",
        "Authorization: Bearer TU_MCP_AUTH_TOKEN"
      ]
    }
  }
}
```

3. Reinicia Claude Desktop (ciérralo desde la bandeja, no sólo la ventana).
4. En el chat, el icono 🔌 debe mostrar `flashscore-fast`.

---

## Parte E — Conectar desde ChatGPT (Custom GPTs / Actions)

ChatGPT aún no consume MCP directo — se conecta vía **Actions** con OpenAPI.

1. Abre <https://chat.openai.com/gpts/editor>.
2. **Configure → Create new action**.
3. **Authentication**: API Key · Auth Type **Bearer** · pega `MCP_AUTH_TOKEN`.
4. En **Schema** pega:

```yaml
openapi: 3.1.0
info:
  title: Flashscore MCP Fast
  version: "1.0"
servers:
  - url: https://angelvis-flashscore-mcp.hf.space
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

5. **Privacy policy**: `https://github.com/angelvis89/flashscore-mcp`.
6. Guarda. Prueba con *"dame los partidos del día"*.

---

## Parte F — Otros clientes (Cursor, Continue.dev, Cline, Zed…)

Patrón genérico HTTP+bearer:

```json
{
  "name": "flashscore-fast",
  "transport": "http",
  "url": "https://angelvis-flashscore-mcp.hf.space/mcp",
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

| Síntoma | Causa | Fix |
|---|---|---|
| Space en `Build error` | Falta secret `HF_TOKEN` o nombre Space mal | Revisar A2 |
| `401 Unauthorized` | Token mal pegado | Verificar bearer en el cliente |
| `503 Service Unavailable` | Space dormido | Primer request lo despierta (15–30 s) |
| Respuestas viejas | Caché L3 sin refrescar | Disparar `Precache flashscore` manual |
| Workflow excede 2000 min/mes | Ventana muy amplia | Editar cron en `.github/workflows/precache.yml` |

### Logs

- **Space**: <https://huggingface.co/spaces/angelvis/flashscore-mcp> → tab **Logs**.
- **Actions**: <https://github.com/angelvis89/flashscore-mcp/actions>.
- **VS Code**: `Output` → canal **MCP**.

### Rotar el token

1. Generar nuevo (paso A1).
2. Actualizar secret `MCP_AUTH_TOKEN` en GitHub + variable `MCP_AUTH_TOKEN` en el Space.
3. Re-run del workflow `deploy-hfspace-fast`.
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
                              │ HF Space     │   │ Branch `data`  │
                              │ (reutilizado)│◀──│ GitHub Pages CDN│
                              │ FastMCP HTTP │   └────────────────┘
                              └──────┬───────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │ Clientes MCP (VS Code, Claude, Codex...) │
              └──────────────────────────────────────────┘
```

- **Hot path** (live, sin caché): ~5–15 s
- **Warm path** (cacheado en CDN Pages): ~300 ms
- **Cold path** (Space dormido despertando): ~15–25 s
