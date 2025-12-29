"""
Configuration and utilities for test scripts.

This module provides shared configuration and helper functions
used across all test scripts.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================
# API CONFIGURATION
# ============================================
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))


# ============================================
# DATABASE CONFIGURATION
# ============================================
DATABASE_URL = os.getenv("DATABASE_URL")


# ============================================
# REDIS CONFIGURATION (Rate Limiting)
# ============================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_ENABLED = REDIS_URL is not None


# ============================================
# TEST CONFIGURATION
# ============================================
DEFAULT_TEST_ENDPOINTS = [
    "/v1/games/",
    "/v1/players/",
    "/v1/teams/",
]

DEFAULT_DELAY_BETWEEN_REQUESTS = 0.05  # 50ms between requests

# Safety limits
MAX_REQUESTS_BEFORE_ABORT = 1000
REQUEST_TIMEOUT_SECONDS = 30


# ============================================
# HELPER FUNCTIONS
# ============================================

def validate_config() -> dict:
    """
    Validate that all required configuration is present.
    
    Returns:
        dict: Configuration status with warnings and errors
    """
    status = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Check database
    if not DATABASE_URL:
        status["errors"].append("DATABASE_URL not configured in .env")
        status["valid"] = False
    
    # Check Redis for rate limiting
    if not REDIS_ENABLED:
        status["warnings"].append(
            "REDIS_URL not configured - rate limiting will be disabled"
        )
    
    return status


def print_config():
    """Print the current configuration (with sensitive values masked)."""
    print("\n" + "="*60)
    print("CONFIGURATION")
    print("="*60)
    print(f"API Base URL:        {API_BASE_URL}")
    print(f"API Timeout:         {API_TIMEOUT}s")
    print(f"Database:            {'✓ Configured' if DATABASE_URL else '✗ Not configured'}")
    print(f"Redis:               {'✓ Configured' if REDIS_ENABLED else '✗ Not configured'}")
    print(f"Default Endpoints:   {len(DEFAULT_TEST_ENDPOINTS)} configured")
    print(f"Request Delay:       {DEFAULT_DELAY_BETWEEN_REQUESTS}s")
    print("="*60 + "\n")


if __name__ == "__main__":
    print_config()
    
    status = validate_config()
    if status["errors"]:
        print("❌ ERRORS:")
        for error in status["errors"]:
            print(f"   - {error}")
    
    if status["warnings"]:
        print("⚠️  WARNINGS:")
        for warning in status["warnings"]:
            print(f"   - {warning}")
    
    if status["valid"]:
        print("✓ Configuration is valid!")
    else:
        print("❌ Configuration is invalid - some features may not work")
