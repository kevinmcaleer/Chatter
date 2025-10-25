from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select
from .models import PageView
from .schemas import PageViewCreate, PageViewStats
from .database import get_session
from typing import Optional
from sqlalchemy import func, text
from datetime import datetime

router = APIRouter()

def format_count(count: int) -> str:
    """
    Format count with K/M suffix
    - Under 1,000: show exact number
    - 1,000-999,999: show as 1k, 1.1k, etc
    - 1,000,000+: show as 1M, 1.1M, etc
    """
    if count < 1000:
        return str(count)
    elif count < 1000000:
        if count < 10000:
            # Show one decimal place for 1.0k-9.9k
            return f"{count/1000:.1f}k"
        else:
            # Show whole number for 10k+
            return f"{int(count/1000)}k"
    else:
        if count < 10000000:
            # Show one decimal place for 1.0M-9.9M
            return f"{count/1000000:.1f}M"
        else:
            # Show whole number for 10M+
            return f"{int(count/1000000)}M"

@router.post("/page-view")
def log_page_view(
    page_view: PageViewCreate,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Log a page view
    Available to all users (no authentication required)
    """
    # Strip leading slash from URL to normalize storage
    url = page_view.url.lstrip('/')

    # Get real IP address from headers (nginx/proxy) or direct connection
    ip_address = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()

    new_view = PageView(
        url=url,
        ip_address=ip_address,
        user_agent=page_view.user_agent
    )
    session.add(new_view)
    session.commit()

    return {"message": "Page view logged", "url": url}

@router.get("/page-views/{url:path}", response_model=PageViewStats)
def get_page_view_stats(
    url: str,
    session: Session = Depends(get_session)
):
    """
    Get page view statistics for a URL
    Returns total views, unique visitors, and formatted count
    Available to all users (no authentication required)
    """
    # Query from materialized view for better performance
    query = text("""
        SELECT view_count, unique_visitors, last_viewed_at
        FROM page_view_counts
        WHERE url = :url
    """)

    result = session.execute(query, {"url": url}).first()

    if result:
        view_count = result[0]
        unique_visitors = result[1]
        last_viewed_at = result[2]
    else:
        # Fall back to live count if not in materialized view
        view_count = session.exec(
            select(func.count()).where(PageView.url == url)
        ).one()
        unique_visitors = session.exec(
            select(func.count(func.distinct(PageView.ip_address))).where(PageView.url == url)
        ).one()
        last_viewed_at = session.exec(
            select(func.max(PageView.viewed_at)).where(PageView.url == url)
        ).one()

    return PageViewStats(
        url=url,
        view_count=view_count,
        view_count_formatted=format_count(view_count),
        unique_visitors=unique_visitors,
        last_viewed_at=last_viewed_at
    )

@router.post("/refresh-page-view-counts")
def refresh_page_view_counts(session: Session = Depends(get_session)):
    """
    Refresh the materialized view for page view counts
    Should be called periodically to keep the view up to date
    """
    try:
        session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY page_view_counts"))
        session.commit()
        return {"message": "Page view counts refreshed successfully"}
    except Exception as e:
        return {"message": f"Error refreshing view: {str(e)}", "status": "error"}

@router.get("/most-viewed")
def get_most_viewed(limit: int = 10, session: Session = Depends(get_session)):
    """
    Get the most viewed pages from the materialized view
    Returns URLs sorted by view count (highest to lowest)
    """
    query = text("""
        SELECT url, view_count, unique_visitors, last_viewed_at
        FROM page_view_counts
        LIMIT :limit
    """)

    result = session.execute(query, {"limit": limit})

    return [
        {
            "url": row[0],
            "view_count": row[1],
            "view_count_formatted": format_count(row[1]),
            "unique_visitors": row[2],
            "last_viewed_at": row[3].isoformat() if row[3] else None
        }
        for row in result
    ]
