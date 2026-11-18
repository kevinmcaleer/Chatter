"""Sign in with kevsrobots (#80): OAuth 2 authorization code flow with PKCE (RFC 6749, RFC 7636, RFC 8252).

Apps outside .kevsrobots.com, like Snakie on app.snakie.org and the Snakie desktop app, can't use the shared
access_token cookie. They send people to /oauth/authorize, get a one-time code back on their redirect URI,
and swap it at /oauth/token for:

- an access token: a normal Chatter JWT plus client_id, scope and gid (grant id) claims, valid for 1 hour;
- a refresh token: random, stored hashed, valid for 90 days and rotated on every use.

App tokens only work on routes that ask for a scope with require_scope(). Everything else (get_current_user,
get_optional_user) turns them away, so an app can never change a password or delete an account.
Cookie sign-ins keep full access everywhere, as before.
"""

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Cookie, Depends, Form, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session, select

from .auth import get_current_user, get_optional_user, get_template_context, is_session_token, templates
from .database import get_session
from .models import User
from .oauth_models import OAuthClient, OAuthCode, OAuthGrant, OAuthRefreshToken
from .profile import get_profile_picture_url
from .suite import CLIENT_APPS, redirect_to_accounts
from .utils import create_access_token, decode_access_token

router = APIRouter()

ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
REFRESH_TOKEN_LIFETIME = timedelta(days=90)
CODE_LIFETIME = timedelta(seconds=60)
CONSENT_LIFETIME = timedelta(minutes=10)

# What each scope lets an app do, in the words the consent page uses. No scope touches code: code stays on GitHub.
SCOPES = {
    "profile": "See your name and profile picture",
    "projects:read": "See your kevsrobots projects, so you can pick one",
    "projects:write": "Add wiring diagrams and parts lists to your projects",
}

# Seeded at startup if missing. Kev adds or changes clients here (or in the oauth_clients table).
DEFAULT_CLIENTS = [
    {
        "client_id": "snakie",
        "name": "Snakie",
        "redirect_uris": "https://app.snakie.org/auth/callback http://127.0.0.1/callback",
        "scopes": "profile projects:read projects:write",
    },
]

LOOPBACK_HOSTS = {"127.0.0.1", "::1"}
PKCE_VALUE = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")  # RFC 7636 section 4.1: unreserved characters, 43 to 128 long


def seed_clients(session: Session) -> None:
    """Add any DEFAULT_CLIENTS that aren't in the table yet. Existing rows are left alone."""
    for client in DEFAULT_CLIENTS:
        if not session.exec(select(OAuthClient).where(OAuthClient.client_id == client["client_id"])).first():
            session.add(OAuthClient(**client))
    session.commit()


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def pkce_s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def parse_scope(scope: Optional[str]) -> list:
    """Scopes in a stable order, without duplicates."""
    seen = []
    for item in (scope or "").split():
        if item not in seen:
            seen.append(item)
    return seen


def get_client(session: Session, client_id: Optional[str]) -> Optional[OAuthClient]:
    if not client_id:
        return None
    return session.exec(select(OAuthClient).where(OAuthClient.client_id == client_id)).first()


def redirect_uri_allowed(client: OAuthClient, uri: Optional[str]) -> bool:
    """Exact match against the client's list, except that a loopback entry allows any port (RFC 8252 section 7.3)."""
    if not uri or "#" in uri:
        return False
    try:
        wanted = urlsplit(uri)
        wanted.port  # raises ValueError for a bad port
    except ValueError:
        return False
    for registered in client.redirect_uris.split():
        if uri == registered:
            return True
        allowed = urlsplit(registered)
        if (
            allowed.scheme == "http"
            and allowed.hostname in LOOPBACK_HOSTS
            and wanted.scheme == "http"
            and wanted.hostname == allowed.hostname
            and wanted.path == allowed.path
            and not wanted.username
            and not wanted.password
            and not wanted.query
        ):
            return True
    return False


