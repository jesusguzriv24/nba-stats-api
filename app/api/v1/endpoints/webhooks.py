"""
Endpoints for receiving webhooks from Supabase Auth.
"""
import os
import hmac
import hashlib
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
    Verify that the webhook originates from Supabase using HMAC-SHA256.
    
    This function validates the authenticity of incoming webhooks by comparing
    the provided signature with a calculated HMAC using the shared webhook secret.
    The comparison is done securely to prevent timing attacks.
    
    Args:
        payload (bytes): Raw request body in bytes
        signature (str): X-Webhook-Signature header value sent by Supabase
        
    Returns:
        bool: True if the signature is valid and authentic, False otherwise
    """
    if not WEBHOOK_SECRET:
        print("⚠️  WARNING: WEBHOOK_SECRET not configured")
        return False
    
    # Calculate HMAC-SHA256 of the payload
    expected_signature = hmac.new(
        key=WEBHOOK_SECRET.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Secure comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


@router.post("/supabase/user-created")
async def handle_user_created(
    request: Request,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook para sincronizar usuarios cuando se registran en Supabase Auth.
    
    Payload esperado de Supabase:
    {
        "type": "INSERT",
        "table": "users",
        "schema": "auth",
        "record": {
            "id": "uuid-del-usuario",
            "email": "usuario@example.com",
            "created_at": "2024-12-24T..."
        },
        "old_record": null
    }
    """
    # Leer body raw para validar firma
    body = await request.body()
    
    # Validar firma del webhook (seguridad)
    if not x_webhook_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Webhook-Signature header"
        )
    
    if not verify_webhook_signature(body, x_webhook_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parsear JSON
    payload = await request.json()
    
    # Validar estructura del payload
    if payload.get("type") != "INSERT":
        return {"status": "ignored", "reason": "Not an INSERT event"}
    
    record = payload.get("record")
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'record' in payload"
        )
    
    supabase_user_id = record.get("id")
    email = record.get("email")
    
    if not supabase_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'id' or 'email' in record"
        )
    
    # Verificar si el usuario ya existe (idempotencia)
    result = await db.execute(
        select(User).where(User.supabase_user_id == supabase_user_id)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        print(f"ℹ️  Usuario ya existe: {email} (ID: {existing_user.id})")
        return {
            "status": "already_exists",
            "user_id": existing_user.id,
            "email": existing_user.email
        }
    
    # Crear usuario en Aiven
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
    
    print(f"✅ Usuario sincronizado via webhook: {email} (ID: {new_user.id})")
    
    return {
        "status": "created",
        "user_id": new_user.id,
        "email": new_user.email,
        "supabase_user_id": new_user.supabase_user_id
    }


@router.get("/health")
async def webhook_health():
    """Health check endpoint to verify webhook receiver is active and configured."""
    return {
        "status": "healthy",
        "webhook_secret_configured": bool(WEBHOOK_SECRET)
    }
"""
Endpoints for receiving webhooks from Supabase Auth.
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
    Verify that the webhook originates from Supabase using HMAC-SHA256.
    
    This function validates the authenticity of incoming webhooks by comparing
    the provided signature with a calculated HMAC using the shared webhook secret.
    The comparison is done securely to prevent timing attacks.
    
    Args:
        payload (bytes): Raw request body in bytes
        signature (str): X-Webhook-Signature header value sent by Supabase
        
    Returns:
        bool: True if the signature is valid and authentic, False otherwise
    """
    if not WEBHOOK_SECRET:
        print("⚠️  WARNING: WEBHOOK_SECRET not configured")
        return False
    
    # Calculate HMAC-SHA256 of the payload
    expected_signature = hmac.new(
        key=WEBHOOK_SECRET.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    print(f"🔐 Signature verification:")
    print(f"   Expected: {expected_signature[:30]}...")
    print(f"   Received: {signature[:30]}...")
    print(f"   Match: {hmac.compare_digest(expected_signature, signature)}")
    
    # Secure comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


@router.post("/supabase/user-created")
async def handle_user_created(
    request: Request,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook handler for synchronizing users when they register in Supabase Auth.
    
    This endpoint receives user creation events from Supabase Realtime and creates
    corresponding User records in the database with default settings (free tier).
    
    Expected Supabase webhook payload structure:
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
        print("\n" + "="*60)
        print("🔔 WEBHOOK RECEIVED")
        print("="*60)
        
        # Read raw body for signature validation
        body = await request.body()
        print(f"📦 Body length: {len(body)} bytes")
        
        # Validate webhook signature for security
        if not x_webhook_signature:
            print("❌ Missing X-Webhook-Signature header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Webhook-Signature header"
            )
        
        if not verify_webhook_signature(body, x_webhook_signature):
            print("❌ Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        print("✅ Signature valid")
        
        # Parse JSON payload
        payload = await request.json()
        print(f"📄 Payload type: {payload.get('type')}")
        print(f"📄 Payload table: {payload.get('table')}")
        
        # Validate payload structure
        if payload.get("type") != "INSERT":
            print(f"⚠️  Event ignored: {payload.get('type')}")
            return {"status": "ignored", "reason": "Not an INSERT event"}
        
        record = payload.get("record")
        if not record:
            print("❌ Missing 'record' in payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'record' in payload"
            )
        
        supabase_user_id = record.get("id")
        email = record.get("email")
        
        print(f"👤 User data:")
        print(f"   - ID: {supabase_user_id}")
        print(f"   - Email: {email}")
        
        if not supabase_user_id or not email:
            print("❌ Missing 'id' or 'email' in record")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'id' or 'email' in record"
            )
        
        # Check if user already exists (idempotency)
        print("🔍 Checking if user exists...")
        result = await db.execute(
            select(User).where(User.supabase_user_id == supabase_user_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"ℹ️  User already exists: {email} (ID: {existing_user.id})")
            return {
                "status": "already_exists",
                "user_id": existing_user.id,
                "email": existing_user.email
            }
        
        # Create new user in database with default settings
        print("💾 Creating user in database...")
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
        
        print(f"✅ User synchronized via webhook: {email} (ID: {new_user.id})")
        print("="*60 + "\n")
        
        return {
            "status": "created",
            "user_id": new_user.id,
            "email": new_user.email,
            "supabase_user_id": new_user.supabase_user_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ WEBHOOK ERROR:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"\n📋 Full traceback:")
        traceback.print_exc()
        print("="*60 + "\n")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def webhook_health():
    """Health check endpoint to verify webhook receiver is active and configured."""
    return {
        "status": "healthy",
        "webhook_secret_configured": bool(WEBHOOK_SECRET)
    }
