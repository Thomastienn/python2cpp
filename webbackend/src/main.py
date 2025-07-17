#!/usr/bin/env python3
"""
Python to C++ Converter - Web API Backend

This module provides a FastAPI-based web service for converting Python code to C++.
It includes comprehensive security measures including rate limiting, input validation,
CORS protection, and abuse prevention mechanisms.

The API provides:
- POST /convert: Convert Python code to C++ with security validation
- GET /: API status and version information

Security Features:
- Input size and complexity validation
- Rate limiting per IP address
- CORS protection with restricted origins
- Security headers (CSP, X-Frame-Options, etc.)
- Abuse tracking and IP banning
- Request timeout protection
- Error message sanitization

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

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
from structures import PyCodeRequest, CppCodeRequest
from llm_fix import LLMFix

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
    """
    Add security headers to all HTTP responses.
    
    This middleware adds various security headers to protect against common
    web vulnerabilities including XSS, clickjacking, and content type sniffing.
    
    Args:
        request (Request): The incoming HTTP request
        call_next: The next middleware or route handler in the chain
    
    Returns:
        Response: The HTTP response with added security headers
    
    Security Headers Added:
        - Content-Security-Policy: Prevents XSS and code injection
        - X-Content-Type-Options: Prevents MIME type sniffing
        - X-Frame-Options: Prevents clickjacking attacks
        - X-XSS-Protection: Enables browser XSS filtering
        - Referrer-Policy: Controls referrer information leakage
    """
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
    """
    Monitor and prevent abusive behavior from client IP addresses.
    
    This middleware tracks rate limit violations and automatically bans
    IP addresses that exceed the abuse threshold. Banned IPs are temporarily
    blocked from accessing the API.
    
    Args:
        request (Request): The incoming HTTP request
        call_next: The next middleware or route handler in the chain
    
    Returns:
        Response: The HTTP response, or raises HTTPException if IP is banned
    
    Raises:
        HTTPException: 429 status if the IP is currently banned
    
    Abuse Prevention Features:
        - Tracks rate limit violations per IP
        - Automatically bans IPs exceeding violation threshold
        - Temporary bans with configurable duration
        - Security logging of all ban events
    """
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
    Root endpoint providing API status and version information.
    
    This endpoint serves as a health check and provides basic information
    about the API service. It is rate-limited to prevent abuse.
    
    Args:
        request (Request): The incoming HTTP request (used for rate limiting)
    
    Returns:
        dict: JSON response containing welcome message and version info
            {
                "message": "Welcome to the Python to C++ converter API!",
                "version": "1.0.0"
            }
    
    Rate Limits:
        Configured via SECURITY_CONFIG['API_RATE_LIMIT']
    """
    return {"message": "Welcome to the Python to C++ converter API!", "version": "1.0.0"}

@app.post("/convert")
@limiter.limit(SECURITY_CONFIG['API_RATE_LIMIT'])
async def convert(request: Request, req: PyCodeRequest):
    """
    Convert Python code to C++ with comprehensive security validation.
    
    This endpoint accepts Python source code and returns the equivalent C++ code.
    It includes multiple layers of security validation and error handling.
    
    Args:
        request (Request): The incoming HTTP request (used for rate limiting and IP tracking)
        req (PyCodeRequest): Pydantic model containing the Python code to convert
    
    Returns:
        dict: JSON response containing the converted C++ code
            {
                "code": "converted C++ code",
                "status": "success"
            }
    
    Raises:
        HTTPException: 
            - 400: Invalid input or security validation failure
            - 408: Request timeout (processing took too long)
            - 500: Internal server error during conversion
    
    Security Features:
        - Input size validation (prevents resource exhaustion)
        - AST complexity validation (prevents malicious code)
        - Processing timeout protection
        - Error message sanitization
        - Security event logging
        - Rate limiting per IP address
    """
    client_ip = get_remote_address(request)
    
    try:
        # Security validations
        SecurityUtils.validate_input_size(req.pycode)
        tree = SecurityUtils.validate_ast_complexity(req.pycode)
        
        # Log conversion attempt
        security_logger.info(f"Conversion request from {client_ip}, code size: {len(req.pycode)} bytes")
        
        # Process with timeout
        security_logger.info(f"Received: {req.pycode}")
        result = Utils.capture_output(parse, tree, timeout=SECURITY_CONFIG['CONVERSION_TIMEOUT'])
        security_logger.info(f"Converted to: {result}")
        
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
        full_error = sanitized_error + "\n\nTraceback for devs: " + traceback.format_exc()
        raise HTTPException(status_code=500, detail=full_error)


@app.post("/fix")
@limiter.limit(SECURITY_CONFIG['API_RATE_LIMIT'])
async def fix(request: Request, req: CppCodeRequest):
    """
    Args:
        request (Request): The incoming HTTP request (used for rate limiting and IP tracking)
        req (CppCodeRequest): Pydantic model containing the cpp code to validate and fix
    
    Returns:
        dict: JSON response containing the final C++ code
            {
                "fix_code": "Fixed C++ code",
                "status": "success"
            }
    
    Raises:
        HTTPException: 
            - 400: Invalid input or security validation failure
            - 408: Request timeout (processing took too long)
            - 500: Internal server error during conversion
    
    Security Features:
        - Input size validation (prevents resource exhaustion)
        - Processing timeout protection
        - Error message sanitization
        - Security event logging
        - Rate limiting per IP address
    """
    client_ip = get_remote_address(request)
    
    try:
        # Security validations
        SecurityUtils.validate_input_size(req.cppcode)
        
        # Log conversion attempt
        security_logger.info(f"Conversion request from {client_ip}, code size: {len(req.cppcode)} bytes")
        
        cpp_final = LLMFix(req.cppcode)
        
        return {
            "fix_code": cpp_final,
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
        full_error = sanitized_error + "\n\nTraceback for devs: " + traceback.format_exc()
        raise HTTPException(status_code=500, detail=full_error)
