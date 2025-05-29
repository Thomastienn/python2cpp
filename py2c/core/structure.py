from __future__ import annotations
import ast
from typing import TYPE_CHECKING
from pydantic import BaseModel, PrivateAttr

if TYPE_CHECKING:
    from py2c.core.processor import ExprParser

class Function(BaseModel):
    name: str
    return_pytype: str | None
    _ast_object: ast.FunctionDef = PrivateAttr()
    
class VisitContext(BaseModel):
    current_indent: int = 0
    allow_print: bool | None = None
    scope: list[str] = ["global"] # Nested scope
    
class ReprVisitContext(BaseModel):
    processor: "ExprParser"
    return_type: bool = False
    # The python type of the variable that is being assigned
    pytype_assign_from: str | list[str] | None = None
    parser_ctx: VisitContext 
    
    model_config = {
        "arbitrary_types_allowed": True
    }
