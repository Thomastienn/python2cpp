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
        "pair": "pair", 
        "auto": "auto",
        "Unknown": "Unknown",
    }
    def __init__(self, funcs: dict[str, Function]):
        self.typed_vars = {
            "global": {},
        }
        self.has_typed = {
            "global": {},
        }
        self.funcs = funcs

    def add_var(self, name, v_type, scope=["global"]):
        cur_scope = self.typed_vars
        for s in scope:
            if s not in cur_scope:
                cur_scope[s] = {}
            cur_scope = cur_scope[s]
        new_var = Variable(
            name=name,
            pytype=v_type
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
        for s in scope:
            if s not in cur_scope:
                return False
            cur_scope = cur_scope[s]
        return name in cur_scope and cur_scope[name]

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
                var: Variable = s[name]
                return var.pytype
                
        # If variable not found in provided scope, try to search in nested scopes
        # This handles cases where variables are defined in for loops or other nested constructs
        def search_recursive(scope_dict, target_name):
            if target_name in scope_dict and isinstance(scope_dict[target_name], Variable):
                return scope_dict[target_name].pytype
            for key, value in scope_dict.items():
                if isinstance(value, dict):
                    result = search_recursive(value, target_name)
                    if result is not None:
                        return result
            return None
            
        # Search recursively starting from the innermost scope
        result = search_recursive(cur, name)
        if result is not None:
            return result

        raise KeyError(f"Variable {name} not found in scope {scope} and upper, current stack {cur}, current scope stack {debug_st}, all vars:  \n\n{self.typed_vars}\n\n")

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
            if len(t_name) == 1:
                # Handle single element list - check for Unknown first
                if t_name[0] == "Unknown":
                    return "auto"
                return Linter.TYPES[t_name[0]]
            container_type = t_name[0]
            # Handle Unknown container type
            if container_type == "Unknown":
                return "auto"
            if container_type in ["list", "set"]:
                return f"{Linter.TYPES[container_type]}<{self.python_to_cpp_type(t_name[1:])}>"
            if container_type in ["pair", "tuple"]:
                return f"{container_type}<{', '.join(self.python_to_cpp_type(t) for t in t_name[1:])}"
            # Check if the first element is actually a basic type, not a container
            # This handles cases where the type system produces malformed type representations
            if container_type in Linter.TYPES:
                # This seems to be a malformed type list - just return the first element's type
                # This is a fallback for cases where type inference produces incorrect structures
                return Linter.TYPES[container_type]
            raise NotImplementedError(f"{container_type} not implemented")
        if t_name in Linter.CAST_TYPES:
            return Linter.CAST_TYPES[t_name]
        if t_name == "Unknown":
            return "auto"  # Use auto for unknown types during scanning
        if t_name not in Linter.TYPES:
            raise NotImplementedError(f"Type {t_name} not implemented", type(t_name))
        return Linter.TYPES[t_name]

    def get_subscript_type(self, base_name, size, scope=["global"]):
        try:
            base_type = self.get_var_type(base_name, scope)
            if base_type == "Unknown":
                return "Unknown"
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

        if "list" in case and "int" in case:
            if op == "*":
                return "list"
            raise SyntaxError(f"Cannot add int and list not implemented")
            
        if "str" in case and "int" in case:
            return "str"

        if "float" in case:
            return "float"

        return pytype_left
