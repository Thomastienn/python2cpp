import re
import sys
from structure import Function

class Linter:
    def __init__(self):
        self.typed_vars = {}
        self.typed_funcs = {}

    def add_var(self, name, v_type):
        self.typed_vars[name] = v_type
        
    def remove_var(self, name):
        del self.typed_vars[name]

    def get_var_type(self, name):
        return self.typed_vars[name]

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
    def get_pytype_from_str(self, s):
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

        print("DEBUG: ", s, file=sys.stderr)
        return type(eval(s)).__name__

    def python_to_cpp_type(self, t_name: str):
        mp = {
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
        if t_name not in mp:
            raise NotImplementedError(f"Type {t_name} not implemented", type(t_name))
        return mp[t_name]

if __name__ == "__main__":
    linter = Linter()
    linter.get_pytype_from_str("map(int())")
