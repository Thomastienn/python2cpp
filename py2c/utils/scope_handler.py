import sys
import ast

from py2c.utils.linter import Linter


class ScopeHandler:
    @staticmethod
    def additional_scope(node: ast.AST, current_scope: list[str], linter: Linter) -> list[str]:
        """
        Returns a list of additional scopes that the node might require.
        This is used to determine if the node needs to be processed in a specific scope.
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

            # Check if function exists in linter's funcs dict first
            # If it's a user function, it should be in the same scope as where it was defined
            if func_name in linter.funcs:
                # User-defined functions are typically in global scope
                if linter.funcs[func_name].user_func:
                    return ["global"]  # User functions are in global scope
                else:
                    return current_scope  # Template functions use current scope
            
            # Try to find the function in scope system, but handle case where it doesn't exist yet
            try:
                return linter.find_scope_by_var(func_name, findVar=False, findFunc=True, scope=current_scope)
            except KeyError:
                # If function not found in scope system yet (during scanning), assume global scope
                return ["global"]
        # if isinstance(node, ast.If):
        #     return [f"if_{id(node)}"]

        return current_scope

    @staticmethod
    def is_in_function_scope(current_scope: list[str]) -> bool:
        """
        Check if the current_scope is within a function scope.
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
