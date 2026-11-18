"""Tables for "Sign in with kevsrobots" (#80): OAuth 2 clients, one-time codes, grants and refresh tokens.

Codes and refresh tokens are stored as SHA-256 hashes only, so a database leak gives nobody a usable token.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class OAuthClient(SQLModel, table=True):
    """An app that can ask for a token, such as Snakie. Seeded by Kev, not self-service."""

    __tablename__ = "oauth_clients"

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str = Field(index=True, unique=True, max_length=64)
    name: str
    # Space-separated. An http://127.0.0.1/… or http://[::1]/… entry also allows that path on any port (RFC 8252).
    redirect_uris: str
    scopes: str  # space-separated scopes the client may ask for
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthCode(SQLModel, table=True):
    """A one-time authorization code. Lives 60 seconds and works once."""

    __tablename__ = "oauth_codes"

    id: Optional[int] = Field(default=None, primary_key=True)
    code_hash: str = Field(index=True, unique=True, max_length=64)
    client_id: str = Field(max_length=64)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    scope: str
    code_challenge: str = Field(max_length=128)
    redirect_uri: str
    expires_at: datetime
    used: bool = Field(default=False)
    grant_id: Optional[int] = None  # the grant this code was exchanged for, so a replayed code can revoke it
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthGrant(SQLModel, table=True):
    """One app signed in to one account (one per device sign-in). Revoking it ends that app's access."""

    __tablename__ = "oauth_grants"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    client_id: str = Field(max_length=64, index=True)
    scope: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None


class OAuthRefreshToken(SQLModel, table=True):
    """A refresh token. Each works once: using it returns a new one. Using an old one again revokes the grant."""

    __tablename__ = "oauth_refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True, max_length=64)
    grant_id: int = Field(foreign_key="oauth_grants.id", ondelete="CASCADE", index=True)
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
