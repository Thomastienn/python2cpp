import sys
import ast
from py2c.commands.parser import parse

content = """
a = reversed([1,2,3])
"""

# sys.stderr = open("test.err", "w")
tree = ast.parse(content)
try:
    parse(tree)
except Exception as e:
    raise e
