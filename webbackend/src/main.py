import ast

from fastapi import FastAPI

from py2c.commands.parser import parse
from py2c.utils.utils import Utils
from structures import CodeRequest

app = FastAPI()

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
