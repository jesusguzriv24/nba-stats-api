from typing import List, Optional
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.api_usage_log import APIUsageLog
from app.schemas.api_usage_log import APIUsageLogResponse

router = APIRouter()

@router.get("/", response_model=List[APIUsageLogResponse])
async def list_api_logs(
    request: Request,
    user_id: Optional[int] = Query(None, description="Filter by User ID"),
    api_key_id: Optional[int] = Query(None, description="Filter by API Key ID"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint path (exact match)"),
    http_method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[date] = Query(None, description="Filter logs on or after this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter logs on or before this date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List API usage logs with various filters.
    
    Requires authentication.
    """
    # Optional: Add check for admin privileges if needed
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="Not authorized")

    stmt = select(APIUsageLog)

    if user_id is not None:
        stmt = stmt.where(APIUsageLog.user_id == user_id)
    
    if api_key_id is not None:
        stmt = stmt.where(APIUsageLog.api_key_id == api_key_id)

    if endpoint is not None:
        stmt = stmt.where(APIUsageLog.endpoint == endpoint)

    if http_method is not None:
        stmt = stmt.where(APIUsageLog.http_method == http_method)

    if status_code is not None:
        stmt = stmt.where(APIUsageLog.status_code == status_code)
    
    if ip_address is not None:
        stmt = stmt.where(APIUsageLog.ip_address == ip_address)

    if start_date:
        stmt = stmt.where(APIUsageLog.created_at >= start_date)
    
    if end_date:
        # To include the entire end_date, we might want to go up to the end of that day.
        # But simple comparison with date obj usually treats it as 00:00:00 of that day.
        # If we want inclusive end date, we should probably add 1 day or cast to date.
        # For simplicity and performance on 'created_at' (DateTime), let's compare dates directly if DB supports,
        # or handle it carefully.
        # Using a simple hack: check if date part <= end_date. 
        # But SQLAlchemy efficient way: cast(APIUsageLog.created_at, Date) <= end_date
        # Or just: APIUsageLog.created_at < end_date + 1 day
        # Let's stick effectively to "created_at < (end_date + 1 day)" logic manually or use generic >= date.
        # Actually, for 'created_at' (timestamp), if I say <= 2023-01-01, it means <= 2023-01-01 00:00:00.
        # So it excludes the day itself effectively if there are times.
        # Let's add 1 day to end_date to make it inclusive.
        import datetime as dt
        next_day = end_date + dt.timedelta(days=1)
        stmt = stmt.where(APIUsageLog.created_at < next_day)

    # Apply ordering (newest first usually makes sense for logs)
    stmt = stmt.order_by(APIUsageLog.created_at.desc())

    # Pagination
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    return logs
