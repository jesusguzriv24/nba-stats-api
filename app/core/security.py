"""
Security utilities for API key generation and verification.
"""
import secrets
from passlib.context import CryptContext


# Argon2 hashing context for secure password and key hashing (more modern than bcrypt)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def generate_api_key() -> dict:
    """
    Generate a secure API key with its Argon2 hash and last characters.
    
    This function creates a cryptographically secure API key using secrets.token_urlsafe,
    applies a consistent prefix for identification, hashes it using Argon2, and extracts
    the last 8 characters for UI display purposes.
    
    Returns:
        dict: Dictionary containing:
            - "key": str - Complete API key (should be shown to user only once)
            - "key_hash": str - Argon2 hash for secure storage in database
            - "last_chars": str - Last 8 characters for UI display (without exposing full key)
    
    Example:
        >>> result = generate_api_key()
        >>> result["key"]
        'bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN'
        >>> result["last_chars"]
        '5cV0bN'
    """
    # Generate cryptographically secure random token (32 bytes = ~43 characters in base64)
    random_token = secrets.token_urlsafe(32)
    
    # Prepend prefix for easy identification of API keys
    api_key = f"bestat_nba_{random_token}"
    
    # Hash the complete API key using Argon2
    key_hash = pwd_context.hash(api_key)
    
    # Extract last 8 characters for safe UI display without revealing full key
    last_chars = api_key[-8:]
    
    return {
        "key": api_key,
        "key_hash": key_hash,
        "last_chars": last_chars
    }


def verify_api_key(plain_key: str, key_hash: str) -> bool:
    """
    Verify if a provided API key matches its stored Argon2 hash.
    
    This function safely compares a plain-text API key against its stored hash
    using Argon2 verification. Any exceptions during verification are caught
    and treated as invalid keys for security purposes.
    
    Args:
        plain_key (str): API key in plain text as provided by the client
        key_hash (str): Argon2 hash stored in the database
    
    Returns:
        bool: True if the key is valid and matches the hash, False otherwise
    
    Example:
        >>> data = generate_api_key()
        >>> verify_api_key(data["key"], data["key_hash"])
        True
        >>> verify_api_key("invalid_key", data["key_hash"])
        False
    """
    try:
        return pwd_context.verify(plain_key, key_hash)
    except Exception:
        # Return False for any verification errors (security best practice)
        return False


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    This function is optional and provided for future use if local password
    authentication is implemented. Currently, Supabase Auth handles authentication.
    
    Args:
        password (str): Plain-text password to hash
    
    Returns:
        str: Argon2 hash of the password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its Argon2 hash.
    
    This function is optional and provided for future use if local password
    authentication is implemented. Currently, Supabase Auth handles authentication.
    
    Args:
        plain_password (str): Plain-text password as provided by the user
        hashed_password (str): Argon2 hash stored in the database
    
    Returns:
        bool: True if the password is correct and matches the hash, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Return False for any verification errors (security best practice)
        return False
