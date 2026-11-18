"""Sign in with kevsrobots (#80): OAuth 2 authorization code + PKCE, refresh rotation, revoke, connected apps."""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import Comment, Like, User
from app.oauth import (
    DEFAULT_CLIENTS,
    hash_secret,
    redirect_uri_allowed,
    require_scope,
    seed_clients,
    with_params,
)
from app.oauth_models import OAuthClient, OAuthCode, OAuthGrant, OAuthRefreshToken
from app.suite import app_for_return_to
from app.utils import create_access_token, decode_access_token, hash_password

WEB = "https://app.snakie.org/auth/callback"
DESKTOP = "http://127.0.0.1:53682/callback"
TABLES = [User.__table__, Like.__table__, Comment.__table__, OAuthClient.__table__, OAuthCode.__table__, OAuthGrant.__table__,
          OAuthRefreshToken.__table__]


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Only the tables used here: the full metadata fails on main today (projects.primary_image_id → project_image).
    SQLModel.metadata.create_all(engine, tables=TABLES)
    with Session(engine) as session:
        seed_clients(session)
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, monkeypatch):
    monkeypatch.delenv("ACCOUNTS_URL", raising=False)
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture(name="user")
def user_fixture(session):
    user = User(username="maker", firstname="Ada", lastname="Maker", email="ada@example.com",
                hashed_password=hash_password("Pass1234"), status="active", type=0, profile_picture="1_ada.png")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def sign_in(client, user):
    client.cookies.set("access_token", f"Bearer {create_access_token({'sub': user.username})}")


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def authorize_params(challenge, redirect_uri=WEB, scope="profile projects:write", **extra):
    params = {
        "response_type": "code", "client_id": "snakie", "redirect_uri": redirect_uri, "scope": scope,
        "state": "xyz", "code_challenge": challenge, "code_challenge_method": "S256",
    }
    params.update(extra)
    return params


def query_of(response):
    return {key: values[0] for key, values in parse_qs(urlsplit(response.headers["location"]).query).items()}


def get_code(client, user, redirect_uri=WEB, scope="profile projects:write"):
    """Sign in, agree on the consent page, and return (code, verifier)."""
    verifier, challenge = pkce()
    sign_in(client, user)
    page = client.get("/oauth/authorize", params=authorize_params(challenge, redirect_uri, scope))
    if page.status_code == 200:
        consent = page.text.split('name="consent" value="')[1].split('"')[0]
        page = client.post("/oauth/authorize", data={"consent": consent, "decision": "allow"})
    assert page.status_code == 303
    assert page.headers["location"].startswith(redirect_uri)
    query = query_of(page)
    assert query["state"] == "xyz"
    return query["code"], verifier


def exchange(client, code, verifier, redirect_uri=WEB):
    return client.post("/oauth/token", data={
        "grant_type": "authorization_code", "client_id": "snakie", "code": code,
        "code_verifier": verifier, "redirect_uri": redirect_uri,
    })


def refresh(client, token):
    return client.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": "snakie",
                                             "refresh_token": token})


# --- Redirect URIs -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("uri, allowed", [
    (WEB, True),
    ("http://127.0.0.1:53682/callback", True),
    ("http://127.0.0.1/callback", True),
    ("http://127.0.0.1:1/callback", True),
    ("https://app.snakie.org/auth/callback/", False),
    ("https://app.snakie.org/auth/callback#x", False),
    ("https://app.snakie.org.evil.com/auth/callback", False),
    ("http://app.snakie.org/auth/callback", False),
    ("http://127.0.0.1:53682/other", False),
    ("http://127.0.0.1:53682/callback?next=x", False),
    ("http://user@127.0.0.1:53682/callback", False),
    ("http://localhost:53682/callback", False),
    ("http://127.0.0.1:99999/callback", False),
    ("", False),
    (None, False),
])
def test_redirect_uri_allowed(uri, allowed):
    client = OAuthClient(**DEFAULT_CLIENTS[0])
    assert redirect_uri_allowed(client, uri) is allowed


def test_with_params_keeps_existing_query():
    assert with_params("https://a.example/cb?x=1", code="c", state=None) == "https://a.example/cb?x=1&code=c"


def test_seed_clients_is_idempotent(session):
    seed_clients(session)
    assert len(session.exec(select(OAuthClient)).all()) == 1


# --- Authorize -----------------------------------------------------------------------------------------------------

def test_signed_out_goes_to_login_and_login_names_snakie(client):
    _, challenge = pkce()
    response = client.get("/oauth/authorize", params=authorize_params(challenge))
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/login?return_to=%2Foauth%2Fauthorize%3F")
    login = client.get(location)
    assert "Continue to Snakie" in login.text
    assert 'name="return_to" value="/oauth/authorize?' in login.text


