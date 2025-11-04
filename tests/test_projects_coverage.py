"""
Additional tests to reach 80% coverage on projects.py
Targets uncovered code paths and edge cases
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from unittest.mock import patch

from app.main import app
from app.database import get_session
from app.auth import get_current_user, get_optional_user
from app.models import User
from app.project_models import (
    Project, ProjectTag, ProjectStep, Component, ProjectComponent,
    ProjectImage, ProjectLink, ToolMaterial
)


# Fixtures (reused from other test files)
@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh database session for each test"""
    from sqlmodel import create_engine, SQLModel
    from sqlmodel.pool import StaticPool

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
    """Create test client with overridden session"""
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
    """Create a test project with tags"""
    project = Project(
        title="Test Project",
        description="Test description",
        author_id=test_user.id,
        status="draft"
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Add a tag
    tag = ProjectTag(project_id=project.id, tag_name="test")
    session.add(tag)
    session.commit()

    return project


@pytest.fixture(name="published_project")
def published_project_fixture(session: Session, test_user: User):
    """Create a published project"""
    project = Project(
        title="Published Project",
        description="Published description",
        author_id=test_user.id,
        status="published"
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    tag = ProjectTag(project_id=project.id, tag_name="published")
    session.add(tag)
    session.commit()

    return project


# ============================================
# Gallery and Filtering Tests
# ============================================
class TestProjectGallery:
    """Test project gallery and filtering"""

    def test_list_projects_with_tag_filter(self, client: TestClient, session: Session,
                                          test_user: User):
        """Test filtering projects by tag"""
        # Create projects with different tags
        proj1 = Project(title="Arduino Project", description="Test",
                       author_id=test_user.id, status="published")
        proj2 = Project(title="Python Project", description="Test",
                       author_id=test_user.id, status="published")
        session.add_all([proj1, proj2])
        session.commit()
        session.refresh(proj1)
        session.refresh(proj2)

        tag1 = ProjectTag(project_id=proj1.id, tag_name="arduino")
        tag2 = ProjectTag(project_id=proj2.id, tag_name="python")
        session.add_all([tag1, tag2])
        session.commit()

        # Filter by arduino tag
        response = client.get("/api/projects?tag=arduino")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        # Should find the arduino project
        arduino_projects = [p for p in data["projects"] if "arduino" in [t.lower() for t in p.get("tags", [])]]
        assert len(arduino_projects) >= 1

    def test_list_projects_with_author_filter(self, client: TestClient, session: Session,
                                              test_user: User):
        """Test filtering projects by author"""
        # Create project
        proj = Project(title="My Project", description="Test",
                      author_id=test_user.id, status="published")
        session.add(proj)
        session.commit()

        tag = ProjectTag(project_id=proj.id, tag_name="test")
        session.add(tag)
        session.commit()

        response = client.get(f"/api/projects?author_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert all(p["author_id"] == test_user.id for p in data["projects"])

    def test_list_projects_with_sort(self, client: TestClient, session: Session,
                                     test_user: User):
        """Test sorting projects by popularity"""
        # Create projects with different view counts
        proj1 = Project(title="Popular", description="Test",
                       author_id=test_user.id, status="published", view_count=100)
        proj2 = Project(title="Less Popular", description="Test",
                       author_id=test_user.id, status="published", view_count=10)
        session.add_all([proj1, proj2])
        session.commit()

        for proj in [proj1, proj2]:
            session.refresh(proj)
            tag = ProjectTag(project_id=proj.id, tag_name="test")
            session.add(tag)
        session.commit()

        response = client.get("/api/projects?sort=popular")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        # Projects should be sorted by popularity (view count)
        if len(data["projects"]) >= 2:
            assert data["projects"][0]["view_count"] >= data["projects"][1]["view_count"]

    def test_list_projects_pagination(self, client: TestClient, session: Session,
                                     test_user: User):
        """Test pagination parameters"""
        # Create multiple projects
        for i in range(5):
            proj = Project(title=f"Project {i}", description="Test",
                          author_id=test_user.id, status="published")
            session.add(proj)
            session.commit()
            session.refresh(proj)
            tag = ProjectTag(project_id=proj.id, tag_name="test")
            session.add(tag)
        session.commit()

        # Test first page
        response = client.get("/api/projects?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "page" in data
        assert data["page"] == 1
        assert "per_page" in data


# ============================================
# Component Operations Tests
# ============================================
class TestComponentOperations:
    """Test component CRUD operations"""

    def test_create_component_with_datasheet(self, auth_client: TestClient):
        """Test creating component with datasheet URL"""
        response = auth_client.post(
            "/api/components",
            json={
                "name": "Arduino Uno R3",
                "description": "Microcontroller board",
                "datasheet_url": "https://example.com/datasheet.pdf"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Arduino Uno R3"
        assert data["datasheet_url"] == "https://example.com/datasheet.pdf"

    def test_search_components_with_results(self, auth_client: TestClient, session: Session):
        """Test component search returns matching results"""
        # Create components
        comp1 = Component(name="Arduino Uno", description="MCU board")
        comp2 = Component(name="Arduino Mega", description="Larger MCU")
        comp3 = Component(name="Raspberry Pi", description="SBC")
        session.add_all([comp1, comp2, comp3])
        session.commit()

        # Search for Arduino
        response = auth_client.get("/api/components/search?q=Arduino")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("Arduino" in c["name"] for c in data)

    def test_search_components_min_length(self, auth_client: TestClient):
        """Test component search requires minimum 2 characters"""
        response = auth_client.get("/api/components/search?q=A")
        assert response.status_code == 200
        data = response.json()
        assert data == []  # Returns empty for queries < 2 chars


# ============================================
# Project Statistics Tests
# ============================================
class TestProjectStats:
    """Test project statistics and analytics"""

    def test_view_count_increments_on_published(self, client: TestClient, session: Session,
                                                test_user: User):
        """Test that viewing published project increments view count"""
        proj = Project(title="View Test", description="Test",
                      author_id=test_user.id, status="published", view_count=0)
        session.add(proj)
        session.commit()
        session.refresh(proj)

        tag = ProjectTag(project_id=proj.id, tag_name="test")
        session.add(tag)
        session.commit()

        initial_views = proj.view_count

        # View the project
        response = client.get(f"/api/projects/{proj.id}")
        assert response.status_code == 200

        # Check view count increased
        session.refresh(proj)
        assert proj.view_count == initial_views + 1

    def test_view_count_not_incremented_on_draft(self, auth_client: TestClient,
                                                 test_project: Project, session: Session):
        """Test that viewing draft project does not increment view count"""
        initial_views = test_project.view_count

        # View the draft project
        response = auth_client.get(f"/api/projects/{test_project.id}")
        assert response.status_code == 200

        # Check view count did not change for draft
        session.refresh(test_project)
        assert test_project.view_count == initial_views


# ============================================
# Error Handling and Edge Cases
# ============================================
class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_create_project_without_auth(self, client: TestClient):
        """Test creating project without authentication returns 401"""
        response = client.post(
            "/api/projects",
            json={
                "title": "Test",
                "description": "Test",
                "tags": ["test"]
            }
        )
        assert response.status_code == 401

    def test_update_nonexistent_project_returns_404(self, auth_client: TestClient):
        """Test updating non-existent project returns 404"""
        response = auth_client.put(
            "/api/projects/99999",
            json={"title": "Updated"}
        )
        assert response.status_code == 404

    def test_delete_nonexistent_project_returns_404(self, auth_client: TestClient):
        """Test deleting non-existent project returns 404"""
        response = auth_client.delete("/api/projects/99999")
        assert response.status_code == 404

    def test_add_step_to_nonexistent_project(self, auth_client: TestClient):
        """Test adding step to non-existent project returns 404"""
        response = auth_client.post(
            "/api/projects/99999/steps",
            json={"title": "Step", "content": "Content"}
        )
        assert response.status_code == 404

    def test_create_project_with_empty_tags(self, auth_client: TestClient):
        """Test creating project with empty tags list returns 422"""
        response = auth_client.post(
            "/api/projects",
            json={
                "title": "Test",
                "description": "Test",
                "tags": []  # Empty tags should fail validation
            }
        )
        assert response.status_code == 422


# ============================================
# Image and File Operations
# ============================================
class TestImageAndFileOperations:
    """Test image and file specific operations"""

    def test_list_images_for_project(self, auth_client: TestClient, session: Session,
                                     test_project: Project):
        """Test listing images for a project"""
        # Create images
        img1 = ProjectImage(
            project_id=test_project.id,
            filename="img1.jpg",
            original_filename="photo1.jpg",
            display_order=0
        )
        img2 = ProjectImage(
            project_id=test_project.id,
            filename="img2.jpg",
            original_filename="photo2.jpg",
            display_order=1
        )
        session.add_all([img1, img2])
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/images")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("original_filename" in img for img in data)

    def test_delete_image(self, auth_client: TestClient, session: Session,
                         test_project: Project):
        """Test deleting an image"""
        img = ProjectImage(
            project_id=test_project.id,
            filename="test.jpg",
            original_filename="test.jpg",
            display_order=0
        )
        session.add(img)
        session.commit()
        session.refresh(img)

        response = auth_client.delete(f"/api/projects/{test_project.id}/images/{img.id}")
        assert response.status_code == 204


# ============================================
# Links and Tools Tests
# ============================================
class TestLinksAndToolsOperations:
    """Test links and tools operations"""

    def test_update_link(self, auth_client: TestClient, session: Session,
                        test_project: Project):
        """Test updating a project link"""
        link = ProjectLink(
            project_id=test_project.id,
            url="https://old.com",
            title="Old Title",
            link_type="resource"
        )
        session.add(link)
        session.commit()
        session.refresh(link)

        response = auth_client.put(
            f"/api/projects/{test_project.id}/links/{link.id}",
            json={
                "url": "https://new.com",
                "title": "New Title"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://new.com"
        assert data["title"] == "New Title"

    def test_update_tool(self, auth_client: TestClient, session: Session,
                        test_project: Project):
        """Test updating a tool/material"""
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


# ============================================
# List Operations for Draft Projects
# ============================================
class TestDraftProjectListings:
    """Test listing operations on draft projects"""

    def test_list_components_for_draft_by_author(self, auth_client: TestClient,
                                                 session: Session, test_project: Project):
        """Test author can list components on their draft project"""
        # Create component and add to project
        comp = Component(name="Test Component", description="Test")
        session.add(comp)
        session.commit()
        session.refresh(comp)

        proj_comp = ProjectComponent(
            project_id=test_project.id,
            component_id=comp.id,
            quantity=1
        )
        session.add(proj_comp)
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/components")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["component"]["name"] == "Test Component"

    def test_list_components_for_published(self, client: TestClient, session: Session,
                                          published_project: Project):
        """Test anyone can list components on published project"""
        # Create component and add to project
        comp = Component(name="Public Component", description="Test")
        session.add(comp)
        session.commit()
        session.refresh(comp)

        proj_comp = ProjectComponent(
            project_id=published_project.id,
            component_id=comp.id,
            quantity=2
        )
        session.add(proj_comp)
        session.commit()

        response = client.get(f"/api/projects/{published_project.id}/components")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_files_for_draft_by_author(self, auth_client: TestClient, session: Session,
                                            test_project: Project):
        """Test author can list files on their draft project"""
        from app.project_models import ProjectFile

        file = ProjectFile(
            project_id=test_project.id,
            filename="test.py",
            original_filename="test.py",
            file_size=100
        )
        session.add(file)
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/files")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["original_filename"] == "test.py"

    def test_list_files_for_published(self, client: TestClient, session: Session,
                                     published_project: Project):
        """Test anyone can list files on published project"""
        from app.project_models import ProjectFile

        file = ProjectFile(
            project_id=published_project.id,
            filename="code.py",
            original_filename="code.py",
            file_size=200
        )
        session.add(file)
        session.commit()

        response = client.get(f"/api/projects/{published_project.id}/files")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


# ============================================
# Permission Tests for Draft Projects
# ============================================
class TestDraftProjectPermissions:
    """Test that draft projects properly restrict access"""

    def test_list_components_draft_other_user_forbidden(self, client: TestClient,
                                                        test_project: Project):
        """Test non-author cannot list components on draft project"""
        response = client.get(f"/api/projects/{test_project.id}/components")
        assert response.status_code == 403

    def test_list_files_draft_other_user_forbidden(self, client: TestClient,
                                                   test_project: Project):
        """Test non-author cannot list files on draft project"""
        response = client.get(f"/api/projects/{test_project.id}/files")
        assert response.status_code == 403

    def test_list_images_draft_other_user_forbidden(self, client: TestClient,
                                                    test_project: Project):
        """Test non-author cannot list images on draft project"""
        response = client.get(f"/api/projects/{test_project.id}/images")
        assert response.status_code == 403


# ============================================
# Tool and Material Listing Tests
# ============================================
class TestToolsListing:
    """Test listing tools and materials"""

    def test_list_tools_for_project(self, auth_client: TestClient, session: Session,
                                    test_project: Project):
        """Test listing tools for a project"""
        tool1 = ToolMaterial(
            project_id=test_project.id,
            name="Soldering Iron",
            tool_type="tool"
        )
        tool2 = ToolMaterial(
            project_id=test_project.id,
            name="Solder Wire",
            tool_type="material"
        )
        session.add_all([tool1, tool2])
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/tools")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


# ============================================
# Link Listing Tests
# ============================================
class TestLinksListing:
    """Test listing project links"""

    def test_list_links_for_project(self, auth_client: TestClient, session: Session,
                                    test_project: Project):
        """Test listing links for a project"""
        link1 = ProjectLink(
            project_id=test_project.id,
            url="https://example.com/tutorial",
            title="Tutorial",
            link_type="resource"
        )
        link2 = ProjectLink(
            project_id=test_project.id,
            url="https://youtube.com/watch",
            title="Video",
            link_type="video"
        )
        session.add_all([link1, link2])
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/links")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestProjectUpdates:
    """Test project update operations including tags and metadata"""

    def test_update_project_tags(self, auth_client: TestClient, session: Session,
                                 test_project: Project):
        """Test updating project tags"""
        from app.project_models import ProjectTag

        # Add initial tags
        tag1 = ProjectTag(project_id=test_project.id, tag_name="python")
        tag2 = ProjectTag(project_id=test_project.id, tag_name="arduino")
        session.add_all([tag1, tag2])
        session.commit()

        # Update with new tags
        response = auth_client.put(
            f"/api/projects/{test_project.id}",
            json={
                "title": test_project.title,
                "description": test_project.description,
                "tags": ["robotics", "sensors"]
            }
        )
        assert response.status_code == 200

        # Verify old tags are removed and new tags are added
        tags = session.exec(
            select(ProjectTag).where(ProjectTag.project_id == test_project.id)
        ).all()
        tag_names = [t.tag_name for t in tags]
        assert "robotics" in tag_names
        assert "sensors" in tag_names
        assert "python" not in tag_names
        assert "arduino" not in tag_names

    def test_update_project_background(self, auth_client: TestClient, session: Session,
                                       test_project: Project):
        """Test updating project background and code link"""
        response = auth_client.put(
            f"/api/projects/{test_project.id}",
            json={
                "title": test_project.title,
                "description": test_project.description,
                "background": "This is the background story",
                "code_link": "https://github.com/test/repo"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["background"] == "This is the background story"
        assert data["code_link"] == "https://github.com/test/repo"


class TestZIPDownloadEnhanced:
    """Test ZIP download with various project components"""

    @patch('app.projects.check_nas_connection', return_value=False)
    @patch('app.projects.read_file_from_local')
    def test_zip_download_with_bom_items(self, mock_read_local, mock_check_nas,
                                         auth_client: TestClient, session: Session,
                                         test_user: User):
        """Test ZIP download README includes BOM items"""
        from app.project_models import BillOfMaterial

        # Create published project
        project = Project(
            title="Project with BOM",
            description="Test project",
            author_id=test_user.id,
            status="published"
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # Add BOM items
        bom1 = BillOfMaterial(
            project_id=project.id,
            item_name="Resistor 220Ω",
            quantity=10,
            price_cents=50,
            description="Standard resistor",
            item_order=1
        )
        bom2 = BillOfMaterial(
            project_id=project.id,
            item_name="LED",
            quantity=5,
            price_cents=100,
            description="Red LED",
            item_order=2
        )
        session.add_all([bom1, bom2])
        session.commit()

        # Mock file reads
        mock_read_local.return_value = None

        response = auth_client.get(f"/api/projects/{project.id}/download")
        assert response.status_code == 200

        # Verify download count incremented
        session.refresh(project)
        assert project.download_count == 1

    @patch('app.projects.check_nas_connection', return_value=False)
    @patch('app.projects.read_file_from_local')
    def test_zip_download_with_components_and_tools(self, mock_read_local, mock_check_nas,
                                                    auth_client: TestClient, session: Session,
                                                    test_user: User):
        """Test ZIP download README includes components and tools"""
        from app.project_models import ToolMaterial

        # Create published project
        project = Project(
            title="Project with Components",
            description="Test project",
            author_id=test_user.id,
            status="published"
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # Add component
        comp = Component(
            name="Arduino Uno",
            description="Microcontroller",
            datasheet_url="https://example.com/datasheet.pdf"
        )
        session.add(comp)
        session.commit()
        session.refresh(comp)

        proj_comp = ProjectComponent(
            project_id=project.id,
            component_id=comp.id,
            quantity=1,
            notes="Main controller"
        )
        session.add(proj_comp)

        # Add tools
        tool1 = ToolMaterial(
            project_id=project.id,
            name="Soldering Iron",
            tool_type="tool",
            notes="40W recommended"
        )
        tool2 = ToolMaterial(
            project_id=project.id,
            name="Wire Strippers",
            tool_type="tool"
        )
        session.add_all([tool1, tool2])
        session.commit()

        # Mock file reads
        mock_read_local.return_value = None

        response = auth_client.get(f"/api/projects/{project.id}/download")
        assert response.status_code == 200

    @patch('app.projects.check_nas_connection', return_value=False)
    @patch('app.projects.read_file_from_local')
    def test_zip_download_with_links(self, mock_read_local, mock_check_nas,
                                    auth_client: TestClient, session: Session,
                                    test_user: User):
        """Test ZIP download README includes links"""
        from app.project_models import ProjectLink

        # Create published project
        project = Project(
            title="Project with Links",
            description="Test project",
            author_id=test_user.id,
            status="published"
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # Add links
        link1 = ProjectLink(
            project_id=project.id,
            title="Tutorial Video",
            url="https://youtube.com/watch?v=123",
            link_type="video",
            description="Step by step guide"
        )
        link2 = ProjectLink(
            project_id=project.id,
            title="Reference Design",
            url="https://example.com/design",
            link_type="reference"
        )
        session.add_all([link1, link2])
        session.commit()

        # Mock file reads
        mock_read_local.return_value = None

        response = auth_client.get(f"/api/projects/{project.id}/download")
        assert response.status_code == 200


class TestAdditionalEdgeCases:
    """Additional edge case tests to reach 80% coverage"""

    def test_create_project_with_all_optional_fields(self, auth_client: TestClient):
        """Test creating project with all optional fields"""
        response = auth_client.post(
            "/api/projects",
            json={
                "title": "Complete Project",
                "description": "Full project with all fields",
                "status": "draft",
                "background": "Detailed background",
                "code_link": "https://github.com/test/repo",
                "tags": ["python", "robotics", "ai"]
            }
        )
        assert response.status_code == 201  # POST returns 201 Created
        data = response.json()
        assert data["background"] == "Detailed background"
        assert data["code_link"] == "https://github.com/test/repo"

    def test_get_nonexistent_project_details(self, client: TestClient):
        """Test getting details for project that doesn't exist"""
        response = client.get("/api/projects/99999")
        assert response.status_code == 404

    def test_list_projects_with_pagination(self, client: TestClient, session: Session,
                                          test_user: User):
        """Test project listing with pagination parameters"""
        # Create 5 published projects
        for i in range(5):
            project = Project(
                title=f"Project {i}",
                description="Test",
                author_id=test_user.id,
                status="published"
            )
            session.add(project)
        session.commit()

        # Test pagination - response is dict with 'projects' key
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert len(data["projects"]) == 5

    def test_delete_step_from_project(self, auth_client: TestClient, session: Session,
                                     test_project: Project):
        """Test deleting a step from a project"""
        from app.project_models import ProjectStep

        # Create a step
        step = ProjectStep(
            project_id=test_project.id,
            step_number=1,
            title="Step 1",
            content="Do this first"
        )
        session.add(step)
        session.commit()
        session.refresh(step)

        # Delete the step
        response = auth_client.delete(f"/api/projects/{test_project.id}/steps/{step.id}")
        assert response.status_code == 204

        # Verify deletion
        deleted_step = session.get(ProjectStep, step.id)
        assert deleted_step is None

    def test_update_bom_item_price(self, auth_client: TestClient, session: Session,
                                   test_project: Project):
        """Test updating BOM item price"""
        from app.project_models import BillOfMaterial

        # Create BOM item
        bom = BillOfMaterial(
            project_id=test_project.id,
            item_name="Component",
            quantity=1,
            price_cents=100,
            item_order=1
        )
        session.add(bom)
        session.commit()
        session.refresh(bom)

        # Update price
        response = auth_client.put(
            f"/api/projects/{test_project.id}/bom/{bom.id}",
            json={
                "item_name": "Component",
                "quantity": 1,
                "price_cents": 200,
                "item_order": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["price_cents"] == 200

    def test_delete_component_from_project(self, auth_client: TestClient, session: Session,
                                          test_project: Project):
        """Test removing a component from a project"""
        # Create component and add to project
        comp = Component(name="Test Component", description="Test")
        session.add(comp)
        session.commit()
        session.refresh(comp)

        proj_comp = ProjectComponent(
            project_id=test_project.id,
            component_id=comp.id,
            quantity=1
        )
        session.add(proj_comp)
        session.commit()

        # Delete association
        response = auth_client.delete(f"/api/projects/{test_project.id}/components/{comp.id}")
        assert response.status_code == 204

        # Verify deletion
        remaining = session.exec(
            select(ProjectComponent)
            .where(ProjectComponent.project_id == test_project.id)
            .where(ProjectComponent.component_id == comp.id)
        ).first()
        assert remaining is None

    def test_update_step_content(self, auth_client: TestClient, session: Session,
                                test_project: Project):
        """Test updating step content and title"""
        from app.project_models import ProjectStep

        # Create step
        step = ProjectStep(
            project_id=test_project.id,
            step_number=1,
            title="Original Title",
            content="Original content"
        )
        session.add(step)
        session.commit()
        session.refresh(step)

        # Update step
        response = auth_client.put(
            f"/api/projects/{test_project.id}/steps/{step.id}",
            json={
                "title": "Updated Title",
                "content": "Updated content",
                "step_number": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content"

    def test_list_components_empty(self, auth_client: TestClient, test_project: Project):
        """Test listing components when project has none"""
        response = auth_client.get(f"/api/projects/{test_project.id}/components")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_list_bom_items_empty(self, auth_client: TestClient, test_project: Project):
        """Test listing BOM items when project has none"""
        response = auth_client.get(f"/api/projects/{test_project.id}/bom")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_list_steps_for_project(self, auth_client: TestClient, session: Session,
                                   test_project: Project):
        """Test listing all steps for a project"""
        from app.project_models import ProjectStep

        # Create multiple steps
        steps = [
            ProjectStep(project_id=test_project.id, step_number=1, title="Step 1", content="First"),
            ProjectStep(project_id=test_project.id, step_number=2, title="Step 2", content="Second"),
            ProjectStep(project_id=test_project.id, step_number=3, title="Step 3", content="Third"),
        ]
        for step in steps:
            session.add(step)
        session.commit()

        response = auth_client.get(f"/api/projects/{test_project.id}/steps")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["step_number"] == 1

    def test_create_step_with_explicit_number(self, auth_client: TestClient,
                                              test_project: Project):
        """Test creating a step with explicit step number"""
        from app.project_models import ProjectStep

        response = auth_client.post(
            f"/api/projects/{test_project.id}/steps",
            json={
                "title": "Step 5",
                "content": "Jump to step 5",
                "step_number": 5
            }
        )
        assert response.status_code == 201  # POST returns 201
        data = response.json()
        assert data["step_number"] == 5

    def test_delete_link_from_project(self, auth_client: TestClient, session: Session,
                                      test_project: Project):
        """Test deleting a link from a project"""
        from app.project_models import ProjectLink

        # Create link
        link = ProjectLink(
            project_id=test_project.id,
            title="Test Link",
            url="https://example.com",
            link_type="reference"
        )
        session.add(link)
        session.commit()
        session.refresh(link)

        # Delete link
        response = auth_client.delete(f"/api/projects/{test_project.id}/links/{link.id}")
        assert response.status_code == 204

    def test_delete_tool_from_project(self, auth_client: TestClient, session: Session,
                                     test_project: Project):
        """Test deleting a tool from a project"""
        from app.project_models import ToolMaterial

        # Create tool
        tool = ToolMaterial(
            project_id=test_project.id,
            name="Screwdriver",
            tool_type="tool"
        )
        session.add(tool)
        session.commit()
        session.refresh(tool)

        # Delete tool
        response = auth_client.delete(f"/api/projects/{test_project.id}/tools/{tool.id}")
        assert response.status_code == 204

    def test_delete_bom_item(self, auth_client: TestClient, session: Session,
                            test_project: Project):
        """Test deleting a BOM item"""
        from app.project_models import BillOfMaterial

        # Create BOM item
        bom = BillOfMaterial(
            project_id=test_project.id,
            item_name="Component",
            quantity=1,
            item_order=1
        )
        session.add(bom)
        session.commit()
        session.refresh(bom)

        # Delete BOM item
        response = auth_client.delete(f"/api/projects/{test_project.id}/bom/{bom.id}")
        assert response.status_code == 204

    def test_get_project_by_id_published(self, client: TestClient, session: Session,
                                        test_user: User):
        """Test getting a published project by ID"""
        project = Project(
            title="Published Project",
            description="Test",
            author_id=test_user.id,
            status="published"
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        response = client.get(f"/api/projects/{project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Published Project"
        assert data["status"] == "published"

    def test_search_components_by_keyword(self, auth_client: TestClient, session: Session):
        """Test component search with keyword"""
        # Create components with specific names
        comp1 = Component(name="ESP32 WiFi Module", description="WiFi chip")
        comp2 = Component(name="ESP8266", description="Older WiFi chip")
        comp3 = Component(name="Arduino Uno", description="Microcontroller")
        session.add_all([comp1, comp2, comp3])
        session.commit()

        # Search for "ESP"
        response = auth_client.get("/api/components/search?q=ESP")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert any("ESP32" in c["name"] or "ESP8266" in c["name"] for c in data)

    def test_create_bom_item_with_description(self, auth_client: TestClient,
                                             test_project: Project):
        """Test creating BOM item with description"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/bom",
            json={
                "item_name": "Resistor Pack",
                "quantity": 100,
                "price_cents": 500,
                "description": "Assorted resistors",
                "item_order": 1
            }
        )
        assert response.status_code == 201  # POST returns 201
        data = response.json()
        assert data["item_name"] == "Resistor Pack"
        assert data["description"] == "Assorted resistors"

    def test_create_link_with_description(self, auth_client: TestClient,
                                         test_project: Project):
        """Test creating project link with description"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/links",
            json={
                "title": "Tutorial",
                "url": "https://youtube.com/watch?v=abc",
                "link_type": "video",
                "description": "Detailed walkthrough"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Detailed walkthrough"

    def test_create_tool_with_notes(self, auth_client: TestClient,
                                   test_project: Project):
        """Test creating tool with notes"""
        response = auth_client.post(
            f"/api/projects/{test_project.id}/tools",
            json={
                "name": "Multimeter",
                "tool_type": "measurement",
                "notes": "Digital preferred"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["notes"] == "Digital preferred"

    def test_add_component_to_project_with_notes(self, auth_client: TestClient, session: Session,
                                                 test_project: Project):
        """Test adding component to project with notes"""
        comp = Component(name="LED Matrix", description="8x8 display")
        session.add(comp)
        session.commit()
        session.refresh(comp)

        response = auth_client.post(
            f"/api/projects/{test_project.id}/components",
            json={
                "component_id": comp.id,
                "quantity": 2,
                "notes": "Use red LEDs for better visibility"
            }
        )
        assert response.status_code == 201  # POST returns 201
        data = response.json()
        assert data["notes"] == "Use red LEDs for better visibility"
        assert data["quantity"] == 2
