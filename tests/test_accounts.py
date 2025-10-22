import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from datetime import datetime
from app.main import app
from app.database import get_session
from app.models import User, AccountLog
from app.utils import hash_password


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh database session for each test"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with overridden database session"""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="regular_user")
def regular_user_fixture(session: Session):
    """Create a regular test user"""
    user = User(
        username="testuser",
        firstname="Test",
        lastname="User",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        status="active",
        type=0
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """Create an admin test user"""
    admin = User(
        username="admin",
        firstname="Admin",
        lastname="User",
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        status="active",
        type=1
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, regular_user: User):
    """Get authentication headers for regular user"""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="admin_headers")
def admin_headers_fixture(client: TestClient, admin_user: User):
    """Get authentication headers for admin user"""
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRegistration:
    """Tests for user registration endpoint"""

    def test_register_success(self, client: TestClient, session: Session):
        """Test successful user registration"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "newuser",
                "firstname": "New",
                "lastname": "User",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["firstname"] == "New"
        assert data["lastname"] == "User"
        assert data["email"] == "newuser@example.com"
        assert data["status"] == "active"
        assert data["type"] == 0
        assert "id" in data
        assert "hashed_password" not in data

        # Verify account log was created
        log = session.query(AccountLog).filter(AccountLog.action == "created").first()
        assert log is not None
        assert log.user_id == data["id"]

    def test_register_with_date_of_birth(self, client: TestClient):
        """Test registration with optional date of birth"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "userwithdob",
                "firstname": "User",
                "lastname": "WithDOB",
                "date_of_birth": "1990-01-01T00:00:00",
                "email": "withdob@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["date_of_birth"] is not None

    def test_register_duplicate_username(self, client: TestClient, regular_user: User):
        """Test registration with existing username fails"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "testuser",
                "firstname": "Another",
                "lastname": "User",
                "email": "another@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client: TestClient, regular_user: User):
        """Test registration with existing email fails"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "anotheruser",
                "firstname": "Another",
                "lastname": "User",
                "email": "test@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email format fails"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "newuser",
                "firstname": "New",
                "lastname": "User",
                "email": "not-an-email",
                "password": "password123"
            }
        )

        assert response.status_code == 422


