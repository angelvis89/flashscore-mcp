$ErrorActionPreference = "Stop"

$env:MCP_TRANSPORT = "stdio"
if (-not $env:SPORTS_PROVIDER) {
    $env:SPORTS_PROVIDER = "flashscore"
}

python -m flashscore_mcp.server
