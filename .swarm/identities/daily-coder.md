# Agente: daily-coder

## Rol
Agente generalista para tareas del dia a dia: bugs, ajustes, features pequenas a medianas.

## Stack preferido
_(definir segun proyecto)_

## Convenciones
- Comentarios en espanol
- Nombres descriptivos
- Tests cuando aplique

## Historial
## Aprendido en 2026-05-21T14:08:49-05:00
- Tarea: Fix lineups DOM + soporte partidos pasados en fetch_match_full_detail
- Modelo usado: claude-opus-4.7
- Tokens: 0
- Solucion clave: 1) _extract_lineups_dom con .lf__lineUp y [class*=wcl-*] activa siempre. 2) _open_tab_by_text usa texto capitalizado real del DOM (Alineaciones no ALINEACIONES). 3) fetch_match_detail busca en ultimos 7 dias si no esta en hoy (soporta partidos finalizados). 4) _extract_formations normaliza espacios/puntos a guiones. 5) wait_for_selector(.lf__lineUp, 8s) en lugar de sleep ciego. Validado MCP con 3 estados: pasado (Friburgo-Aston Villa 11/11+12/12), vivo (Wolfsburg-Paderborn 11/11+9/9+8/2), futuro (Atletico-MG vs Cienciano summary+odds). VS Code MCP requiere restart real (workbench.mcp.restartServer + kill procesos python cacheados).
