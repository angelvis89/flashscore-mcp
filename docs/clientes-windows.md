# Clientes MCP en Windows

## Claude Desktop

Archivo de configuracion:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

Ejemplo recomendado usando el Python del entorno virtual:

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

Despues de editar el archivo, reinicia el cliente MCP.

## Provider mock

Para probar sin red:

```json
"SPORTS_PROVIDER": "mock"
```

Instala Chromium antes:

```powershell
python -m playwright install chromium
```
