import sys
import ast
from py2c.commands.parser import parse
from py2c.utils.utils import Utils
from py2c.utils.constants import PROD

def run():
    if PROD:
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
            input_file_no_ext = Utils.get_file_no_ext(input_file)
            if len(sys.argv) > 2:
                output_file = sys.argv[2]
            else:
                output_file = f"{input_file_no_ext}.cpp"
        else:
            raise Exception("No input file")
    else:
        input_file = "python.py"
        input_file_no_ext = Utils.get_file_no_ext(input_file)
        output_file = f"{input_file_no_ext}.cpp"
            
    with open(input_file, 'r') as f:
        tree = ast.parse(f.read())

    sys.stdout = open(f'{output_file}', 'w')
    sys.stderr = open(f'{input_file_no_ext}.err', 'w')
    
    parse(tree)

if __name__ == "__main__":
    run()
