import sys
import ast
import copy
from structure import Function, VisitContext
from processor import ExprParser
from constants import PROD

# tree = ast.parse("res = [[0 for j in range(len(b[0]))] for i in range(len(a))]")


# name: Function
def run(tree):
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

    print(
    """#include <bits/stdc++.h>
using namespace std;

    """
)

    for func in funcs.values():
        printer.visit(func._ast_object, VisitContext(scope=func.name, allow_print=True))
    print()

    print(
    """
int main() {"""
)

    for exp in normal_exps:
        printer.visit(exp, VisitContext(allow_print=True, current_indent=1))

    print(
    """
    return 0;
}
    """
    )

def get_file_no_ext(filename):
    if "." in filename:
        return filename.split(".")[0]
    else:
        return filename

if __name__ == "__main__":
    if PROD:
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
            input_file_no_ext = get_file_no_ext(input_file)
            if len(sys.argv) > 2:
                output_file = sys.argv[2]
            else:
                output_file = f"{input_file_no_ext}.out"
        else:
            raise Exception("No input file")
    else:
        input_file = "python.py"
        input_file_no_ext = get_file_no_ext(input_file)
        output_file = f"{input_file_no_ext}.out"
            
    with open(input_file, 'r') as f:
        tree = ast.parse(f.read())

    sys.stdout = open(f'{output_file}', 'w')
    sys.stderr = open(f'{input_file_no_ext}.err', 'w')
    
    run(tree)
