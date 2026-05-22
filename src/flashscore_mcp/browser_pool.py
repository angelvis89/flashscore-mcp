"""Pool singleton de navegador Chromium para reutilizar el proceso entre requests.

Beneficio: evita pagar el costo de ``chromium.launch()`` (~5 s) en cada llamada.
Una unica instancia de ``Browser`` vive durante toda la vida del MCP server.
Cada request abre un ``Context`` + ``Page`` (operaciones baratas, < 100 ms).

Tambien instala una ruta global de bloqueo de recursos pesados (imagenes,
fuentes, ads, trackers) para reducir bandwidth y latencia 30-50%.

El pool es thread-safe via ``asyncio.Lock`` y se auto-relanza si el browser
queda desconectado (crash, OOM, etc.).
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import Browser, Playwright

    from flashscore_mcp.config import Settings


logger = logging.getLogger(__name__)

# Patrones de recursos a bloquear (imagen, fuente, ads, analytics).
# Atajamos por extension y por dominio conocido.
_BLOCKED_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".mp4",
    ".webm",
)
_BLOCKED_HOSTS = (
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "facebook.net",
    "facebook.com",
    "googlesyndication.com",
    "adservice.google",
    "scorecardresearch",
    "hotjar.com",
    "amplitude.com",
    "criteo.com",
    "taboola.com",
    "outbrain.com",
)

_CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-sync",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-dev-shm-usage",
    "--disable-background-networking",
    "--disable-default-apps",
    "--mute-audio",
]


def _should_block(url: str, resource_type: str) -> bool:
    if resource_type in {"image", "media", "font"}:
        return True
    lower = url.lower()
    if any(lower.endswith(ext) for ext in _BLOCKED_EXTENSIONS):
        return True
    if any(host in lower for host in _BLOCKED_HOSTS):
        return True
    return False


async def _block_route(route: Any) -> None:  # pragma: no cover - integracion playwright
    request = route.request
    try:
        if _should_block(request.url, request.resource_type):
            await route.abort()
        else:
            await route.continue_()
    except Exception:
        # Si el browser se cerro entre tanto, ignorar silenciosamente
        try:
            await route.continue_()
        except Exception:
            pass


class BrowserPool:
    """Singleton asincrono que mantiene un Chromium vivo entre requests."""

    _instance: BrowserPool | None = None

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()
        self._page_semaphore = asyncio.Semaphore(settings.max_concurrent_pages)

    @classmethod
    def get_instance(cls, settings: Settings) -> BrowserPool:
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance

    async def _ensure_browser(self) -> Browser:
        from playwright.async_api import async_playwright

        async with self._lock:
            if (
                self._browser is not None
                and self._playwright is not None
                and self._browser.is_connected()
            ):
                return self._browser

            # (Re)inicializar
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.settings.headless,
                args=_CHROMIUM_ARGS,
            )
            logger.info("Chromium iniciado en pool (headless=%s)", self.settings.headless)
            return self._browser

    @asynccontextmanager
    async def page(self) -> Any:
        """Devuelve un ``(context, page)`` listo para navegar.

        - Limita la concurrencia segun ``settings.max_concurrent_pages``.
        - Instala bloqueo de recursos pesados via ``route``.
        - Si existe ``settings.storage_state_path`` valido, lo carga (cookies cacheadas).
        - Cierra el context al salir (no el browser, que es persistente).
        """
        async with self._page_semaphore:
            browser = await self._ensure_browser()
            context_kwargs: dict[str, Any] = dict(
                locale="es-PE",
                timezone_id="America/Lima",
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                extra_http_headers={"Accept-Language": "es-PE,es;q=0.9"},
            )
            state_path = getattr(self.settings, "storage_state_path", "") or ""
            if state_path and os.path.isfile(state_path):
                try:
                    context_kwargs["storage_state"] = state_path
                except Exception:
                    pass
            context = await browser.new_context(**context_kwargs)
            try:
                await context.route("**/*", _block_route)
                page = await context.new_page()
                page.set_default_timeout(self.settings.timeout_ms)
                yield context, page
            finally:
                try:
                    await context.close()
                except Exception:
                    pass

    async def save_storage_state(self, context: Any) -> None:
        """Persiste cookies + localStorage del context a disco para reuso."""
        state_path = getattr(self.settings, "storage_state_path", "") or ""
        if not state_path:
            return
        try:
            os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
            await context.storage_state(path=state_path)
            logger.info("storage_state guardado en %s", state_path)
        except Exception as exc:  # pragma: no cover
            logger.warning("No se pudo guardar storage_state: %s", exc)

    async def close(self) -> None:
        async with self._lock:
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
        logger.info("Pool de Chromium cerrado")


async def get_browser_pool(settings: Settings) -> BrowserPool:
    """Helper factoria para obtener el pool singleton."""
    return BrowserPool.get_instance(settings)
