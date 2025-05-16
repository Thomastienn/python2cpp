import ast
from pydantic import BaseModel, PrivateAttr

class Parameter(BaseModel):
    name: str
    pytype: str
        
class Function(BaseModel):
    name: str
    return_pytype: str | None
    params: list[Parameter] | None
    _ast_object: ast.FunctionDef = PrivateAttr()