def test_app_for_return_to_reads_the_client_from_authorize():
    assert app_for_return_to("/oauth/authorize?client_id=snakie&scope=profile")["name"] == "Snakie"
    assert app_for_return_to("/oauth/authorize?client_id=nobody") is None
    assert app_for_return_to("/account") is None


def test_consent_page_lists_permissions(client, user):
    _, challenge = pkce()
    sign_in(client, user)
    page = client.get("/oauth/authorize", params=authorize_params(challenge))
    assert page.status_code == 200
    assert "Allow Snakie to use your account?" in page.text
    assert "Add wiring diagrams and parts lists to your projects" in page.text
    assert "See your name and profile picture" in page.text
    assert "Continue to Snakie" in page.text
    assert "/logout?return_to=%2Foauth%2Fauthorize" in page.text


def test_logout_keeps_a_safe_return_to(client):
    response = client.get("/logout", params={"return_to": "/oauth/authorize?client_id=snakie"})
    assert response.headers["location"] == "/login?return_to=%2Foauth%2Fauthorize%3Fclient_id%3Dsnakie"
    assert client.get("/logout", params={"return_to": "https://evil.example/"}).headers["location"] == "/login"


@pytest.mark.parametrize("params, message", [
    ({"client_id": "nobody"}, "registered with kevsrobots"),
    ({"client_id": None}, "registered with kevsrobots"),
    ({"redirect_uri": "https://evil.example/callback"}, "allowed to"),
])
def test_bad_client_or_redirect_shows_an_error_page(client, user, params, message):
    _, challenge = pkce()
    sign_in(client, user)
    query = {k: v for k, v in {**authorize_params(challenge), **params}.items() if v is not None}
    response = client.get("/oauth/authorize", params=query)
    assert response.status_code == 400
    assert message in response.text


@pytest.mark.parametrize("params, error", [
    ({"response_type": "token"}, "unsupported_response_type"),
    ({"code_challenge_method": "plain"}, "invalid_request"),
    ({"code_challenge": "short"}, "invalid_request"),
    ({"scope": "code:write"}, "invalid_scope"),
    ({"scope": ""}, "invalid_scope"),
])
def test_bad_requests_go_back_to_the_app_with_an_error(client, user, params, error):
    _, challenge = pkce()
    sign_in(client, user)
    response = client.get("/oauth/authorize", params={**authorize_params(challenge), **params})
    assert response.status_code == 303
    assert response.headers["location"].startswith(WEB)
    assert query_of(response)["error"] == error
    assert query_of(response)["state"] == "xyz"


def test_cancel_sends_access_denied(client, user):
    _, challenge = pkce()
    sign_in(client, user)
    page = client.get("/oauth/authorize", params=authorize_params(challenge))
    consent = page.text.split('name="consent" value="')[1].split('"')[0]
    response = client.post("/oauth/authorize", data={"consent": consent, "decision": "cancel"})
    assert query_of(response)["error"] == "access_denied"
    assert query_of(response)["state"] == "xyz"


def test_consent_from_another_account_is_refused(client, user, session):
    other = User(username="other", firstname="O", lastname="T", email="o@example.com",
                 hashed_password=hash_password("x"), status="active", type=0)
    session.add(other)
    session.commit()
    _, challenge = pkce()
    sign_in(client, user)
    page = client.get("/oauth/authorize", params=authorize_params(challenge))
    consent = page.text.split('name="consent" value="')[1].split('"')[0]
    sign_in(client, other)
    response = client.post("/oauth/authorize", data={"consent": consent, "decision": "allow"})
    assert response.status_code == 400
    assert "expired" in response.text


def test_consent_token_is_not_a_sign_in_token(client, user):
    _, challenge = pkce()
    sign_in(client, user)
    page = client.get("/oauth/authorize", params=authorize_params(challenge))
    consent = page.text.split('name="consent" value="')[1].split('"')[0]
    assert "sub" not in decode_access_token(consent)
    client.cookies.clear()
    assert client.get("/api/me", headers={"Authorization": f"Bearer {consent}"}).status_code in (401, 403)


def test_second_sign_in_skips_consent(client, user):
    code, verifier = get_code(client, user)
    assert exchange(client, code, verifier).status_code == 200
    _, challenge = pkce()
    response = client.get("/oauth/authorize", params=authorize_params(challenge, scope="profile"))
    assert response.status_code == 303
    assert "code" in query_of(response)


# --- Token ---------------------------------------------------------------------------------------------------------

def test_happy_path_web(client, user):
    code, verifier = get_code(client, user)
    response = exchange(client, code, verifier)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert body["scope"] == "profile projects:write"
    claims = decode_access_token(body["access_token"])
    assert claims["sub"] == "maker"
    assert claims["client_id"] == "snakie"
    assert claims["scope"] == "profile projects:write"
    assert body["refresh_token"]


