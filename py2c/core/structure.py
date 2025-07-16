"""
Core Data Structures for Python to C++ Conversion

This module defines the fundamental data structures used throughout the
py2cpp conversion process, including:

- Function representations
- Variable metadata
- Type definitions
- Context objects for AST traversal
- Visitor context management

These structures provide the foundation for type inference, scope management,
and code generation during the conversion process.

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

from __future__ import annotations
import ast
from typing import TYPE_CHECKING
from pydantic import BaseModel, PrivateAttr

if TYPE_CHECKING:
    from py2c.core.processor import ExprParser


class Function(BaseModel):
    """
    Represents a function definition in the conversion process.
    
    This class stores metadata about functions encountered during AST processing,
    including both user-defined functions and built-in Python functions.
    
    Attributes:
        name (str): The function name
        return_pytype (list[str] | str | None): The inferred return type
        _ast_object (ast.FunctionDef): The original AST node (private)
        user_func (bool): Whether this is a user-defined function
    """
    
    name: str
    return_pytype: list[str] | str | None
    _ast_object: ast.FunctionDef = PrivateAttr()
    user_func: bool = False


# Type alias for variable types - can be simple strings or nested type lists
type VarType = str | list[VarType]

# TODO: Use this in the future for more structured type representation
# class VarType(BaseModel):
#     base_type: str
#     sub_types: list[VarType] = []


class Variable(BaseModel):
    """
    Represents a variable in the conversion process.
    
    This class stores metadata about variables encountered during AST processing,
    including type information and scope context.
    
    Attributes:
        name (str): The variable name
        is_param (bool): Whether this variable is a function parameter
        pytype (VarType): The inferred Python type
        lowest_val (int): Minimum value for optimization (future use)
        highest_val (int): Maximum value for optimization (future use)
    """
    
    name: str
    is_param: bool = False
    pytype: VarType = "Unknown"
    lowest_val: int = 0
    highest_val: int = 100

    def __hash__(self):
        """
        Hash function to allow Variable objects to be used in sets.
        
        Returns:
            int: Hash value based on the variable name
        """
        return hash(self.name)
    

class VisitContext(BaseModel):
    """
    Context information for AST node processing.
    
    This class maintains state during AST traversal, including indentation,
    printing control, scanning mode, and scope information.
    
    Attributes:
        current_indent (int): Current indentation level for code generation
        allow_print (bool | None): Whether to output generated code
        is_scanning (bool): Whether in scanning phase (type inference)
        scope (list[str]): Current nested scope path
    """
    
    current_indent: int = 0
    allow_print: bool | None = None
    is_scanning: bool = False
    scope: list[str] = ["global"]  # Nested scope

    def copy(self) -> VisitContext:
        """
        Create a copy of this context.
        
        Returns:
            VisitContext: A new context with copied values
        """
        return VisitContext(
            current_indent=self.current_indent,
            allow_print=self.allow_print,
            is_scanning=self.is_scanning,
            scope=self.scope.copy()
        )
    

class ReprVisitContext(BaseModel):
    """
    Context information for expression representation generation.
    
    This class provides context for the ReprVisitor when converting AST nodes
    to their C++ string representations.
    
    Attributes:
        processor (ExprParser): Reference to the main processor
        return_type (bool): Whether to return type information instead of code
        parser_ctx (VisitContext): The current parser context
        expr_node (ast.AST): The current expression node being processed
        prev_node (ast.AST | None): Previous node in the traversal
    """
    
    processor: "ExprParser"
    return_type: bool = False
    parser_ctx: VisitContext 
    expr_node: ast.AST
    prev_node: ast.AST | None = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def copy(self) -> ReprVisitContext:
        """
        Create a copy of this representation context.
        
        Returns:
            ReprVisitContext: A new context with copied values
        """
        return ReprVisitContext(
            processor=self.processor,
            return_type=self.return_type,
            parser_ctx=self.parser_ctx.copy(),
            expr_node=self.expr_node
        )
