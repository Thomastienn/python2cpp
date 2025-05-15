import ast
from typing import BaseModel

class Parameter(BaseModel):
    name: str
    type: str
        
class Function:
    name: str
    params: list[Parameter]
    ast_object: ast.FunctionDef
