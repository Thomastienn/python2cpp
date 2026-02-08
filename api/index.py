"""
Vercel Serverless API - Python to C++ Converter

This module provides a FastAPI-based serverless API for Vercel deployment.
Each request is handled by an independent serverless function invocation.

Endpoints:
- GET /api/ : Health check
- POST /api/convert : Convert Python code to C++
- POST /api/fix : Fix C++ compilation errors via LLM (no g++ needed)

Key differences from the Render (Docker/Uvicorn) deployment:
- No g++ available: /fix endpoint sends code directly to Gemini without
  compiling first to get error messages
- No persistent filesystem: security logging goes to stdout (Vercel Logs)
  instead of security.log file
- No persistent state: rate limiting and IP abuse tracking are removed
  (each invocation is independent). Vercel has its own DDoS protection.
- Vercel natively detects the FastAPI `app` variable -- no adapter needed

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

import sys
import os
import logging
import traceback

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add the project root to sys.path so py2c can be imported
# On Vercel, the project root is one level up from api/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Patch security logging BEFORE importing py2c modules that call it.
# Vercel has a read-only filesystem, so FileHandler("security.log") would crash.
# Redirect security logs to stdout so they appear in Vercel's log viewer.
import py2c.utils.utils as _utils_module


def _serverless_security_logging() -> logging.Logger:
    """Setup security logging for serverless (stdout instead of file)."""
    logger = logging.getLogger("py2cpp.security")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - SECURITY - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


_utils_module.Utils.setup_security_logging = staticmethod(_serverless_security_logging)

from py2c.commands.parser import parse
from py2c.utils.utils import Utils, SecurityUtils, SecurityError
from py2c.utils.constants import SECURITY_CONFIG
from py2c.core.structure import LLMFixResponse

from pydantic import BaseModel, Field, field_validator

# ---------- Request Models ----------


class PyCodeRequest(BaseModel):
    pycode: str = Field(
        ...,
        min_length=1,
        max_length=SECURITY_CONFIG["MAX_INPUT_SIZE"],
        description="Python code to convert to C++",
    )

    @field_validator("pycode")
    @classmethod
    def validate_pycode(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Python code cannot be empty")
        dangerous_imports = ["os", "sys", "subprocess", "eval", "exec", "__import__"]
        lines = v.lower().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                for dangerous in dangerous_imports:
                    if dangerous in line:
                        raise ValueError(
                            f"Potentially unsafe import detected: {dangerous}"
                        )
        return v


class CppCodeRequest(BaseModel):
    cppcode: str = Field(
        ...,
        min_length=1,
        max_length=SECURITY_CONFIG["MAX_INPUT_SIZE"],
        description="C++ code to validate and fix",
    )


# ---------- FastAPI App ----------

app = FastAPI()

# CORS - allow all origins (same as your current config)
app.add_middleware(
    CORSMiddleware,
    allow_origins=SECURITY_CONFIG["ALLOWED_ORIGINS"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = SECURITY_CONFIG["CSP_HEADER"]
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ---------- Endpoints ----------


@app.get("/api/")
@app.get("/api")
async def root():
    """Health check endpoint."""
    return {
        "message": "Welcome to the Python to C++ converter API!",
        "version": "1.0.0",
        "runtime": "vercel-serverless",
    }


@app.post("/api/convert")
async def convert(request: Request, req: PyCodeRequest):
    """Convert Python code to C++ with security validation."""
    try:
        SecurityUtils.validate_input_size(req.pycode)
        tree = SecurityUtils.validate_ast_complexity(req.pycode)

        result = Utils.capture_output(
            parse, tree, timeout=SECURITY_CONFIG["CONVERSION_TIMEOUT"]
        )

        return {"code": result, "status": "success"}

    except SecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except TimeoutError:
        raise HTTPException(
            status_code=408, detail="Request timeout: Code processing took too long"
        )

    except Exception as e:
        sanitized_error = SecurityUtils.sanitize_error_message(e, debug_mode=False)
        full_error = (
            sanitized_error + "\n\nTraceback for devs: " + traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=full_error)


@app.post("/api/fix")
async def fix(request: Request, req: CppCodeRequest):
    """
    Fix C++ code using LLM.

    NOTE: This endpoint does NOT compile with g++ (not available on Vercel).
    Instead, it sends the C++ code directly to Gemini for analysis and fixing.
    """
    try:
        SecurityUtils.validate_input_size(req.cppcode)

        # Lazy import to keep cold starts fast
        from dotenv import load_dotenv
        from google import genai
        from google.genai import types

        load_dotenv()
        client = genai.Client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Here is a C++ code that may have compilation errors:\n\n"
                + req.cppcode,
                "Please analyze this code for any compilation errors, syntax errors, or other issues (except logic errors) and fix them.",
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
                system_instruction=(
                    "You are a C++ expert. You will be given C++ code that may have "
                    "compilation errors. Analyze the code, identify any compile errors, "
                    "syntax errors, or other issues (except logic errors), and fix them. "
                    "Make sure the code is valid C++ code and can be compiled without "
                    "any errors. Do not add extra comments or explanations, just return "
                    "the fixed C++ code."
                ),
                response_mime_type="application/json",
                response_schema=LLMFixResponse,
            ),
        )

        llm_response: LLMFixResponse = response.parsed
        if not llm_response.code:
            raise Exception("LLM failed to fix the code")

        return {"fix_code": llm_response.code, "status": "success"}

    except SecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except TimeoutError:
        raise HTTPException(
            status_code=408, detail="Request timeout: Code processing took too long"
        )

    except Exception as e:
        sanitized_error = SecurityUtils.sanitize_error_message(e, debug_mode=False)
        full_error = (
            sanitized_error + "\n\nTraceback for devs: " + traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=full_error)


# Vercel automatically detects this `app` variable and serves it as ASGI.
# No additional handler/adapter needed.
