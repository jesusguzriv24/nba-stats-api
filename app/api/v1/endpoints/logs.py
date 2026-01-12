from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.api_key import APIKey
from app.models.api_usage_log import APIUsageLog
from app.schemas.api_usage_log import APIUsageLogResponse

router = APIRouter()

@router.get("/logs", response_model=List[APIUsageLogResponse])
async def get_api_usage_logs(
    api_key_id: int = Query(..., description="ID of the API Key to fetch logs for"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint path (exact match)"),
    http_method: Optional[str] = Query(None, description="Filter by HTTP method (e.g., GET, POST)"),
    status_code: Optional[int] = Query(None, description="Filter by HTTP status code"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[datetime] = Query(None, description="Filter logs created after this date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter logs created before this date (inclusive)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get API usage logs for a specific API Key owned by the authenticated user.
    
    Returns a list of logs filtered by various criteria.
    
    Requires:
        - Valid Supabase JWT in Authorization header OR
        - Valid API key in X-API-Key header
    """
    # 1. Verify that the api_key_id belongs to the current user
    api_key_result = await db.execute(
        select(APIKey).where(
            APIKey.id == api_key_id,
            APIKey.user_id == user.id
        )
    )
    api_key = api_key_result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found or does not belong to the user"
        )

    # 2. Build the query for APIUsageLog
    query = select(APIUsageLog).where(APIUsageLog.api_key_id == api_key_id)

    if endpoint:
        query = query.where(APIUsageLog.endpoint == endpoint)
    
    if http_method:
        query = query.where(APIUsageLog.http_method == http_method)
        
    if status_code:
        query = query.where(APIUsageLog.status_code == status_code)
        
    if ip_address:
        query = query.where(APIUsageLog.ip_address == ip_address)
        
    if start_date:
        query = query.where(APIUsageLog.created_at >= start_date)
        
    if end_date:
        query = query.where(APIUsageLog.created_at <= end_date)

    # 3. Apply pagination and ordering
    query = query.order_by(APIUsageLog.created_at.desc()).offset(skip).limit(limit)

    # 4. Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    return logs
