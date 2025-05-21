import ast
import re
import sys
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
        self.typed_nested_list = defaultdict(lambda : defaultdict(list))

    def add_var(self, name, v_type, scope="global"):
        self.typed_vars[scope][name] = v_type

    def add_nested_list(self, name, v_type, scope="global"):
        self.typed_nested_list[scope][name].append(v_type)
        
    def remove_var(self, name, scope="global"):
        del self.typed_vars[scope][name]

    def get_var_type(self, name, scope="global"):
        return self.typed_vars[scope][name]

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
    
    # Except for functions
    def get_pytype_from_str(self, s, visitor):
        for pattern in self.pattern_constants():
            match = re.match(pattern, s)
            if match:
                return type(eval(s)).__name__
        
        pattern_var = r"(\w+)"
        # Then this is a variable
        match_var = re.match(pattern_var, s)
        if match_var:
            var_name = match_var[1]
            return self.typed_vars[var_name]

        for t_name, pattern in self.pattern_pytype():
            match = re.match(pattern, s)
            if match:
                return t_name

        try:
            return_type = type(eval(s)).__name__
        except BaseException as e:
            return_type = visitor.visit(ast.parse(s).body[0].value, True)
        return return_type

    def python_to_cpp_type(self, t_name: str):
        if t_name is None:
            return "void"
        if t_name not in Linter.TYPES:
            raise NotImplementedError(f"Type {t_name} not implemented", type(t_name))
        return Linter.TYPES[t_name]

    def get_subscript_type(self, base_name, size, scope="global"):
        return self.typed_nested_list[scope][base_name][size-1]

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

        if "float" in case:
            return "float"

        return pytype_left


if __name__ == "__main__":
    linter = Linter()
    linter.get_pytype_from_str("map(int())")