def test_happy_path_desktop_loopback(client, user):
    code, verifier = get_code(client, user, redirect_uri=DESKTOP)
    assert exchange(client, code, verifier, redirect_uri=DESKTOP).status_code == 200


def test_wrong_verifier(client, user):
    code, _ = get_code(client, user)
    response = exchange(client, code, pkce()[0])
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"


def test_reused_code_is_refused_and_revokes_the_grant(client, user, session):
    code, verifier = get_code(client, user)
    tokens = exchange(client, code, verifier).json()
    again = exchange(client, code, verifier)
    assert again.status_code == 400
    assert again.json()["error"] == "invalid_grant"
    assert session.exec(select(OAuthGrant)).one().revoked_at is not None
    assert refresh(client, tokens["refresh_token"]).json()["error"] == "invalid_grant"


def test_expired_code(client, user, session):
    code, verifier = get_code(client, user)
    row = session.exec(select(OAuthCode)).one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    session.add(row)
    session.commit()
    assert exchange(client, code, verifier).json()["error"] == "invalid_grant"


def test_wrong_redirect_uri_at_token(client, user):
    code, verifier = get_code(client, user)
    assert exchange(client, code, verifier, redirect_uri="http://127.0.0.1:1/callback").json()["error"] == "invalid_grant"


def test_unknown_code_client_and_grant_type(client, user):
    assert exchange(client, "nope", pkce()[0]).json()["error"] == "invalid_grant"
    bad_client = client.post("/oauth/token", data={"grant_type": "authorization_code", "client_id": "x"})
    assert bad_client.status_code == 401
    assert bad_client.json()["error"] == "invalid_client"
    assert client.post("/oauth/token", data={"grant_type": "password", "client_id": "snakie"}).json()["error"] == \
        "unsupported_grant_type"
    assert client.post("/oauth/token", data={"grant_type": "authorization_code", "client_id": "snakie"}).json()[
        "error"] == "invalid_request"
    assert client.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": "snakie"}).json()[
        "error"] == "invalid_request"


def test_code_for_another_client_is_refused(client, user, session):
    session.add(OAuthClient(client_id="other", name="Other", redirect_uris=WEB, scopes="profile"))
    session.commit()
    code, verifier = get_code(client, user)
    response = client.post("/oauth/token", data={"grant_type": "authorization_code", "client_id": "other",
                                                 "code": code, "code_verifier": verifier, "redirect_uri": WEB})
    assert response.json()["error"] == "invalid_grant"


# --- Refresh -------------------------------------------------------------------------------------------------------

def test_refresh_rotates(client, user):
    code, verifier = get_code(client, user)
    first = exchange(client, code, verifier).json()
    second = refresh(client, first["refresh_token"])
    assert second.status_code == 200
    assert second.json()["refresh_token"] != first["refresh_token"]
    assert refresh(client, second.json()["refresh_token"]).status_code == 200


def test_refresh_reuse_revokes_the_grant(client, user, session):
    code, verifier = get_code(client, user)
    first = exchange(client, code, verifier).json()
    second = refresh(client, first["refresh_token"]).json()
    reused = refresh(client, first["refresh_token"])
    assert reused.json()["error"] == "invalid_grant"
    assert session.exec(select(OAuthGrant)).one().revoked_at is not None
    # The newer token stops working too: whoever copied the old one can't keep the app signed in.
    assert refresh(client, second["refresh_token"]).json()["error"] == "invalid_grant"


def test_expired_refresh_token(client, user, session):
    code, verifier = get_code(client, user)
    tokens = exchange(client, code, verifier).json()
    row = session.exec(select(OAuthRefreshToken)).one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    session.add(row)
    session.commit()
    assert refresh(client, tokens["refresh_token"]).json()["error"] == "invalid_grant"


def test_refresh_with_another_client_or_unknown_token(client, user, session):
    session.add(OAuthClient(client_id="other", name="Other", redirect_uris=WEB, scopes="profile"))
    session.commit()
    code, verifier = get_code(client, user)
    tokens = exchange(client, code, verifier).json()
    other = client.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": "other",
                                              "refresh_token": tokens["refresh_token"]})
    assert other.json()["error"] == "invalid_grant"
    assert refresh(client, "nope").json()["error"] == "invalid_grant"


def test_stored_secrets_are_hashed(client, user, session):
    code, verifier = get_code(client, user)
    tokens = exchange(client, code, verifier).json()
    assert session.exec(select(OAuthCode)).one().code_hash == hash_secret(code)
    assert session.exec(select(OAuthRefreshToken)).one().token_hash == hash_secret(tokens["refresh_token"])


