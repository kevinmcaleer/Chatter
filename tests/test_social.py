"""Batch like status, the public Liked list and its privacy switch."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

os.environ["TESTING"] = "true"

from app.database import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Comment, Like, User, UserPrivacy  # noqa: E402
from app.utils import create_access_token, hash_password  # noqa: E402

PASSWORD = "TestPass123"


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # Only the tables these endpoints touch: the full metadata has a broken
    # project_image foreign key that SQLite's create_all trips over.
    tables = [User.__table__, Like.__table__, UserPrivacy.__table__, Comment.__table__]
    SQLModel.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _user(session: Session, username: str) -> User:
    user = User(
        username=username, firstname=username.title(), lastname="Maker",
        email=f"{username}@example.com", hashed_password=hash_password(PASSWORD),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(client: TestClient, username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': username})}"}


def _like(session: Session, user: User, url: str) -> None:
    session.add(Like(url=url, user_id=user.id))
    session.commit()


@pytest.fixture(name="people")
def people_fixture(session: Session):
    alice, bob = _user(session, "alice"), _user(session, "bob")
    _like(session, alice, "projects/view.html?id=1")
    _like(session, bob, "projects/view.html?id=1")
    _like(session, bob, "projects/view.html?id=2")
    _like(session, bob, "blog/some-post.html")
    return alice, bob


URLS = ["projects/view.html?id=1", "/projects/view.html?id=2", "projects/view.html?id=3"]


def test_batch_counts_for_anonymous(client, people):
    r = client.post("/interact/like-status/batch", json={"urls": URLS})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items["projects/view.html?id=1"] == {"like_count": 2, "user_has_liked": False, "comment_count": 0}
    assert items["/projects/view.html?id=2"] == {"like_count": 1, "user_has_liked": False, "comment_count": 0}
    assert items["projects/view.html?id=3"] == {"like_count": 0, "user_has_liked": False, "comment_count": 0}


def test_batch_marks_my_likes(client, people):
    r = client.post("/interact/like-status/batch", json={"urls": URLS}, headers=_headers(client, "alice"))
    items = r.json()["items"]
    assert items["projects/view.html?id=1"]["user_has_liked"] is True
    assert items["/projects/view.html?id=2"]["user_has_liked"] is False


def test_batch_counts_visible_comments(client, session, people):
    alice, _ = people
    url = "projects/view.html?id=1"
    session.add(Comment(url=url, content="Nice build", user_id=alice.id))
    session.add(Comment(url=url, content="Spam", user_id=alice.id, is_hidden=True))
    session.add(Comment(url=url, content="Gone", user_id=alice.id, is_removed=True))
    session.commit()
    items = client.post("/interact/like-status/batch", json={"urls": [url]}).json()["items"]
    assert items[url]["comment_count"] == 1


def test_batch_limits(client):
    assert client.post("/interact/like-status/batch", json={"urls": []}).status_code == 422
    too_many = [f"projects/view.html?id={i}" for i in range(51)]
    assert client.post("/interact/like-status/batch", json={"urls": too_many}).status_code == 422


def test_likes_are_private_by_default(client, people):
    r = client.get("/interact/users/bob/liked")
    assert r.status_code == 403


def test_owner_can_always_see_their_likes(client, people):
    r = client.get("/interact/users/bob/liked?prefix=projects/", headers=_headers(client, "bob"))
    assert r.status_code == 200, r.text
    assert sorted(r.json()["urls"]) == ["projects/view.html?id=1", "projects/view.html?id=2"]


def test_public_likes_after_opting_in(client, people):
    bob = _headers(client, "bob")
    assert client.get("/interact/me/privacy", headers=bob).json() == {"likes_public": False}
    r = client.put("/interact/me/privacy", json={"likes_public": True}, headers=bob)
    assert r.status_code == 200 and r.json() == {"likes_public": True}

    r = client.get("/interact/users/bob/liked?prefix=/projects/")
    assert r.status_code == 200
    assert len(r.json()["urls"]) == 2

    client.put("/interact/me/privacy", json={"likes_public": False}, headers=bob)
    assert client.get("/interact/users/bob/liked").status_code == 403


def test_liked_unknown_user(client):
    assert client.get("/interact/users/nobody/liked").status_code == 404


def test_privacy_needs_sign_in(client):
    assert client.put("/interact/me/privacy", json={"likes_public": True}).status_code == 401
