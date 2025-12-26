"""
Test rate limiting con API key.
"""
import requests
import time
import os

# Leer API key del archivo generado
API_KEY = "bestat_nba_H1F84TVvSexJUlac13l1M7NK5LdHCm6Vc1w6fTHAnAc"

API_URL = "https://bestat-nba-api.onrender.com/api/v1"

headers = {"X-API-Key": API_KEY}

print("\n" + "="*70)
print("🔥 TESTING RATE LIMITING")
print("="*70)
print(f"\nAPI Key: {API_KEY[:30]}...{API_KEY[-10:]}")
print(f"\nMaking 105 requests to exceed free tier limit (100/hour)...\n")
print("-"*70)

success_count = 0
rate_limited_at = None

for i in range(1, 106):
    try:
        response = requests.get(f"{API_URL}/teams?limit=1", headers=headers)
        
        # Obtener headers de rate limit
        remaining = response.headers.get("X-RateLimit-Remaining", "?")
        limit = response.headers.get("X-RateLimit-Limit", "?")
        reset = response.headers.get("X-RateLimit-Reset", "?")
        
        if response.status_code == 200:
            success_count += 1
            status_icon = "✅"
        elif response.status_code == 429:
            status_icon = "🛑"
            if not rate_limited_at:
                rate_limited_at = i
        else:
            status_icon = "⚠️"
        
        print(f"{status_icon} Request {i:3d}: Status {response.status_code} | "
              f"Remaining: {remaining:>3}/{limit} | Reset: {reset}")
        
        if response.status_code == 429:
            print("\n" + "="*70)
            print("🛑 RATE LIMIT EXCEEDED!")
            print("="*70)
            print(f"\nBlocked at request: {i}")
            print(f"Successful requests: {success_count}")
            print(f"\nResponse body:")
            print(response.json())
            print("\n" + "="*70)
            break
        
        time.sleep(0.05)  # 50ms entre requests
        
    except Exception as e:
        print(f"❌ Error on request {i}: {e}")
        break

print("\n" + "="*70)
print("📊 TEST SUMMARY")
print("="*70)
print(f"Total requests sent: {i}")
print(f"Successful requests: {success_count}")
print(f"Rate limited at request: {rate_limited_at or 'N/A'}")
print(f"Free tier limit: 100/hour")
print("="*70 + "\n")
