"""
Pydantic schemas for User Projects API (Issue #15)
Request/response models for project endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


# Tag Schemas
class ProjectTagCreate(BaseModel):
    tag_name: str = Field(..., max_length=100, description="Category tag (lowercase)")

    @validator('tag_name')
    def tag_must_be_lowercase(cls, v):
        return v.lower().strip()


class ProjectTagRead(BaseModel):
    id: int
    tag_name: str


# Step Schemas
class ProjectStepCreate(BaseModel):
    step_number: int = Field(..., ge=1, description="Step number (1-based)")
    title: str = Field(..., max_length=255)
    content: str = Field(..., description="Markdown content")


class ProjectStepUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None


class ProjectStepRead(BaseModel):
    id: int
    step_number: int
    title: str
    content: str
    created_at: datetime


# Bill of Materials Schemas
class BillOfMaterialCreate(BaseModel):
    item_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    price_cents: Optional[int] = Field(None, ge=0, description="Price in cents")
    item_order: int = Field(default=0, ge=0)


class BillOfMaterialUpdate(BaseModel):
    item_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=1)
    price_cents: Optional[int] = Field(None, ge=0)
    item_order: Optional[int] = Field(None, ge=0)


class BillOfMaterialRead(BaseModel):
    id: int
    item_name: str
    description: Optional[str]
    quantity: int
    price_cents: Optional[int]
    item_order: int


# Component Schemas
class ComponentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    datasheet_url: Optional[str] = Field(None, max_length=500)


class ComponentRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    datasheet_url: Optional[str]
    created_at: datetime


class ProjectComponentCreate(BaseModel):
    component_id: int
    quantity: int = Field(default=1, ge=1)
    notes: Optional[str] = None


class ProjectComponentRead(BaseModel):
    id: int
    component: ComponentRead
    quantity: int
    notes: Optional[str]


# File Schemas
class ProjectFileRead(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: Optional[str]
    description: Optional[str]
    uploaded_at: datetime


# Image Schemas
class ProjectImageCreate(BaseModel):
    display_order: int = Field(default=0, ge=0)
    caption: Optional[str] = None


class ProjectImageUpdate(BaseModel):
    display_order: Optional[int] = Field(None, ge=0)
    caption: Optional[str] = None


class ProjectImageRead(BaseModel):
    id: int
    filename: str
    original_filename: str
    display_order: int
    caption: Optional[str]
    uploaded_at: datetime


# Link Schemas
class ProjectLinkCreate(BaseModel):
    url: str = Field(..., max_length=500)
    title: str = Field(..., max_length=255)
    link_type: str = Field(..., regex="^(resource|video|course|article|related_project)$")
    description: Optional[str] = None


class ProjectLinkUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=500)
    title: Optional[str] = Field(None, max_length=255)
    link_type: Optional[str] = Field(None, regex="^(resource|video|course|article|related_project)$")
    description: Optional[str] = None


class ProjectLinkRead(BaseModel):
    id: int
    url: str
    title: str
    link_type: str
    description: Optional[str]


# Tool/Material Schemas
class ToolMaterialCreate(BaseModel):
    name: str = Field(..., max_length=255)
    tool_type: str = Field(..., regex="^(tool|material)$")
    notes: Optional[str] = None


class ToolMaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    tool_type: Optional[str] = Field(None, regex="^(tool|material)$")
    notes: Optional[str] = None


class ToolMaterialRead(BaseModel):
    id: int
    name: str
    tool_type: str
    notes: Optional[str]


# Project Create/Update Schemas
class ProjectCreate(BaseModel):
    """Schema for creating a new project (draft by default)"""
    title: str = Field(..., max_length=255, min_length=1)
    description: str = Field(..., min_length=1)
    tags: List[str] = Field(..., min_items=1, description="At least one tag required")
    background: Optional[str] = None
    code_link: Optional[str] = Field(None, max_length=500)

    @validator('tags')
    def tags_must_be_lowercase(cls, v):
        return [tag.lower().strip() for tag in v]


class ProjectUpdate(BaseModel):
    """Schema for updating project fields"""
    title: Optional[str] = Field(None, max_length=255, min_length=1)
    description: Optional[str] = Field(None, min_length=1)
    background: Optional[str] = None
    code_link: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None

    @validator('tags')
    def tags_must_be_lowercase(cls, v):
        if v is not None:
            return [tag.lower().strip() for tag in v]
        return v


# Project Read Schemas
class ProjectSummary(BaseModel):
    """Lightweight project summary for gallery/list views"""
    id: int
    title: str
    description: str
    author_id: int
    author_username: str
    status: str
    created_at: datetime
    updated_at: datetime
    primary_image_url: Optional[str] = None
    view_count: int
    download_count: int
    like_count: int
    comment_count: int
    tags: List[str]


class ProjectDetail(BaseModel):
    """Complete project details with all related data"""
    id: int
    title: str
    description: str
    author_id: int
    author_username: str
    status: str
    background: Optional[str]
    code_link: Optional[str]
    created_at: datetime
    updated_at: datetime
    view_count: int
    download_count: int
    like_count: int
    comment_count: int

    # Related data
    tags: List[ProjectTagRead]
    steps: List[ProjectStepRead]
    bill_of_materials: List[BillOfMaterialRead]
    components: List[ProjectComponentRead]
    files: List[ProjectFileRead]
    images: List[ProjectImageRead]
    links: List[ProjectLinkRead]
    tools_materials: List[ToolMaterialRead]


# Gallery/List Response
class ProjectGallery(BaseModel):
    """Paginated project gallery response"""
    projects: List[ProjectSummary]
    total: int
    page: int
    per_page: int
    pages: int


# Publish/Status Change
class ProjectPublish(BaseModel):
    """Response when publishing a project"""
    id: int
    status: str
    message: str


# Statistics
class ProjectStats(BaseModel):
    """Project statistics for dashboard"""
    total_projects: int
    published_projects: int
    draft_projects: int
    total_views: int
    total_downloads: int
    total_likes: int
    total_comments: int
