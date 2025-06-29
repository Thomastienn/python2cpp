import os
import sys
import ast
from py2c.commands.parser import parse
from py2c.utils.utils import Utils

def run():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if not os.path.exists(input_file):
            raise Exception(f"Input file {input_file} does not exist")
    else:
        # Fallback to python.py if the input file does not exist (Mostly for testing)
        if os.path.exists("test.py"):
            input_file = "test.py"
        else:
            raise Exception("No input file")

    input_file_no_ext = Utils.get_file_no_ext(input_file)
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = f"{input_file_no_ext}.cpp"
            
    with open(input_file, 'r') as f:
        tree = ast.parse(f.read())

    if not os.path.exists("out/"):
        os.makedirs("out/")
    sys.stdout = open(f'out/{output_file}', 'w')
    sys.stderr = open(f'out/{output_file}.err', 'w')
    
    try:
        parse(tree)
    except Exception as e:
        sys.__stdout__. write(f"Error! Check the logs\n")
        raise e
    sys.__stdout__.write("\n// All done! Check outputs\n")

if __name__ == "__main__":
    run()
