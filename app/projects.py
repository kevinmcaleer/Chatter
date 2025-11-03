"""
User Projects API Router (Issue #15)
Handles project CRUD operations, publishing, and gallery views
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func
from typing import List, Optional
import logging
import os
import uuid
import zipfile
import io
from pathlib import Path
from datetime import datetime

from .database import get_session
from .auth import get_current_user, get_optional_user
from .models import User
from .storage import (
    check_nas_connection,
    save_file_to_nas, read_file_from_nas,
    save_file_to_local, read_file_from_local
)
from .config import (
    NAS_PROJECT_FILES_PATH, NAS_PROJECT_IMAGES_PATH,
    LOCAL_PROJECT_FILES_PATH, LOCAL_PROJECT_IMAGES_PATH,
    MAX_PROJECT_FILE_SIZE, MAX_PROJECT_IMAGE_SIZE,
    ALLOWED_PROJECT_FILE_EXTENSIONS, ALLOWED_PROJECT_IMAGE_EXTENSIONS
)
from .project_models import (
    Project, ProjectTag, ProjectStep, BillOfMaterial,
    Component, ProjectComponent, ProjectFile, ProjectImage,
    ProjectLink, ToolMaterial
)
from .project_schemas import (
    ProjectCreate, ProjectUpdate, ProjectDetail, ProjectSummary,
    ProjectGallery, ProjectPublish, ProjectTagRead, ProjectStepRead,
    ProjectStepCreate, ProjectStepUpdate,
    BillOfMaterialRead, BillOfMaterialCreate, BillOfMaterialUpdate,
    ProjectComponentRead, ProjectComponentCreate, ComponentRead, ComponentCreate,
    ProjectFileRead, ProjectImageRead,
    ProjectLinkRead, ProjectLinkCreate, ProjectLinkUpdate,
    ToolMaterialRead, ToolMaterialCreate, ToolMaterialUpdate
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new project (draft by default).
    Requires authentication.
    """
    logger.info(f"User {current_user.username} creating new project: {project_data.title}")

    # Create the project
    project = Project(
        title=project_data.title,
        description=project_data.description,
        author_id=current_user.id,
        status="draft",
        background=project_data.background,
        code_link=project_data.code_link
    )
    session.add(project)
    session.flush()  # Get the project ID

    # Add tags
    for tag_name in project_data.tags:
        tag = ProjectTag(project_id=project.id, tag_name=tag_name)
        session.add(tag)

    session.commit()
    session.refresh(project)

    logger.info(f"Project created: ID={project.id}, Title={project.title}")

    # Return detailed project data
    return _build_project_detail(project, current_user.username, session)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get detailed project information.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    # Increment view count for published projects
    if project.status == "published":
        project.view_count += 1
        session.add(project)
        session.commit()
        session.refresh(project)

    # Get author username
    author = session.get(User, project.author_id)
    author_username = author.username if author else "Unknown"

    return _build_project_detail(project, author_username, session)


@router.put("/projects/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update project details.
    Only the author can update their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own projects"
        )

    logger.info(f"User {current_user.username} updating project {project_id}")

    # Update fields
    if project_data.title is not None:
        project.title = project_data.title
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.background is not None:
        project.background = project_data.background
    if project_data.code_link is not None:
        project.code_link = project_data.code_link

    # Update tags if provided
    if project_data.tags is not None:
        # Remove existing tags
        existing_tags = session.exec(
            select(ProjectTag).where(ProjectTag.project_id == project_id)
        ).all()
        for tag in existing_tags:
            session.delete(tag)

        # Add new tags
        for tag_name in project_data.tags:
            tag = ProjectTag(project_id=project.id, tag_name=tag_name)
            session.add(tag)

    from datetime import datetime
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)

    return _build_project_detail(project, current_user.username, session)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a project.
    Only the author can delete their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own projects"
        )

    logger.info(f"User {current_user.username} deleting project {project_id}")

    session.delete(project)
    session.commit()


@router.post("/projects/{project_id}/publish", response_model=ProjectPublish)
def publish_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Publish a draft project (make it publicly visible).
    Only the author can publish their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only publish your own projects"
        )

    # Check if already published
    if project.status == "published":
        raise HTTPException(
            status_code=400,
            detail="Project is already published"
        )

    logger.info(f"User {current_user.username} publishing project {project_id}")

    project.status = "published"
    session.add(project)
    session.commit()

    return ProjectPublish(
        id=project.id,
        status=project.status,
        message="Project published successfully"
    )


@router.post("/projects/{project_id}/unpublish", response_model=ProjectPublish)
def unpublish_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Unpublish a project (revert to draft).
    Only the author can unpublish their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only unpublish your own projects"
        )

    # Check if already draft
    if project.status == "draft":
        raise HTTPException(
            status_code=400,
            detail="Project is already a draft"
        )

    logger.info(f"User {current_user.username} unpublishing project {project_id}")

    project.status = "draft"
    session.add(project)
    session.commit()

    return ProjectPublish(
        id=project.id,
        status=project.status,
        message="Project unpublished successfully"
    )


