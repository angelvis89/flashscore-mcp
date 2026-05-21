$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"
python -c "from flashscore_mcp.config import Settings; from flashscore_mcp.providers.factory import build_provider; from flashscore_mcp.services.poller import live_cache_key; settings=Settings(); provider=build_provider(settings); print(settings.sports_provider); print(provider.source_name); print(live_cache_key('football', None, True))"

Write-Host "Smoke core completado."
