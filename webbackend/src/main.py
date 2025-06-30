import ast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.post("/convert")
async def convert(req: CodeRequest):
    """
    Convert Python code to Cpp.
    """
    tree = ast.parse(req.pycode)
    try:
        result = Utils.capture_output(parse, tree)
    except Exception as e:
        return {
            "status_code": 500,
            "message": str(e),
        }
    return {
        "status_code": 200,
        "code": result,
    }
