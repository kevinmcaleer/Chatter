"""
Extended tests for User Projects feature to achieve 80%+ coverage.
Covers endpoints and edge cases not tested in test_projects.py
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel, select
from sqlmodel.pool import StaticPool
from unittest.mock import patch

from app.main import app
from app.database import get_session
from app.models import User
from app.project_models import (
    Project, ProjectStep, BillOfMaterial, Component,
    ProjectComponent, ProjectLink, ToolMaterial, ProjectFile, ProjectImage
)
from app.auth import get_current_user, get_optional_user


# Fixtures (reused from test_projects.py)
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
    """Create another test user"""
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

    def get_optional_user_override():
        return test_user

    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[get_optional_user] = get_optional_user_override
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_project")
def test_project_fixture(session: Session, test_user: User):
    """Create a test project"""
    project = Project(
        title="Test Project",
        description="A test project",
        author_id=test_user.id,
        status="draft"
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture(name="published_project")
def published_project_fixture(session: Session, test_user: User):
    """Create a published test project"""
    project = Project(
        title="Published Project",
        description="A published project",
        author_id=test_user.id,
        status="published"
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Add tags separately
    from app.project_models import ProjectTag
    tag1 = ProjectTag(project_id=project.id, tag_name="arduino")
    tag2 = ProjectTag(project_id=project.id, tag_name="robotics")
    session.add_all([tag1, tag2])
    session.commit()

    return project


# ============================================
# Unpublish Tests
# ============================================
class TestProjectUnpublish:
    """Test project unpublish functionality"""

    def test_unpublish_project(self, auth_client: TestClient, published_project: Project):
        """Test unpublishing a project"""
        response = auth_client.post(f"/api/projects/{published_project.id}/unpublish")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"

    def test_unpublish_already_draft(self, auth_client: TestClient, test_project: Project):
        """Test unpublishing an already draft project"""
        response = auth_client.post(f"/api/projects/{test_project.id}/unpublish")
        assert response.status_code == 400


# ============================================
# Step Reordering Tests
# ============================================
class TestStepReordering:
    """Test step reordering functionality"""

    def test_reorder_steps(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test reordering project steps"""
        # Create steps
        step1 = ProjectStep(project_id=test_project.id, step_number=1, title="First", content="Content 1")
        step2 = ProjectStep(project_id=test_project.id, step_number=2, title="Second", content="Content 2")
        step3 = ProjectStep(project_id=test_project.id, step_number=3, title="Third", content="Content 3")
        session.add_all([step1, step2, step3])
        session.commit()
        session.refresh(step1)
        session.refresh(step2)
        session.refresh(step3)

        # Reorder: swap first and third (provide list of step IDs in new order)
        response = auth_client.put(
            f"/api/projects/{test_project.id}/steps/reorder",
            json={"step_ids": [step3.id, step2.id, step1.id]}  # New order: third, second, first
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["id"] == step3.id
        assert data[0]["step_number"] == 1


# ============================================
# BOM Update/Delete Tests
# ============================================
class TestBOMOperations:
    """Test BOM update and delete operations"""

    def test_update_bom_item(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test updating a BOM item"""
        bom = BillOfMaterial(
            project_id=test_project.id,
            item_name="Arduino Uno",
            quantity=1,
            price_cents=2500
        )
        session.add(bom)
        session.commit()
        session.refresh(bom)

        response = auth_client.put(
            f"/api/projects/{test_project.id}/bom/{bom.id}",
            json={
                "item_name": "Arduino Mega",
                "quantity": 2,
                "price_cents": 4500
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["item_name"] == "Arduino Mega"
        assert data["quantity"] == 2
        assert data["price_cents"] == 4500

    def test_delete_bom_item(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test deleting a BOM item"""
        bom = BillOfMaterial(
            project_id=test_project.id,
            item_name="Arduino Uno",
            quantity=1,
            price_cents=2500
        )
        session.add(bom)
        session.commit()
        session.refresh(bom)

        response = auth_client.delete(f"/api/projects/{test_project.id}/bom/{bom.id}")
        assert response.status_code == 204

        # Verify deletion
        deleted_bom = session.get(BillOfMaterial, bom.id)
        assert deleted_bom is None


# ============================================
# Component Search Tests
# ============================================
class TestComponentSearch:
    """Test component search functionality"""

    def test_search_components(self, auth_client: TestClient, session: Session):
        """Test searching for components"""
        # Create test components
        comp1 = Component(name="Arduino Uno", description="Microcontroller board")
        comp2 = Component(name="Arduino Mega", description="Larger board")
        comp3 = Component(name="Raspberry Pi", description="Single board computer")
        session.add_all([comp1, comp2, comp3])
        session.commit()

        # Search for "Arduino"
        response = auth_client.get("/api/components/search?q=Arduino")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert any(c["name"] == "Arduino Uno" for c in data)

    def test_search_components_empty_query(self, auth_client: TestClient):
        """Test search with short query returns empty list"""
        response = auth_client.get("/api/components/search?q=a")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # Returns empty array for queries < 2 chars


# ============================================
# Component CRUD Tests
# ============================================
class TestComponentOperations:
    """Test component creation and management"""

    def test_delete_project_component(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test removing a component from a project"""
        # Create component
        comp = Component(name="Test Component", description="Test")
        session.add(comp)
        session.commit()
        session.refresh(comp)

        # Add to project
        proj_comp = ProjectComponent(
            project_id=test_project.id,
            component_id=comp.id,
            quantity=1
        )
        session.add(proj_comp)
        session.commit()
        session.refresh(proj_comp)

        # Delete
        response = auth_client.delete(f"/api/projects/{test_project.id}/components/{proj_comp.id}")
        assert response.status_code == 204


# ============================================
# Links Update/Delete Tests
# ============================================
class TestLinkOperations:
    """Test link update and delete operations"""

    def test_update_link(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test updating a project link"""
        link = ProjectLink(
            project_id=test_project.id,
            title="Original Link",
            url="https://example.com",
            link_type="resource"
        )
        session.add(link)
        session.commit()
        session.refresh(link)

        response = auth_client.put(
            f"/api/projects/{test_project.id}/links/{link.id}",
            json={
                "title": "Updated Link",
                "url": "https://updated.com",
                "link_type": "video"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Link"
        assert data["link_type"] == "video"

    def test_delete_link(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test deleting a project link"""
        link = ProjectLink(
            project_id=test_project.id,
            title="Test Link",
            url="https://example.com",
            link_type="resource"
        )
        session.add(link)
        session.commit()
        session.refresh(link)

        response = auth_client.delete(f"/api/projects/{test_project.id}/links/{link.id}")
        assert response.status_code == 204


# ============================================
# Tools/Materials Tests
# ============================================
class TestToolsOperations:
    """Test tools and materials management"""

    def test_create_tool(self, auth_client: TestClient, test_project: Project):
        """Test adding a tool to project"""
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
        assert data["name"] == "Soldering Iron"
        assert data["tool_type"] == "tool"

    def test_list_tools(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test listing tools for a project"""
        tool1 = ToolMaterial(
            project_id=test_project.id,
            name="Screwdriver",
            tool_type="tool"
        )
        tool2 = ToolMaterial(
            project_id=test_project.id,
            name="Wire",
            tool_type="material"
        )
        session.add_all([tool1, tool2])
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/tools")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_update_tool(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test updating a tool"""
        tool = ToolMaterial(
            project_id=test_project.id,
            name="Old Tool",
            tool_type="tool"
        )
        session.add(tool)
        session.commit()
        session.refresh(tool)

        response = auth_client.put(
            f"/api/projects/{test_project.id}/tools/{tool.id}",
            json={
                "name": "New Tool",
                "tool_type": "material"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Tool"
        assert data["tool_type"] == "material"

    def test_delete_tool(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test deleting a tool"""
        tool = ToolMaterial(
            project_id=test_project.id,
            name="Test Tool",
            tool_type="tool",
            is_required=False
        )
        session.add(tool)
        session.commit()
        session.refresh(tool)

        response = auth_client.delete(f"/api/projects/{test_project.id}/tools/{tool.id}")
        assert response.status_code == 204


# ============================================
# File Download Tests
# ============================================
class TestFileDownload:
    """Test file download functionality"""

    @pytest.mark.skip(reason="File download endpoint not yet implemented")
    @patch('app.storage.check_nas_connection')
    @patch('app.storage.read_file_from_nas')
    def test_download_file(self, mock_read_nas, mock_check_nas,
                          auth_client: TestClient, session: Session, test_project: Project):
        """Test downloading a project file"""
        mock_check_nas.return_value = True
        mock_read_nas.return_value = b"Test file content"

        # Create file record
        file = ProjectFile(
            project_id=test_project.id,
            filename="test.py",
            original_filename="test.py",
            file_size=100,
            file_type="text/plain"
        )
        session.add(file)
        session.commit()
        session.refresh(file)

        response = auth_client.get(f"/api/projects/{test_project.id}/files/{file.id}/download")
        assert response.status_code == 200
        assert response.content == b"Test file content"


# ============================================
# Image Operations Tests
# ============================================
class TestImageOperations:
    """Test image-specific operations"""

    def test_set_primary_image(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test setting a primary image"""
        image = ProjectImage(
            project_id=test_project.id,
            filename="image.jpg",
            original_filename="test.jpg",
            caption="Test image"
        )
        session.add(image)
        session.commit()
        session.refresh(image)

        response = auth_client.put(f"/api/projects/{test_project.id}/images/{image.id}/primary")
        assert response.status_code == 200
        data = response.json()
        assert data["primary_image_id"] == image.id

    def test_list_images(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test listing project images"""
        image1 = ProjectImage(
            project_id=test_project.id,
            filename="img1.jpg",
            original_filename="img1.jpg",
            caption="First"
        )
        image2 = ProjectImage(
            project_id=test_project.id,
            filename="img2.jpg",
            original_filename="img2.jpg",
            caption="Second"
        )
        session.add_all([image1, image2])
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/images")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_delete_image(self, auth_client: TestClient, session: Session, test_project: Project):
        """Test deleting an image"""
        image = ProjectImage(
            project_id=test_project.id,
            filename="test.jpg",
            original_filename="test.jpg",
            caption="Test"
        )
        session.add(image)
        session.commit()
        session.refresh(image)

        response = auth_client.delete(f"/api/projects/{test_project.id}/images/{image.id}")
        assert response.status_code == 204


# ============================================
# Project Filtering and Sorting Tests
# ============================================
class TestProjectFiltering:
    """Test project list filtering and sorting"""

    def test_filter_by_tag(self, client: TestClient, session: Session, test_user: User):
        """Test filtering projects by tag"""
        from app.project_models import ProjectTag

        # Create projects with different tags
        proj1 = Project(
            title="Arduino Project",
            description="Test",
            author_id=test_user.id,
            status="published"
        )
        proj2 = Project(
            title="Raspberry Pi Project",
            description="Test",
            author_id=test_user.id,
            status="published"
        )
        session.add_all([proj1, proj2])
        session.commit()
        session.refresh(proj1)
        session.refresh(proj2)

        # Add tags
        tag1 = ProjectTag(project_id=proj1.id, tag_name="arduino")
        tag2 = ProjectTag(project_id=proj1.id, tag_name="beginner")
        tag3 = ProjectTag(project_id=proj2.id, tag_name="raspberrypi")
        tag4 = ProjectTag(project_id=proj2.id, tag_name="advanced")
        session.add_all([tag1, tag2, tag3, tag4])
        session.commit()

        response = client.get("/api/projects?tag=arduino")
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) >= 1
        assert any(p["title"] == "Arduino Project" for p in data["projects"])

    def test_filter_by_author(self, client: TestClient, session: Session, test_user: User, other_user: User):
        """Test filtering projects by author"""
        proj1 = Project(
            title="User 1 Project",
            description="Test",
            author_id=test_user.id,
            status="published"
        )
        proj2 = Project(
            title="User 2 Project",
            description="Test",
            author_id=other_user.id,
            status="published"
        )
        session.add_all([proj1, proj2])
        session.commit()

        response = client.get(f"/api/projects?author_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert all(p["author_username"] == "testuser" for p in data["projects"])

    def test_sort_by_popular(self, client: TestClient, session: Session, test_user: User):
        """Test sorting projects by popularity"""
        proj1 = Project(
            title="Popular",
            description="Test",
            author_id=test_user.id,
            status="published",
            like_count=100
        )
        proj2 = Project(
            title="Less Popular",
            description="Test",
            author_id=test_user.id,
            status="published",
            like_count=10
        )
        session.add_all([proj1, proj2])
        session.commit()

        response = client.get("/api/projects?sort=popular")
        assert response.status_code == 200
        data = response.json()
        if len(data["projects"]) >= 2:
            # Most popular should be first
            assert data["projects"][0]["like_count"] >= data["projects"][1]["like_count"]


# ============================================
# Error Handling Tests
# ============================================
class TestErrorHandling:
    """Test error handling for various edge cases"""

    def test_get_nonexistent_project(self, client: TestClient):
        """Test getting a project that doesn't exist"""
        response = client.get("/api/projects/99999")
        assert response.status_code == 404

    def test_update_nonexistent_project(self, auth_client: TestClient):
        """Test updating a project that doesn't exist"""
        response = auth_client.put(
            "/api/projects/99999",
            json={"title": "Updated", "description": "Test"}
        )
        assert response.status_code == 404

    def test_delete_nonexistent_project(self, auth_client: TestClient):
        """Test deleting a project that doesn't exist"""
        response = auth_client.delete("/api/projects/99999")
        assert response.status_code == 404

    def test_create_step_for_nonexistent_project(self, auth_client: TestClient):
        """Test creating a step for non-existent project"""
        response = auth_client.post(
            "/api/projects/99999/steps",
            json={"title": "Test", "content": "Test"}
        )
        assert response.status_code == 404

    def test_unauthorized_project_access(self, client: TestClient, session: Session, test_user: User):
        """Test accessing draft project without authentication"""
        project = Project(
            title="Draft Project",
            description="Test",
            author_id=test_user.id,
            status="draft"
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        response = client.get(f"/api/projects/{project.id}")
        assert response.status_code == 403
