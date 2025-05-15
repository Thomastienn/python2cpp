import ast
from linter import Linter
from visitor import ReprVisitor
from structure import Function


class ASTPrinter:
    TAB = " " * 4

    def __init__(self, funcs):
        self.repr = ReprVisitor()
        self.funcs: list[Function] = funcs
        self.linter = Linter(self.funcs)
        self.allow_print = True

    def print_line(self, line: str, current_indent: int, end="\n", tab: bool = True):
        if self.allow_print:
            print(((self.TAB * current_indent) if tab else "") + line, end=end)

    def visit(self, node: ast.AST, current_indent: int = 0, allow_print: bool = True):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)

        original = self.allow_print
        self.allow_print = allow_print
        visitor(node, current_indent)
        self.allow_print = original

    def generic_visit(self, node, current_indent):
        print(node)  
        return

    def visit_Assign(self, node: ast.Assign, current_indent):
        self.print_line("ASSIGN: ", current_indent)
        targets = node.targets
        value = node.value
        value_str = self.repr.visit(value)
        
        type_name_val = self.linter.get_type_from_str(value_str)
        for target in targets:
            target_str = self.repr.visit(target)
            
            # Linter
            self.linter.add_var(target_str, type_name_val)
            cpp_type = self.linter.python_to_cpp_type(type_name_val)
            
            self.print_line(f"{cpp_type} {target_str} = {value_str}", current_indent)
        self.print_line("END ASSIGN", current_indent)

    def visit_AugAssign(self, node: ast.AugAssign, current_indent):
        self.print_line("AUG ASSIGN: ", current_indent, end="")
        self.print_line(self.repr.visit(node.target) + " " + \
                        self.repr.visit_op(node.op) + "=" + \
                        self.repr.visit(node.value)
                        ,tab=False)

    def visit_FunctionDef(self, node: ast.FunctionDef, current_indent):
        arguments = [arg.arg for arg in node.args.args]
        self.print_line(
            f"FUNCTION DEF: {node.name}({', '.join(arguments)})", current_indent)
        self.print_line("IN BODY: ", current_indent)
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        self.print_line("END", current_indent)

    def visit_For(self, node: ast.For, current_indent):
        self.print_line(
            f"FOR LOOP: for {self.repr.visit(node.target)} in {self.repr.visit(node.iter)}", current_indent)
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        self.print_line("END", current_indent)

    def visit_If(self, node: ast.If, current_indent):
        self.print_line(
            f"IF EXPRESSION: if {self.repr.visit(node.test)}", current_indent)
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        if node.orelse:
            self.print_line("ELSE EXP:", current_indent)
            for expr in node.orelse:
                self.visit(expr, current_indent + 1)
        self.print_line("END", current_indent)

    def visit_Return(self, node: ast.Return, current_indent):
        self.print_line("RETURN: ", current_indent, end="")
        self.print_line(self.repr.visit(node.value))

    def visit_While(self, node: ast.While, current_indent):
        self.print_line(
            f"WHILE EXPRESSION: while {self.repr.visit(node.test)}", current_indent)
        for expr in node.body:
            self.visit(expr, current_indent + 1)
        self.print_line("END", current_indent)

    def visit_Expr(self, node: ast.Expr, current_indent):
        self.print_line("EXPRESSION: ", current_indent, end="")
        self.print_line(self.repr.visit(node.value), tab=False)

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
