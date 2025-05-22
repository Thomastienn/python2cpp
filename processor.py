import sys
import ast
from linter import Linter
from visitor import ReprVisitor
from structure import Function, VisitContext


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
        
        print(self.linter.typed_vars, file=sys.stderr)
        print(visit_ctx, file=sys.stderr)
        print(node, file=sys.stderr)
        print("-" * 20, file=sys.stderr)
        result = visitor(node, VisitContext(
            current_indent=visit_ctx.current_indent,
            allow_print=allow_print,
            scope=visit_ctx.scope
        ))
        self.allow_print = original
        return result

    def generic_visit(self, node, visit_ctx: VisitContext):
        print("NOT IMPLEMENTED: ",node, file=sys.stderr)
        return

    def find_type_func(self, func_name, full_str, func_node, visit_ctx: VisitContext):
        match_func = self.linter.is_func(full_str)
        if match_func:
            func_name = match_func[1]
            if func_name in self.linter.typed_funcs:
                return self.linter.typed_funcs[func_name]
            if func_name in self.funcs:
                return self.visit(func_node, visit_ctx)

            return self.linter.get_type_from_pyfunction(func_name, full_str)

    def visit_Assign(self, node: ast.Assign, visit_ctx: VisitContext):
        # self.print_line("ASSIGN: ", current_indent)
        targets = node.targets
        value = node.value
        value_str = self.repr.visit(value, scope=visit_ctx.scope)

        match_func_val = self.linter.is_func(value_str)
        if match_func_val:
            type_name_val = self.find_type_func(match_func_val[1], value_str, value, visit_ctx)
        else:
            type_name_val = self.repr.visit(value, return_type=True, scope=visit_ctx.scope) 

        cpp_type = self.linter.python_to_cpp_type(type_name_val)
        for target in targets:
            target_str = self.repr.visit(target, scope=visit_ctx.scope)

            # It's a tuple of variables
            if "," in target_str:
                for target_s in target_str.split(","):
                    self.linter.add_var(target_s, type_name_val, scope=visit_ctx.scope)
            else:
                self.linter.add_var(target_str, type_name_val, scope=visit_ctx.scope)

            self.print_line(f"{cpp_type} {target_str} = {value_str};", visit_ctx.current_indent)

        return "None"

    def visit_AugAssign(self, node: ast.AugAssign, visit_ctx: VisitContext):
        # self.print_line("AUG ASSIGN: ", current_indent, end="")
        self.print_line(self.repr.visit(node.target) + " " + \
                        self.repr.visit_op(node.op) + "= " + \
                        self.repr.visit(node.value) + ";"
                        , visit_ctx.current_indent)
        return "None"

    def visit_Call(self, node: ast.Call, visit_ctx: VisitContext):
        func_name: str = node.func.id
        func: Function = self.funcs[func_name]
        print(func, file=sys.stderr)
        if func.return_pytype is not None:
            return func.return_pytype

        # Now we know the type of parameters, put this in the info
        func_ast_obj = func._ast_object
        for func_param, arg in zip(func_ast_obj.args.args, node.args):
            # Get the type from argument and pass it to parameter
            type_ = self.repr.visit(arg, return_type=True, scope=visit_ctx.scope)
            self.linter.add_var(func_param.arg, type_, scope=func_name)

        # For keywords like a=1, b=(math.pi*2) something
        for arg, value in node.keywords:
            type_ = self.repr.visit(arg, return_type=True, scope=visit_ctx.scope)
            self.linter.add_var(arg, type_, scope=func_name)

        # Now need to return the type by going to function definition
        new_ctx = VisitContext(
            current_indent=visit_ctx.current_indent,
            allow_print = False,
            scope=func._ast_object.name
        )
        return_type = self.visit(func._ast_object, new_ctx)
        func.return_pytype = return_type
        return return_type
                          
    def visit_FunctionDef(self, node: ast.FunctionDef, visit_ctx: VisitContext):
        def pytype_arg(name):
            type_ = self.linter.get_var_type(name, scope=visit_ctx.scope)
            return type_
        def ctype_arg(name):
            return self.linter.python_to_cpp_type(pytype_arg(name))
        arguments = [(ctype_arg(arg.arg) + " " + arg.arg) for arg in node.args.args]

        # GUESS WHAT THE RETURN TYPE IS
        expected_return_type = "None"
        walk_already = {node.name}
        for expr in node.body:
            if isinstance(expr, ast.Return):
                return_val = expr.value

                if isinstance(return_val, ast.Call):
                    name_func = return_val.name
                    # Skip some type of recursion
                    if name_func in walk_already:
                        continue
                    walk_already.add(name_func)
                    if expected_return_type == "None":
                        new_ctx = VisitContext(
                            current_indent = visit_ctx.current_indent + 1,
                            allow_print = False,
                            scope = name_func
                        )
                        expected_return_type = self.visit(return_val, new_ctx)
                else:
                    if expected_return_type == "None":
                        expected_return_type = self.repr.visit(return_val, return_type=True, scope=node.name)

            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                allow_print = False,
                scope = node.name,
            )
            self.visit(expr, new_ctx)
            
        # PRINT FORMAT FUCNTION
        self.print_line(f"{self.linter.python_to_cpp_type(expected_return_type)} {node.name}({', '.join(arguments)}) {{", visit_ctx.current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope = visit_ctx.scope,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)
        
        return expected_return_type


    def visit_For(self, node: ast.For, visit_ctx: VisitContext):
        self.print_line(f"for ({self.repr.visit(node.target)} in {self.repr.visit(node.iter)}) {{", visit_ctx.current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope = visit_ctx.scope,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

    def visit_If(self, node: ast.If, visit_ctx: VisitContext):
        self.print_line(
            f"if ({self.repr.visit(node.test)}) {{", visit_ctx.current_indent)

        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope=visit_ctx.scope,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

        if node.orelse:
            # self.print_line("ELSE EXP:", current_indent)
            self.print_line("else {", visit_ctx.current_indent)
            for expr in node.orelse:
                new_ctx = VisitContext(
                    current_indent = visit_ctx.current_indent + 1,
                    scope=visit_ctx.scope,
                )
                self.visit(expr, new_ctx)
            self.print_line("}", visit_ctx.current_indent)
        # self.print_line("END", current_indent)

    def visit_Return(self, node: ast.Return, visit_ctx: VisitContext):
        # self.print_line("RETURN: ", current_indent, end="")
        self.print_line(f"return {self.repr.visit(node.value)};", visit_ctx.current_indent)

    def visit_While(self, node: ast.While, visit_ctx: VisitContext):
        self.print_line(
            f"while ({self.repr.visit(node.test)}) {{", visit_ctx.current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope=visit_ctx.scope,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

    def visit_Expr(self, node: ast.Expr, visit_ctx: VisitContext):
        # self.print_line("EXPRESSION: ", current_indent, end="")
        value = self.repr.visit(node.value)
        self.print_line(value, visit_ctx.current_indent)
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
