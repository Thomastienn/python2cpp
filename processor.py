import sys
import ast
from linter import Linter
from visitctx import VisitContext
from visitor import ReprVisitor
from structure import Function, Parameter


class ExprParser:
    TAB = " " * 4

    def __init__(self, funcs: dict[str, Function]):
        self.funcs = funcs
        self.linter = Linter()
        self.repr = ReprVisitor(self.linter)
        self.allow_print = True

    def print_line(self, line: str, current_indent: int, end="\n", tab: bool = True):
        if self.allow_print:
            print(((self.TAB * current_indent) if tab else "") + line, end=end)

    def visit(self, node: ast.AST, visit_ctx: VisitContext = VisitContext()):
        if visit_ctx.allow_print is None:
            allow_print = self.allow_print
        else:
            allow_print = visit_ctx.allow_print
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)

        original = self.allow_print
        self.allow_print = allow_print
        visitor(node, VisitContext(
            allow_print=allow_print,
        ))
        self.allow_print = original

    def generic_visit(self, node, visit_ctx: VisitContext):
        print("NOT IMPLEMENTED: ",node, file=sys.stderr)
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

    def visit_Assign(self, node: ast.Assign, visit_ctx: VisitContext):
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
            type_name_val = self.linter.get_pytype_from_str(value_str, self.repr)
        # print("END: ", type_name_val, file=sys.stderr)

        cpp_type = self.linter.python_to_cpp_type(type_name_val)
        # print(self.linter.typed_vars, file=sys.stderr)
        # print(self.linter.typed_nested_list, file=sys.stderr)
        for target in targets:
            target_str = self.repr.visit(target)

            # It's a tuple of variables
            if "," in target_str:
                for target_s in target_str.split(","):
                    self.linter.add_var(target_s, type_name_val)
            else:
                self.linter.add_var(target_str, type_name_val)
                if type_name_val == "list":
                    all_types = self.repr.visit(value, True)
                    if isinstance(all_types, list):
                        for t in all_types:
                            self.linter.add_nested_list(target_str, t)
                    else:
                        self.linter.add_nested_list(target_str, all_types)

            self.print_line(f"{cpp_type} {target_str} = {value_str}", visit_ctx.current_indent)
        # self.print_line("END ASSIGN", current_indent)

        # print("-"*20, file=sys.stderr)
        return "None"

    def visit_AugAssign(self, node: ast.AugAssign, visit_ctx: VisitContext):
        # self.print_line("AUG ASSIGN: ", current_indent, end="")
        self.print_line(self.repr.visit(node.target) + " " + \
                        self.repr.visit_op(node.op) + "=" + \
                        self.repr.visit(node.value)
                        , visit_ctx.current_indent)
        return "None"

    def visit_Call(self, node: ast.Call, visit_ctx: VisitContext):
        func_name: str = node.func.id
        func: Function = self.funcs[func_name]

        # Now we know the type of parameters, put this in the info
        func_ast_obj = func._ast_object
        for func_param, arg in zip(func_ast_obj.args.args, node.args):
            # Get the type from argument and pass it to parameter
            new_param = Parameter(
                name = func_param.arg,
                pytype = self.linter.get_pytype_from_str(self.repr.visit(arg), self.repr)
            )
            func.params.append(new_param)
            self.linter.add_var(new_param.name, new_param.pytype)

        # For keywords like a=1, b=(math.pi*2) something
        for arg, value in node.keywords:
            new_param = Parameter(
                name=arg,
                pytype=self.linter.get_pytype_from_str(self.repr.visit(value), self.repr)
            )
            func.params.append(new_param)
            self.linter.add_var(new_param.name, new_param.pytype)

        # Now need to return the type by going to function definition
        new_ctx = VisitContext(
            allow_print = False,
        )
        return self.visit(func._ast_object, new_ctx)

    def visit_FunctionDef(self, node: ast.FunctionDef, visit_ctx: VisitContext):
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
                        new_ctx = VisitContext(
                            current_indent = visit_ctx.current_indent + 1,
                            allow_print = False,
                        )
                        expected_return_type = self.visit(return_val, new_ctx)
                else:
                    if expected_return_type is None:
                        expected_return_type = self.linter.get_pytype_from_str(self.repr.visit(return_val), self.repr)

            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                allow_print = False,
            )
            self.visit(expr, new_ctx)
        return expected_return_type

        # PRINT FORMAT FUCNTION
        self.print_line(f"{self.linter.get_func_type(node.name)} {node.name}({', '.join(arguments)}) {{", visit_ctx.current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)


    def visit_For(self, node: ast.For, visit_ctx: VisitContext):
        # self.print_line(
            # f"FOR LOOP: for {self.repr.visit(node.target)} in {self.repr.visit(node.iter)}", current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
            )
            self.visit(expr, new_ctx)
        # self.print_line("END", current_indent)

    def visit_If(self, node: ast.If, visit_ctx: VisitContext):
        self.print_line(
            f"if ({self.repr.visit(node.test)}) {{", visit_ctx.current_indent)

        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

        if node.orelse:
            # self.print_line("ELSE EXP:", current_indent)
            self.print_line("else {", visit_ctx.current_indent)
            for expr in node.orelse:
                new_ctx = VisitContext(
                    current_indent = visit_ctx.current_indent + 1,
                )
                self.visit(expr, new_ctx)
            self.print_line("}", visit_ctx.current_indent)
        # self.print_line("END", current_indent)

    def visit_Return(self, node: ast.Return, visit_ctx: VisitContext):
        # self.print_line("RETURN: ", current_indent, end="")
        self.print_line(self.repr.visit(node.value), visit_ctx.current_indent)

    def visit_While(self, node: ast.While, visit_ctx: VisitContext):
        self.print_line(
            f"while ({self.repr.visit(node.test)}) {{", visit_ctx.current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

    def visit_Expr(self, node: ast.Expr, visit_ctx: VisitContext):
        # self.print_line("EXPRESSION: ", current_indent, end="")
        value = self.repr.visit(node.value)
        self.print_line(value, visit_ctx.current_indent, tab=False)
        return type(value).__name__

    def visit_Pass(self, node: ast.Pass, visit_ctx: VisitContext):
        pass

    def visit_Load(self, node: ast.Load, visit_ctx: VisitContext):
        pass

    def visit_Store(self, node: ast.Store, visit_ctx: VisitContext):
        pass

# Usage example:

# repr = ReprVisitor()
# printer = ASTPrinter(repr)
# tree = ast.parse(your_code_string)
# for node in tree.body:
#     printer.visit(node)
