"""
Scope Management for Python to C++ Conversion

This module provides utilities for managing variable and function scopes
during the AST traversal and conversion process. It handles scope resolution,
nested scope creation, and scope-based lookups.

The ScopeHandler class provides static methods for determining appropriate
scopes for different AST nodes and managing scope hierarchies.

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

import sys
import ast

from py2c.utils.typeinferencer import TypeInferencer
from py2c.core.errors import typeinferencerError


class ScopeHandler:
    """
    Utility class for managing variable and function scopes during conversion.
    
    This class provides static methods to determine appropriate scopes for
    different AST nodes and manage scope hierarchies during the conversion process.
    """
    
    @staticmethod
    def additional_scope(node: ast.AST, current_scope: list[str], typeinferencer: TypeInferencer) -> list[str]:
        """
        Determine the appropriate scope for an AST node.
        
        This method analyzes AST nodes and returns the scope that should be used
        for processing the node, taking into account nested scopes like functions,
        loops, and conditionals.
        
        Args:
            node (ast.AST): The AST node to analyze
            current_scope (list[str]): Current scope path
            typeinferencer (typeinferencer): The typeinferencer instance for scope lookups
        
        Returns:
            list[str]: The appropriate scope path for the node
        """
        if isinstance(node, ast.For):
            return current_scope + [f"for_{id(node)}"]
        if isinstance(node, ast.FunctionDef):
            return current_scope + [node.name]
        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name =  node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            assert func_name is not None, f"Function node is node {node.func}"

            # Check if function exists in typeinferencer's funcs dict first
            # If it's a user function, it should be in the same scope as where it was defined
            if func_name in typeinferencer.funcs:
                # User-defined functions are typically in global scope
                if typeinferencer.funcs[func_name].user_func:
                    return ["global"]  # User functions are in global scope
                else:
                    return current_scope  # Template functions use current scope
            
            # Try to find the function in scope system, but handle case where it doesn't exist yet
            try:
                return typeinferencer.find_scope_by_var(func_name, findVar=False, findFunc=True, scope=current_scope)
            except typeinferencerError:
                # If function not found in scope system yet (during scanning), assume global scope
                return ["global"]
        # if isinstance(node, ast.If):
        #     return [f"if_{id(node)}"]

        return current_scope

    @staticmethod
    def is_in_function_scope(current_scope: list[str]) -> bool:
        """
        Check if the current scope is within a function scope.
        
        This method examines the scope path to determine if the current
        context is inside a function definition.
        
        Args:
            current_scope (list[str]): Current scope path to check
        
        Returns:
            bool: True if currently in a function scope, False otherwise
        """
        for i in range(len(current_scope) - 1, -1, -1):
            if current_scope[i] == "global":
                return False
            if current_scope[i].startswith("for"):
                continue
            if current_scope[i].startswith("if"):
                continue
            return True

        return False
