import ast
from typing import Any
from pydantic import BaseModel, PrivateAttr

class Function(BaseModel):
    name: str
    return_pytype: str | None
    _ast_object: ast.FunctionDef = PrivateAttr()
    
class VisitContext(BaseModel):
    current_indent: int = 0
    allow_print: bool | None = None
    scope: str = "global"
    
class ReprVisitContext(BaseModel):
    processor: Any # IT IS A PROCESSOR (CANNOT TYPE DUE TO CIRCULAR DEPENDENCY)
    return_type: bool = False
    scope: str = "global"
