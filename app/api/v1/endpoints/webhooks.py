"""
Webhook endpoints for receiving Supabase authentication events.

Updated to work with the new subscription system. When a user is created
in Supabase, this webhook creates the corresponding user record in our
database and automatically assigns them to the free plan.
"""
import os
import traceback
from fastapi import APIRouter, Header, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription

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
    
    This webhook is triggered by Supabase when a new user signs up.
    It synchronizes the user data to our local database and automatically
    creates a free subscription for them.
    
    Flow:
    1. Validate webhook authentication token
    2. Extract user data from Supabase payload
    3. Check if user already exists (idempotency)
    4. Create user record in our database
    5. Create free subscription for the new user
    6. Return success response
    
    Authentication:
    Uses Bearer token authentication via Authorization header.
    Authorization Header Format: Authorization: Bearer {WEBHOOK_SECRET}
    
    Webhook Setup in Supabase:
    1. Go to Authentication > Webhooks in Supabase Dashboard
    2. Create webhook for "user.created" event
    3. Set URL to: https://your-api.com/api/v1/webhooks/supabase/user-created
    4. Set secret to match WEBHOOK_SECRET in your .env
    
    Args:
        request (Request): FastAPI request object
        authorization (str): Authorization header with Bearer token
        db (AsyncSession): Database session
        
    Returns:
        dict: Status and user information
        
    Raises:
        HTTPException 401: If authorization token is invalid
        HTTPException 400: If payload is invalid or missing data
        HTTPException 500: If internal error occurs
    """
    try:
        print("\n" + "=" * 70)
        print("WEBHOOK RECEIVED - User Creation Event")
        print("-" * 70)
        
        # Validate authorization token
        if not authorization:
            print("[ERROR] No Authorization header provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header"
            )
        
        # Extract token from "Bearer {token}" format
        if not authorization.startswith("Bearer "):
            print("[ERROR] Invalid Authorization header format")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected: Bearer {token}"
            )
        
        provided_token = authorization.replace("Bearer ", "").strip()
        
        # Verify token matches configured webhook secret
        if not WEBHOOK_TOKEN:
            print("[ERROR] WEBHOOK_SECRET not configured in environment")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook authentication not configured"
            )
        
        if provided_token != WEBHOOK_TOKEN:
            print("[ERROR] Invalid webhook token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token"
            )
        
        print("[AUTH] Webhook token validated successfully")
        
        # Read and parse payload
        body = await request.body()
        body_str = body.decode("utf-8")
        print(f"[INFO] Payload size: {len(body)} bytes")
        
        import json
        payload = json.loads(body_str)
        
        print(f"[INFO] Event type: {payload.get('type')}")
        print(f"[INFO] Table: {payload.get('table')}")
        print(f"[INFO] Schema: {payload.get('schema')}")
        
        # Validate event type is INSERT (user creation)
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
        
        # Check if user already exists (idempotency - webhook may be called multiple times)
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
            is_active=True
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        print(f"[SUCCESS] User successfully created")
        print(f"  Email: {email}")
        print(f"  Database ID: {new_user.id}")
        print(f"  Supabase ID: {new_user.supabase_user_id}")
        
        # Get the free plan
        print("[DB] Assigning free subscription to new user...")
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_name == "free")
        )
        free_plan = result.scalar_one_or_none()
        
        if not free_plan:
            print("[WARNING] Free plan not found in database - user created without subscription")
            print("          Please ensure subscription plans are seeded in database")
        else:
            # Create free subscription for new user
            now = datetime.now()
            
            # Free plan has no expiration (set to 100 years in future)
            free_subscription = UserSubscription(
                user_id=new_user.id,
                plan_id=free_plan.id,
                status="active",
                billing_cycle="monthly",
                subscribed_at=now,
                current_period_start=now,
                current_period_end=now + timedelta(days=36500),  # ~100 years
                price_paid_cents=0,
                auto_renew=False  # Free plan doesn't auto-renew
            )
            
            db.add(free_subscription)
            await db.commit()
            await db.refresh(free_subscription)
            
            print(f"[SUCCESS] Free subscription created (ID: {free_subscription.id})")
        
        print("-" * 70)
        
        return {
            "status": "created",
            "user_id": new_user.id,
            "email": new_user.email,
            "supabase_user_id": new_user.supabase_user_id,
            "subscription": "free" if free_plan else "none"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (authentication failures, validation errors)
        raise
        
    except Exception as e:
        # Catch any unexpected errors
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
    """
    Health check endpoint for webhook service.
    
    Use this to verify the webhook service is running and configured.
    
    Returns:
        dict: Health status and configuration info
    """
    return {
        "status": "healthy",
        "webhook_token_configured": bool(WEBHOOK_TOKEN),
        "authentication_method": "Bearer token"
    }
