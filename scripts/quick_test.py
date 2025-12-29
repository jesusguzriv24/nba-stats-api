"""
Quick test script to verify the complete workflow works.

This is a condensed version of main_test_flow.py for quick testing.
Run this to verify everything is set up correctly.

Usage:
    python quick_test.py
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.user_generator import create_test_user
from scripts.subscription_generator import assign_free_subscription
from scripts.apikey_generator import create_api_key_for_user
from scripts.api_client import APIClient
from scripts.config import validate_config, print_config, DEFAULT_TEST_ENDPOINTS, API_BASE_URL


async def quick_test():
    """Run a quick test of the complete workflow."""
    
    print("\n" + "="*70)
    print(" "*20 + "QUICK TEST - Complete Workflow")
    print("="*70 + "\n")
    
    # Validate configuration
    print("Validating configuration...")
    config_status = validate_config()
    
    if not config_status["valid"]:
        print("❌ Configuration errors found:")
        for error in config_status["errors"]:
            print(f"   - {error}")
        return False
    
    if config_status["warnings"]:
        print("⚠️  Warnings:")
        for warning in config_status["warnings"]:
            print(f"   - {warning}\n")
    
    print("✓ Configuration valid\n")
    
    try:
        # Step 1: Create user
        print("[1/4] Creating user...", end=" ", flush=True)
        email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        user, _ = await create_test_user(email)
        if not user or not user.id:
            print("❌ Failed")
            return False
        print(f"✓ Created (ID: {user.id})")
        
        # Step 2: Assign subscription
        print("[2/4] Assigning subscription...", end=" ", flush=True)
        subscription, _ = await assign_free_subscription(user)
        if not subscription or not subscription.id:
            print("❌ Failed")
            return False
        print(f"✓ Assigned (ID: {subscription.id})")
        
        # Step 3: Create API key
        print("[3/4] Creating API key...", end=" ", flush=True)
        key_response, _ = await create_api_key_for_user(user, "Quick Test Key")
        if not key_response or "key" not in key_response:
            print("❌ Failed")
            return False
        print(f"✓ Created (ID: {key_response['api_key_id']})")
        
        # Step 4: Test API with minimal requests
        print("[4/4] Testing API (3 requests)...", end=" ", flush=True)
        client = APIClient(API_BASE_URL, key_response["key"])
        
        # Make just 3 requests to verify it works
        for i, endpoint in enumerate(DEFAULT_TEST_ENDPOINTS[:3]):
            data, status, error = await client.make_request(endpoint)
            if status not in (200, 429):
                print(f"\n       ❌ Failed at request {i+1}: HTTP {status}")
                if error:
                    print(f"       Error: {error}")
                return False
        
        print("✓ Successful")
        
        print("\n" + "="*70)
        print("✓ QUICK TEST PASSED - All systems operational!")
        print("="*70)
        print(f"\nYou can now run the full test:")
        print(f"  python scripts/main_test_flow.py\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("ℹ️  Prerequisites:")
    print("   1. API running on", API_BASE_URL)
    print("   2. PostgreSQL database configured")
    print("   3. Redis running for rate limiting\n")
    
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)
