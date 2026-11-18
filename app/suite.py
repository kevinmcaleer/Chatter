"""The kevsrobots suite around the sign-in pages (#81).

Every kevsrobots app (Learn, Projects, BetterCAD, Snakie) signs people in on Chatter's pages. These helpers work out
which app sent someone here, so the page can say "Continue to BetterCAD", and move the pages to their public address,
accounts.kevsrobots.com, once ACCOUNTS_URL is set.
"""

import os
from typing import Optional
from urllib.parse import parse_qsl, urlsplit

from fastapi import Request
from fastapi.responses import RedirectResponse

LEARN = {"name": "kevsrobots.com", "mark": "KR", "accent": "red"}
PROJECTS = {"name": "Projects", "mark": "P", "accent": "gold"}
BETTERCAD = {"name": "BetterCAD", "mark": "B", "accent": "violet"}
SNAKIE = {"name": "Snakie", "mark": "S", "accent": "green"}

HOST_APPS = {
    "bettercad.kevsrobots.com": BETTERCAD,
    "snakie.kevsrobots.com": SNAKIE,
    "app.snakie.org": SNAKIE,
    "projects.kevsrobots.com": PROJECTS,
}

# "Sign in with kevsrobots" clients (#80), by client_id, for the chip on the login and consent pages.
CLIENT_APPS = {
    "snakie": SNAKIE,
}


def app_for_return_to(return_to: Optional[str]) -> Optional[dict]:
    """The suite app a (sanitised) return_to address belongs to, or None for Chatter's own pages."""
    if not return_to:
        return None
    parts = urlsplit(return_to)
    if return_to.startswith("/oauth/authorize"):
        # Signing in on the way to an app's consent page: name the app that asked.
        return CLIENT_APPS.get(dict(parse_qsl(parts.query)).get("client_id", ""))
    if not return_to.startswith("https://"):
        return None
    host = (parts.hostname or "").lower()
    if host in HOST_APPS:
        return HOST_APPS[host]
    if host in ("kevsrobots.com", "www.kevsrobots.com"):
        return PROJECTS if parts.path.startswith("/projects") else LEARN
    return None


def accounts_url() -> str:
    """The public address of the sign-in pages, e.g. https://accounts.kevsrobots.com, or "" while it isn't set up."""
    return os.getenv("ACCOUNTS_URL", "").strip().rstrip("/")


def redirect_to_accounts(request: Request) -> Optional[RedirectResponse]:
    """Send a sign-in page request on any other host (chatter.kevsrobots.com) to the same page on ACCOUNTS_URL."""
    target = accounts_url()
    if not target:
        return None
    target_host = (urlsplit(target).hostname or "").lower()
    if not target_host or (request.url.hostname or "").lower() == target_host:
        return None
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"{target}{request.url.path}{query}", status_code=302)
