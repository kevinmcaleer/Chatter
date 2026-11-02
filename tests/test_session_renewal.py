"""Login lifetime and sliding renewal (logins used to die after 30 minutes)."""

import time
from datetime import timedelta

from jose import jwt

from app.models import User
from app.session_renewal import token_needs_renewal
from app.utils import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ACCESS_TOKEN_MAX_AGE_SECONDS,
    create_access_token,
    hash_password,
)
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app

TEST_PASSWORD = "TestPass123"


@pytest.fixture(name="session")
def session_fixture():
    # Only the users table: these tests don't need the rest of the schema.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine, tables=[User.__table__])
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_user(session, username="slider"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        firstname="S",
        lastname="L",
        hashed_password=hash_password(TEST_PASSWORD),
    )
    session.add(user)
    session.commit()
    return user


def _exp(token):
    return jwt.get_unverified_claims(token)["exp"]


def test_default_lifetime_is_seven_days():
    assert ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 7
    token = create_access_token({"sub": "x"})
    remaining = _exp(token) - time.time()
    assert remaining > 6.9 * 24 * 3600


def test_needs_renewal_only_past_half_life():
    now = time.time()
    life = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert not token_needs_renewal({"exp": now + life * 0.9}, now)
    assert token_needs_renewal({"exp": now + life * 0.4}, now)
    assert not token_needs_renewal({"exp": now - 10}, now)
    assert not token_needs_renewal({}, now)


def test_api_login_cookie_matches_lifetime(client, session):
    _make_user(session)
    r = client.post("/api/login", data={"username": "slider", "password": TEST_PASSWORD})
    assert r.status_code == 200
    cookies = r.headers.get_list("set-cookie")
    assert any(c.startswith("access_token=") and f"Max-Age={ACCESS_TOKEN_MAX_AGE_SECONDS}" in c for c in cookies)
    assert any(c.startswith("username=") and f"Max-Age={ACCESS_TOKEN_MAX_AGE_SECONDS}" in c for c in cookies)


def test_old_token_is_renewed_on_use(client, session):
    _make_user(session)
    old = create_access_token({"sub": "slider"}, expires_delta=timedelta(hours=1))
    client.cookies.set("access_token", f"Bearer {old}")
    r = client.get("/api/me")
    assert r.status_code == 200
    renewed = [c for c in r.headers.get_list("set-cookie") if c.startswith("access_token=")]
    assert renewed, "expected a fresh access_token cookie"
    new_token = renewed[0].split("=", 1)[1].split(";", 1)[0].strip('"').replace("Bearer ", "").replace("Bearer\\040", "")
    assert _exp(new_token) > _exp(old) + 24 * 3600


def test_fresh_token_is_not_renewed(client, session):
    _make_user(session)
    token = create_access_token({"sub": "slider"})
    client.cookies.set("access_token", f"Bearer {token}")
    r = client.get("/api/me")
    assert r.status_code == 200
    assert not any(c.startswith("access_token=") for c in r.headers.get_list("set-cookie"))


def test_expired_token_is_not_renewed(client, session):
    _make_user(session)
    expired = create_access_token({"sub": "slider"}, expires_delta=timedelta(seconds=-5))
    client.cookies.set("access_token", f"Bearer {expired}")
    r = client.get("/api/me")
    assert r.status_code == 401
    assert not any(c.startswith("access_token=") for c in r.headers.get_list("set-cookie"))


def test_logout_is_not_undone_by_renewal(client, session):
    _make_user(session)
    old = create_access_token({"sub": "slider"}, expires_delta=timedelta(hours=1))
    client.cookies.set("access_token", f"Bearer {old}")
    r = client.get("/logout?redirect=false")
    cookies = [c for c in r.headers.get_list("set-cookie") if c.startswith("access_token=")]
    assert len(cookies) == 1
    assert "Max-Age=0" in cookies[0] or "expires=" in cookies[0].lower()
