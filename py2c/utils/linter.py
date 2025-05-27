import ast
import re
import sys
from copy import deepcopy
from collections import defaultdict

from py2c.core.structure import Function


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
        "pair": "pair", # This doesnt exist but i want to make sure everything doesn't break.
        "None": "void",
    }
    def __init__(self, funcs: dict[str, Function]):
        self.typed_vars = defaultdict(dict)
        self.has_typed = defaultdict(lambda : defaultdict(bool))
        self.funcs = funcs

    def add_var(self, name, v_type, scope="global"):
        self.typed_vars[scope][name] = v_type

    def remove_var(self, name, scope="global"):
        del self.typed_vars[scope][name]

    def type_list_to_str(self, type_list: list[str]) -> str:
        return_type = "list<"
        n = len(type_list)
        for i, type_ in enumerate(type_list):
            return_type += type_
            if i != n - 1:
                return_type += "<"
        return_type += ">" * (n+1)
        return return_type

        
    def get_var_type(self, name, scope="global") -> str | list[str]:
        try:
            return_type = self.typed_vars[scope][name]
        except KeyError:
            try:
                # print(self.typed_vars, file=sys.stderr)
                # print(name, scope, file=sys.stderr)
                return_type = self.typed_vars["global"][name]
            except KeyError:
                raise KeyError(f"Variable {name} not found")
        return deepcopy(return_type)

    def add_func(self, name, f_type):
        self.typed_funcs[name] = f_type

    def get_func_type(self, name):
        return self.typed_funcs[name]

    def get_type_from_pyfunction(self, func_node: ast.Call) -> str:
        """
            Return the return pytype of a builtin function
        """
        func_name = func_node.func.id
        if func_name in Linter.TYPES:
            return func_name
        
        if func_name == "map":
            return func_node.args[0].id
        elif func_name == "input":
            return "str"
        elif func_name == "len":
            return "int"

        return func_name

    def pattern_pytype(self) -> list:
        return [
            ("list", r"\[(.*)\]|^list\((.*)\)"),
            ("set", r"\{[^:]\}|^set\((.*)\)"),
            ("dict", r"\{.+:{1,}.*\}|^dict\((.*)\)"),
            ("tuple", r".*,.*|^tuple\((.*)\)"),
        ]

    def pattern_constants(self):
        return [
            r"\bNone\b",
            r"\bTrue\b",
            r"\bFalse\b",
            r"\d+",
            r"float\(.+\)",
            r"int\(.+\)",
            r"\d+\.\d*([eE][+-]?\d+)?"
        ]
    
    def python_to_cpp_type(self, t_name: str | list[str]):
        if t_name is None:
            return "void"
        if isinstance(t_name, list):
            if len(t_name) == 1:
                return Linter.TYPES[t_name[0]]
            container_type = t_name[0]
            if container_type in ["list", "set"]:
                return f"{Linter.TYPES[container_type]}<{self.python_to_cpp_type(t_name[1:])}>"
            if container_type in ["pair", "tuple"]:
                return f"{container_type}<{', '.join(self.python_to_cpp_type(t) for t in t_name[1:])}>"
            raise NotImplementedError(f"{container_type} not implemented")
        if t_name not in Linter.TYPES:
            raise NotImplementedError(f"Type {t_name} not implemented", type(t_name))
        return Linter.TYPES[t_name]

    def get_subscript_type(self, base_name, size, scope="global"):
        return self.get_var_type(base_name, scope)[size]

    def get_binop_type(self, pytype_left, pytype_right, op: str):
        if pytype_left not in Linter.TYPES:
            pytype_left = self.get_var_type(pytype_left)
        if pytype_right not in Linter.TYPES:
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
