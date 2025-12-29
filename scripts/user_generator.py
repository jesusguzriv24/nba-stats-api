"""
Module for creating new users in the database.

This module provides functionality to create user records in the users table.
Since we're not using Supabase Auth for this test, we'll use dummy values
for the supabase_user_id field.
"""
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.core.database import async_session_maker


async def create_test_user(
    email: str,
    role: str = "user",
    is_active: bool = True
) -> tuple[User, str]:
    """
    Create a new user in the database.
    
    Args:
        email (str): User email address
        role (str): User role (default: "user")
        is_active (bool): Whether the user is active (default: True)
    
    Returns:
        tuple[User, str]: Created User object and a status message
    
    Raises:
        Exception: If user with this email already exists
    """
    async with async_session_maker() as session:
        # Check if user already exists using raw SQL to avoid mapper issues
        result = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email}
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Get the existing user
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            return user, f"User with email {email} already exists"
        
        # Create a dummy Supabase UUID for testing
        # In production, this would come from Supabase Auth
        dummy_supabase_id = str(uuid.uuid4())
        
        # Create new user
        new_user = User(
            email=email,
            role=role,
            is_active=is_active,
            supabase_user_id=dummy_supabase_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        message = (
            f"✓ User created successfully!\n"
            f"  - ID: {new_user.id}\n"
            f"  - Email: {new_user.email}\n"
            f"  - Role: {new_user.role}\n"
            f"  - Supabase ID: {new_user.supabase_user_id}"
        )
        
        return new_user, message


async def get_user_by_email(email: str) -> User | None:
    """
    Retrieve a user by email address.
    
    Args:
        email (str): User email
    
    Returns:
        User | None: User object if found, None otherwise
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()


async def get_user_by_id(user_id: int) -> User | None:
    """
    Retrieve a user by ID.
    
    Args:
        user_id (int): User ID
    
    Returns:
        User | None: User object if found, None otherwise
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


if __name__ == "__main__":
    # Test the user creation
    async def main():
        print("\n" + "="*60)
        print("TEST: Creating a new user")
        print("="*60 + "\n")
        
        user, message = await create_test_user(
            email="test_user@example.com"
        )
        print(message)
        print("\n" + "="*60 + "\n")
    
    asyncio.run(main())
