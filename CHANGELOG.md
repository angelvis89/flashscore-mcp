# Changelog

## 0.1.1 - 2026-05-21

- fix(lineups): extraccion DOM con `.lf__lineUp` + `data-testid` y `[class*='wcl-*']`.
  Titulares, suplentes, ausentes y entrenadores ahora se entregan estructurados
  por equipo (`home`/`away`) con numero, nombre, pais, URL del jugador, roles
  (`(G)` portero, `(C)` capitan) y motivo de ausencia (lesion, sancion).
- fix(navegacion): la pestana "Alineaciones" se localiza por texto capitalizado
  (el CSS la pinta en mayusculas pero el DOM la tiene como `Alineaciones`).
  `_open_tab_by_text` ahora prueba multiples variantes y regex case-insensitive.
- fix(espera): se reemplaza el sleep ciego por `wait_for_selector('.lf__lineUp')`
  con timeout de 8s; si no aparece, se cae al parser de texto previo.
- chore: scripts de smoke y diagnostico (`smoke_wolfsburg_paderborn.py`,
  `compare_two_matches.py`, `debug_lineups_dom.py`).

## 0.1.0 - 2026-05-21

- Implementacion inicial del servidor MCP.
- Tools para marcadores, detalle, cache y poller.
- Provider `mock` para pruebas locales.
- Provider experimental `flashscore` con Playwright.
- Documentacion Windows y arquitectura inicial.
