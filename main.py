import sys
import ast
import copy
from structure import Function
from processor import ExprParser

# tree = ast.parse("res = [[0 for j in range(len(b[0]))] for i in range(len(a))]")
with open('python.py', 'r') as f:
    tree = ast.parse(f.read())

output_file = "c"
sys.stdout = open(f'{output_file}.out', 'w')
sys.stderr = open(f'{output_file}.err', 'w')


# name: Function
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
    printer.visit(exp, allow_print=False)

print(
    """
#include <bits/stdc++.h>
using namespace std;

    """
)

for func in funcs.values():
    printer.visit(func)
print()

print(
    """
int main() {
    """
)

for exp in normal_exps:
    printer.visit(exp, current_indent=1)
    
print(
    """
    return 0;
}
    """
)