def with_params(uri: str, **params) -> str:
    """The redirect URI with extra query parameters, keeping any it already has."""
    parts = urlsplit(uri)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query += [(key, value) for key, value in params.items() if value is not None]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def token_error(error: str, description: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        {"error": error, "error_description": description},
        status_code=status_code,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


def active_grant_covering(session: Session, user: User, client_id: str, scopes: list) -> Optional[OAuthGrant]:
    """A grant the person already gave this app that covers these scopes, so they don't have to agree again."""
    grants = session.exec(
        select(OAuthGrant).where(
            OAuthGrant.user_id == user.id, OAuthGrant.client_id == client_id, OAuthGrant.revoked_at == None  # noqa: E711
        )
    ).all()
    for grant in grants:
        if set(scopes) <= set(grant.scope.split()):
            return grant
    return None


def issue_code(session: Session, client: OAuthClient, user: User, scopes: list, code_challenge: str,
               redirect_uri: str, state: Optional[str]) -> RedirectResponse:
    code = secrets.token_urlsafe(32)
    session.add(OAuthCode(
        code_hash=hash_secret(code),
        client_id=client.client_id,
        user_id=user.id,
        scope=" ".join(scopes),
        code_challenge=code_challenge,
        redirect_uri=redirect_uri,
        expires_at=datetime.utcnow() + CODE_LIFETIME,
    ))
    session.commit()
    return RedirectResponse(with_params(redirect_uri, code=code, state=state), status_code=303)


def issue_tokens(session: Session, grant: OAuthGrant, user: User) -> JSONResponse:
    now = datetime.utcnow()
    access_token = create_access_token(
        {"sub": user.username, "client_id": grant.client_id, "scope": grant.scope, "gid": grant.id},
        expires_delta=ACCESS_TOKEN_LIFETIME,
    )
    refresh_token = secrets.token_urlsafe(48)
    session.add(OAuthRefreshToken(token_hash=hash_secret(refresh_token), grant_id=grant.id,
                                  expires_at=now + REFRESH_TOKEN_LIFETIME))
    grant.last_used_at = now
    session.add(grant)
    session.commit()
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": int(ACCESS_TOKEN_LIFETIME.total_seconds()),
            "refresh_token": refresh_token,
            "scope": grant.scope,
        },
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


def revoke_grant(session: Session, grant: Optional[OAuthGrant]) -> None:
    if grant and not grant.revoked_at:
        grant.revoked_at = datetime.utcnow()
        session.add(grant)
        session.commit()


