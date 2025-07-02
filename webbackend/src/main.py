import ast
import traceback
import time
from collections import defaultdict
from typing import Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from py2c.commands.parser import parse
from py2c.utils.utils import Utils, SecurityUtils, SecurityError
from py2c.utils.constants import SECURITY_CONFIG
from structures import CodeRequest

app = FastAPI()

# Initialize rate limiter with stricter limits
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security tracking for abuse prevention
abuse_tracker: Dict[str, Dict] = defaultdict(lambda: {'violations': 0, 'ban_until': 0})

# Setup security logging
security_logger = Utils.setup_security_logging()

# Configure CORS with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=SECURITY_CONFIG['ALLOWED_ORIGINS'],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict methods
    allow_headers=["Content-Type", "Authorization"],  # Restrict headers
    max_age=3600,  # Cache preflight for 1 hour
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Content Security Policy
    response.headers["Content-Security-Policy"] = SECURITY_CONFIG['CSP_HEADER']
    
    # Additional security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

@app.middleware("http")
async def check_abuse_tracking(request: Request, call_next):
    """Check for abusive behavior and implement bans"""
    client_ip = get_remote_address(request)
    current_time = time.time()
    
    # Check if IP is currently banned
    if abuse_tracker[client_ip]['ban_until'] > current_time:
        security_logger.warning(f"Blocked banned IP: {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail="Your IP has been temporarily banned due to abuse. Please try again later."
        )
    
    try:
        response = await call_next(request)
        return response
    except RateLimitExceeded:
        # Track rate limit violations
        abuse_tracker[client_ip]['violations'] += 1
        
        if abuse_tracker[client_ip]['violations'] >= SECURITY_CONFIG['RATE_LIMIT_ABUSE_THRESHOLD']:
            # Ban the IP for configured duration
            abuse_tracker[client_ip]['ban_until'] = current_time + SECURITY_CONFIG['RATE_LIMIT_BAN_DURATION']
            security_logger.warning(f"IP banned for abuse: {client_ip}")
        
        raise


@app.get("/")
@limiter.limit(SECURITY_CONFIG['API_RATE_LIMIT'])
async def root(request: Request):
    """
    Root endpoint to check if the server is running.
    """
    return {"message": "Welcome to the Python to C++ converter API!", "version": "1.0.0"}

@app.post("/convert")
@limiter.limit(SECURITY_CONFIG['API_RATE_LIMIT'])
async def convert(request: Request, req: CodeRequest):
    """
    Convert Python code to C++.
    """
    client_ip = get_remote_address(request)
    
    try:
        # Security validations
        SecurityUtils.validate_input_size(req.pycode)
        tree = SecurityUtils.validate_ast_complexity(req.pycode)
        
        # Log conversion attempt
        security_logger.info(f"Conversion request from {client_ip}, code size: {len(req.pycode)} bytes")
        
        # Process with timeout
        result = Utils.capture_output(parse, tree, timeout=SECURITY_CONFIG['CONVERSION_TIMEOUT'])
        
        return {
            "code": result,
            "status": "success"
        }
        
    except SecurityError as e:
        security_logger.warning(f"Security violation from {client_ip}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except TimeoutError as e:
        security_logger.warning(f"Conversion timeout from {client_ip}")
        raise HTTPException(status_code=408, detail="Request timeout: Code processing took too long")
    
    except Exception as e:
        # Log the actual error for debugging but don't expose it
        security_logger.error(f"Conversion error from {client_ip}: {type(e).__name__}: {str(e)}")
        
        # Return sanitized error message
        sanitized_error = SecurityUtils.sanitize_error_message(e, debug_mode=False)
        raise HTTPException(status_code=500, detail=sanitized_error)
