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
    scope: str = "global"
    
class ReprVisitContext(BaseModel):
    processor: ExprParser 
    return_type: bool = False
    parser_ctx: VisitContext 
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
from py2c.core.processor import ExprParser
ReprVisitContext.model_rebuild()
