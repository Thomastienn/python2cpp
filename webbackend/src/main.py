import ast
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException

from py2c.commands.parser import parse
from py2c.utils.utils import Utils
from structures import CodeRequest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
async def root():
    """
    Root endpoint to check if the server is running.
    """
    return {"message": "Welcome to the Python to C++ converter API!"}

@app.post("/convert")
async def convert(req: CodeRequest):
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
