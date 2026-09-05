# Browser evidence harness fixtures — CIR-PROC-BROWSER-EVIDENCE (system tier, ⚖-R48).
#
# The "real component" here is a headless browser fetching the BAKED page over real HTTP
# (not file://) and reporting measurable properties — never a screenshot
# (CIR-PROC-BROWSER-EVIDENCE#screenshots-are-not-the-assertion).
#
# Inputs come from scripts/test-browser.sh, which bakes the fixture person into
# CIRCLES_PAGES_DIR (`index.html` — the fixture at reference date 2026-08-03 — and
# `index-2-warnings.html` — the same artifact with exactly 2 warnings). Tests never invent
# a second person (CIR-PROC-TEST-FIXTURES).
#
# Not collected by the unit run: pyproject.toml addopts carries `--ignore=tests/browser`;
# the harness overrides it with `-o addopts=`.

from __future__ import annotations

import functools
import http.server
import os
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

# CIR-RENDER-REFERENCE-VIEWPORT#viewport-gate-is-fixed: every one-screen assertion is
# evaluated at 1280 × 800 CSS px (⚖-R37). This is the harness's single source for it.
REFERENCE_VIEWPORT: tuple[int, int] = (1280, 800)


@pytest.fixture(scope="session")
def reference_viewport() -> tuple[int, int]:
    """The harness constant, exposed as a fixture (tests/ is not an importable package)."""
    return REFERENCE_VIEWPORT


@pytest.fixture(scope="session")
def pages_dir() -> Path:
    raw = os.environ.get("CIRCLES_PAGES_DIR")
    if not raw:
        pytest.fail(
            "CIRCLES_PAGES_DIR is not set — run the browser tier via "
            "`devbox run test-browser` (scripts/test-browser.sh bakes the pages)"
        )
    path = Path(raw)
    for name in ("index.html", "index-2-warnings.html"):
        if not (path / name).is_file():
            pytest.fail(f"CIRCLES_PAGES_DIR={raw} has no {name} — bake step missing")
    return path


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        pass


@pytest.fixture(scope="session")
def served(pages_dir: Path) -> Iterator[str]:
    """Serve CIRCLES_PAGES_DIR over real HTTP on 127.0.0.1:<free port>."""
    handler = functools.partial(_QuietHandler, directory=str(pages_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, name="circles-pages", daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(headless=True)
        try:
            yield chromium
        finally:
            chromium.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    """A fresh headless-Chromium page per test, opened at the reference viewport."""
    width, height = REFERENCE_VIEWPORT
    context = browser.new_context(viewport={"width": width, "height": height})
    try:
        yield context.new_page()
    finally:
        context.close()