# --- Using the token -----------------------------------------------------------------------------------------------

def test_userinfo_with_profile_scope(client, user):
    code, verifier = get_code(client, user)
    access = exchange(client, code, verifier).json()["access_token"]
    client.cookies.clear()
    response = client.get("/oauth/userinfo", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 200
    assert response.json()["username"] == "maker"
    assert response.json()["name"] == "Ada Maker"
    assert response.json()["picture"].endswith("/profile_pictures/1_ada.png")


def test_userinfo_without_profile_scope(client, user):
    code, verifier = get_code(client, user, scope="projects:write")
    access = exchange(client, code, verifier).json()["access_token"]
    client.cookies.clear()
    response = client.get("/oauth/userinfo", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 403
    assert "insufficient_scope" in response.headers["www-authenticate"]


def test_userinfo_takes_a_normal_sign_in_and_refuses_junk(client, user):
    sign_in(client, user)
    assert client.get("/oauth/userinfo").json()["username"] == "maker"
    client.cookies.clear()
    assert client.get("/oauth/userinfo").status_code == 401
    assert client.get("/oauth/userinfo", headers={"Authorization": "Bearer junk"}).status_code == 401
    odd = create_access_token({"sub": "maker", "purpose": "something"})
    assert client.get("/oauth/userinfo", headers={"Authorization": f"Bearer {odd}"}).status_code == 401
    ghost = create_access_token({"sub": "ghost"})
    assert client.get("/oauth/userinfo", headers={"Authorization": f"Bearer {ghost}"}).status_code == 401


def test_app_tokens_cant_use_account_routes(client, user):
    code, verifier = get_code(client, user)
    access = exchange(client, code, verifier).json()["access_token"]
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {access}"}
    assert client.get("/api/me", headers=headers).status_code == 403
    assert client.delete("/api/me", headers=headers).status_code == 403
    assert client.post("/api/me/password", headers=headers, json={}).status_code in (403, 422)


def test_revoked_grant_stops_access_tokens(client, user, session):
    code, verifier = get_code(client, user)
    access = exchange(client, code, verifier).json()["access_token"]
    client.cookies.clear()
    grant = session.exec(select(OAuthGrant)).one()
    grant.revoked_at = datetime.utcnow()
    session.add(grant)
    session.commit()
    response = client.get("/oauth/userinfo", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "This app has been disconnected"


def test_require_scope_works_on_any_route(client, user):
    @app.get("/_test/projects-write")
    def _route(current: User = Depends(require_scope("projects:write"))):
        return {"user": current.username}

    try:
        code, verifier = get_code(client, user, scope="profile")
        access = exchange(client, code, verifier).json()["access_token"]
        client.cookies.clear()
        assert client.get("/_test/projects-write", headers={"Authorization": f"Bearer {access}"}).status_code == 403
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/_test/projects-write"]


# --- Revoke and connected apps -------------------------------------------------------------------------------------

def test_revoke_with_refresh_token(client, user, session):
    code, verifier = get_code(client, user)
    tokens = exchange(client, code, verifier).json()
    response = client.post("/oauth/revoke", data={"token": tokens["refresh_token"], "client_id": "snakie"})
    assert response.status_code == 200
    assert session.exec(select(OAuthGrant)).one().revoked_at is not None
    assert refresh(client, tokens["refresh_token"]).json()["error"] == "invalid_grant"


def test_revoke_with_access_token_and_junk(client, user, session):
    code, verifier = get_code(client, user)
    tokens = exchange(client, code, verifier).json()
    assert client.post("/oauth/revoke", data={"token": "junk"}).status_code == 200
    assert client.post("/oauth/revoke", data={}).status_code == 200
    assert client.post("/oauth/revoke", data={"token": tokens["access_token"], "client_id": "other"}).status_code == 200
    assert session.exec(select(OAuthGrant)).one().revoked_at is None
    client.post("/oauth/revoke", data={"token": tokens["access_token"]})
    assert session.exec(select(OAuthGrant)).one().revoked_at is not None


def test_account_lists_and_disconnects_apps(client, user, session):
    sign_in(client, user)
    assert "No apps are connected" in client.get("/account").text
    code, verifier = get_code(client, user)
    tokens = exchange(client, code, verifier).json()
    page = client.get("/account")
    assert "Connected apps" in page.text
    assert "Snakie" in page.text
    assert "Add wiring diagrams and parts lists to your projects" in page.text
    response = client.post("/account/connected-apps/disconnect", data={"client_id": "snakie"})
    assert response.status_code == 303
    assert "No apps are connected" in client.get("/account").text
    assert refresh(client, tokens["refresh_token"]).json()["error"] == "invalid_grant"
