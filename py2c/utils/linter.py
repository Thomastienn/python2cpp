import ast
import re
import sys
from copy import deepcopy
from collections import defaultdict

from py2c.core.structure import Function, Variable


class Linter:
    TYPES = {
        "int": "int",
        "float": "float",
        "bool": "bool",
        "str": "string",
        "list": "vector",
        "dict": "map",
        "set": "set",
        "tuple": "tuple",
        "None": "void",
    }
    CAST_TYPES = {
        "char": "char",
        "pair": "pair", 
        "auto": "auto",
        "ll": "long long",
        "Unknown": "auto",
    }
    MAP_VALUE = {
        "True": "true",
        "False": "false",
        "None": "nullptr",
    }

    def __init__(self, funcs: dict[str, Function]):
        self.typed_vars = {
            "global": {},
        }
        self.has_typed = {
            "global": {},
        }
        self.funcs = funcs
        self.actual_global_vars = set()

    def add_var(self, name, v_type, scope=["global"], **kwargs):
        cur_scope = self.typed_vars
        for s in scope:
            if s not in cur_scope:
                cur_scope[s] = {}
            cur_scope = cur_scope[s]
        new_var = Variable(
            name=name,
            pytype=v_type,
            **kwargs
        )
        cur_scope[name] = new_var

    def set_has_type(self, name, scope=["global"]):
        cur_scope = self.has_typed
        for s in scope:
            if s not in cur_scope:
                cur_scope[s] = {}
            cur_scope = cur_scope[s]
        cur_scope[name] = True

    def has_higher_scope_var(self, name, scope=["global"]):
        """
            Check if a variable has been declared in a higher scope
            params:
                name: The name of the variable
                scope: The full nested scope of the variable
            returns:
                True if the variable has been declared in a higher scope
                False otherwise
        """
        if len(scope) == 1:
            return False
        cur_scope = self.typed_vars
        in_order = []
        debug_inorder = []
        for s in scope:
            cur_scope = cur_scope[s]
            in_order.append(cur_scope)
            debug_inorder.append(s)
        
        for cur_s in list(reversed(in_order[1:])):
            if name in cur_s:
                return True

        return False

    def does_has_type(self, name, scope=["global"]):
        cur_scope = self.has_typed
        scope_refs = []
        
        # Build list of scope references from outermost to innermost
        # Stop when we can't find a scope (but still check parent scopes)
        for s in scope:
            if s not in cur_scope:
                break
            cur_scope = cur_scope[s]
            scope_refs.append(cur_scope)
        
        # Check from innermost to outermost scope
        for scope_ref in reversed(scope_refs):
            if name in scope_ref and scope_ref[name]:
                return True
        
        return False

    def unset_has_type(self, name, scope=["global"]):
        cur_scope = self.has_typed
        for s in scope:
            assert s in cur_scope, "Scope not found"
            cur_scope = cur_scope[s]
        cur_scope[name] = False

    def remove_var(self, name, scope=["global"]):
        cur_scope = self.typed_vars
        for s in scope:
            assert s in cur_scope, "Scope not found"
            cur_scope = cur_scope[s]
        del cur_scope[name]

    def type_list_to_str(self, type_list: list[str]) -> str:
        return_type = "list<"
        n = len(type_list)
        for i, type_ in enumerate(type_list):
            return_type += type_
            if i != n - 1:
                return_type += "<"
        return_type += ">" * (n+1)
        return return_type

    def get_var(self, name, scope=["global"], return_scope_found=False) -> Variable:
        cur = self.typed_vars
        st = []
        debug_st = []
        for s in scope:
            assert s in cur, f"Scope not found \"{s}\" in {scope}, stop finding {name}, current stack {cur}, current scope stack {debug_st}, all vars:  \n\n{self.typed_vars}\n\n"
            cur = cur[s]
            st.append(cur)
            debug_st.append(s)
        while st:
            s = st.pop()
            if name in s:
                return (s[name], debug_st) if return_scope_found else s[name]
            debug_st.pop()
        
        # If not found in the direct scope hierarchy, also check global scope
        if scope != ["global"] and "global" in self.typed_vars:
            global_scope = self.typed_vars["global"]
            if name in global_scope and isinstance(global_scope[name], Variable):
                return (global_scope[name], ["global"]) if return_scope_found else global_scope[name]
                
        # If variable not found in provided scope, try to search in nested scopes
        # This handles cases where variables are defined in for loops or other nested constructs
        def search_recursive(scope_dict, target_name, prev_func):
            if target_name in scope_dict and isinstance(scope_dict[target_name], Variable):
                return (scope_dict[target_name], prev_func) if return_scope_found else scope_dict[target_name]
            for key, value in scope_dict.items():
                if isinstance(value, dict):
                    result = search_recursive(value, target_name, key)
                    if result is not None:
                        return result 
            return None
            
        # Search recursively starting from the innermost scope
        result = search_recursive(cur, name, None)
        if result is not None:
            return result

        raise KeyError(f"Variable {name} not found in scope {scope} and upper, current stack {cur}, current scope stack {debug_st}, all vars:  \n\n{self.typed_vars}\n\n")

    def get_var_type(self, name, scope=["global"]) -> str | list[str]:
        """
            Get the type of a variable by going from innermost to outermost
            params:
                name: The name of the variable
                scope: The full nested scope of the variable
            returns:
                The type of the variable if found
                raise KeyError if not found
        """
        return self.get_var(name, scope).pytype

    def find_scope_by_var(self, name, findVar=False, findFunc=True, scope=["global"]):
        """
        Find the scope of a variable/function by going from innermost to outermost.
        params:
            name: The name of the variable/function
            scope: The current scope we are in
        """
        assert findVar != findFunc, "Cannot find both variable and function at the same time"

        cur = self.typed_vars
        st = []
        st_str = []
        for s in scope:
            assert s in cur, f"Scope not found \"{s}\" in {scope}, stop finding {name}, current stack {cur}, current scope stack {st_str}, all vars:  \n\n{self.typed_vars}\n\n"
            cur = cur[s]
            st.append(cur)
            st_str.append(s)

        while st:
            s = st.pop()
            st_str.pop()
            if name in s:
                if findVar and isinstance(s[name], Variable):
                    return deepcopy(st_str)
                if findFunc and isinstance(s[name], dict):
                    return deepcopy(st_str)
        
        raise KeyError(f"Variable/Function {name} not found in scope {scope} and upper, current stack {cur}, current scope stack {st_str}, all vars:  \n\n{self.typed_vars}\n\n")

    def add_func(self, name, f_type):
        self.typed_funcs[name] = f_type

    def get_func_type(self, name):
        return self.typed_funcs[name]

    def python_to_cpp_type(self, t_name: str | list[str]):
        if t_name is None:
            return "void"
        if isinstance(t_name, list):
            return f"{self.python_to_cpp_type(t_name[0])}<{', '.join(self.python_to_cpp_type(t) for t in t_name[1:])}>"
        if t_name in Linter.CAST_TYPES:
            return Linter.CAST_TYPES[t_name]
        if t_name in Linter.TYPES:
            return Linter.TYPES[t_name]
            
        raise NotImplementedError(f"Type {t_name} not implemented", type(t_name))

    def get_subscript_type(self, base_name, size, scope=["global"]):
        try:
            base_type = self.get_var_type(base_name, scope)
            if base_type == "Unknown":
                return "Unknown"
            if base_type == "str" or \
                (isinstance(base_type, list) and base_type[-1] == "str" \
                 and size == len(base_type)):
                return "char"
            return base_type[size]
        except (KeyError, IndexError, TypeError):
            # If we can't determine the subscript type, return Unknown
            return "Unknown"

    def get_attr_type(self, pytype_from, attr: str):
        if attr == "split":
            return ["list", "str"]
        if attr in ["strip", "lower", "upper", "replace"]:
            return "str"
        if attr in ["sort", "reverse"]:
            return pytype_from
        if attr == "pop":
            return pytype_from[1:]
        if attr == "bit_length":
            return "int"
    
        raise NotImplementedError(f"Attribute {attr} not implemented")

    def is_list_repeatition(self, pytype_left, pytype_right, op: str):
        if op != "*":
            return False
        return (isinstance(pytype_left, list) and pytype_left[0] == "list" and pytype_right=="int") or \
            (isinstance(pytype_right, list) and pytype_right[0] == "list" and pytype_left=="int")

    
    def get_binop_type(self, pytype_left, pytype_right, op: str):
        if not isinstance(pytype_left, list) and \
            pytype_left not in Linter.TYPES and \
            pytype_left != "Unknown":
            pytype_left = self.get_var_type(pytype_left)
        if not isinstance(pytype_right, list) and \
            pytype_right not in Linter.TYPES and \
            pytype_right != "Unknown":
            pytype_right = self.get_var_type(pytype_right)
        
        case = (pytype_left, pytype_right)
        if self.is_list_repeatition(pytype_left, pytype_right, op):
            return pytype_left if isinstance(pytype_left, list) else pytype_right
            
        if "str" in case and "int" in case:
            return "str"

        if "float" in case:
            return "float"

        return pytype_left

    def get_pytype_from_annotations(self, annotations: ast.AST) -> str | list[str]:
        """
        Extract type information from function annotations.
        """
        if isinstance(annotations, (ast.Constant, ast.List)):
            raise ValueError(f"Annotations shouldn't have {type(annotations)}, got {annotations.value}")

        if isinstance(annotations, ast.Name):
            return annotations.id
        if isinstance(annotations, ast.Subscript):
            base = annotations.value
            if not isinstance(base, ast.Name):
                raise ValueError(f"Subscript base should be a Name, got {type(base)}")
            base_type = base.id
            type_ = self.get_pytype_from_annotations(annotations.slice)
            if isinstance(annotations.slice, ast.Tuple):
                return [base_type, *type_]
            return [base_type, type_]
            
        if isinstance(annotations, ast.Tuple):
            return [self.get_pytype_from_annotations(elt) for elt in annotations.elts]
        
        
        raise NotImplementedError(f"Annotation type {type(annotations)} not implemented")
