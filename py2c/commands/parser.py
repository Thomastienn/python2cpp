"""
Python to C++ Parser Module

This module contains the main parsing logic that converts Python Abstract Syntax Trees (AST)
into equivalent C++ code. It orchestrates the conversion process by:

1. Extracting function definitions from the AST
2. Processing global scope to determine variable types
3. Generating C++ headers and templates
4. Converting Python code to C++ equivalents
5. Generating the main() function

The parser handles:
- Function definitions and calls
- Variable type inference
- Template generation for Python built-ins
- Global variable declarations
- Scope management

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

import sys
import ast

from py2c.core.structure import Function, VisitContext, ReprVisitContext
from py2c.core.processor import ExprParser
from py2c.utils.constants import HEADER, TAB
from py2c.utils.template import CPPTemplate, CPPTemplateReturnType
from py2c.utils.utils import Utils
from py2c.utils.scope_handler import ScopeHandler
from py2c.utils.logger import setup_logger
from py2c.commands.llm_fallback import LLMParser

ReprVisitContext.model_rebuild()

@LLMParser
def parse(tree):
    """
    Parse a Python AST and convert it to C++ code.
    
    This is the main entry point for the Python to C++ conversion process.
    It takes a Python AST and performs a multi-pass conversion:
    
    1. First pass: Extract function definitions and separate normal expressions
    2. Second pass: Pre-process global scope to infer variable types
    3. Third pass: Generate C++ output including headers, templates, and code
    
    Args:
        tree (ast.AST): The Python Abstract Syntax Tree to convert
    
    Returns:
        None: The function prints the converted C++ code to stdout
    
    Raises:
        Exception: Various exceptions during AST processing, wrapped with context
    
    Output Structure:
        1. C++ headers and includes
        2. Global variable declarations
        3. Template function definitions
        4. User-defined function implementations
        5. Main function with converted code
    """
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
    try:
        for i, exp in enumerate(normal_exps):
            logger.debug("SCAN: %d", i)
            printer.visit(exp, VisitContext(allow_print=False, is_scanning=True, scope=["global"]))
    except Exception as e:
        raise (type(e))(f"Error while scanning the AST: {e}") from e

    # print(printer.typeinferencer.funcs, file=sys.stderr)
    # JUST A HEADER LIB
    print(HEADER)

    print("\n// All the variables I assume you want to be global\n" if len(printer.typeinferencer.actual_global_vars) > 0 else "", end="")
    # All the actual global variables
    for var in printer.typeinferencer.actual_global_vars:
        if var.pytype is None:
            var.pytype = "auto"
        print(f"{printer.typeinferencer.python_to_cpp_type(var.pytype)} {var.name};")

    # ALL TEMPLATES USED
    print("\n// Just my templates to replace python functions" if len(Utils.template_uses) > 0  else "",end="")
    for template in Utils.template_uses:
        print(CPPTemplate[template].value)

    print("\n// Your functions are here\n" if sum(func.user_func and func.return_pytype is not None for func in funcs.values()) > 0 else "", end="")
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

    # print(printer.typeinferencer.typed_vars, file=sys.stderr)
    # print(printer.typeinferencer.funcs, file=sys.stderr)

    printer.visit_Str("DEBUG", VisitContext(allow_print=False))
    Utils.template_uses.clear()
