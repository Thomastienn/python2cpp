import ast
from pydantic import BaseModel, PrivateAttr

class Function(BaseModel):
    name: str
    return_pytype: str | None
    _ast_object: ast.FunctionDef = PrivateAttr()

class VisitContext(BaseModel):
    current_indent: int = 0
    allow_print: bool | None = None
    scope: str = "global"
