import sys
import ast

from py2c.core.structure import Function, VisitContext, ReprVisitContext
from py2c.core.processor import ExprParser
from py2c.utils.constants import HEADER, TAB
from py2c.utils.template import CPPTemplate, CPPTemplateReturnType
from py2c.utils.utils import Utils
from py2c.utils.scope_handler import ScopeHandler
from py2c.utils.logger import setup_logger

ReprVisitContext.model_rebuild()
def parse(tree):
    logger = setup_logger("py2cpp.parser")
    funcs = {}
    normal_exps = []
    printer = ExprParser(funcs)
    for exp in tree.body:
        if isinstance(exp, ast.FunctionDef):
            myf = Function(
                name=exp.name,
                return_pytype=None,
                user_func=True
            )
            myf._ast_object = exp
            funcs[exp.name] = myf
        else:
            normal_exps.append(exp)

    # Put my template return type inside
    for func in CPPTemplate:
        func_name = func.name
        myf = Function(
            name=func_name.lower(),
            return_pytype=CPPTemplateReturnType[func_name].value,
        )
        funcs[func_name.lower()] = myf
        

    # Process the global scope first to know the type of arguments of functions and each type of variables
    # Like pre-processing
    for i, exp in enumerate(normal_exps):
        logger.debug("SCAN: %d", i)
        printer.visit(exp, VisitContext(allow_print=False, is_scanning=True, scope=["global"]))

    # print(printer.linter.funcs, file=sys.stderr)
    # JUST A HEADER LIB
    print(HEADER)

    # ALL TEMPLATES USED
    print("\n// Just my templates to replace python functions",end="")
    for template in Utils.template_uses:
        print(CPPTemplate[template].value)

    print("\n// Your functions are here")
    # ALL DECLARED FUNCTIONS
    for func in funcs.values():
        if func.user_func and func.return_pytype is not None:
            printer.visit(func._ast_object, VisitContext(
                scope=["global"], allow_print=True
            ))
    print()

    # MAIN FUNCTION
    print("int main() {")
    for i,exp in enumerate(normal_exps):
        logger.debug("MAIN: %d", i)
        printer.visit(exp, VisitContext(allow_print=True, current_indent=1, scope=["global"]))
    print(TAB + "return 0;")
    print("}")

    # print(printer.linter.typed_vars, file=sys.stderr)
    # print(printer.linter.funcs, file=sys.stderr)

    printer.visit_Str("DEBUG", VisitContext(allow_print=False))
