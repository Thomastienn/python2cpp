import sys
import ast
from linter import Linter
from visitor import ReprVisitor
from structure import Function, Parameter


class ExprParser:
    TAB = " " * 4

    def __init__(self, funcs: dict[str, Function]):
        self.repr = ReprVisitor()
        self.funcs = funcs
        self.linter = Linter()
        self.allow_print = True

    def print_line(self, line: str, current_indent: int, end="\n", tab: bool = True):
        if self.allow_print:
            print(((self.TAB * current_indent) if tab else "") + line, end=end)

    def visit(self, node: ast.AST, current_indent: int = 0, allow_print: bool = self.allow_print):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)

        original = self.allow_print
        self.allow_print = allow_print
        visitor(node, current_indent)
        self.allow_print = original

    def generic_visit(self, node, current_indent):
        print(node, file=sys.stderr)
        return

    def find_type_func(self, func_name, full_str, func_node):
        match_func = self.linter.is_func(full_str)
        if match_func:
            func_name = match_func[1]
            if func_name in self.linter.typed_funcs:
                return self.linter.typed_funcs[func_name]
            if func_name in self.funcs:
                return self.visit(func_node)
            
            return self.linter.get_type_from_pyfunction(func_name, full_str)
    
    def visit_Assign(self, node: ast.Assign, current_indent):
        # self.print_line("ASSIGN: ", current_indent)
        targets = node.targets
        value = node.value
        value_str = self.repr.visit(value)
        
        match_func_val = self.linter.is_func(value_str)
        # print("START: ", value_str, file=sys.stderr)
        if match_func_val:
            # print("IN 1", file=sys.stderr)
            type_name_val = self.find_type_func(match_func_val[1], value_str, value)
        else:
            # print("IN 2", file=sys.stderr)
            type_name_val = self.linter.get_pytype_from_str(value_str)
        # print("END: ", type_name_val, file=sys.stderr)
        
        for target in targets:
            target_str = self.repr.visit(target)
            
            # It's a tuple of variables
            if "," in target_str:
                for target_s in target_str.split(","):
                    self.linter.add_var(target_s, type_name_val)
            else:
                self.linter.add_var(target_str, type_name_val)
            cpp_type = self.linter.python_to_cpp_type(type_name_val)
            
            self.print_line(f"{cpp_type} {target_str} = {value_str}", current_indent)
        # self.print_line("END ASSIGN", current_indent)

    def visit_AugAssign(self, node: ast.AugAssign, current_indent):
        # self.print_line("AUG ASSIGN: ", current_indent, end="")
        self.print_line(self.repr.visit(node.target) + " " + \
                        self.repr.visit_op(node.op) + "=" + \
                        self.repr.visit(node.value)
                        , current_indent)

    def visit_Call(self, node: ast.Call, current_indent):
        func_name: str = node.func.id
        func: Function = self.funcs[func_name]

        # Now we know the type of parameters, put this in the info
        func_ast_obj = func._ast_object
        for func_param, arg in zip(func_ast_obj.args.args, node.args):
            # Get the type from argument and pass it to parameter
            new_param = Parameter(
                name = func_param.arg,
                pytype = self.linter.get_pytype_from_str(self.repr.visit(arg))
            )
            func.params.append(new_param)
            self.linter.add_var(new_param.name, new_param.pytype)

        # For keywords like a=1, b=(math.pi*2) something
        for arg, value in node.keywords:
            new_param = Parameter(
                name=arg,
                pytype=self.linter.get_pytype_from_str(self.repr.visit(value))
            )
            func.params.append(new_param)
            self.linter.add_var(new_param.name, new_param.pytype)

        # Now need to return the type by going to function definition
        return self.visit(func._ast_object, current_indent, allow_print=False)

    def visit_FunctionDef(self, node: ast.FunctionDef, current_indent):
        def ctype_arg(name):
            return self.linter.python_to_cpp_type(self.linter.get_var_type(name))
        arguments = [(ctype_arg(arg.arg) + arg.arg) for arg in node.args.args]

        # GUESS WHAT THE RETURN TYPE IS
        expected_return_type = "None"
        walk_already = {node.name}
        for expr in node.body:
            if isinstance(expr, ast.Return):
                return_val = expr.value
                
                # My linter does not support functions
                if isinstance(return_val, ast.Call):
                    name_func = return_val.name
                    # Skip some type of recursion
                    if name_func in walk_already:
                        continue
                    walk_already.add(name_func)
                    if expected_return_type == None:
                        expected_return_type = self.visit(return_val, current_indent + 1, allow_print=False)
                else:
                    if expected_return_type == None:
                        expected_return_type = self.linter.get_pytype_from_str(self.repr.visit(return_val))
            self.visit(expr, current_indent + 1, allow_print=False)
        return expected_return_type
            
        # PRINT FORMAT FUCNTION
        self.print_line(f"{self.linter.get_func_type(node.name)} {node.name}({', '.join(arguments)}) {{", current_indent)
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        self.print_line("}", current_indent)
        

    def visit_For(self, node: ast.For, current_indent):
        # self.print_line(
            # f"FOR LOOP: for {self.repr.visit(node.target)} in {self.repr.visit(node.iter)}", current_indent)
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        # self.print_line("END", current_indent)

    def visit_If(self, node: ast.If, current_indent):
        self.print_line(
            f"if ({self.repr.visit(node.test)}) {{", current_indent)
    
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        self.print_line("}", current_indent)
            
        if node.orelse:
            # self.print_line("ELSE EXP:", current_indent)
            self.print_line("else {", current_indent)
            for expr in node.orelse:
                self.visit(expr, current_indent + 1)
            self.print_line("}", current_indent)
        # self.print_line("END", current_indent)

    def visit_Return(self, node: ast.Return, current_indent):
        # self.print_line("RETURN: ", current_indent, end="")
        self.print_line(self.repr.visit(node.value))

    def visit_While(self, node: ast.While, current_indent):
        self.print_line(
            f"while ({self.repr.visit(node.test)}) {{", current_indent)
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        self.print_line("}", current_indent)

    def visit_Expr(self, node: ast.Expr, current_indent):
        # self.print_line("EXPRESSION: ", current_indent, end="")
        self.print_line(self.repr.visit(node.value),current_indent, tab=False)

    def visit_Pass(self, node: ast.Pass, current_indent):
        pass

    def visit_Load(self, node: ast.Load, current_indent):
        pass

    def visit_Store(self, node: ast.Store, current_indent):
        pass

# Usage example:

# repr = ReprVisitor()
# printer = ASTPrinter(repr)
# tree = ast.parse(your_code_string)
# for node in tree.body:
#     printer.visit(node)
