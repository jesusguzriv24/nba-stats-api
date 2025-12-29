"""
Main orchestrator for the complete test flow.

This script coordinates all the separate modules to:
1. Create a test user
2. Assign a free subscription
3. Generate an API key
4. Test the API with the key until rate limit is reached

Run this script to perform the complete workflow:
    python main_test_flow.py
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models FIRST to avoid SQLAlchemy mapper issues
from app.models.user import User
from app.models.api_key import APIKey
from app.models.user_subscription import UserSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.api_usage_log import APIUsageLog
from app.models.api_usage_aggregate import APIUsageAggregate

from scripts.user_generator import create_test_user
from scripts.subscription_generator import assign_free_subscription
from scripts.apikey_generator import create_api_key_for_user
from scripts.api_client import APIClient


# Configuration
API_BASE_URL = "https://bestat-nba-api.onrender.com"  # Render deployment
TEST_EMAIL = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
API_ENDPOINTS = [
    "/api/v1/games/",
    "/api/v1/players/",
    "/api/v1/teams/"
]
DELAY_BETWEEN_REQUESTS = 0.01  # 10ms delay between requests


async def main():
    """
    Execute the complete workflow:
    1. Create user → 2. Assign subscription → 3. Create API key → 4. Test API
    """
    
    print("\n" + "="*70)
    print(" "*15 + "NBA STATS API - COMPLETE TEST FLOW")
    print("="*70)
    
    try:
        # ===== STEP 1: Create User =====
        print("\n[STEP 1/4] Creating test user...")
        print("-"*70)
        
        user, user_msg = await create_test_user(TEST_EMAIL)
        print(user_msg)
        
        if not user or not user.id:
            print("❌ Failed to create user. Aborting.")
            return
        
        # ===== STEP 2: Assign Subscription =====
        print("\n[STEP 2/4] Assigning free subscription...")
        print("-"*70)
        
        subscription, sub_msg = await assign_free_subscription(user)
        print(sub_msg)
        
        if not subscription or not subscription.id:
            print("❌ Failed to assign subscription. Aborting.")
            return
        
        # ===== STEP 3: Create API Key =====
        print("\n[STEP 3/4] Generating API key...")
        print("-"*70)
        
        key_response, key_msg = await create_api_key_for_user(
            user,
            name="Test Key",
            rate_limit_plan="free"
        )
        print(key_msg)
        
        if not key_response or "key" not in key_response:
            print("❌ Failed to create API key. Aborting.")
            return
        
        api_key = key_response["key"]
        
        # ===== STEP 4: Test API Until Rate Limited =====
        print("\n[STEP 4/4] Testing API endpoints until rate limit...")
        print("-"*70)
        
        client = APIClient(
            base_url=API_BASE_URL,
            api_key=api_key,
            rate_limit_per_minute=10  # Free plan limit
        )
        
        await client.test_endpoints_until_rate_limited(
            API_ENDPOINTS,
            delay_between_requests=DELAY_BETWEEN_REQUESTS
        )
        
        # Print final summary
        client.print_summary()
        
        # ===== FINAL REPORT =====
        print("="*70)
        print("✓ TEST FLOW COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"\n📊 TEST SUMMARY:")
        print(f"   User Email:           {user.email}")
        print(f"   User ID:              {user.id}")
        print(f"   Subscription:         Free Plan")
        print(f"   API Key ID:           {key_response['api_key_id']}")
        print(f"   API Key Last Chars:   ...{key_response['last_chars']}")
        print(f"   Total Requests Made:  {client.request_count}")
        print(f"   Rate Limited:         {'Yes' if client.rate_limited_at else 'No'}")
        print(f"   API Base URL:         {API_BASE_URL}")
        print(f"   Endpoints Tested:     {', '.join(API_ENDPOINTS)}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    return True


if __name__ == "__main__":
    print("\nℹ️  Make sure:")
    print("   1. The NBA Stats API is running on http://localhost:8000")
    print("   2. PostgreSQL database is configured")
    print("   3. Redis is running for rate limiting")
    print("   4. All environment variables are set in .env\n")
    
    try:
        success = asyncio.run(main())
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
