from __future__ import annotations
import ast
from typing import TYPE_CHECKING
from pydantic import BaseModel, PrivateAttr

if TYPE_CHECKING:
    from py2c.core.processor import ExprParser

class Function(BaseModel):
    name: str
    return_pytype: list[str] | str | None
    _ast_object: ast.FunctionDef = PrivateAttr()
    user_func: bool = False

class Variable(BaseModel):
    name: str
    is_param: bool = False
    pytype: list[str] | str = "Unknown"
    lowest_val: int = 0
    highest_val: int = 100
    
class VisitContext(BaseModel):
    current_indent: int = 0
    allow_print: bool | None = None
    is_scanning: bool = False
    scope: list[str] = ["global"] # Nested scope

    def copy(self) -> VisitContext:
        return VisitContext(
            current_indent=self.current_indent,
            allow_print=self.allow_print,
            is_scanning=self.is_scanning,
            scope=self.scope.copy()
        )
    
class ReprVisitContext(BaseModel):
    processor: "ExprParser"
    return_type: bool = False
    parser_ctx: VisitContext 
    expr_node: ast.AST
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def copy(self) -> ReprVisitContext:
        return ReprVisitContext(
            processor=self.processor,
            return_type=self.return_type,
            parser_ctx=self.parser_ctx.copy(),
            expr_node=self.expr_node
        )
