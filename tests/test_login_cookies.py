"""A leftover host-only login cookie must not keep people bounced back to /login."""
from fastapi.responses import RedirectResponse

from app.auth import clear_host_only_login_cookies


def test_production_login_expires_host_only_cookies():
    r = RedirectResponse("/account", status_code=303)
    clear_host_only_login_cookies(r, production=True)
    r.set_cookie("access_token", "Bearer t", domain=".kevsrobots.com")
    cookies = r.headers.getlist("set-cookie")
    expired = [c for c in cookies if "Max-Age=0" in c]
    assert {c.split("=")[0] for c in expired} == {"access_token", "username"}
    assert all("Domain" not in c for c in expired)
    assert any("Domain=.kevsrobots.com" in c and "Bearer t" in c for c in cookies)


def test_development_leaves_cookies_alone():
    r = RedirectResponse("/account", status_code=303)
    clear_host_only_login_cookies(r, production=False)
    assert r.headers.getlist("set-cookie") == []
