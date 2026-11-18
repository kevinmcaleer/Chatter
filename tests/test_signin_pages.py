"""The shared kevsrobots sign-in pages (#81): suite look, "Continue to" chip, accounts.kevsrobots.com, reset form."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import User
from app.suite import app_for_return_to
from app.utils import hash_password, verify_password


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Only the users table: the full metadata fails on main today (projects.primary_image_id → project_image).
    SQLModel.metadata.create_all(engine, tables=[User.__table__])
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, monkeypatch):
    monkeypatch.delenv("ACCOUNTS_URL", raising=False)
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(session, **extra):
    user = User(username="maker", firstname="Ada", lastname="Maker", email="ada@example.com",
                hashed_password=hash_password("OldPass123"), status="active", type=0, **extra)
    session.add(user)
    session.commit()
    return user


@pytest.mark.parametrize("return_to, name", [
    ("https://bettercad.kevsrobots.com/#/library", "BetterCAD"),
    ("https://www.kevsrobots.com/learn/micropython/", "kevsrobots.com"),
    ("https://www.kevsrobots.com/projects/42", "Projects"),
    ("https://projects.kevsrobots.com/", "Projects"),
    ("https://app.snakie.org/", "Snakie"),
])
def test_app_for_return_to_names_the_app(return_to, name):
    assert app_for_return_to(return_to)["name"] == name


@pytest.mark.parametrize("return_to", [None, "", "/account", "https://chatter.kevsrobots.com/account"])
def test_app_for_return_to_is_none_for_chatter_itself(return_to):
    assert app_for_return_to(return_to) is None


def test_login_page_says_which_app_sent_you(client):
    page = client.get("/login", params={"return_to": "https://bettercad.kevsrobots.com/#/library"}).text
    assert "Continue to BetterCAD" in page
    assert "kr-violet" in page
    assert 'name="return_to" value="https://bettercad.kevsrobots.com/#/library"' in page
    # Create an account keeps the way back.
    assert "/register?return_to=https%3A%2F%2Fbettercad.kevsrobots.com%2F%23%2Flibrary" in page


def test_login_page_without_return_to_has_no_chip(client):
    page = client.get("/login").text
    assert "Continue to" not in page
    assert "Sign in" in page


def test_register_page_links_back_to_sign_in_with_return_to(client):
    page = client.get("/register", params={"return_to": "https://www.kevsrobots.com/learn/"}).text
    assert "Continue to kevsrobots.com" in page
    assert "/login?return_to=https%3A%2F%2Fwww.kevsrobots.com%2Flearn%2F" in page


def test_pages_move_to_accounts_url_when_set(client, monkeypatch):
    monkeypatch.setenv("ACCOUNTS_URL", "https://accounts.kevsrobots.com/")
    for path in ["/login?return_to=%2Faccount", "/register", "/reset-password"]:
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 302, path
        assert r.headers["location"] == "https://accounts.kevsrobots.com" + path


def test_pages_stay_put_on_the_accounts_host(monkeypatch, session):
    monkeypatch.setenv("ACCOUNTS_URL", "https://accounts.kevsrobots.com")
    app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(app, base_url="https://accounts.kevsrobots.com")
        assert client.get("/login", follow_redirects=False).status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_pages_stay_put_while_accounts_url_is_unset(client):
    assert client.get("/login", follow_redirects=False).status_code == 200


def test_reset_password_page_renders(client):
    page = client.get("/reset-password", params={"username": "maker"}).text
    assert "Reset your password" in page
    assert 'value="maker"' in page


def test_reset_password_form_sets_new_password(client, session):
    user = make_user(session, password_reset_code="ABCD1234", code_expires_at=datetime.utcnow() + timedelta(hours=1))
    r = client.post("/reset-password", data={"username": "maker", "reset_code": "abcd1234",
                                             "new_password": "NewPass456", "confirm_password": "NewPass456"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login?reset=done"
    session.refresh(user)
    assert verify_password("NewPass456", user.hashed_password)
    assert user.password_reset_code is None
    assert "Your password has been changed" in client.get("/login?reset=done").text


def test_reset_password_form_refuses_mismatched_passwords(client, session):
    make_user(session, password_reset_code="ABCD1234", code_expires_at=datetime.utcnow() + timedelta(hours=1))
    page = client.post("/reset-password", data={"username": "maker", "reset_code": "ABCD1234",
                                                "new_password": "NewPass456", "confirm_password": "Other456"}).text
    assert "Passwords do not match" in page


@pytest.mark.parametrize("code, expires, problem", [
    ("WRONG123", timedelta(hours=1), "Invalid reset code"),
    ("ABCD1234", timedelta(hours=-1), "Reset code has expired"),
])
def test_reset_password_form_shows_why_a_code_fails(client, session, code, expires, problem):
    make_user(session, password_reset_code="ABCD1234", code_expires_at=datetime.utcnow() + expires)
    page = client.post("/reset-password", data={"username": "maker", "reset_code": code,
                                                "new_password": "NewPass456", "confirm_password": "NewPass456"}).text
    assert problem in page


def test_reset_password_api_still_works(client, session):
    make_user(session, password_reset_code="ABCD1234", code_expires_at=datetime.utcnow() + timedelta(hours=1))
    r = client.post("/api/reset-password", json={"username": "maker", "reset_code": "ABCD1234", "new_password": "NewPass456"})
    assert r.status_code == 200
    r = client.post("/api/reset-password", json={"username": "nobody", "reset_code": "X", "new_password": "NewPass456"})
    assert r.status_code == 400


def test_force_password_reset_page_uses_suite_look(client, session):
    make_user(session, force_password_reset=True)
    r = client.post("/login", data={"username": "maker", "password": "OldPass123"}, follow_redirects=False)
    assert r.headers["location"] == "/force-password-reset"
    page = client.get("/force-password-reset").text
    assert "Choose a new password" in page
    assert "kr-card" in page
