"""
Webhook endpoints for receiving Supabase authentication events.
"""
import os
import hmac
import hashlib
import base64
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


def verify_webhook_signature_multi(payload: bytes, signature: str, raw_payload_str: str = None) -> bool:
    """
    Verify webhook signature using multiple HMAC methods.
    
    Supabase may use different signature formats (hex, base64, v2 format).
    This function tests all common methods to ensure compatibility.
    
    Args:
        payload: Request body as bytes
        signature: X-Webhook-Signature header value
        raw_payload_str: Decoded payload string for v2 format
        
    Returns:
        bool: True if signature is valid using any method
    """
    if not WEBHOOK_SECRET:
        print("[WARNING] WEBHOOK_SECRET not configured")
        return False
    
    print("[SIGNATURE VERIFICATION] Testing multiple methods")
    print(f"  Secret length: {len(WEBHOOK_SECRET)} chars")
    print(f"  Secret (first 10): {WEBHOOK_SECRET[:10]}...")
    print(f"  Payload length: {len(payload)} bytes")
    print(f"  Received signature: {signature[:30]}...")
    
    # Method 1: HMAC-SHA256 hex format
    method1 = hmac.new(
        key=WEBHOOK_SECRET.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    print(f"\n  [Method 1] HMAC-SHA256 -> Hex:")
    print(f"    Calculated: {method1[:30]}...")
    print(f"    Match: {hmac.compare_digest(method1, signature)}")
    if hmac.compare_digest(method1, signature):
        return True
    
    # Method 2: HMAC-SHA256 base64 format
    method2_bytes = hmac.new(
        key=WEBHOOK_SECRET.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).digest()
    method2 = base64.b64encode(method2_bytes).decode('utf-8')
    print(f"\n  [Method 2] HMAC-SHA256 -> Base64:")
    print(f"    Calculated: {method2[:30]}...")
    print(f"    Match: {hmac.compare_digest(method2, signature)}")
    if hmac.compare_digest(method2, signature):
        return True
    
    # Method 3: Secret decoded from base64
    try:
        secret_decoded = base64.b64decode(WEBHOOK_SECRET)
        method3 = hmac.new(
            key=secret_decoded,
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        print(f"\n  [Method 3] Secret as Base64 -> HMAC-SHA256 -> Hex:")
        print(f"    Calculated: {method3[:30]}...")
        print(f"    Match: {hmac.compare_digest(method3, signature)}")
        if hmac.compare_digest(method3, signature):
            return True
    except Exception:
        print(f"\n  [Method 3] Secret not valid base64, skipping")
    
    # Method 4: Signature as base64
    try:
        signature_decoded = base64.b64decode(signature)
        signature_hex = signature_decoded.hex()
        print(f"\n  [Method 4] Signature as Base64:")
        print(f"    Decoded to hex: {signature_hex[:30]}...")
        print(f"    Match with method 1: {hmac.compare_digest(method1, signature_hex)}")
        if hmac.compare_digest(method1, signature_hex):
            return True
    except Exception:
        print(f"\n  [Method 4] Signature not valid base64")
    
    # Method 5: Supabase v2 format (timestamp.signature)
    try:
        if ',' in signature:
            parts = signature.split(',')
            if len(parts) == 3:
                version, timestamp, sig = parts
                print(f"\n  [Method 5] Supabase v2 format detected:")
                print(f"    Version: {version}")
                print(f"    Timestamp: {timestamp}")
                print(f"    Signature: {sig[:30]}...")
                
                # Construct signed payload: timestamp + "." + body
                signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
                expected_sig = hmac.new(
                    key=WEBHOOK_SECRET.encode('utf-8'),
                    msg=signed_payload.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).hexdigest()
                
                print(f"    Calculated: {expected_sig[:30]}...")
                print(f"    Match: {hmac.compare_digest(expected_sig, sig)}")
                if hmac.compare_digest(expected_sig, sig):
                    return True
    except Exception:
        print(f"\n  [Method 5] Not Supabase v2 format")
    
    print(f"\n  [ERROR] All verification methods failed")
    return False


@router.post("/supabase/user-created")
async def handle_user_created(
    request: Request,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle user creation webhook from Supabase Auth.
    
    Syncs user data from Supabase to the local database.
    Ensures idempotency by checking for duplicate entries.
    """
    try:
        print("\n" + "-" * 70)
        print("WEBHOOK RECEIVED - User Creation Event")
        print("-" * 70)
        
        # Read raw body for signature validation
        body = await request.body()
        body_str = body.decode('utf-8')
        print(f"[INFO] Payload size: {len(body)} bytes")
        
        # Debug: show payload preview
        print(f"[DEBUG] Payload preview: {body_str[:200]}...")
        
        # Validate webhook signature
        if not x_webhook_signature:
            print("[ERROR] Missing X-Webhook-Signature header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Webhook-Signature header"
            )
        
        if not verify_webhook_signature_multi(body, x_webhook_signature, body_str):
            print("[ERROR] Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        print("[SUCCESS] Signature validation passed")
        
        # Parse JSON payload
        import json
        payload = json.loads(body_str)
        print(f"[INFO] Event type: {payload.get('type')}")
        print(f"[INFO] Event table: {payload.get('table')}")
        
        # Validate payload structure
        if payload.get("type") != "INSERT":
            print(f"[SKIP] Event type not INSERT: {payload.get('type')}")
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
        
        print(f"[USER DATA]")
        print(f"  ID: {supabase_user_id}")
        print(f"  Email: {email}")
        
        if not supabase_user_id or not email:
            print("[ERROR] Missing 'id' or 'email' in record")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'id' or 'email' in record"
            )
        
        # Check if user already exists (idempotency)
        print("[DB] Querying for existing user...")
        result = await db.execute(
            select(User).where(User.supabase_user_id == supabase_user_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"[SKIP] User already exists: {email} (ID: {existing_user.id})")
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
        
        print(f"[SUCCESS] User synced via webhook: {email} (ID: {new_user.id})")
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
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        traceback.print_exc()
        print("-" * 70 + "\n")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def webhook_health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "webhook_secret_configured": bool(WEBHOOK_SECRET)
    }
