from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session, select
from .models import PageView
from .schemas import PageViewCreate, PageViewStats, PageViewTimeline, PageViewTimelineDataPoint
from .database import get_session
from typing import Optional, Literal
from sqlalchemy import func, text
from datetime import datetime, timedelta

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

@router.options("/page-view")
def page_view_options():
    """Handle preflight OPTIONS request for page-view"""
    return {}

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
    Queries live pageview table for real-time accuracy
    """
    # Strip leading slash to match storage format
    url = url.lstrip('/')

    # Query live pageview table directly for real-time counts
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
    Get the most viewed pages from live pageview table
    Returns URLs sorted by view count (highest to lowest)
    """
    # Query live pageview table for real-time most viewed pages
    query = text("""
        SELECT
            url,
            COUNT(*) as view_count,
            COUNT(DISTINCT ip_address) as unique_visitors,
            MAX(viewed_at) as last_viewed_at
        FROM pageview
        GROUP BY url
        ORDER BY view_count DESC
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


@router.get("/page-views/{url:path}/timeline", response_model=PageViewTimeline)
def get_page_view_timeline(
    url: str,
    period: Literal["weekly", "monthly", "annual"] = Query(default="weekly"),
    session: Session = Depends(get_session)
):
    """
    Get page view timeline data for graphing.

    Returns time-series data grouped by day or month depending on period:
    - weekly: Last 7 days, grouped by day
    - monthly: Last 30 days, grouped by day
    - annual: Last 12 months, grouped by month

    Available to all users (no authentication required)
    """
    # Strip leading slash to match storage format
    url = url.lstrip('/')

    # Calculate date range based on period
    now = datetime.utcnow()

    if period == "weekly":
        start_date = now - timedelta(days=6)  # Last 7 days including today
        date_format = "%Y-%m-%d"
        group_by_format = "DATE(viewed_at)"

    elif period == "monthly":
        start_date = now - timedelta(days=29)  # Last 30 days including today
        date_format = "%Y-%m-%d"
        group_by_format = "DATE(viewed_at)"

    else:  # annual
        start_date = now - timedelta(days=364)  # Last 12 months including current
        date_format = "%Y-%m"
        group_by_format = "DATE_TRUNC('month', viewed_at)"

    # Query database for view counts grouped by date
    if period in ["weekly", "monthly"]:
        query = text("""
            SELECT
                DATE(viewed_at) as date,
                COUNT(*) as count
            FROM pageview
            WHERE url = :url
              AND viewed_at >= :start_date
            GROUP BY DATE(viewed_at)
            ORDER BY date
        """)
    else:  # annual
        query = text("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', viewed_at), 'YYYY-MM') as date,
                COUNT(*) as count
            FROM pageview
            WHERE url = :url
              AND viewed_at >= :start_date
            GROUP BY DATE_TRUNC('month', viewed_at)
            ORDER BY DATE_TRUNC('month', viewed_at)
        """)

    result = session.execute(query, {"url": url, "start_date": start_date})
    rows = result.fetchall()

    # Create a dict of dates to counts for easy lookup
    view_counts = {str(row[0]): row[1] for row in rows}

    # Generate complete date range with labels
    data_points = []
    total_views = 0

    if period == "weekly":
        # Last 7 days with day labels (M, T, W, T, F, S, S)
        day_labels = ["M", "T", "W", "T", "F", "S", "S"]
        for i in range(7):
            date = start_date + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            count = view_counts.get(date_str, 0)
            total_views += count

            data_points.append(PageViewTimelineDataPoint(
                date=date_str,
                label=day_labels[date.weekday()],
                count=count
            ))

    elif period == "monthly":
        # Last 30 days with day of month labels
        for i in range(30):
            date = start_date + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            count = view_counts.get(date_str, 0)
            total_views += count

            data_points.append(PageViewTimelineDataPoint(
                date=date_str,
                label=str(date.day),
                count=count
            ))

    else:  # annual
        # Last 12 months with month labels (Jan, Feb, etc.)
        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for i in range(12):
            date = (start_date.replace(day=1) + timedelta(days=32 * i)).replace(day=1)
            date_str = date.strftime("%Y-%m")
            count = view_counts.get(date_str, 0)
            total_views += count

            data_points.append(PageViewTimelineDataPoint(
                date=date_str,
                label=month_labels[date.month - 1],
                count=count
            ))

    return PageViewTimeline(
        url=url,
        period=period,
        data=data_points,
        total_views=total_views
    )
