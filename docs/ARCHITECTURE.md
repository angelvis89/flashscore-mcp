# Arquitectura

## Objetivo

Exponer datos deportivos vivos por MCP sin acoplar las tools al scraping. El servidor depende de la interfaz `SportsDataProvider`, de modo que se pueda usar `mock`, `flashscore` u otro proveedor futuro.

## Flujo

```text
Host MCP
  -> FastMCP server
  -> tools/resources
  -> AsyncTTLCache
  -> LivePoller opcional
  -> SportsDataProvider
```

## Modos

- `stdio`: recomendado para escritorio y pruebas locales.
- `streamable-http`: recomendado para despliegue remoto o multiusuario.

## Datos vivos

El patron profesional es:

1. `start_live_poller` mantiene un snapshot en cache.
2. `get_live_scores` devuelve cache fresco si existe.
3. Si el cache esta vencido o se fuerza refresco, se consulta el proveedor.
4. Si el proveedor falla, se devuelve cache viejo con `stale=true` cuando exista.

## Proveedores

- `MockSportsProvider`: pruebas sin red.
- `FlashscorePlaywrightProvider`: experimental, extrae DOM con Playwright.

## Siguientes mejoras recomendadas

- Persistir cache en Redis si hay varios procesos.
- Agregar un proveedor basado en endpoints observados si se decide investigar trafico.
- Agregar autenticacion Bearer para `streamable-http`.
- Agregar logging estructurado por `stderr` en `stdio`.
