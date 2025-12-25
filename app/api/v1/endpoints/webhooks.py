"""
Webhook endpoints for receiving Supabase authentication events.
"""
import os
import traceback
from fastapi import APIRouter, Header, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.user import User

load_dotenv()

router = APIRouter()

# Webhook authentication token from environment
WEBHOOK_TOKEN = os.getenv("WEBHOOK_SECRET")


@router.post("/supabase/user-created")
async def handle_user_created(
    request: Request,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle user creation webhook from Supabase Auth.
    
    Synchronizes user data from Supabase to the local database.
    Uses Bearer token authentication via Authorization header.
    
    Authorization Header Format:
        Authorization: Bearer <WEBHOOK_SECRET>
    """
    try:
        print("\n" + "-" * 70)
        print("WEBHOOK RECEIVED - User Creation Event")
        print("-" * 70)
        
        # Validate authorization header
        if not authorization:
            print("[ERROR] Missing Authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header"
            )
        
        # Extract and validate Bearer token format
        if not authorization.startswith("Bearer "):
            print("[ERROR] Invalid Authorization format. Expected: 'Bearer <token>'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization format"
            )
        
        token = authorization.replace("Bearer ", "")
        
        # Validate token value
        if token != WEBHOOK_TOKEN:
            print("[ERROR] Invalid webhook token")
            print(f"  Expected: {WEBHOOK_TOKEN[:10]}...")
            print(f"  Received: {token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token"
            )
        
        print("[SUCCESS] Authentication validation passed")
        
        # Read and parse payload
        body = await request.body()
        body_str = body.decode('utf-8')
        print(f"[INFO] Payload size: {len(body)} bytes")
        
        import json
        payload = json.loads(body_str)
        
        print(f"[INFO] Event type: {payload.get('type')}")
        print(f"[INFO] Table: {payload.get('table')}")
        print(f"[INFO] Schema: {payload.get('schema')}")
        
        # Validate event type is INSERT
        if payload.get("type") != "INSERT":
            print(f"[SKIP] Event ignored - Not an INSERT event: {payload.get('type')}")
            return {"status": "ignored", "reason": "Not an INSERT event"}
        
        # Extract user record from payload
        record = payload.get("record")
        if not record:
            print("[ERROR] Missing 'record' in payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'record' in payload"
            )
        
        supabase_user_id = record.get("id")
        email = record.get("email")
        
        print(f"[USER DATA]")
        print(f"  Supabase ID: {supabase_user_id}")
        print(f"  Email: {email}")
        
        if not supabase_user_id or not email:
            print("[ERROR] Missing user ID or email in record")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing user ID or email in record"
            )
        
        # Check if user already exists (idempotency)
        print("[DB] Checking for existing user...")
        result = await db.execute(
            select(User).where(User.supabase_user_id == supabase_user_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"[SKIP] User already exists in database: {email} (ID: {existing_user.id})")
            return {
                "status": "already_exists",
                "user_id": existing_user.id,
                "email": existing_user.email
            }
        
        # Create new user in database
        print("[DB] Creating new user in database...")
        new_user = User(
            supabase_user_id=supabase_user_id,
            email=email,
            role="user",
            is_active=True,
            rate_limit_tier="free",
            usage_count=0
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        print(f"[SUCCESS] User successfully synced")
        print(f"  Email: {email}")
        print(f"  Database ID: {new_user.id}")
        print(f"  Supabase ID: {new_user.supabase_user_id}")
        print("-" * 70 + "\n")
        
        return {
            "status": "created",
            "user_id": new_user.id,
            "email": new_user.email,
            "supabase_user_id": new_user.supabase_user_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[ERROR] Unexpected error in webhook handler")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print(f"\n[TRACEBACK]")
        traceback.print_exc()
        print("-" * 70 + "\n")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhook service."""
    return {
        "status": "healthy",
        "webhook_token_configured": bool(WEBHOOK_TOKEN),
        "authentication_method": "Bearer token"
    }
