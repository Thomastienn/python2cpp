import ast
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from py2c.commands.parser import parse
from py2c.utils.utils import Utils
from structures import CodeRequest

app = FastAPI()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    """
    Root endpoint to check if the server is running.
    """
    return {"message": "Welcome to the Python to C++ converter API!"}

@app.post("/convert")
@limiter.limit("10/minute")
async def convert(request: Request, req: CodeRequest):
    """
    Convert Python code to Cpp.
    """
    tree = ast.parse(req.pycode)
    try:
        result = Utils.capture_output(parse, tree)
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"{tb}\n{e}")

    return {
        "code": result,
    }
