import unittest
import ast

from py2c.utils.linter import Linter

class TestLinter(unittest.TestCase):
    def setUp(self):
        self.linter = Linter({})

    def test_python_to_cpp(self):
        self.assertEqual(self.linter.python_to_cpp_type(["tuple", ["list", "int"], "str", "float"]),
                         "tuple<vector<int>, string, float>")
        self.assertEqual(self.linter.python_to_cpp_type(["list", "int"]),
                         "vector<int>")
        self.assertEqual(self.linter.python_to_cpp_type("int"),
                         "int")
        self.assertEqual(self.linter.python_to_cpp_type("str"),
                         "string")
        self.assertEqual(self.linter.python_to_cpp_type("float"),
                         "float")
        self.assertEqual(self.linter.python_to_cpp_type("bool"),
                         "bool")
        self.assertEqual(self.linter.python_to_cpp_type(["dict", "str", "int"]),
                         "map<string, int>")
        self.assertEqual(self.linter.python_to_cpp_type(["list", ["list", "int"]]),
                         "vector<vector<int>>")

    def test_get_type_from_annotations(self):
        self.assertEqual(self.linter.get_pytype_from_annotations(ast.parse("int").body[0].value), "int")
        self.assertEqual(self.linter.get_pytype_from_annotations(ast.parse("list[int]").body[0].value), ["list", "int"])
        self.assertEqual(self.linter.get_pytype_from_annotations(ast.parse("dict[list[int], int]").body[0].value), ["dict", ["list", "int"], "int"])
        self.assertEqual(self.linter.get_pytype_from_annotations(ast.parse("tuple[int, str, list[int]]").body[0].value), ["tuple", "int", "str", ["list", "int"]])
        self.assertEqual(self.linter.get_pytype_from_annotations(ast.parse("pair[int, int]").body[0].value), ["pair", "int", "int"])
        self.assertEqual(self.linter.get_pytype_from_annotations(ast.parse("list[list[int]]").body[0].value), ["list", ["list", "int"]])


if __name__ == "__main__":
    unittest.main()
