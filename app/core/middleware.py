"""
Custom middleware for rate limiting and request tracking.

This middleware integrates with the subscription system and rate limiter
to enforce limits and add appropriate headers to responses.
"""
from fastapi import Request
from fastapi.responses import Response
import time
from datetime import datetime


async def rate_limit_headers_middleware(request: Request, call_next):
    """
    Middleware to add rate limit headers to all API responses.
    
    This middleware runs after the request has been processed and adds
    standardized rate limit headers to the response. These headers inform
    clients about their current rate limit status.
    
    Headers added:
    - X-RateLimit-Limit-Minute: Maximum requests per minute
    - X-RateLimit-Limit-Hour: Maximum requests per hour  
    - X-RateLimit-Limit-Day: Maximum requests per day
    - X-RateLimit-Remaining-Minute: Remaining requests this minute
    - X-RateLimit-Remaining-Hour: Remaining requests this hour
    - X-RateLimit-Remaining-Day: Remaining requests this day
    - X-RateLimit-Reset-Minute: Unix timestamp when minute limit resets
    - X-RateLimit-Reset-Hour: Unix timestamp when hour limit resets
    - X-RateLimit-Reset-Day: Unix timestamp when day limit resets
    
    Args:
        request (Request): Incoming FastAPI request
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response: Response with rate limit headers added
    """
    # Process the request through the rest of the chain
    response = await call_next(request)
    
    try:
        # Check if rate limit info was stored by authentication dependency
        if hasattr(request.state, "rate_limit_info"):
            info = request.state.rate_limit_info
            
            # Add minute limits
            response.headers["X-RateLimit-Limit-Minute"] = str(info.get("limit_minute", 0))
            response.headers["X-RateLimit-Remaining-Minute"] = str(info.get("remaining_minute", 0))
            response.headers["X-RateLimit-Reset-Minute"] = str(info.get("reset_minute", 0))
            
            # Add hour limits
            response.headers["X-RateLimit-Limit-Hour"] = str(info.get("limit_hour", 0))
            response.headers["X-RateLimit-Remaining-Hour"] = str(info.get("remaining_hour", 0))
            response.headers["X-RateLimit-Reset-Hour"] = str(info.get("reset_hour", 0))
            
            # Add day limits
            response.headers["X-RateLimit-Limit-Day"] = str(info.get("limit_day", 0))
            response.headers["X-RateLimit-Remaining-Day"] = str(info.get("remaining_day", 0))
            response.headers["X-RateLimit-Reset-Day"] = str(info.get("reset_day", 0))
            
            print(f"[HEADERS] Added rate limit headers - Minute: {info.get('remaining_minute')}/{info.get('limit_minute')}")
    
    except Exception as e:
        # Don't fail the request if header addition fails
        print(f"[HEADERS] Error adding rate limit headers: {e}")
    
    return response


async def usage_logging_middleware(request: Request, call_next):
    """
    Middleware to log API usage for analytics and monitoring.
    
    This middleware tracks every API request and logs it to the database.
    It captures request details, response status, and performance metrics.
    
    Logged information:
    - User ID and API key ID (if authenticated)
    - Endpoint and HTTP method
    - Response status code and time
    - Client IP address and user agent
    - Whether request was rate limited
    
    This data is used for:
    - Usage analytics and reporting
    - Rate limit enforcement auditing
    - Performance monitoring
    - Security analysis
    
    Args:
        request (Request): Incoming FastAPI request
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response: Original response from endpoint
    """
    # Record start time for response time calculation
    start_time = time.time()
    
    # Extract request metadata
    endpoint = request.url.path
    http_method = request.method
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Initialize variables for user/api_key (set by authentication)
    user_id = None
    api_key_id = None
    rate_limit_plan = None
    rate_limited = False
    
    # Process the request
    try:
        response = await call_next(request)
        status_code = response.status_code
        error_message = None
        
        # Check if this was a rate limit error
        if status_code == 429:
            rate_limited = True
        
    except Exception as e:
        # If request failed with exception, log it
        status_code = 500
        error_message = str(e)
        # Re-raise the exception after logging
        raise
    
    finally:
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Extract user and API key info if available
        if hasattr(request.state, "user"):
            user_id = request.state.user.id
        
        if hasattr(request.state, "api_key"):
            api_key_id = request.state.api_key.id
        
        if hasattr(request.state, "subscription_plan"):
            rate_limit_plan = request.state.subscription_plan.plan_name
        
        # Log the usage (async, don't wait for completion)
        if user_id:
            try:
                # Import here to avoid circular imports
                from app.core.dependencies import log_api_usage
                from app.core.database import async_session_maker
                
                # Create a new DB session for logging
                async with async_session_maker() as db:
                    await log_api_usage(
                        db=db,
                        user_id=user_id,
                        api_key_id=api_key_id,
                        endpoint=endpoint,
                        http_method=http_method,
                        status_code=status_code,
                        response_time_ms=response_time_ms,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_id=None,  # Can add request ID tracking if needed
                        rate_limit_plan=rate_limit_plan,
                        rate_limited=rate_limited,
                        error_message=error_message
                    )
            except Exception as log_error:
                # Don't fail the request if logging fails
                print(f"[ERROR] Failed to log API usage: {log_error}")
    
    return response


async def request_id_middleware(request: Request, call_next):
    """
    Middleware to add unique request ID to each request.
    
    Generates a unique identifier for each request that can be used for:
    - Request tracking across logs
    - Debugging distributed systems
    - Correlating client issues with server logs
    
    The request ID is:
    - Stored in request.state.request_id
    - Added to response headers as X-Request-ID
    - Can be logged in usage logs for tracking
    
    Args:
        request (Request): Incoming FastAPI request
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response: Response with X-Request-ID header
    """
    import uuid
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    # Store in request state for access in endpoints
    request.state.request_id = request_id
    
    # Process request
    response = await call_next(request)
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response