def require_scope(scope: str):
    """A dependency for routes apps may call. Cookie or session-token sign-ins pass as before (full access);
    an app token passes only if it carries this scope and its grant hasn't been revoked."""

    def dependency(
        token_cookie: Optional[str] = Cookie(default=None, alias="access_token"),
        token_header: Optional[str] = Header(default=None, alias="Authorization"),
        session: Session = Depends(get_session),
    ) -> User:
        token = None
        if token_header and token_header.startswith("Bearer "):
            token = token_header[7:]
        elif token_cookie and token_cookie.startswith("Bearer "):
            token = token_cookie[7:]
        payload = decode_access_token(token) if token else None
        if not payload or not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid or expired token",
                                headers={"WWW-Authenticate": "Bearer"})
        if "client_id" in payload:
            if scope not in str(payload.get("scope", "")).split():
                raise HTTPException(status_code=403, detail=f"This app wasn't given the {scope} scope",
                                    headers={"WWW-Authenticate": f'Bearer error="insufficient_scope", scope="{scope}"'})
            grant = session.get(OAuthGrant, payload.get("gid"))
            if not grant or grant.revoked_at or grant.client_id != payload["client_id"]:
                raise HTTPException(status_code=401, detail="This app has been disconnected",
                                    headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
        elif not is_session_token(payload):
            raise HTTPException(status_code=401, detail="Invalid or expired token",
                                headers={"WWW-Authenticate": "Bearer"})
        user = session.exec(select(User).where(User.username == payload["sub"])).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found", headers={"WWW-Authenticate": "Bearer"})
        return user

    return dependency


def error_page(request: Request, message: str):
    context = get_template_context(request, message=message)
    return templates.TemplateResponse("oauth_error.html", context, status_code=400)


@router.get("/oauth/authorize")
def authorize(
    request: Request,
    response_type: Optional[str] = None,
    client_id: Optional[str] = None,
    redirect_uri: Optional[str] = None,
    scope: Optional[str] = None,
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    moved = redirect_to_accounts(request)
    if moved:
        return moved

    # Until the client and redirect URI check out, never redirect anywhere: show the error here.
    client = get_client(session, client_id)
    if not client:
        return error_page(request, "This app isn't registered with kevsrobots, so it can't sign you in.")
    if not redirect_uri_allowed(client, redirect_uri):
        return error_page(request, f"{client.name} asked to send you somewhere it isn't allowed to.")

    def fail(error: str, description: str) -> RedirectResponse:
        return RedirectResponse(
            with_params(redirect_uri, error=error, error_description=description, state=state), status_code=303
        )

    if response_type != "code":
        return fail("unsupported_response_type", "response_type must be code")
    if code_challenge_method != "S256" or not code_challenge or not PKCE_VALUE.match(code_challenge):
        return fail("invalid_request", "PKCE is required: send code_challenge with code_challenge_method=S256")
    scopes = parse_scope(scope)
    if not scopes or not set(scopes) <= set(client.scopes.split()) or not set(scopes) <= set(SCOPES):
        return fail("invalid_scope", f"Ask for one or more of: {client.scopes}")

    if not user:
        return RedirectResponse("/login?" + urlencode({"return_to": f"{request.url.path}?{request.url.query}"}),
                                status_code=303)

    if active_grant_covering(session, user, client.client_id, scopes):
        return issue_code(session, client, user, scopes, code_challenge, redirect_uri, state)

    consent = create_access_token(
        {
            "purpose": "oauth_consent",
            "uid": user.id,
            "client_id": client.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
        },
        expires_delta=CONSENT_LIFETIME,
    )
    context = get_template_context(
        request,
        client=client,
        user=user,
        scopes=[(item, SCOPES[item]) for item in scopes],
        consent=consent,
        continue_app=CLIENT_APPS.get(client.client_id),
        switch_account="/logout?" + urlencode({"return_to": f"{request.url.path}?{request.url.query}"}),
    )
    return templates.TemplateResponse("oauth_consent.html", context)


@router.post("/oauth/authorize")
def authorize_decision(
    request: Request,
    consent: str = Form(...),
    decision: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    payload = decode_access_token(consent)
    if not payload or payload.get("purpose") != "oauth_consent" or payload.get("uid") != user.id:
        return error_page(request, "That sign-in request has expired. Go back to the app and try again.")
    client = get_client(session, payload.get("client_id"))
    redirect_uri = payload.get("redirect_uri")
    if not client or not redirect_uri_allowed(client, redirect_uri):
        return error_page(request, "This app can no longer sign you in.")
    state = payload.get("state")
    if decision != "allow":
        return RedirectResponse(
            with_params(redirect_uri, error="access_denied", error_description="You cancelled sign-in", state=state),
            status_code=303,
        )
    return issue_code(session, client, user, parse_scope(payload.get("scope")), payload["code_challenge"],
                      redirect_uri, state)


@router.post("/oauth/token")
def token(
    grant_type: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    client = get_client(session, client_id)
    if not client:
        return token_error("invalid_client", "Unknown client_id", status_code=401)

    if grant_type == "authorization_code":
        if not code or not code_verifier or not redirect_uri:
            return token_error("invalid_request", "code, code_verifier and redirect_uri are required")
        row = session.exec(select(OAuthCode).where(OAuthCode.code_hash == hash_secret(code))).first()
        if not row or row.client_id != client.client_id:
            return token_error("invalid_grant", "The code isn't valid")
        if row.used:
            # A code used twice may have been stolen: end whatever the first use started (RFC 6749 section 4.1.2).
            revoke_grant(session, session.get(OAuthGrant, row.grant_id) if row.grant_id else None)
            return token_error("invalid_grant", "The code has already been used")
        row.used = True
        session.add(row)
        session.commit()
        if row.expires_at < datetime.utcnow():
            return token_error("invalid_grant", "The code has expired")
        if redirect_uri != row.redirect_uri:
            return token_error("invalid_grant", "redirect_uri doesn't match the one used to get the code")
        if not PKCE_VALUE.match(code_verifier) or not hmac.compare_digest(pkce_s256(code_verifier), row.code_challenge):
            return token_error("invalid_grant", "code_verifier doesn't match the code_challenge")
        user = session.get(User, row.user_id)
        if not user:
            return token_error("invalid_grant", "The account no longer exists")
        grant = OAuthGrant(user_id=user.id, client_id=client.client_id, scope=row.scope)
        session.add(grant)
        session.commit()
        session.refresh(grant)
        row.grant_id = grant.id
        session.add(row)
        session.commit()
        return issue_tokens(session, grant, user)

    if grant_type == "refresh_token":
        if not refresh_token:
            return token_error("invalid_request", "refresh_token is required")
        row = session.exec(
            select(OAuthRefreshToken).where(OAuthRefreshToken.token_hash == hash_secret(refresh_token))
        ).first()
        grant = session.get(OAuthGrant, row.grant_id) if row else None
        if not row or not grant or grant.client_id != client.client_id:
            return token_error("invalid_grant", "The refresh token isn't valid")
        if grant.revoked_at:
            return token_error("invalid_grant", "This app has been disconnected")
        if row.used_at:
            # Each refresh token works once. Seeing one again means it was copied: disconnect the app.
            revoke_grant(session, grant)
            return token_error("invalid_grant", "The refresh token has already been used")
        if row.expires_at < datetime.utcnow():
            return token_error("invalid_grant", "The refresh token has expired")
        row.used_at = datetime.utcnow()
        session.add(row)
        session.commit()
        user = session.get(User, grant.user_id)
        if not user:
            return token_error("invalid_grant", "The account no longer exists")
        return issue_tokens(session, grant, user)

    return token_error("unsupported_grant_type", "grant_type must be authorization_code or refresh_token")


@router.post("/oauth/revoke")
def revoke(
    token: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    """Sign an app out (RFC 7009). Takes a refresh or access token; always answers 200 so tokens can't be probed."""
    grant = None
    if token:
        row = session.exec(select(OAuthRefreshToken).where(OAuthRefreshToken.token_hash == hash_secret(token))).first()
        if row:
            grant = session.get(OAuthGrant, row.grant_id)
        else:
            payload = decode_access_token(token)
            if payload and payload.get("gid"):
                grant = session.get(OAuthGrant, payload["gid"])
    if grant and (not client_id or grant.client_id == client_id):
        revoke_grant(session, grant)
    return JSONResponse({}, headers={"Cache-Control": "no-store"})


@router.get("/oauth/userinfo")
def userinfo(request: Request, user: User = Depends(require_scope("profile"))):
    """Name and picture for the suite bar in an app."""
    picture = get_profile_picture_url(user.profile_picture)
    return {
        "username": user.username,
        "name": f"{user.firstname} {user.lastname}".strip(),
        "picture": str(request.base_url).rstrip("/") + picture if picture else None,
        "profile_url": f"https://www.kevsrobots.com/profile/{user.username}",
    }


def connected_apps(session: Session, user: User) -> list:
    """The apps signed in to this account, one row per app, for the account page."""
    grants = session.exec(
        select(OAuthGrant).where(OAuthGrant.user_id == user.id, OAuthGrant.revoked_at == None)  # noqa: E711
    ).all()
    apps = {}
    for grant in grants:
        entry = apps.setdefault(grant.client_id, {"client_id": grant.client_id, "scopes": [], "last_used_at": None})
        for item in grant.scope.split():
            if item not in entry["scopes"]:
                entry["scopes"].append(item)
        if not entry["last_used_at"] or grant.last_used_at > entry["last_used_at"]:
            entry["last_used_at"] = grant.last_used_at
    for entry in apps.values():
        client = get_client(session, entry["client_id"])
        entry["name"] = client.name if client else entry["client_id"]
        entry["permissions"] = [SCOPES.get(item, item) for item in entry["scopes"]]
    return sorted(apps.values(), key=lambda entry: entry["name"].lower())


@router.post("/account/connected-apps/disconnect")
def disconnect_app(
    client_id: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    grants = session.exec(
        select(OAuthGrant).where(
            OAuthGrant.user_id == user.id, OAuthGrant.client_id == client_id, OAuthGrant.revoked_at == None  # noqa: E711
        )
    ).all()
    for grant in grants:
        grant.revoked_at = datetime.utcnow()
        session.add(grant)
    session.commit()
    return RedirectResponse("/account#connected-apps", status_code=303)