@router.get("/projects", response_model=ProjectGallery)
def list_projects(
    status_filter: Optional[str] = None,  # 'draft', 'published', or None for all
    tag: Optional[str] = None,
    author_id: Optional[int] = None,
    sort: str = "recent",  # 'recent', 'popular', 'views', 'downloads'
    page: int = 1,
    per_page: int = 20,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get paginated list of projects for gallery view.
    Filters: status, tag, author, sorting options.
    """
    # Build base query
    statement = select(Project)

    # Apply status filter
    if status_filter:
        if status_filter == "draft":
            # Only show drafts to their author
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required to view drafts")
            statement = statement.where(Project.status == "draft", Project.author_id == current_user.id)
        elif status_filter == "published":
            statement = statement.where(Project.status == "published")
    else:
        # Default: show published projects + user's own drafts if authenticated
        if current_user:
            statement = statement.where(
                (Project.status == "published") |
                ((Project.status == "draft") & (Project.author_id == current_user.id))
            )
        else:
            statement = statement.where(Project.status == "published")

    # Apply tag filter
    if tag:
        tag_subquery = select(ProjectTag.project_id).where(ProjectTag.tag_name == tag.lower())
        statement = statement.where(Project.id.in_(tag_subquery))

    # Apply author filter
    if author_id:
        statement = statement.where(Project.author_id == author_id)

    # Apply sorting
    if sort == "popular":
        statement = statement.order_by(Project.like_count.desc())
    elif sort == "views":
        statement = statement.order_by(Project.view_count.desc())
    elif sort == "downloads":
        statement = statement.order_by(Project.download_count.desc())
    else:  # recent (default)
        statement = statement.order_by(Project.created_at.desc())

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    # Apply pagination
    offset = (page - 1) * per_page
    statement = statement.offset(offset).limit(per_page)

    # Execute query
    projects = session.exec(statement).all()

    # Build summaries
    summaries = []
    for project in projects:
        author = session.get(User, project.author_id)
        author_username = author.username if author else "Unknown"

        # Get tags
        tags = session.exec(
            select(ProjectTag.tag_name).where(ProjectTag.project_id == project.id)
        ).all()

        # Get primary image URL if exists
        primary_image_url = None
        if project.primary_image_id:
            image = session.get(ProjectImage, project.primary_image_id)
            if image:
                primary_image_url = f"/projects/{project.id}/images/{image.filename}"

        summaries.append(ProjectSummary(
            id=project.id,
            title=project.title,
            description=project.description,
            author_id=project.author_id,
            author_username=author_username,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
            primary_image_url=primary_image_url,
            view_count=project.view_count,
            download_count=project.download_count,
            like_count=project.like_count,
            comment_count=project.comment_count,
            tags=tags
        ))

    # Calculate pagination info
    pages = (total + per_page - 1) // per_page

    return ProjectGallery(
        projects=summaries,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("/projects/{project_id}/steps", response_model=ProjectStepRead, status_code=status.HTTP_201_CREATED)
def create_project_step(
    project_id: int,
    step_data: ProjectStepCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new step to a project.
    Only the author can add steps to their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only add steps to your own projects"
        )

    # Check if step number already exists
    existing_step = session.exec(
        select(ProjectStep).where(
            ProjectStep.project_id == project_id,
            ProjectStep.step_number == step_data.step_number
        )
    ).first()

    if existing_step:
        raise HTTPException(
            status_code=400,
            detail=f"Step number {step_data.step_number} already exists for this project"
        )

    logger.info(f"User {current_user.username} adding step {step_data.step_number} to project {project_id}")

    step = ProjectStep(
        project_id=project_id,
        step_number=step_data.step_number,
        title=step_data.title,
        content=step_data.content
    )
    session.add(step)
    session.commit()
    session.refresh(step)

    return ProjectStepRead(
        id=step.id,
        step_number=step.step_number,
        title=step.title,
        content=step.content,
        created_at=step.created_at
    )


@router.get("/projects/{project_id}/steps", response_model=List[ProjectStepRead])
def list_project_steps(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all steps for a project.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    steps = session.exec(
        select(ProjectStep)
        .where(ProjectStep.project_id == project_id)
        .order_by(ProjectStep.step_number)
    ).all()

    return [
        ProjectStepRead(
            id=s.id,
            step_number=s.step_number,
            title=s.title,
            content=s.content,
            created_at=s.created_at
        )
        for s in steps
    ]


@router.put("/projects/{project_id}/steps/{step_id}", response_model=ProjectStepRead)
def update_project_step(
    project_id: int,
    step_id: int,
    step_data: ProjectStepUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a project step.
    Only the author can update steps in their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update steps in your own projects"
        )

    step = session.get(ProjectStep, step_id)
    if not step or step.project_id != project_id:
        raise HTTPException(status_code=404, detail="Step not found")

    logger.info(f"User {current_user.username} updating step {step_id} in project {project_id}")

    # Update fields
    if step_data.title is not None:
        step.title = step_data.title
    if step_data.content is not None:
        step.content = step_data.content

    session.add(step)
    session.commit()
    session.refresh(step)

    return ProjectStepRead(
        id=step.id,
        step_number=step.step_number,
        title=step.title,
        content=step.content,
        created_at=step.created_at
    )


@router.delete("/projects/{project_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_step(
    project_id: int,
    step_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a project step.
    Only the author can delete steps from their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete steps from your own projects"
        )

    step = session.get(ProjectStep, step_id)
    if not step or step.project_id != project_id:
        raise HTTPException(status_code=404, detail="Step not found")

    logger.info(f"User {current_user.username} deleting step {step_id} from project {project_id}")

    session.delete(step)
    session.commit()


@router.put("/projects/{project_id}/steps/reorder", response_model=List[ProjectStepRead])
def reorder_project_steps(
    project_id: int,
    step_order: List[int],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Reorder project steps.
    Provide a list of step IDs in the desired order.
    Only the author can reorder steps in their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only reorder steps in your own projects"
        )

    logger.info(f"User {current_user.username} reordering steps in project {project_id}")

    # Verify all step IDs belong to this project
    steps = session.exec(
        select(ProjectStep).where(ProjectStep.project_id == project_id)
    ).all()

    step_map = {s.id: s for s in steps}

    if len(step_order) != len(steps):
        raise HTTPException(
            status_code=400,
            detail="Step order list must include all steps"
        )

    for step_id in step_order:
        if step_id not in step_map:
            raise HTTPException(
                status_code=400,
                detail=f"Step {step_id} does not belong to this project"
            )

    # Update step numbers
    for new_number, step_id in enumerate(step_order, start=1):
        step = step_map[step_id]
        step.step_number = new_number
        session.add(step)

    session.commit()

    # Return updated steps in order
    updated_steps = session.exec(
        select(ProjectStep)
        .where(ProjectStep.project_id == project_id)
        .order_by(ProjectStep.step_number)
    ).all()

    return [
        ProjectStepRead(
            id=s.id,
            step_number=s.step_number,
            title=s.title,
            content=s.content,
            created_at=s.created_at
        )
        for s in updated_steps
    ]


@router.post("/projects/{project_id}/bom", response_model=BillOfMaterialRead, status_code=status.HTTP_201_CREATED)
def create_bom_item(
    project_id: int,
    bom_data: BillOfMaterialCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new item to the bill of materials.
    Only the author can add items to their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only add BOM items to your own projects"
        )

    logger.info(f"User {current_user.username} adding BOM item to project {project_id}")

    bom_item = BillOfMaterial(
        project_id=project_id,
        item_name=bom_data.item_name,
        description=bom_data.description,
        quantity=bom_data.quantity,
        price_cents=bom_data.price_cents,
        item_order=bom_data.item_order
    )
    session.add(bom_item)
    session.commit()
    session.refresh(bom_item)

    return BillOfMaterialRead(
        id=bom_item.id,
        item_name=bom_item.item_name,
        description=bom_item.description,
        quantity=bom_item.quantity,
        price_cents=bom_item.price_cents,
        item_order=bom_item.item_order
    )


@router.get("/projects/{project_id}/bom", response_model=List[BillOfMaterialRead])
def list_bom_items(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all bill of materials items for a project.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    bom_items = session.exec(
        select(BillOfMaterial)
        .where(BillOfMaterial.project_id == project_id)
        .order_by(BillOfMaterial.item_order)
    ).all()

    return [
        BillOfMaterialRead(
            id=b.id,
            item_name=b.item_name,
            description=b.description,
            quantity=b.quantity,
            price_cents=b.price_cents,
            item_order=b.item_order
        )
        for b in bom_items
    ]


@router.put("/projects/{project_id}/bom/{bom_id}", response_model=BillOfMaterialRead)
def update_bom_item(
    project_id: int,
    bom_id: int,
    bom_data: BillOfMaterialUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a bill of materials item.
    Only the author can update BOM items in their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update BOM items in your own projects"
        )

    bom_item = session.get(BillOfMaterial, bom_id)
    if not bom_item or bom_item.project_id != project_id:
        raise HTTPException(status_code=404, detail="BOM item not found")

    logger.info(f"User {current_user.username} updating BOM item {bom_id} in project {project_id}")

    # Update fields
    if bom_data.item_name is not None:
        bom_item.item_name = bom_data.item_name
    if bom_data.description is not None:
        bom_item.description = bom_data.description
    if bom_data.quantity is not None:
        bom_item.quantity = bom_data.quantity
    if bom_data.price_cents is not None:
        bom_item.price_cents = bom_data.price_cents
    if bom_data.item_order is not None:
        bom_item.item_order = bom_data.item_order

    session.add(bom_item)
    session.commit()
    session.refresh(bom_item)

    return BillOfMaterialRead(
        id=bom_item.id,
        item_name=bom_item.item_name,
        description=bom_item.description,
        quantity=bom_item.quantity,
        price_cents=bom_item.price_cents,
        item_order=bom_item.item_order
    )


@router.delete("/projects/{project_id}/bom/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bom_item(
    project_id: int,
    bom_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a bill of materials item.
    Only the author can delete BOM items from their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete BOM items from your own projects"
        )

    bom_item = session.get(BillOfMaterial, bom_id)
    if not bom_item or bom_item.project_id != project_id:
        raise HTTPException(status_code=404, detail="BOM item not found")

    logger.info(f"User {current_user.username} deleting BOM item {bom_id} from project {project_id}")

    session.delete(bom_item)
    session.commit()


@router.get("/components/search", response_model=List[ComponentRead])
def search_components(
    q: str,
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Search for components by name (autocomplete).
    Returns matching components for reuse across projects.
    """
    if len(q) < 2:
        return []

    components = session.exec(
        select(Component)
        .where(Component.name.ilike(f"%{q}%"))
        .limit(limit)
    ).all()

    return [
        ComponentRead(
            id=c.id,
            name=c.name,
            description=c.description,
            datasheet_url=c.datasheet_url,
            created_at=c.created_at
        )
        for c in components
    ]


@router.post("/components", response_model=ComponentRead, status_code=status.HTTP_201_CREATED)
def create_component(
    component_data: ComponentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new reusable component.
    Requires authentication.
    """
    # Check if component already exists
    existing = session.exec(
        select(Component).where(Component.name == component_data.name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Component with this name already exists"
        )

    logger.info(f"User {current_user.username} creating component: {component_data.name}")

    component = Component(
        name=component_data.name,
        description=component_data.description,
        datasheet_url=component_data.datasheet_url
    )
    session.add(component)
    session.commit()
    session.refresh(component)

    return ComponentRead(
        id=component.id,
        name=component.name,
        description=component.description,
        datasheet_url=component.datasheet_url,
        created_at=component.created_at
    )


@router.post("/projects/{project_id}/components", response_model=ProjectComponentRead, status_code=status.HTTP_201_CREATED)
def add_component_to_project(
    project_id: int,
    component_data: ProjectComponentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Add a component to a project.
    Only the author can add components to their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only add components to your own projects"
        )

    # Verify component exists
    component = session.get(Component, component_data.component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    # Check if already added
    existing = session.exec(
        select(ProjectComponent).where(
            ProjectComponent.project_id == project_id,
            ProjectComponent.component_id == component_data.component_id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Component already added to this project"
        )

    logger.info(f"User {current_user.username} adding component {component_data.component_id} to project {project_id}")

    project_component = ProjectComponent(
        project_id=project_id,
        component_id=component_data.component_id,
        quantity=component_data.quantity,
        notes=component_data.notes
    )
    session.add(project_component)
    session.commit()
    session.refresh(project_component)

    return ProjectComponentRead(
        id=project_component.id,
        component=ComponentRead(
            id=component.id,
            name=component.name,
            description=component.description,
            datasheet_url=component.datasheet_url,
            created_at=component.created_at
        ),
        quantity=project_component.quantity,
        notes=project_component.notes
    )


@router.get("/projects/{project_id}/components", response_model=List[ProjectComponentRead])
def list_project_components(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all components for a project.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    project_components = session.exec(
        select(ProjectComponent).where(ProjectComponent.project_id == project_id)
    ).all()

    result = []
    for pc in project_components:
        component = session.get(Component, pc.component_id)
        if component:
            result.append(ProjectComponentRead(
                id=pc.id,
                component=ComponentRead(
                    id=component.id,
                    name=component.name,
                    description=component.description,
                    datasheet_url=component.datasheet_url,
                    created_at=component.created_at
                ),
                quantity=pc.quantity,
                notes=pc.notes
            ))

    return result


@router.delete("/projects/{project_id}/components/{project_component_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_component_from_project(
    project_id: int,
    project_component_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a component from a project.
    Only the author can remove components from their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only remove components from your own projects"
        )

    project_component = session.get(ProjectComponent, project_component_id)
    if not project_component or project_component.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project component not found")

    logger.info(f"User {current_user.username} removing component {project_component_id} from project {project_id}")

    session.delete(project_component)
    session.commit()


@router.post("/projects/{project_id}/links", response_model=ProjectLinkRead, status_code=status.HTTP_201_CREATED)
def create_project_link(
    project_id: int,
    link_data: ProjectLinkCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new link to a project.
    Only the author can add links to their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only add links to your own projects"
        )

    logger.info(f"User {current_user.username} adding link to project {project_id}")

    link = ProjectLink(
        project_id=project_id,
        url=link_data.url,
        title=link_data.title,
        link_type=link_data.link_type,
        description=link_data.description
    )
    session.add(link)
    session.commit()
    session.refresh(link)

    return ProjectLinkRead(
        id=link.id,
        url=link.url,
        title=link.title,
        link_type=link.link_type,
        description=link.description
    )


@router.get("/projects/{project_id}/links", response_model=List[ProjectLinkRead])
def list_project_links(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all links for a project.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    links = session.exec(
        select(ProjectLink).where(ProjectLink.project_id == project_id)
    ).all()

    return [
        ProjectLinkRead(
            id=l.id,
            url=l.url,
            title=l.title,
            link_type=l.link_type,
            description=l.description
        )
        for l in links
    ]


@router.put("/projects/{project_id}/links/{link_id}", response_model=ProjectLinkRead)
def update_project_link(
    project_id: int,
    link_id: int,
    link_data: ProjectLinkUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a project link.
    Only the author can update links in their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update links in your own projects"
        )

    link = session.get(ProjectLink, link_id)
    if not link or link.project_id != project_id:
        raise HTTPException(status_code=404, detail="Link not found")

    logger.info(f"User {current_user.username} updating link {link_id} in project {project_id}")

    # Update fields
    if link_data.url is not None:
        link.url = link_data.url
    if link_data.title is not None:
        link.title = link_data.title
    if link_data.link_type is not None:
        link.link_type = link_data.link_type
    if link_data.description is not None:
        link.description = link_data.description

    session.add(link)
    session.commit()
    session.refresh(link)

    return ProjectLinkRead(
        id=link.id,
        url=link.url,
        title=link.title,
        link_type=link.link_type,
        description=link.description
    )


@router.delete("/projects/{project_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_link(
    project_id: int,
    link_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a project link.
    Only the author can delete links from their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete links from your own projects"
        )

    link = session.get(ProjectLink, link_id)
    if not link or link.project_id != project_id:
        raise HTTPException(status_code=404, detail="Link not found")

    logger.info(f"User {current_user.username} deleting link {link_id} from project {project_id}")

    session.delete(link)
    session.commit()


@router.post("/projects/{project_id}/tools", response_model=ToolMaterialRead, status_code=status.HTTP_201_CREATED)
def create_tool_material(
    project_id: int,
    tool_data: ToolMaterialCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new tool or material to a project.
    Only the author can add tools/materials to their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only add tools/materials to your own projects"
        )

    logger.info(f"User {current_user.username} adding tool/material to project {project_id}")

    tool = ToolMaterial(
        project_id=project_id,
        name=tool_data.name,
        tool_type=tool_data.tool_type,
        notes=tool_data.notes
    )
    session.add(tool)
    session.commit()
    session.refresh(tool)

    return ToolMaterialRead(
        id=tool.id,
        name=tool.name,
        tool_type=tool.tool_type,
        notes=tool.notes
    )


@router.get("/projects/{project_id}/tools", response_model=List[ToolMaterialRead])
def list_tools_materials(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all tools and materials for a project.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    tools = session.exec(
        select(ToolMaterial).where(ToolMaterial.project_id == project_id)
    ).all()

    return [
        ToolMaterialRead(
            id=t.id,
            name=t.name,
            tool_type=t.tool_type,
            notes=t.notes
        )
        for t in tools
    ]


@router.put("/projects/{project_id}/tools/{tool_id}", response_model=ToolMaterialRead)
def update_tool_material(
    project_id: int,
    tool_id: int,
    tool_data: ToolMaterialUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a tool or material.
    Only the author can update tools/materials in their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update tools/materials in your own projects"
        )

    tool = session.get(ToolMaterial, tool_id)
    if not tool or tool.project_id != project_id:
        raise HTTPException(status_code=404, detail="Tool/material not found")

    logger.info(f"User {current_user.username} updating tool/material {tool_id} in project {project_id}")

    # Update fields
    if tool_data.name is not None:
        tool.name = tool_data.name
    if tool_data.tool_type is not None:
        tool.tool_type = tool_data.tool_type
    if tool_data.notes is not None:
        tool.notes = tool_data.notes

    session.add(tool)
    session.commit()
    session.refresh(tool)

    return ToolMaterialRead(
        id=tool.id,
        name=tool.name,
        tool_type=tool.tool_type,
        notes=tool.notes
    )


@router.delete("/projects/{project_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool_material(
    project_id: int,
    tool_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a tool or material.
    Only the author can delete tools/materials from their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete tools/materials from your own projects"
        )

    tool = session.get(ToolMaterial, tool_id)
    if not tool or tool.project_id != project_id:
        raise HTTPException(status_code=404, detail="Tool/material not found")

    logger.info(f"User {current_user.username} deleting tool/material {tool_id} from project {project_id}")

    session.delete(tool)
    session.commit()


@router.post("/projects/{project_id}/files", response_model=ProjectFileRead, status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    project_id: int,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file to a project.
    Only the author can upload files to their project.
    Max file size: 25MB
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only upload files to your own projects"
        )

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_PROJECT_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_PROJECT_FILE_EXTENSIONS)}"
        )

    # Read and check file size
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_PROJECT_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_PROJECT_FILE_SIZE / 1024 / 1024}MB"
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"

    # Try to save to NAS first, fallback to local
    saved_to_nas = False
    if check_nas_connection():
        if save_file_to_nas(contents, unique_filename, NAS_PROJECT_FILES_PATH):
            saved_to_nas = True
            logger.info(f"Saved file to NAS: {unique_filename}")
        else:
            logger.warning("NAS save failed, trying local storage...")

    if not saved_to_nas:
        if not save_file_to_local(contents, unique_filename, LOCAL_PROJECT_FILES_PATH):
            raise HTTPException(
                status_code=500,
                detail="Failed to save file to storage"
            )
        logger.info(f"Saved file to local storage: {unique_filename}")

    logger.info(f"User {current_user.username} uploaded file {file.filename} ({file_size} bytes) to project {project_id}")

    # Create database record
    project_file = ProjectFile(
        project_id=project_id,
        filename=unique_filename,  # UUID filename for storage
        original_filename=file.filename,  # User's original filename
        file_size=file_size,
        file_type=file.content_type,
        description=f"{title}: {description}" if description else title
    )
    session.add(project_file)
    session.commit()
    session.refresh(project_file)

    return ProjectFileRead(
        id=project_file.id,
        filename=project_file.filename,
        original_filename=project_file.original_filename,
        file_size=project_file.file_size,
        file_type=project_file.file_type,
        description=project_file.description,
        uploaded_at=project_file.uploaded_at
    )


@router.get("/projects/{project_id}/files", response_model=List[ProjectFileRead])
def list_project_files(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all files for a project.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    files = session.exec(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.uploaded_at.desc())
    ).all()

    return [
        ProjectFileRead(
            id=f.id,
            filename=f.filename,
            file_size=f.file_size,
            title=f.title,
            description=f.description,
            uploaded_at=f.uploaded_at
        )
        for f in files
    ]


@router.delete("/projects/{project_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_file(
    project_id: int,
    file_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a project file.
    Only the author can delete files from their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete files from your own projects"
        )

    project_file = session.get(ProjectFile, file_id)
    if not project_file or project_file.project_id != project_id:
        raise HTTPException(status_code=404, detail="File not found")

    logger.info(f"User {current_user.username} deleting file {file_id} from project {project_id}")

    # Delete physical file
    try:
        # Delete from NAS first, fallback to local
        file_deleted = False
        if check_nas_connection():
            from .storage import save_file_to_nas
            # TODO: Implement delete_file_from_nas function
            pass

        # Try local storage
        local_path = LOCAL_PROJECT_FILES_PATH / project_file.filename
        if local_path.exists():
            local_path.unlink()
            file_deleted = True
    except Exception as e:
        logger.error(f"Error deleting physical file: {e}")

    # Delete database record
    session.delete(project_file)
    session.commit()


@router.post("/projects/{project_id}/images", response_model=ProjectImageRead, status_code=status.HTTP_201_CREATED)
async def upload_project_image(
    project_id: int,
    image: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an image to a project.
    Only the author can upload images to their project.
    Max image size: 10MB
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only upload images to your own projects"
        )

    # Check file extension
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in ALLOWED_PROJECT_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Image type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_PROJECT_IMAGE_EXTENSIONS)}"
        )

    # Read and check file size
    contents = await image.read()
    file_size = len(contents)

    if file_size > MAX_PROJECT_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Max size: {MAX_PROJECT_IMAGE_SIZE / 1024 / 1024}MB"
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"

    # Try to save to NAS first, fallback to local
    saved_to_nas = False
    if check_nas_connection():
        if save_file_to_nas(contents, unique_filename, NAS_PROJECT_IMAGES_PATH):
            saved_to_nas = True
            logger.info(f"Saved image to NAS: {unique_filename}")
        else:
            logger.warning("NAS save failed, trying local storage...")

    if not saved_to_nas:
        if not save_file_to_local(contents, unique_filename, LOCAL_PROJECT_IMAGES_PATH):
            raise HTTPException(
                status_code=500,
                detail="Failed to save image to storage"
            )
        logger.info(f"Saved image to local storage: {unique_filename}")

    logger.info(f"User {current_user.username} uploaded image {image.filename} ({file_size} bytes) to project {project_id}")

    # Create database record
    project_image = ProjectImage(
        project_id=project_id,
        filename=unique_filename,  # UUID filename for storage
        original_filename=image.filename,  # User's original filename
        caption=caption
    )
    session.add(project_image)
    session.commit()
    session.refresh(project_image)

    return ProjectImageRead(
        id=project_image.id,
        filename=project_image.filename,
        image_url=f"/api/projects/{project_id}/images/{project_image.id}/file",
        caption=project_image.caption,
        uploaded_at=project_image.uploaded_at
    )


@router.get("/projects/{project_id}/images", response_model=List[ProjectImageRead])
def list_project_images(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all images for a project.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    images = session.exec(
        select(ProjectImage)
        .where(ProjectImage.project_id == project_id)
        .order_by(ProjectImage.uploaded_at.desc())
    ).all()

    return [
        ProjectImageRead(
            id=img.id,
            filename=img.filename,
            image_url=f"/api/projects/{project_id}/images/{img.id}/file",
            caption=img.caption,
            uploaded_at=img.uploaded_at
        )
        for img in images
    ]


@router.put("/projects/{project_id}/images/{image_id}/primary", response_model=ProjectDetail)
def set_primary_image(
    project_id: int,
    image_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Set an image as the primary image for a project.
    Only the author can set the primary image.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only set primary image for your own projects"
        )

    # Verify image belongs to this project
    image = session.get(ProjectImage, image_id)
    if not image or image.project_id != project_id:
        raise HTTPException(status_code=404, detail="Image not found")

    logger.info(f"User {current_user.username} setting image {image_id} as primary for project {project_id}")

    # Update project
    project.primary_image_id = image_id
    session.add(project)
    session.commit()
    session.refresh(project)

    # Get author username
    author = session.get(User, project.author_id)
    return _build_project_detail(project, author.username, session)


@router.delete("/projects/{project_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_image(
    project_id: int,
    image_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a project image.
    Only the author can delete images from their project.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check authorization
    if project.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete images from your own projects"
        )

    project_image = session.get(ProjectImage, image_id)
    if not project_image or project_image.project_id != project_id:
        raise HTTPException(status_code=404, detail="Image not found")

    # Check if it's the primary image
    if project.primary_image_id == image_id:
        project.primary_image_id = None
        session.add(project)

    logger.info(f"User {current_user.username} deleting image {image_id} from project {project_id}")

    # Delete physical file
    try:
        # Delete from NAS first, fallback to local
        image_deleted = False
        if check_nas_connection():
            # TODO: Implement delete_file_from_nas function
            pass

        # Try local storage
        local_path = LOCAL_PROJECT_IMAGES_PATH / project_image.filename
        if local_path.exists():
            local_path.unlink()
            image_deleted = True
    except Exception as e:
        logger.error(f"Error deleting physical image: {e}")

    # Delete database record
    session.delete(project_image)
    session.commit()


@router.get("/projects/{project_id}/download")
async def download_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Download a complete project as a ZIP file with auto-generated README.
    Includes all files, images, and project metadata.
    Published projects are public, drafts only visible to author.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions for draft projects
    if project.status == "draft":
        if not current_user or current_user.id != project.author_id:
            raise HTTPException(
                status_code=403,
                detail="Draft projects are only visible to their authors"
            )

    logger.info(f"Generating ZIP download for project {project_id}")

    # Get author
    author = session.get(User, project.author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Project author not found")

    # Generate README content
    readme_content = _generate_readme(project, author, session)

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add README.md
        zip_file.writestr('README.md', readme_content)

        # Add all project files
        files = session.exec(
            select(ProjectFile).where(ProjectFile.project_id == project_id)
        ).all()

        for file in files:
            # Try to read from NAS first, fallback to local
            file_content = None
            if check_nas_connection():
                file_content = read_file_from_nas(file.filename, NAS_PROJECT_FILES_PATH)

            if not file_content:
                file_content = read_file_from_local(file.filename, LOCAL_PROJECT_FILES_PATH)

            if file_content:
                # Add to files/ subdirectory with original filename
                arcname = f"files/{file.original_filename}"
                zip_file.writestr(arcname, file_content)
            else:
                logger.warning(f"Could not read file {file.filename} for project {project_id}")

        # Add all project images
        images = session.exec(
            select(ProjectImage).where(ProjectImage.project_id == project_id)
        ).all()

        for image in images:
            # Try to read from NAS first, fallback to local
            image_content = None
            if check_nas_connection():
                image_content = read_file_from_nas(image.filename, NAS_PROJECT_IMAGES_PATH)

            if not image_content:
                image_content = read_file_from_local(image.filename, LOCAL_PROJECT_IMAGES_PATH)

            if image_content:
                # Add to images/ subdirectory with original filename
                arcname = f"images/{image.original_filename}"
                zip_file.writestr(arcname, image_content)
            else:
                logger.warning(f"Could not read image {image.filename} for project {project_id}")

    # Increment download count
    project.download_count += 1
    session.add(project)
    session.commit()

    logger.info(f"ZIP generated successfully for project {project_id} ({project.download_count} downloads)")

    # Prepare ZIP for download
    zip_buffer.seek(0)

    # Create safe filename from project title
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in project.title)
    safe_title = safe_title.replace(' ', '_')
    filename = f"{safe_title}_project.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


def _generate_readme(project: Project, author: User, session: Session) -> str:
    """
    Generate a comprehensive README.md file for the project.
    Includes all project metadata, steps, BOM, components, and resources.
    """
    lines = []

    # Title and description
    lines.append(f"# {project.title}\n")
    lines.append(f"{project.description}\n")

    # Metadata
    lines.append(f"**Author:** {author.username}")
    lines.append(f"**Created:** {project.created_at.strftime('%Y-%m-%d')}")
    lines.append(f"**Last Updated:** {project.updated_at.strftime('%Y-%m-%d')}\n")

    # Tags
    tags = session.exec(
        select(ProjectTag).where(ProjectTag.project_id == project.id)
    ).all()
    if tags:
        tag_list = ", ".join([f"`{tag.tag_name}`" for tag in tags])
        lines.append(f"**Tags:** {tag_list}\n")

    # Background story (if provided)
    if project.background:
        lines.append("## Background\n")
        lines.append(f"{project.background}\n")

    # Code repository link (if provided)
    if project.code_link:
        lines.append(f"**Source Code:** {project.code_link}\n")

    # Build steps
    steps = session.exec(
        select(ProjectStep)
        .where(ProjectStep.project_id == project.id)
        .order_by(ProjectStep.step_number)
    ).all()

    if steps:
        lines.append("## Build Instructions\n")
        for step in steps:
            lines.append(f"### Step {step.step_number}: {step.title}\n")
            lines.append(f"{step.content}\n")

    # Bill of Materials
    bom_items = session.exec(
        select(BillOfMaterial)
        .where(BillOfMaterial.project_id == project.id)
        .order_by(BillOfMaterial.item_order)
    ).all()

    if bom_items:
        lines.append("## Bill of Materials\n")
        lines.append("| Item | Quantity | Price | Description |")
        lines.append("|------|----------|-------|-------------|")
        for item in bom_items:
            price = f"${item.price_cents / 100:.2f}" if item.price_cents else "N/A"
            desc = item.description or ""
            lines.append(f"| {item.item_name} | {item.quantity} | {price} | {desc} |")
        lines.append("")

    # Electronic Components
    project_components = session.exec(
        select(ProjectComponent).where(ProjectComponent.project_id == project.id)
    ).all()

    if project_components:
        lines.append("## Electronic Components\n")
        lines.append("| Component | Quantity | Notes | Datasheet |")
        lines.append("|-----------|----------|-------|-----------|")
        for pc in project_components:
            component = session.get(Component, pc.component_id)
            if component:
                notes = pc.notes or ""
                datasheet = component.datasheet_url if component.datasheet_url else "N/A"
                lines.append(f"| {component.name} | {pc.quantity} | {notes} | {datasheet} |")
        lines.append("")

    # Tools and Materials
    tools = session.exec(
        select(ToolMaterial).where(ToolMaterial.project_id == project.id)
    ).all()

    if tools:
        lines.append("## Required Tools & Materials\n")
        for tool in tools:
            notes = f" - {tool.notes}" if tool.notes else ""
            lines.append(f"- **{tool.name}** ({tool.tool_type}){notes}")
        lines.append("")

    # Links and Resources
    links = session.exec(
        select(ProjectLink).where(ProjectLink.project_id == project.id)
    ).all()

    if links:
        lines.append("## Additional Resources\n")
        for link in links:
            desc = f" - {link.description}" if link.description else ""
            lines.append(f"- [{link.title}]({link.url}) ({link.link_type}){desc}")
        lines.append("")

    # Files included in ZIP
    files = session.exec(
        select(ProjectFile).where(ProjectFile.project_id == project.id)
    ).all()

    if files:
        lines.append("## Included Files\n")
        lines.append("All project files are included in the `files/` directory:")
        for file in files:
            desc = f" - {file.description}" if file.description else ""
            size_mb = file.file_size / (1024 * 1024)
            lines.append(f"- **{file.title}** (`{file.filename}`, {size_mb:.2f} MB){desc}")
        lines.append("")

    # Images included in ZIP
    images = session.exec(
        select(ProjectImage).where(ProjectImage.project_id == project.id)
    ).all()

    if images:
        lines.append("## Project Images\n")
        lines.append("All project images are included in the `images/` directory:")
        for image in images:
            caption = f" - {image.caption}" if image.caption else ""
            lines.append(f"- `{image.filename}`{caption}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"\n*Downloaded from Kev's Robots on {datetime.utcnow().strftime('%Y-%m-%d')}*")
    lines.append(f"\nThis project was created by {author.username}.")
    lines.append("For more projects and tutorials, visit https://kevsrobots.com")

    return "\n".join(lines)


def _build_project_detail(project: Project, author_username: str, session: Session) -> ProjectDetail:
    """Helper function to build complete project detail response"""

    # Get tags
    tags = session.exec(
        select(ProjectTag).where(ProjectTag.project_id == project.id)
    ).all()

    # Get steps
    steps = session.exec(
        select(ProjectStep)
        .where(ProjectStep.project_id == project.id)
        .order_by(ProjectStep.step_number)
    ).all()

    # Get bill of materials
    bom = session.exec(
        select(BillOfMaterial)
        .where(BillOfMaterial.project_id == project.id)
        .order_by(BillOfMaterial.item_order)
    ).all()

    # Get components with details
    project_components = session.exec(
        select(ProjectComponent)
        .where(ProjectComponent.project_id == project.id)
    ).all()

    components_list = []
    for pc in project_components:
        component = session.get(Component, pc.component_id)
        if component:
            components_list.append(ProjectComponentRead(
                id=pc.id,
                component=ComponentRead(
                    id=component.id,
                    name=component.name,
                    description=component.description,
                    datasheet_url=component.datasheet_url,
                    created_at=component.created_at
                ),
                quantity=pc.quantity,
                notes=pc.notes
            ))

    # Get files
    files = session.exec(
        select(ProjectFile).where(ProjectFile.project_id == project.id)
    ).all()

    # Get images
    images = session.exec(
        select(ProjectImage)
        .where(ProjectImage.project_id == project.id)
        .order_by(ProjectImage.display_order)
    ).all()

    # Get links
    links = session.exec(
        select(ProjectLink).where(ProjectLink.project_id == project.id)
    ).all()

    # Get tools/materials
    tools_materials = session.exec(
        select(ToolMaterial).where(ToolMaterial.project_id == project.id)
    ).all()

    return ProjectDetail(
        id=project.id,
        title=project.title,
        description=project.description,
        author_id=project.author_id,
        author_username=author_username,
        status=project.status,
        background=project.background,
        code_link=project.code_link,
        created_at=project.created_at,
        updated_at=project.updated_at,
        view_count=project.view_count,
        download_count=project.download_count,
        like_count=project.like_count,
        comment_count=project.comment_count,
        tags=[ProjectTagRead(id=t.id, tag_name=t.tag_name) for t in tags],
        steps=[ProjectStepRead(
            id=s.id,
            step_number=s.step_number,
            title=s.title,
            content=s.content,
            created_at=s.created_at
        ) for s in steps],
        bill_of_materials=[BillOfMaterialRead(
            id=b.id,
            item_name=b.item_name,
            description=b.description,
            quantity=b.quantity,
            price_cents=b.price_cents,
            item_order=b.item_order
        ) for b in bom],
        components=components_list,
        files=[ProjectFileRead(
            id=f.id,
            filename=f.filename,
            original_filename=f.original_filename,
            file_size=f.file_size,
            file_type=f.file_type,
            description=f.description,
            uploaded_at=f.uploaded_at
        ) for f in files],
        images=[ProjectImageRead(
            id=i.id,
            filename=i.filename,
            original_filename=i.original_filename,
            display_order=i.display_order,
            caption=i.caption,
            uploaded_at=i.uploaded_at
        ) for i in images],
        links=[ProjectLinkRead(
            id=l.id,
            url=l.url,
            title=l.title,
            link_type=l.link_type,
            description=l.description
        ) for l in links],
        tools_materials=[ToolMaterialRead(
            id=tm.id,
            name=tm.name,
            tool_type=tm.tool_type,
            notes=tm.notes
        ) for tm in tools_materials]
    )
