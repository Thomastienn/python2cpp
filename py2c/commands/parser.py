import sys
import ast
from py2c.core.structure import Function, VisitContext
from py2c.core.processor import ExprParser
from py2c.utils.constants import HEADER, TAB

def parse(tree):
    funcs = {}
    normal_exps = []
    printer = ExprParser(funcs)
    for exp in tree.body:
        if isinstance(exp, ast.FunctionDef):
            myf = Function(
                name=exp.name,
                return_pytype=None,
                params=[],
            )
            myf._ast_object = exp
            funcs[exp.name] = myf
        else:
            normal_exps.append(exp)

    # Process the global scope first to know the type of arguments of functions
    for exp in normal_exps:
        printer.visit(exp, VisitContext(allow_print=False))

    # JUST A HEADER LIB
    print(HEADER)

    # ALL DECLARED FUNCTIONS
    for func in funcs.values():
        printer.visit(func._ast_object, VisitContext(scope=func.name, allow_print=True))
    print()

    # MAIN FUNCTION
    print("int main() {")
    for exp in normal_exps:
        printer.visit(exp, VisitContext(allow_print=True, current_indent=1))
    print(TAB + "return 0;")
    print("}")
