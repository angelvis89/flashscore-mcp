# AGENTS.md â€” Cerebro del Swarm

## Contexto del usuario y entorno
- **Usuario**: Elvis Camacho (nivel bÃ¡sico de VS Code, paciente)
- **Idioma**: espaÃ±ol latinoamericano en TODO (cÃ³digo, comentarios, logs, mensajes al usuario)
- **OS**: Windows 11 (Victus HP, RTX 5060, 16GB RAM)
- **Shell principal**: PowerShell 5.1 (no PowerShell 7+ por defecto)
- **Modelo recomendado**: claude-opus-4.7 vÃ­a BlackBox AI (NO modelos locales Ollama)
- **Editor**: VS Code con extensiones Claude Code y Copilot Chat

## Stack tÃ­pico de las tareas
- **Automatizaciones locales**: PowerShell + .bat (Windows nativo, sin Node/Python si se puede)
- **APIs REST**: `System.Net.Http.HttpClient` para multipart, `Invoke-RestMethod` para JSON simple
- **Persistencia**: archivos JSON locales (`config.json`, `state.json`) â€” NO bases de datos a menos que se pida
- **UI/notificaciones**: Toast WinRT > Balloon NotifyIcon > MessageBox (cadena de respaldo)
- **Web/scraping**: Playwright MCP cuando es interactivo, fetch directo cuando es API
- **Documentos**: pandoc MCP para PDF/DOCX
- **Archivos**: salida default al Escritorio salvo indicaciÃ³n

## Reglas Generales (todos los agentes)
- Comentarios en espaÃ±ol, identificadores en inglÃ©s cuando aporta legibilidad
- Sin emojis salvo que el usuario los pida
- Logs siempre con timestamp `yyyy-MM-dd HH:mm:ss`
- Encoding UTF-8 con BOM para `.ps1`, sin BOM para `.jsonl`
- Manejar excepciones con mensajes en espaÃ±ol descriptivos
- Doble click en `.bat` es la UX preferida del usuario para automatizaciones

## Token Efficiency Rules
- Output solo lo pedido, sin re-explicar la tarea
- Diffs sobre archivos completos cuando es posible
- No agregar comentarios obvios (`# inicializar variable x`)
- No crear `.md` de documentaciÃ³n a menos que se pida explÃ­citamente
- No agregar features, refactors o "mejoras" no solicitadas

## Sistema de Memoria Persistente

### Antes de empezar tareas (pre-task)
1. Leer `.swarm/memory/index.md` y filtrar por tema relevante
2. `pwsh .swarm/hooks/pre-task.ps1 -Task "<descripcion>" -Agent "<nombre>"` para inyectar contexto
3. Si hay soluciÃ³n previa para tarea similar â†’ REUTILIZAR

### Al terminar tareas (post-task)
1. SIEMPRE invocar `Invoke-PostTask.ps1` (wrapper) â€” NO escribir a `learnings.jsonl` con `Add-Content` a mano
2. El wrapper valida schema, deduplica y actualiza `index.md` automÃ¡ticamente
3. Schema canÃ³nico:
```json
{"timestamp":"ISO-8601","agent":"...","model":"...","task_summary":"...","files_touched":[],"key_solution":"...","errors_encountered":[],"tokens_used":N,"topic_tags":[],"complexity":"simple|moderada|compleja"}
```

## ActivaciÃ³n inteligente del swarm (TRIAGE)

**El swarm NO se activa para todo.** Antes de orquestar agentes, ejecutar:

```powershell
.\.swarm\hooks\triage.ps1 -Task "<descripcion>"
```

Devuelve un objeto con `complexity`, `score` y `recommended_mode`. Reglas:

| Score | Modo | Comportamiento |
|---|---|---|
| 0â€“2 | `direct` | Ejecutar directo con el agente actual + post-task hook. **NO invocar swarm.** |
| 3â€“5 | `assisted` | Cargar contexto de memoria (pre-task) pero ejecutar con un solo agente |
| 6+ | `swarm` | Plan multi-agente con dependencias, reviewer obligatorio |

### SeÃ±ales que suben el score (cada una +1)
- Tarea menciona â‰¥2 capas: backend + frontend / API + tests / DB + auth
- Keywords: `arquitectura`, `migracion`, `refactor masivo`, `multiples archivos`, `varios servicios`
- EstimaciÃ³n de archivos a tocar â‰¥4
- Requiere investigaciÃ³n previa (reverse engineering, lectura de docs externas)
- Riesgo: `produccion`, `borrar`, `destructivo`, `seguridad`
- Dominio nuevo no presente en `learnings.jsonl`
- Tiempo estimado >30 min

### SeÃ±ales que bajan el score (cada una -1)
- Tarea de 1 archivo, 1 funciÃ³n
- "Quick fix", "typo", "ajustar", "cambiar texto"
- SoluciÃ³n conocida ya estÃ¡ en `learnings.jsonl` (similitud >70%)
- Usuario pide explÃ­citamente algo simple ("hazlo rÃ¡pido")

### Ejemplos clasificados
- "ajustar el mensaje del log" â†’ score 0 â†’ `direct`
- "agregar campo en config.json y leerlo" â†’ score 1 â†’ `direct`
- "tracker Shalom con BAT + 15 min loop + notificaciÃ³n" â†’ score 4 â†’ `assisted` (no swarm completo: dominio acotado, 1 stack)
- "migrar app Django de SQLite a Postgres con tests + CI + deploy" â†’ score 8 â†’ `swarm` completo

## Estructura
- `/.swarm/hooks/` â†’ pre-task, post-task, triage
- `/.swarm/memory/` â†’ learnings.jsonl + index.md (cerebro)
- `/.swarm/identities/` â†’ un .md por agente con su perfil acumulado
- `/.swarm/skills/` â†’ recetas reusables (opcional, cargadas selectivamente)
- `/swarm-smart.ps1` â†’ orchestrator inteligente (entry point recomendado)
- `/Invoke-PostTask.ps1` â†’ wrapper para registrar aprendizaje al cerrar
- `/plans/` â†’ planes JSON generados por el orchestrator (cuando aplica)

## Identidades de agentes disponibles
- `architect` â†’ diseÃ±o de sistemas, decisiones de stack
- `executor` â†’ escribe cÃ³digo, ejecuta cambios
- `reviewer` â†’ audita seguridad, calidad, regresiones
- `daily-coder` â†’ tareas del dÃ­a a dÃ­a (default cuando triage = direct)