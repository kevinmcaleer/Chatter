"""
User Projects API Router (Issue #15)
Handles project CRUD operations, publishing, and gallery views
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from typing import List, Optional
import logging

from .database import get_session
from .auth import get_current_user, get_optional_user
from .models import User
from .project_models import (
    Project, ProjectTag, ProjectStep, BillOfMaterial,
    Component, ProjectComponent, ProjectFile, ProjectImage,
    ProjectLink, ToolMaterial
)
from .project_schemas import (
    ProjectCreate, ProjectUpdate, ProjectDetail, ProjectSummary,
    ProjectGallery, ProjectPublish, ProjectTagRead, ProjectStepRead,
    BillOfMaterialRead, ProjectComponentRead, ProjectFileRead,
    ProjectImageRead, ProjectLinkRead, ToolMaterialRead, ComponentRead
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
