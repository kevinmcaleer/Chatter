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
    title: str = Field(max_length=255, nullable=False, index=True)
    description: str = Field(sa_column_kwargs={"type_": "TEXT"}, nullable=False)
    author_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    status: str = Field(default="draft", max_length=20, nullable=False, index=True)  # 'draft' or 'published'
    background: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})  # Markdown
    code_link: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    primary_image_id: Optional[int] = Field(default=None, foreign_key="project_image.id")
    view_count: int = Field(default=0, nullable=False)
    download_count: int = Field(default=0, nullable=False)
    like_count: int = Field(default=0, nullable=False)
    comment_count: int = Field(default=0, nullable=False)

    # Relationships
    author: Optional["User"] = Relationship(back_populates="projects")
    tags: List["ProjectTag"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    steps: List["ProjectStep"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    bill_of_materials: List["BillOfMaterial"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    components: List["ProjectComponent"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    files: List["ProjectFile"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    images: List["ProjectImage"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    links: List["ProjectLink"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    tools_materials: List["ToolMaterial"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ProjectTag(SQLModel, table=True):
    """
    Category tags for projects (lowercase, user-defined)
    Multiple tags can be added per project
    """
    __tablename__ = "project_tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    tag_name: str = Field(max_length=100, nullable=False, index=True)

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
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    step_number: int = Field(nullable=False)
    title: str = Field(max_length=255, nullable=False)
    content: str = Field(sa_column_kwargs={"type_": "TEXT"}, nullable=False)  # Markdown
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

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
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    item_name: str = Field(max_length=255, nullable=False)
    description: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})
    quantity: int = Field(default=1, nullable=False)
    price_cents: Optional[int] = Field(default=None)  # Price in cents
    item_order: int = Field(default=0, nullable=False)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="bill_of_materials")


class Component(SQLModel, table=True):
    """
    Reusable electronic components database
    Used for autocomplete and linking projects
    """
    __tablename__ = "component"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, unique=True, nullable=False, index=True)
    description: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})
    datasheet_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    project_components: List["ProjectComponent"] = Relationship(back_populates="component")


class ProjectComponent(SQLModel, table=True):
    """
    Many-to-many relationship between projects and components
    Includes quantity and notes
    """
    __tablename__ = "project_component"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    component_id: int = Field(foreign_key="component.id", nullable=False, index=True)
    quantity: int = Field(default=1, nullable=False)
    notes: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})

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
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    filename: str = Field(max_length=255, nullable=False)  # Stored filename
    original_filename: str = Field(max_length=255, nullable=False)  # User's original filename
    file_size: int = Field(nullable=False)  # Size in bytes
    file_type: Optional[str] = Field(default=None, max_length=100)  # MIME type
    description: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="files")


class ProjectImage(SQLModel, table=True):
    """
    Image gallery for projects
    Supports drag-drop ordering, first image is primary
    """
    __tablename__ = "project_image"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    filename: str = Field(max_length=255, nullable=False)  # Stored filename
    original_filename: str = Field(max_length=255, nullable=False)  # User's original filename
    display_order: int = Field(default=0, nullable=False, index=True)
    caption: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="images")


class ProjectLink(SQLModel, table=True):
    """
    External resource links for projects
    YouTube videos, courses, articles, related projects
    """
    __tablename__ = "project_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    url: str = Field(max_length=500, nullable=False)
    title: str = Field(max_length=255, nullable=False)
    link_type: str = Field(max_length=50, nullable=False, index=True)  # 'resource', 'video', 'course', 'article', 'related_project'
    description: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="links")


class ToolMaterial(SQLModel, table=True):
    """
    Tools and materials used in projects
    """
    __tablename__ = "tool_material"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    name: str = Field(max_length=255, nullable=False)
    tool_type: str = Field(max_length=20, nullable=False)  # 'tool' or 'material'
    notes: Optional[str] = Field(default=None, sa_column_kwargs={"type_": "TEXT"})

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="tools_materials")
