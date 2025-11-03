"""
SQLModel models for User Projects (Issue #15)
Contains all project-related database models
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .models import User


class Project(SQLModel, table=True):
    """
    Core project table with mandatory and optional fields
    Users can create, manage and publish their projects
    """
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255, index=True)
    description: str = Field(nullable=False)
    author_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="draft", max_length=20, index=True)  # 'draft' or 'published'
    background: Optional[str] = Field(default=None)  # Markdown
    code_link: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    primary_image_id: Optional[int] = Field(default=None, foreign_key="project_image.id")
    view_count: int = Field(default=0)
    download_count: int = Field(default=0)
    like_count: int = Field(default=0)
    comment_count: int = Field(default=0)

    # Relationships
    author: Optional["User"] = Relationship(back_populates="projects")
    tags: List["ProjectTag"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    steps: List["ProjectStep"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    bill_of_materials: List["BillOfMaterial"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    components: List["ProjectComponent"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    files: List["ProjectFile"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    images: List["ProjectImage"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "foreign_keys": "[ProjectImage.project_id]"
        }
    )
    links: List["ProjectLink"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    tools_materials: List["ToolMaterial"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ProjectTag(SQLModel, table=True):
    """
    Category tags for projects (lowercase, user-defined)
    Multiple tags can be added per project
    """
    __tablename__ = "project_tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    tag_name: str = Field(max_length=100, index=True)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="tags")

    class Config:
        unique_together = [("project_id", "tag_name")]


class ProjectStep(SQLModel, table=True):
    """
    Sequential instruction steps for projects
    Each step has a number, title, and markdown content
    """
    __tablename__ = "project_step"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    step_number: int = Field(nullable=False)
    title: str = Field(max_length=255)
    content: str = Field(nullable=False)  # Markdown
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="steps")

    class Config:
        unique_together = [("project_id", "step_number")]


class BillOfMaterial(SQLModel, table=True):
    """
    Bill of materials for projects
    Items with description, quantity, and optional price
    """
    __tablename__ = "bill_of_material"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    item_name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    quantity: int = Field(default=1)
    price_cents: Optional[int] = Field(default=None)  # Price in cents
    item_order: int = Field(default=0)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="bill_of_materials")


class Component(SQLModel, table=True):
    """
    Reusable electronic components database
    Used for autocomplete and linking projects
    """
    __tablename__ = "component"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, unique=True, index=True)
    description: Optional[str] = Field(default=None)
    datasheet_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project_components: List["ProjectComponent"] = Relationship(back_populates="component")


class ProjectComponent(SQLModel, table=True):
    """
    Many-to-many relationship between projects and components
    Includes quantity and notes
    """
    __tablename__ = "project_component"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    component_id: int = Field(foreign_key="component.id", index=True)
    quantity: int = Field(default=1)
    notes: Optional[str] = Field(default=None)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="components")
    component: Optional["Component"] = Relationship(back_populates="project_components")

    class Config:
        unique_together = [("project_id", "component_id")]


class ProjectFile(SQLModel, table=True):
    """
    Downloadable files for projects (STL, PDFs, code, etc.)
    25MB limit per project enforced in application
    """
    __tablename__ = "project_file"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    filename: str = Field(max_length=255)  # Stored filename
    original_filename: str = Field(max_length=255)  # User's original filename
    file_size: int = Field(nullable=False)  # Size in bytes
    file_type: Optional[str] = Field(default=None, max_length=100)  # MIME type
    description: Optional[str] = Field(default=None)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="files")


class ProjectImage(SQLModel, table=True):
    """
    Image gallery for projects
    Supports drag-drop ordering, first image is primary
    """
    __tablename__ = "project_image"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    filename: str = Field(max_length=255)  # Stored filename
    original_filename: str = Field(max_length=255)  # User's original filename
    display_order: int = Field(default=0, index=True)
    caption: Optional[str] = Field(default=None)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Optional["Project"] = Relationship(
        back_populates="images",
        sa_relationship_kwargs={"foreign_keys": "[ProjectImage.project_id]"}
    )


class ProjectLink(SQLModel, table=True):
    """
    External resource links for projects
    YouTube videos, courses, articles, related projects
    """
    __tablename__ = "project_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    url: str = Field(max_length=500)
    title: str = Field(max_length=255)
    link_type: str = Field(max_length=50, index=True)  # 'resource', 'video', 'course', 'article', 'related_project'
    description: Optional[str] = Field(default=None)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="links")


class ToolMaterial(SQLModel, table=True):
    """
    Tools and materials used in projects
    """
    __tablename__ = "tool_material"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    name: str = Field(max_length=255)
    tool_type: str = Field(max_length=20)  # 'tool' or 'material'
    notes: Optional[str] = Field(default=None)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="tools_materials")
