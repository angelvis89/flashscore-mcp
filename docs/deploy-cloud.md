# Guia de deploy a Hugging Face Spaces

Esta guia te lleva de cero a tener tu MCP corriendo en la nube, gratis, sin
tarjeta. El subproyecto local (`main` branch, PID 7252) sigue intacto.

## 1. Crear cuenta y Space (5 min, una sola vez)

1. Crear cuenta gratis: https://huggingface.co/join (solo email, sin tarjeta).
2. Generar token de acceso:
   - Ir a https://huggingface.co/settings/tokens
   - Click **New token**, nombre `flashscore-mcp-deploy`, tipo **Write**
   - Guarda el token (se ve una sola vez). Anotalo como `HF_TOKEN`.
3. Crear el Space:
   - Ir a https://huggingface.co/new-space
   - **Owner**: tu usuario
   - **Space name**: `flashscore-mcp`
   - **License**: MIT
   - **SDK**: **Docker** (NO Gradio ni Streamlit)
   - **Hardware**: `CPU basic (2 vCPU, 16 GB RAM, free)`
   - **Visibility**: Private (recomendado) o Public
   - Click **Create Space**

URL final: `https://huggingface.co/spaces/<tu-usuario>/flashscore-mcp`
URL de runtime: `https://<tu-usuario>-flashscore-mcp.hf.space`

## 2. Configurar secrets y variables del Space (2 min)

En el Space, ir a **Settings** (engranaje arriba derecha):

- **Variables and secrets** → **New secret**:
  - Name: `MCP_AUTH_TOKEN`
  - Value: genera uno fuerte. En PowerShell:
    ```powershell
    [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
    ```
    Copia el output. Este token sera tu llave privada para usar el MCP desde
    cualquier cliente. Guardalo tambien en tu administrador de contrasenas.

- **Variables and secrets** → **New variable** (opcionales):
  - `FLASHSCORE_MAX_CONCURRENT_PAGES` = `2`
  - `FLASHSCORE_TTL_LIVE_SECONDS` = `8`
  - `MCP_CORS_ORIGINS` = `*` (o restringe a tu dominio)

## 3. Deploy automatico via GitHub Actions (recomendado)

### 3.1. Subir el repo a GitHub

```powershell
cd "c:\Users\User\Desktop\Crear MCP"
# Si todavia no creaste el repo remoto, hazlo en https://github.com/new
# Nombre: flashscore-mcp, privado o publico
git remote add origin https://github.com/<tu-usuario-github>/flashscore-mcp.git
git push -u origin main
git push -u origin cloud
```

### 3.2. Configurar secrets en GitHub

En tu repo de GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

- `HF_TOKEN`: el token de paso 1.2
- `HF_SPACE_REPO`: `<tu-usuario-hf>/flashscore-mcp`

### 3.3. Disparar el deploy

Cada push a la rama `cloud` que toque `src/`, `cloud/` o `pyproject.toml` dispara
el workflow `deploy-hfspace.yml`. Manualmente desde la pestana **Actions**:
seleccionar **deploy-hfspace** → **Run workflow** → rama `cloud`.

El primer build tarda 5-8 min (HF construye la imagen Docker). Logs visibles en
el tab **Logs** del Space.

## 4. Deploy manual sin GitHub (alternativa)

```powershell
cd "c:\Users\User\Desktop\Crear MCP"
.\.venv\Scripts\python.exe -m pip install huggingface_hub

$env:HF_TOKEN = "<tu-token-HF>"
.\.venv\Scripts\python.exe -c @"
from huggingface_hub import HfApi
import os, shutil
os.makedirs('hf-space', exist_ok=True)
shutil.copytree('src', 'hf-space/src', dirs_exist_ok=True)
shutil.copy('cloud/Dockerfile', 'hf-space/Dockerfile')
shutil.copy('cloud/README.md', 'hf-space/README.md')
shutil.copy('pyproject.toml', 'hf-space/pyproject.toml')
api = HfApi(token=os.environ['HF_TOKEN'])
api.upload_folder(folder_path='hf-space', repo_id='<tu-usuario>/flashscore-mcp',
                  repo_type='space', commit_message='deploy manual')
print('OK')
"@
```

## 5. Verificar que esta vivo

```powershell
# Healthcheck publico (no requiere token)
Invoke-WebRequest "https://<tu-usuario>-flashscore-mcp.hf.space/healthz" -UseBasicParsing | Select-Object -ExpandProperty Content
# Debe responder: {"status":"ok","service":"flashscore-mcp"}

# Listar tools (requiere token)
$token = "<MCP_AUTH_TOKEN>"
Invoke-WebRequest -Uri "https://<tu-usuario>-flashscore-mcp.hf.space/mcp" `
  -Method POST `
  -Headers @{Authorization="Bearer $token"; "Content-Type"="application/json"; "Accept"="application/json, text/event-stream"} `
  -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' `
  -UseBasicParsing | Select-Object -ExpandProperty Content
```

## 6. Conectar VS Code / Codex al MCP en la nube

Editar `~/.codex/config.toml` (o el `mcp.json` de VS Code):

```toml
[mcp_servers.flashscore-cloud]
type = "http"
url = "https://<tu-usuario>-flashscore-mcp.hf.space/mcp"

[mcp_servers.flashscore-cloud.headers]
Authorization = "Bearer <MCP_AUTH_TOKEN>"
```

## 7. Notas importantes

- **Sleep automatico**: Spaces gratis duermen tras ~48h sin trafico. Primera
  request despues despertara en 30-60s. Tu cliente reintenta y listo.
- **Limites**: 2 vCPU, 16 GB RAM, 50 GB disco efimero. Suficiente para Chromium
  + tu uso individual.
- **Logs**: en el Space, tab **Logs**. Para errores de Docker mira **Container logs**.
- **Actualizar**: cualquier push a `cloud` redepliega automaticamente.
- **Rollback**: en el Space, tab **Files** → **History** → click en commit
  anterior → **Restore**.
- **Token rotation**: cambia `MCP_AUTH_TOKEN` en Settings; el Space se reinicia
  solo en ~30s.

## 8. Plan B: Fly.io (requiere tarjeta desde 2024)

Si HF Spaces no funciona por algun motivo:

```powershell
# Instalar flyctl
iwr https://fly.io/install.ps1 -useb | iex
fly auth signup  # requiere tarjeta
cd "c:\Users\User\Desktop\Crear MCP\cloud"
fly launch --copy-config --no-deploy
fly secrets set MCP_AUTH_TOKEN="<token-fuerte>"
fly deploy
```

## 9. Plan C: GHCR + cualquier VPS

El workflow `publish-image.yml` publica una imagen Docker en
`ghcr.io/<usuario>/flashscore-mcp:cloud` que puedes correr en cualquier
servidor con Docker (Oracle Cloud free tier, Railway, Render, tu propio
servidor casero, etc.):

```bash
docker run -d -p 8000:8000 \
  -e MCP_AUTH_TOKEN="<token>" \
  --restart=unless-stopped \
  ghcr.io/<usuario>/flashscore-mcp:cloud
```
