import sys
import ast
from py2c.core.structure import Function, VisitContext, ReprVisitContext
from py2c.core.processor import ExprParser
from py2c.utils.constants import HEADER, TAB
from py2c.utils.template import CPPTemplate
from py2c.utils.utils import Utils

ReprVisitContext.model_rebuild()
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

    # Process the global scope first to know the type of arguments of functions and each type of variables
    # Like pre-processing
    for exp in normal_exps:
        printer.visit(exp, VisitContext(allow_print=False))

    # JUST A HEADER LIB
    print(HEADER)

    # ALL TEMPLATES USED
    print("\n// Just my templates to replace python functions",end="")
    for template in Utils.template_uses:
        print(CPPTemplate[template].value)

    print("\n// Your functions are here")
    # ALL DECLARED FUNCTIONS
    for func in funcs.values():
        printer.visit(func._ast_object, VisitContext(
            scope=["global", func.name], allow_print=True
        ))
    print()

    # MAIN FUNCTION
    print("int main() {")
    for i,exp in enumerate(normal_exps):
        print(f"MAIN: {i}", file=printer.debug)
        printer.visit(exp, VisitContext(allow_print=True, current_indent=1))
    print(TAB + "return 0;")
    print("}")

    print(printer.linter.typed_vars, file=sys.stderr)

    printer.visit("DEBUG", VisitContext(allow_print=False))
    printer.debug.close()
