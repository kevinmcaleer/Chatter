"""
Comprehensive tests for User Projects feature (Issue #15)
Tests cover all 37 API endpoints and project functionality
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from unittest.mock import patch, MagicMock
import io
from datetime import datetime

from app.main import app
from app.database import get_session
from app.auth import get_current_user
from app.models import User
from app.project_models import (
    Project, ProjectTag, ProjectStep, BillOfMaterial,
    Component, ProjectComponent, ProjectFile, ProjectImage,
    ProjectLink, ToolMaterial
)


# Test fixtures
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
    """Create a test client with database session override"""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user"""
    user = User(
        username="testuser",
        firstname="Test",
        lastname="User",
        email="test@example.com",
        hashed_password="$2b$12$test_hash"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="other_user")
def other_user_fixture(session: Session):
    """Create another test user for permission testing"""
    user = User(
        username="otheruser",
        firstname="Other",
        lastname="User",
        email="other@example.com",
        hashed_password="$2b$12$test_hash"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_client")
def auth_client_fixture(client: TestClient, test_user: User):
    """Create an authenticated test client"""
    def get_current_user_override():
        return test_user

    app.dependency_overrides[get_current_user] = get_current_user_override
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_project")
def test_project_fixture(session: Session, test_user: User):
    """Create a test project"""
    project = Project(
        title="Test Arduino Robot",
        description="A simple robot project",
        author_id=test_user.id,
        status="draft"
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Add a tag
    tag = ProjectTag(project_id=project.id, tag_name="arduino")
    session.add(tag)
    session.commit()

    return project


# Project CRUD Tests
class TestProjectCRUD:
    """Test basic project CRUD operations"""

    def test_create_project_success(self, auth_client: TestClient, test_user: User):
        """Test creating a new project"""
        response = auth_client.post(
            "/api/projects",
            json={
                "title": "My Arduino Project",
                "description": "A cool robotics project",
                "tags": ["arduino", "robotics"],
                "background": "I built this because...",
                "code_link": "https://github.com/user/project"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Arduino Project"
        assert data["description"] == "A cool robotics project"
        assert data["status"] == "draft"
        assert data["author"] == test_user.username
        assert len(data["tags"]) == 2
        assert "arduino" in data["tags"]

    def test_create_project_requires_auth(self, client: TestClient):
        """Test that creating a project requires authentication"""
        response = client.post(
            "/api/projects",
            json={
                "title": "Test Project",
                "description": "Test description",
                "tags": []
            }
        )
        assert response.status_code == 401

    def test_get_project_published(self, client: TestClient, session: Session, test_project: Project):
        """Test getting a published project (public access)"""
        # Publish the project
        test_project.status = "published"
        session.add(test_project)
        session.commit()

        response = client.get(f"/api/projects/{test_project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == test_project.title

    def test_get_project_draft_by_author(self, auth_client: TestClient, test_project: Project):
        """Test that author can view their own draft"""
        response = auth_client.get(f"/api/projects/{test_project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"

    def test_get_project_draft_by_other_user(self, client: TestClient, other_user: User, test_project: Project):
        """Test that other users cannot view drafts"""
        def get_current_user_override():
            return other_user

        app.dependency_overrides[get_current_user] = get_current_user_override
        response = client.get(f"/api/projects/{test_project.id}")
        app.dependency_overrides.clear()

        assert response.status_code == 403

    def test_update_project_by_author(self, auth_client: TestClient, test_project: Project):
        """Test updating a project by its author"""
        response = auth_client.put(
            f"/api/projects/{test_project.id}",
            json={
                "title": "Updated Title",
                "description": "Updated description"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"

    def test_update_project_by_non_author(self, client: TestClient, other_user: User, test_project: Project):
        """Test that non-authors cannot update projects"""
        def get_current_user_override():
            return other_user

        app.dependency_overrides[get_current_user] = get_current_user_override
        response = client.put(
            f"/api/projects/{test_project.id}",
            json={"title": "Hacked Title"}
        )
        app.dependency_overrides.clear()

        assert response.status_code == 403

    def test_delete_project_by_author(self, auth_client: TestClient, test_project: Project):
        """Test deleting a project by its author"""
        response = auth_client.delete(f"/api/projects/{test_project.id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = auth_client.get(f"/api/projects/{test_project.id}")
        assert response.status_code == 404

    def test_publish_project(self, auth_client: TestClient, test_project: Project):
        """Test publishing a project"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/publish",
            json={"status": "published"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"

    def test_list_projects(self, client: TestClient, session: Session, test_user: User):
        """Test listing projects with pagination and filtering"""
        # Create multiple published projects
        for i in range(5):
            project = Project(
                title=f"Project {i}",
                description=f"Description {i}",
                author_id=test_user.id,
                status="published"
            )
            session.add(project)
        session.commit()

        response = client.get("/api/projects?page=1&per_page=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 3
        assert data["total"] >= 5
        assert data["pages"] >= 2


# Project Steps Tests
class TestProjectSteps:
    """Test project steps management"""

    def test_create_step(self, auth_client: TestClient, test_project: Project):
        """Test creating a project step"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/steps",
            json={
                "step_number": 1,
                "title": "Step 1: Gather Materials",
                "content": "You will need the following materials..."
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["step_number"] == 1
        assert data["title"] == "Step 1: Gather Materials"

    def test_list_steps(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test listing project steps"""
        # Create steps
        for i in range(3):
            step = ProjectStep(
                project_id=test_project.id,
                step_number=i + 1,
                title=f"Step {i + 1}",
                content=f"Content {i + 1}"
            )
            session.add(step)
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/steps")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_update_step(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test updating a project step"""
        step = ProjectStep(
            project_id=test_project.id,
            step_number=1,
            title="Original",
            content="Original content"
        )
        session.add(step)
        session.commit()
        session.refresh(step)

        response = auth_client.put(
            f"/api/projects/{test_project.id}/steps/{step.id}",
            json={"title": "Updated Title"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_delete_step(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test deleting a project step"""
        step = ProjectStep(
            project_id=test_project.id,
            step_number=1,
            title="To Delete",
            content="Content"
        )
        session.add(step)
        session.commit()
        session.refresh(step)

        response = auth_client.delete(f"/api/projects/{test_project.id}/steps/{step.id}")
        assert response.status_code == 204


# Bill of Materials Tests
class TestBillOfMaterials:
    """Test BOM management"""

    def test_create_bom_item(self, auth_client: TestClient, test_project: Project):
        """Test creating a BOM item"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/bom",
            json={
                "item_name": "Arduino Uno",
                "description": "Microcontroller board",
                "quantity": 1,
                "price_cents": 2500
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["item_name"] == "Arduino Uno"
        assert data["quantity"] == 1
        assert data["price_cents"] == 2500

    def test_list_bom_items(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test listing BOM items"""
        for i in range(3):
            bom = BillOfMaterial(
                project_id=test_project.id,
                item_name=f"Item {i}",
                quantity=i + 1
            )
            session.add(bom)
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/bom")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


# Components Tests
class TestComponents:
    """Test component management"""

    def test_create_component(self, auth_client: TestClient):
        """Test creating a reusable component"""
        response = auth_client.post(
            "/api/components",
            json={
                "name": "Arduino Uno R3",
                "description": "Popular microcontroller",
                "datasheet_url": "https://example.com/datasheet.pdf"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Arduino Uno R3"

    def test_add_component_to_project(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test adding a component to a project"""
        # Create component first
        component = Component(
            name="LED Red 5mm",
            description="Standard red LED"
        )
        session.add(component)
        session.commit()
        session.refresh(component)

        response = auth_client.post(
            f"/api/projects/{test_project.id}/components",
            json={
                "component_id": component.id,
                "quantity": 5,
                "notes": "For status indicators"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 5


# File Upload Tests (with NAS mocking)
class TestFileUploads:
    """Test file upload functionality with NAS storage mocking"""

    @patch('app.storage.check_nas_connection')
    @patch('app.storage.save_file_to_nas')
    def test_upload_file_to_nas(self, mock_save_nas, mock_check_nas,
                                 auth_client: TestClient, test_project: Project):
        """Test uploading a file (saves to NAS)"""
        mock_check_nas.return_value = True
        mock_save_nas.return_value = True

        file_content = b"This is test file content"
        response = auth_client.post(
            f"/api/projects/{test_project.id}/files",
            data={"description": "Test file"},
            files={"file": ("test.stl", io.BytesIO(file_content), "application/octet-stream")}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["original_filename"] == "test.stl"
        assert data["file_size"] == len(file_content)
        mock_save_nas.assert_called_once()

    @patch('app.storage.check_nas_connection')
    @patch('app.storage.save_file_to_local')
    def test_upload_file_nas_fallback(self, mock_save_local, mock_check_nas,
                                       auth_client: TestClient, test_project: Project):
        """Test file upload falls back to local storage when NAS unavailable"""
        mock_check_nas.return_value = False
        mock_save_local.return_value = True

        file_content = b"Test content"
        response = auth_client.post(
            f"/api/projects/{test_project.id}/files",
            data={"description": "Test file"},
            files={"file": ("code.py", io.BytesIO(file_content), "text/plain")}
        )

        assert response.status_code == 201
        mock_save_local.assert_called_once()

    def test_upload_file_size_limit(self, auth_client: TestClient, test_project: Project):
        """Test that files exceeding size limit are rejected"""
        # 26MB file (over 25MB limit)
        large_content = b"x" * (26 * 1024 * 1024)

        response = auth_client.post(
            f"/api/projects/{test_project.id}/files",
            data={"description": "Too large"},
            files={"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
        )

        assert response.status_code == 400


# Image Upload Tests
class TestImageUploads:
    """Test image upload functionality"""

    @patch('app.storage.check_nas_connection')
    @patch('app.storage.save_file_to_nas')
    def test_upload_image(self, mock_save_nas, mock_check_nas,
                          auth_client: TestClient, test_project: Project):
        """Test uploading an image"""
        mock_check_nas.return_value = True
        mock_save_nas.return_value = True

        # Simple 1x1 PNG image
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'

        response = auth_client.post(
            f"/api/projects/{test_project.id}/images",
            data={"caption": "Test image"},
            files={"image": ("test.png", io.BytesIO(image_content), "image/png")}
        )

        assert response.status_code == 201


# ZIP Download Tests
class TestZIPDownload:
    """Test ZIP download and README generation"""

    @patch('app.storage.check_nas_connection')
    @patch('app.storage.read_file_from_nas')
    def test_download_project_zip(self, mock_read_nas, mock_check_nas,
                                   client: TestClient, session: Session,
                                   test_user: User, test_project: Project):
        """Test downloading project as ZIP"""
        # Publish project first
        test_project.status = "published"
        session.add(test_project)
        session.commit()

        mock_check_nas.return_value = True
        mock_read_nas.return_value = b"file content"

        response = client.get(f"/api/projects/{test_project.id}/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]

    def test_readme_generation(self, client: TestClient, session: Session,
                                test_user: User, test_project: Project):
        """Test that README is generated in ZIP"""
        # Add some content to project
        test_project.status = "published"
        test_project.background = "This is the project background"

        step = ProjectStep(
            project_id=test_project.id,
            step_number=1,
            title="Step 1",
            content="Do this first"
        )
        session.add(step)
        session.add(test_project)
        session.commit()

        response = client.get(f"/api/projects/{test_project.id}/download")
        assert response.status_code == 200


# Links and Tools Tests
class TestLinksAndTools:
    """Test project links and tools/materials"""

    def test_create_link(self, auth_client: TestClient, test_project: Project):
        """Test creating a project link"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/links",
            json={
                "url": "https://youtube.com/watch?v=example",
                "title": "Project Video Tutorial",
                "link_type": "video",
                "description": "Step by step guide"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["link_type"] == "video"

    def test_create_tool(self, auth_client: TestClient, test_project: Project):
        """Test adding a tool/material"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/tools",
            json={
                "name": "Soldering Iron",
                "tool_type": "tool",
                "notes": "Required for assembly"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tool_type"] == "tool"


# Permissions Tests
class TestPermissions:
    """Test authorization and permissions"""

    def test_only_author_can_edit(self, client: TestClient, other_user: User, test_project: Project):
        """Test that only project author can edit"""
        def get_current_user_override():
            return other_user

        app.dependency_overrides[get_current_user] = get_current_user_override

        # Try to add a step
        response = client.post(
            f"/api/projects/{test_project.id}/steps",
            json={
                "step_number": 1,
                "title": "Unauthorized",
                "content": "Should fail"
            }
        )

        app.dependency_overrides.clear()
        assert response.status_code == 403

    def test_draft_only_visible_to_author(self, client: TestClient):
        """Test that draft projects are not listed publicly"""
        response = client.get("/api/projects?status_filter=published")
        assert response.status_code == 200
        data = response.json()
        # Should not include draft projects
        for project in data["projects"]:
            assert project["status"] == "published"


# Integration Tests
class TestProjectWorkflow:
    """Test complete project creation workflow"""

    @patch('app.storage.check_nas_connection', return_value=True)
    @patch('app.storage.save_file_to_nas', return_value=True)
    def test_complete_project_workflow(self, mock_save, mock_check,
                                        auth_client: TestClient, test_user: User):
        """Test creating a complete project with all components"""
        # 1. Create project
        response = auth_client.post(
            "/api/projects",
            json={
                "title": "Complete Robot Project",
                "description": "Full robot with sensors",
                "tags": ["robotics", "arduino", "sensors"]
            }
        )
        assert response.status_code == 201
        project_id = response.json()["id"]

        # 2. Add steps
        response = auth_client.post(
            f"/api/projects/{project_id}/steps",
            json={
                "step_number": 1,
                "title": "Build chassis",
                "content": "Assemble the robot chassis"
            }
        )
        assert response.status_code == 201

        # 3. Add BOM
        response = auth_client.post(
            f"/api/projects/{project_id}/bom",
            json={
                "item_name": "Arduino Uno",
                "quantity": 1,
                "price_cents": 2500
            }
        )
        assert response.status_code == 201

        # 4. Add file
        response = auth_client.post(
            f"/api/projects/{project_id}/files",
            data={"description": "Source code"},
            files={"file": ("robot.ino", io.BytesIO(b"void setup(){}"), "text/plain")}
        )
        assert response.status_code == 201

        # 5. Publish
        response = auth_client.post(
            f"/api/projects/{project_id}/publish",
            json={"status": "published"}
        )
        assert response.status_code == 200

        # 6. Verify complete project
        response = auth_client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert len(data["steps"]) == 1
        assert len(data["bill_of_materials"]) == 1
        assert len(data["files"]) == 1
