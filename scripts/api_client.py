"""
Module for making API requests using an API key.

This module provides functionality to make authenticated requests to the API
endpoints using the generated API keys. It handles rate limiting and tracks
usage until the limit is reached.
"""
import asyncio
import httpx
import time
from typing import Optional, List
from datetime import datetime


class APIClient:
    """
    HTTP client for making authenticated API requests with rate limiting tracking.
    
    This client handles:
    - Automatic API key authentication via X-API-Key header
    - Rate limit tracking and enforcement
    - Request/response logging
    - Graceful handling of rate limit errors (429)
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        rate_limit_per_minute: int = 10
    ):
        """
        Initialize the API client.
        
        Args:
            base_url (str): Base URL of the API (e.g., "http://localhost:8000")
            api_key (str): The API key for authentication
            rate_limit_per_minute (int): Expected rate limit per minute
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_count = 0
        self.rate_limited_at = None
        self.requests_log: List[dict] = []
        self.start_time = datetime.now()
    
    async def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        timeout: int = 30
    ) -> tuple[Optional[dict], int, Optional[str]]:
        """
        Make an authenticated HTTP request to the API.
        
        Args:
            endpoint (str): API endpoint path (e.g., "/v1/games")
            method (str): HTTP method (GET, POST, PUT, DELETE)
            params (dict, optional): Query parameters
            json_data (dict, optional): JSON body data
            timeout (int): Request timeout in seconds
        
        Returns:
            tuple[dict | None, int, str | None]: 
                - Response data (if successful)
                - Status code
                - Error message (if any)
        """
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        request_log = {
            "timestamp": datetime.now(),
            "method": method,
            "endpoint": endpoint,
            "status_code": None,
            "error": None
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=json_data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=json_data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return None, 400, f"Unsupported method: {method}"
                
                self.request_count += 1
                request_log["status_code"] = response.status_code
                
                # Handle rate limit (429)
                if response.status_code == 429:
                    self.rate_limited_at = datetime.now()
                    error_msg = f"Rate limited! Status: {response.status_code}"
                    request_log["error"] = error_msg
                    self.requests_log.append(request_log)
                    return None, 429, error_msg
                
                # Handle other errors
                if response.status_code >= 400:
                    error_msg = response.text or f"HTTP {response.status_code}"
                    request_log["error"] = error_msg
                    self.requests_log.append(request_log)
                    return None, response.status_code, error_msg
                
                # Success
                self.requests_log.append(request_log)
                try:
                    return response.json(), response.status_code, None
                except:
                    return {"status": "ok"}, response.status_code, None
                    
        except httpx.TimeoutException:
            error_msg = f"Request timeout after {timeout}s"
            request_log["error"] = error_msg
            self.requests_log.append(request_log)
            return None, 0, error_msg
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            request_log["error"] = error_msg
            self.requests_log.append(request_log)
            return None, 0, error_msg
    
    async def test_endpoints_until_rate_limited(
        self,
        endpoints: List[str],
        delay_between_requests: float = 0.1
    ) -> dict:
        """
        Make requests to endpoints until rate limit is reached.
        
        Args:
            endpoints (List[str]): List of endpoints to test
            delay_between_requests (float): Delay between requests in seconds
        
        Returns:
            dict: Summary of the rate limiting test
        """
        print(f"\n[*] Starting rate limit test with {len(endpoints)} endpoint(s)")
        print(f"    Expected rate limit: {self.rate_limit_per_minute} requests/minute")
        print(f"    Delay between requests: {delay_between_requests}s\n")
        
        endpoint_index = 0
        cycle_count = 0
        
        while True:
            endpoint = endpoints[endpoint_index % len(endpoints)]
            
            # Make request
            data, status_code, error = await self.make_request(
                endpoint,
                method="GET",
                params={"limit": 10, "skip": 0}
            )
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            # Show progress
            print(
                f"[{self.request_count:3d}] {endpoint:30s} "
                f"Status: {status_code:3d} | "
                f"Elapsed: {elapsed:6.1f}s"
            )
            
            # Check if rate limited
            if status_code == 429:
                print(
                    f"\n✓ Rate limit reached!\n"
                    f"  Total requests: {self.request_count}\n"
                    f"  Time taken: {elapsed:.2f}s\n"
                    f"  Error: {error}"
                )
                break
            
            if status_code >= 400 and status_code != 429:
                print(f"  ⚠️  Error: {error}")
            
            # Move to next endpoint
            endpoint_index += 1
            if endpoint_index % len(endpoints) == 0:
                cycle_count += 1
                print(f"  --- Completed cycle {cycle_count} ---")
            
            # Wait before next request
            await asyncio.sleep(delay_between_requests)
            
            # Safety limit: stop after 1000 requests
            if self.request_count >= 1000:
                print(
                    f"\n⚠️  Safety limit reached (1000 requests)\n"
                    f"  Total requests: {self.request_count}\n"
                    f"  Note: Rate limit was not reached within safety threshold"
                )
                break
        
        return self.get_summary()
    
    def get_summary(self) -> dict:
        """
        Get a summary of the API client's activity.
        
        Returns:
            dict: Summary statistics
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        successful = sum(1 for r in self.requests_log if r["error"] is None)
        failed = len(self.requests_log) - successful
        
        summary = {
            "total_requests": self.request_count,
            "successful_requests": successful,
            "failed_requests": failed,
            "elapsed_time_seconds": round(elapsed, 2),
            "requests_per_minute": round((self.request_count / max(elapsed, 1)) * 60, 2),
            "rate_limited": self.rate_limited_at is not None,
            "rate_limited_at": self.rate_limited_at.isoformat() if self.rate_limited_at else None
        }
        
        return summary
    
    def print_summary(self):
        """Print a formatted summary of API activity."""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("API CLIENT SUMMARY")
        print("="*60)
        print(f"Total Requests:       {summary['total_requests']}")
        print(f"Successful:           {summary['successful_requests']}")
        print(f"Failed:               {summary['failed_requests']}")
        print(f"Elapsed Time:         {summary['elapsed_time_seconds']}s")
        print(f"Requests/Minute:      {summary['requests_per_minute']}")
        print(f"Rate Limited:         {'Yes' if summary['rate_limited'] else 'No'}")
        if summary['rate_limited']:
            print(f"Rate Limited At:      {summary['rate_limited_at']}")
        print("="*60 + "\n")


async def test_api_with_key(
    base_url: str,
    api_key: str,
    endpoints: List[str]
) -> dict:
    """
    Test API endpoints with the provided API key until rate limit is reached.
    
    Args:
        base_url (str): Base URL of the API
        api_key (str): API key for authentication
        endpoints (List[str]): List of endpoints to test
    
    Returns:
        dict: Summary of the test
    """
    client = APIClient(base_url, api_key, rate_limit_per_minute=10)
    await client.test_endpoints_until_rate_limited(endpoints)
    client.print_summary()
    return client.get_summary()


if __name__ == "__main__":
    # Test with example API key
    async def main():
        print("\n" + "="*60)
        print("TEST: API Client Rate Limiting")
        print("="*60)
        
        # Using a test API key
        test_key = "bestat_nba_testkey123"
        
        client = APIClient(
            base_url="http://localhost:8000",
            api_key=test_key
        )
        
        # Test multiple endpoints
        endpoints = [
            "/v1/games/",
            "/v1/players/",
            "/v1/teams/"
        ]
        
        await client.test_endpoints_until_rate_limited(endpoints)
        client.print_summary()
    
    asyncio.run(main())
