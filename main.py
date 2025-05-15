import sys
import ast
import copy
from printer import ASTPrinter

# tree = ast.parse("res = [[0 for j in range(len(b[0]))] for i in range(len(a))]")
with open('python.py', 'r') as f:
    tree = ast.parse(f.read())
# sys.stdout = open('c.txt', 'w')
# sys.stderr = sys.stdout


# name: object
funcs = {}
normal_exps = []
printer = ASTPrinter(funcs)
for exp in tree.body:
    if isinstance(exp, ast.FunctionDef):
        funcs[exp.name] = exp
    else:
        normal_exps.append(exp)

# process the body to determine some types and finally know the return type of func
# this needs to process first to figure out the return type
# so the other variables can know its type
for func in funcs.values():
    printer.visit(func.body, False)
    
# global scope first to understand types parameter of functions
for exp in normal_exps:
    printer.visit(exp, False)
    
    
