"""
Module for generating and managing API keys.

This module provides functionality to create, store, and manage API keys
for users. It handles the secure generation of keys using Argon2 hashing.
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.api_key import APIKey
from app.core.database import async_session_maker
from app.core.security import generate_api_key


async def create_api_key_for_user(
    user,
    name: str = "Default API Key",
    rate_limit_plan: str = "free",
    expires_in_days: int = 365
) -> tuple[dict, str]:
    """
    Create a new API key for a user.
    
    Args:
        user: The user to create the key for
        name (str): Human-readable name for the API key
        rate_limit_plan (str): Rate limit plan to associate with this key
        expires_in_days (int): Days until key expires (None = no expiration)
    
    Returns:
        tuple[dict, str]: Tuple containing:
            - Dictionary with 'key', 'key_hash', 'last_chars', and 'api_key_id'
            - Status message
    
    Note:
        IMPORTANT: The full API key is only shown once at creation time.
        Store it securely. The database only stores the hash.
    """
    async with async_session_maker() as session:
        user_id = user.id
        
        # Generate secure API key
        key_data = generate_api_key()
        
        # Calculate expiration date
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        # Create API key record
        api_key_record = APIKey(
            user_id=user_id,
            key_hash=key_data["key_hash"],
            name=name,
            last_chars=key_data["last_chars"],
            is_active=True,
            rate_limit_plan=rate_limit_plan,
            expires_at=expires_at,
            created_at=datetime.now()
        )
        
        session.add(api_key_record)
        await session.commit()
        await session.refresh(api_key_record)
        
        # Prepare response with key details
        key_response = {
            "key": key_data["key"],
            "key_hash": key_data["key_hash"],
            "last_chars": key_data["last_chars"],
            "api_key_id": api_key_record.id
        }
        
        expiration_text = (
            f"Expires: {expires_at.strftime('%Y-%m-%d')}" if expires_at 
            else "No expiration"
        )
        
        message = (
            f"✓ API Key created successfully!\n"
            f"  - Key ID: {api_key_record.id}\n"
            f"  - Name: {api_key_record.name}\n"
            f"  - Last 8 chars: ...{key_data['last_chars']}\n"
            f"  - Rate Limit Plan: {rate_limit_plan}\n"
            f"  - {expiration_text}\n"
            f"\n⚠️  IMPORTANT: The full API key below is only shown once!\n"
            f"   Copy and store it securely - you won't be able to see it again.\n\n"
            f"   Key: {key_data['key']}\n"
            f"\n   Usage: Include this in API requests via the X-API-Key header:"
            f"\n   curl -H 'X-API-Key: {key_data['key']}' https://api.example.com/v1/..."
        )
        
        return key_response, message


async def get_user_api_keys(user_id: int) -> list[APIKey]:
    """
    Get all active API keys for a user.
    
    Args:
        user_id (int): User ID
    
    Returns:
        list[APIKey]: List of API key objects
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .where(APIKey.is_active == True)
        )
        return result.scalars().all()


async def revoke_api_key(api_key_id: int) -> str:
    """
    Revoke an API key by marking it as inactive.
    
    Args:
        api_key_id (int): ID of the API key to revoke
    
    Returns:
        str: Status message
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(APIKey).where(APIKey.id == api_key_id)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return f"API Key {api_key_id} not found"
        
        api_key.is_active = False
        api_key.revoked_at = datetime.now()
        await session.commit()
        
        return f"✓ API Key {api_key_id} has been revoked"


async def get_api_key_by_id(api_key_id: int) -> APIKey | None:
    """
    Get an API key record by ID.
    
    Args:
        api_key_id (int): API key ID
    
    Returns:
        APIKey | None: API key object if found, None otherwise
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(APIKey).where(APIKey.id == api_key_id)
        )
        return result.scalar_one_or_none()


if __name__ == "__main__":
    # Test creating an API key
    async def main():
        from user_generator import create_test_user
        
        print("\n" + "="*60)
        print("TEST: Creating API key for user")
        print("="*60 + "\n")
        
        user, user_msg = await create_test_user("test_apikey@example.com")
        print(user_msg)
        
        print("\n" + "-"*60 + "\n")
        
        key_response, key_msg = await create_api_key_for_user(
            user,
            name="Test API Key"
        )
        print(key_msg)
        
        print("\n" + "="*60 + "\n")
    
    asyncio.run(main())