class TestGetCurrentAccount:
    """Tests for getting current account information"""

    def test_get_account_success(self, client: TestClient, auth_headers: dict, regular_user: User):
        """Test getting current account information"""
        response = client.get("/accounts/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_account_unauthorized(self, client: TestClient):
        """Test getting account without authentication fails"""
        response = client.get("/accounts/me")

        assert response.status_code == 401


class TestUpdateAccount:
    """Tests for updating account information"""

    def test_update_firstname(self, client: TestClient, auth_headers: dict, session: Session, regular_user: User):
        """Test updating firstname"""
        response = client.patch(
            "/accounts/me",
            headers=auth_headers,
            json={"firstname": "UpdatedFirst"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["firstname"] == "UpdatedFirst"

        # Verify account log
        log = session.query(AccountLog).filter(
            AccountLog.field_changed == "firstname"
        ).first()
        assert log is not None
        assert log.old_value == "Test"
        assert log.new_value == "UpdatedFirst"

    def test_update_lastname(self, client: TestClient, auth_headers: dict, session: Session):
        """Test updating lastname"""
        response = client.patch(
            "/accounts/me",
            headers=auth_headers,
            json={"lastname": "UpdatedLast"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["lastname"] == "UpdatedLast"

    def test_update_email(self, client: TestClient, auth_headers: dict, session: Session):
        """Test updating email"""
        response = client.patch(
            "/accounts/me",
            headers=auth_headers,
            json={"email": "newemail@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

    def test_update_email_duplicate(self, client: TestClient, auth_headers: dict, session: Session):
        """Test updating to existing email fails"""
        # Create another user
        other_user = User(
            username="otheruser",
            firstname="Other",
            lastname="User",
            email="other@example.com",
            hashed_password=hash_password("password"),
            status="active"
        )
        session.add(other_user)
        session.commit()

        response = client.patch(
            "/accounts/me",
            headers=auth_headers,
            json={"email": "other@example.com"}
        )

        assert response.status_code == 400
        assert "Email already in use" in response.json()["detail"]

    def test_update_date_of_birth(self, client: TestClient, auth_headers: dict):
        """Test updating date of birth"""
        response = client.patch(
            "/accounts/me",
            headers=auth_headers,
            json={"date_of_birth": "1990-01-01T00:00:00"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date_of_birth"] is not None

    def test_update_multiple_fields(self, client: TestClient, auth_headers: dict, session: Session):
        """Test updating multiple fields at once"""
        response = client.patch(
            "/accounts/me",
            headers=auth_headers,
            json={
                "firstname": "Multi",
                "lastname": "Update",
                "email": "multi@example.com"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["firstname"] == "Multi"
        assert data["lastname"] == "Update"
        assert data["email"] == "multi@example.com"

        # Verify multiple logs created
        logs = session.query(AccountLog).filter(AccountLog.action == "updated").all()
        assert len(logs) >= 3


class TestPasswordReset:
    """Tests for password reset endpoint"""

    def test_reset_password_success(self, client: TestClient, auth_headers: dict, session: Session, regular_user: User):
        """Test successful password reset"""
        response = client.post(
            "/accounts/reset-password",
            headers=auth_headers,
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            }
        )

        assert response.status_code == 200
        assert "Password reset successfully" in response.json()["message"]

        # Verify account log with redacted password
        log = session.query(AccountLog).filter(
            AccountLog.field_changed == "password"
        ).first()
        assert log is not None
        assert log.old_value == "[REDACTED]"
        assert log.new_value == "[REDACTED]"

    def test_reset_password_wrong_old_password(self, client: TestClient, auth_headers: dict):
        """Test password reset with incorrect old password fails"""
        response = client.post(
            "/accounts/reset-password",
            headers=auth_headers,
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword123"
            }
        )

        assert response.status_code == 400
        assert "Incorrect password" in response.json()["detail"]


class TestDeleteAccount:
    """Tests for account deletion endpoint"""

    def test_delete_account_success(self, client: TestClient, auth_headers: dict, session: Session, regular_user: User):
        """Test successful account deletion"""
        user_id = regular_user.id

        response = client.delete("/accounts/me", headers=auth_headers)

        assert response.status_code == 200
        assert "Account deleted successfully" in response.json()["message"]

        # Verify user is deleted
        user = session.get(User, user_id)
        assert user is None


class TestAdminUpdateStatus:
    """Tests for admin account status updates"""

    def test_admin_activate_account(self, client: TestClient, admin_headers: dict, session: Session):
        """Test admin activating an account"""
        # Create inactive user
        user = User(
            username="inactive",
            firstname="Inactive",
            lastname="User",
            email="inactive@example.com",
            hashed_password=hash_password("password"),
            status="inactive"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        response = client.patch(
            f"/accounts/admin/{user.id}/status",
            headers=admin_headers,
            json={"status": "active"}
        )

        assert response.status_code == 200
        assert "activated successfully" in response.json()["message"]

        # Verify status changed
        session.refresh(user)
        assert user.status == "active"

        # Verify log
        log = session.query(AccountLog).filter(
            AccountLog.action == "activated"
        ).first()
        assert log is not None

    def test_admin_deactivate_account(self, client: TestClient, admin_headers: dict, regular_user: User, session: Session):
        """Test admin deactivating an account"""
        response = client.patch(
            f"/accounts/admin/{regular_user.id}/status",
            headers=admin_headers,
            json={"status": "inactive"}
        )

        assert response.status_code == 200
        assert "deactivated successfully" in response.json()["message"]

        # Verify status changed
        session.refresh(regular_user)
        assert regular_user.status == "inactive"

    def test_admin_update_status_invalid_value(self, client: TestClient, admin_headers: dict, regular_user: User):
        """Test admin updating status with invalid value fails"""
        response = client.patch(
            f"/accounts/admin/{regular_user.id}/status",
            headers=admin_headers,
            json={"status": "invalid"}
        )

        assert response.status_code == 400
        assert "must be 'active' or 'inactive'" in response.json()["detail"]

    def test_admin_update_status_non_admin(self, client: TestClient, auth_headers: dict, session: Session):
        """Test non-admin cannot update account status"""
        user = User(
            username="target",
            firstname="Target",
            lastname="User",
            email="target@example.com",
            hashed_password=hash_password("password"),
            status="active"
        )
        session.add(user)
        session.commit()

        response = client.patch(
            f"/accounts/admin/{user.id}/status",
            headers=auth_headers,
            json={"status": "inactive"}
        )

        assert response.status_code == 403

    def test_admin_update_status_user_not_found(self, client: TestClient, admin_headers: dict):
        """Test admin updating status for non-existent user fails"""
        response = client.patch(
            "/accounts/admin/99999/status",
            headers=admin_headers,
            json={"status": "inactive"}
        )

        assert response.status_code == 404


class TestAdminPasswordReset:
    """Tests for admin password reset"""

    def test_admin_reset_password_success(self, client: TestClient, admin_headers: dict, regular_user: User, session: Session):
        """Test admin resetting user password"""
        response = client.post(
            f"/accounts/admin/{regular_user.id}/reset-password",
            headers=admin_headers,
            json={"new_password": "newadminpassword"}
        )

        assert response.status_code == 200
        assert "Password reset successfully" in response.json()["message"]

        # Verify log
        log = session.query(AccountLog).filter(
            AccountLog.field_changed == "password",
            AccountLog.user_id == regular_user.id
        ).first()
        assert log is not None
        assert log.changed_by != regular_user.id  # Changed by admin

    def test_admin_reset_password_non_admin(self, client: TestClient, auth_headers: dict, session: Session):
        """Test non-admin cannot reset passwords"""
        user = User(
            username="target",
            firstname="Target",
            lastname="User",
            email="target@example.com",
            hashed_password=hash_password("password"),
            status="active"
        )
        session.add(user)
        session.commit()

        response = client.post(
            f"/accounts/admin/{user.id}/reset-password",
            headers=auth_headers,
            json={"new_password": "newpassword"}
        )

        assert response.status_code == 403

    def test_admin_reset_password_user_not_found(self, client: TestClient, admin_headers: dict):
        """Test admin resetting password for non-existent user fails"""
        response = client.post(
            "/accounts/admin/99999/reset-password",
            headers=admin_headers,
            json={"new_password": "newpassword"}
        )

        assert response.status_code == 404


class TestAdminDeleteAccount:
    """Tests for admin account deletion"""

    def test_admin_delete_account_success(self, client: TestClient, admin_headers: dict, session: Session):
        """Test admin deleting user account"""
        # Create a fresh user just for this test
        test_user = User(
            username="tobedeleted",
            firstname="Delete",
            lastname="Me",
            email="delete@example.com",
            hashed_password=hash_password("password"),
            status="active"
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        user_id = test_user.id

        response = client.delete(
            f"/accounts/admin/{user_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify user is deleted
        user = session.get(User, user_id)
        assert user is None

    def test_admin_delete_own_account_fails(self, client: TestClient, admin_headers: dict, admin_user: User):
        """Test admin cannot delete own account via admin endpoint"""
        response = client.delete(
            f"/accounts/admin/{admin_user.id}",
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]

    def test_admin_delete_account_non_admin(self, client: TestClient, auth_headers: dict, session: Session):
        """Test non-admin cannot delete accounts"""
        user = User(
            username="target",
            firstname="Target",
            lastname="User",
            email="target@example.com",
            hashed_password=hash_password("password"),
            status="active"
        )
        session.add(user)
        session.commit()

        response = client.delete(
            f"/accounts/admin/{user.id}",
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_admin_delete_account_user_not_found(self, client: TestClient, admin_headers: dict):
        """Test admin deleting non-existent user fails"""
        response = client.delete(
            "/accounts/admin/99999",
            headers=admin_headers
        )

        assert response.status_code == 404


class TestAccountLogging:
    """Tests for account logging functionality"""

    def test_log_includes_ip_address(self, client: TestClient, session: Session):
        """Test that account logs capture IP address"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "iptest",
                "firstname": "IP",
                "lastname": "Test",
                "email": "iptest@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 201
        user_id = response.json()["id"]

        log = session.query(AccountLog).filter(AccountLog.user_id == user_id).first()
        assert log is not None
        assert log.ip_address is not None

    def test_log_includes_user_agent(self, client: TestClient, session: Session):
        """Test that account logs capture user agent"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "uatest",
                "firstname": "UA",
                "lastname": "Test",
                "email": "uatest@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 201
        user_id = response.json()["id"]

        log = session.query(AccountLog).filter(AccountLog.user_id == user_id).first()
        assert log is not None
        assert log.user_agent is not None


class TestLastLoginTracking:
    """Tests for last_login timestamp tracking (issue #30)"""

    def test_last_login_updated_on_login(self, client: TestClient, regular_user: User, session: Session):
        """Test that last_login is updated when user logs in"""
        # Verify initial last_login is None
        assert regular_user.last_login is None

        # Login
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password123"}
        )

        assert response.status_code == 200

        # Refresh user and check last_login was set
        session.refresh(regular_user)
        assert regular_user.last_login is not None
        assert isinstance(regular_user.last_login, datetime)

    def test_last_login_updates_on_subsequent_logins(self, client: TestClient, regular_user: User, session: Session):
        """Test that last_login updates on each login"""
        # First login
        response1 = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password123"}
        )
        assert response1.status_code == 200

        session.refresh(regular_user)
        first_login_time = regular_user.last_login
        assert first_login_time is not None

        # Wait a moment to ensure timestamp difference
        import time
        time.sleep(0.1)

        # Second login
        response2 = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password123"}
        )
        assert response2.status_code == 200

        session.refresh(regular_user)
        second_login_time = regular_user.last_login
        assert second_login_time is not None
        assert second_login_time > first_login_time

    def test_last_login_in_user_response(self, client: TestClient, auth_headers: dict, regular_user: User, session: Session):
        """Test that last_login is included in user response"""
        # Login to set last_login
        client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password123"}
        )

        # Get account info
        response = client.get("/accounts/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "last_login" in data
        assert data["last_login"] is not None

    def test_registration_does_not_set_last_login(self, client: TestClient, session: Session):
        """Test that registration does not set last_login (only login does)"""
        response = client.post(
            "/accounts/register",
            json={
                "username": "newuser",
                "firstname": "New",
                "lastname": "User",
                "email": "new@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["last_login"] is None
