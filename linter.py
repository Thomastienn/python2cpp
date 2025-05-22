import ast
import re
import sys
from copy import deepcopy
from structure import Function
from collections import defaultdict

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
    def __init__(self):
        self.typed_vars = defaultdict(dict)
        self.typed_funcs = {}

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
        print(name, scope, file=sys.stderr)
        try:
            return_type = self.typed_vars[scope][name]
        except KeyError:
            try:
                return_type = self.typed_vars["global"][name]
            except KeyError:
                raise KeyError(f"Variable {name} not found")
        return deepcopy(return_type)

    def add_func(self, name, f_type):
        self.typed_funcs[name] = f_type

    def get_func_type(self, name):
        return self.typed_funcs[name]


    def get_type_from_pyfunction(self, func_name, full_str):
        if func_name == "map":
            regex_map = r"map\((\w+),.+\)"
            type_to = re.match(regex_map, full_str)[1]
            return self.python_to_cpp_type(type_to)
        raise NotImplementedError(f"Function {func_name} not implemented")

    def pattern_pytype(self) -> list:
        return [
            ("list", r"\[(.*)\]|^list\((.*)\)"),
            ("set", r"\{[^:]\}|^set\((.*)\)"),
            ("dict", r"\{.+:{1,}.*\}|^dict\((.*)\)"),
            ("tuple", r".*,.*|^tuple\((.*)\)"),
        ]

    def is_func(self, string: str):
        pattern_func = r"^(\w+)\(.*\)"
        # Then this is a function if match
        match_func = re.match(pattern_func, string)
        return match_func

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
            return f"{Linter.TYPES[t_name[0]]}<{self.python_to_cpp_type(t_name[1:])}>"
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
            raise NotImplementedError
            
        if "str" in case and "int" in case:
            return "str"

        if "float" in case:
            return "float"

        return pytype_left
