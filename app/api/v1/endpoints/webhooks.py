"""
Webhook endpoints for receiving Supabase authentication events.
"""
import os
import hmac
import hashlib
import traceback
from fastapi import APIRouter, Header, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.user import User

load_dotenv()

router = APIRouter()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify webhook authenticity using HMAC-SHA256.
    
    Supabase sends the signature in hex format directly.
    Uses timing-safe comparison to prevent timing attacks.
    
    Args:
        payload: Request body as bytes
        signature: X-Webhook-Signature header from Supabase
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not WEBHOOK_SECRET:
        print("[WARNING] WEBHOOK_SECRET not configured")
        return False
    
    # Calculate HMAC of payload using SHA-256
    expected_signature = hmac.new(
        key=WEBHOOK_SECRET.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    print("[SIGNATURE VERIFICATION]")
    print(f"  Expected: {expected_signature[:30]}...")
    print(f"  Received: {signature[:30]}...")
    print(f"  Secret length: {len(WEBHOOK_SECRET)} chars")
    print(f"  Payload length: {len(payload)} bytes")
    print(f"  Match: {hmac.compare_digest(expected_signature, signature)}")
    
    # Timing-safe comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


@router.post("/supabase/user-created")
async def handle_user_created(
    request: Request,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle user creation webhook from Supabase Auth.
    
    Syncs user data from Supabase to the local database.
    
    Expected Supabase webhook payload:
    {
        "type": "INSERT",
        "table": "users",
        "schema": "auth",
        "record": {
            "id": "user-uuid",
            "email": "user@example.com",
            "created_at": "2024-12-24T..."
        },
        "old_record": null
    }
    """
    try:
        print("\n" + "-" * 70)
        print("WEBHOOK RECEIVED - User Creation Event")
        print("-" * 70)
        
        # Read raw body for signature validation
        body = await request.body()
        print(f"[INFO] Body length: {len(body)} bytes")
        
        # Validate webhook signature (security)
        if not x_webhook_signature:
            print("[ERROR] Missing X-Webhook-Signature header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Webhook-Signature header"
            )
        
        if not verify_webhook_signature(body, x_webhook_signature):
            print("[ERROR] Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        print("[SUCCESS] Signature validation passed")
        
        # Parse JSON payload
        payload = await request.json()
        print(f"[INFO] Event type: {payload.get('type')}")
        print(f"[INFO] Event table: {payload.get('table')}")
        
        # Validate payload structure
        if payload.get("type") != "INSERT":
            print(f"[INFO] Event ignored - Type: {payload.get('type')}")
            return {"status": "ignored", "reason": "Not an INSERT event"}
        
        record = payload.get("record")
        if not record:
            print("[ERROR] Missing 'record' in payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'record' in payload"
            )
        
        supabase_user_id = record.get("id")
        email = record.get("email")
        
        print(f"[INFO] User data:")
        print(f"       - ID: {supabase_user_id}")
        print(f"       - Email: {email}")
        
        if not supabase_user_id or not email:
            print("[ERROR] Missing 'id' or 'email' in record")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'id' or 'email' in record"
            )
        
        # Check if user already exists (idempotency)
        print("[PROCESS] Checking if user exists...")
        result = await db.execute(
            select(User).where(User.supabase_user_id == supabase_user_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"[INFO] User already exists: {email} (ID: {existing_user.id})")
            return {
                "status": "already_exists",
                "user_id": existing_user.id,
                "email": existing_user.email
            }
        
        # Create user in database
        print("[PROCESS] Creating new user in database...")
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
        
        print(f"[SUCCESS] User synced: {email} (ID: {new_user.id})")
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
        print(f"\n[ERROR] Exception in webhook handler:")
        print(f"        Type: {type(e).__name__}")
        print(f"        Message: {str(e)}")
        print(f"\n[DEBUG] Full traceback:")
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
        "webhook_secret_configured": bool(WEBHOOK_SECRET)
    }
