import sys, io
import unittest
import ast
from py2c.utils.utils import Utils
from py2c.core.processor import ExprParser
from py2c.core.structure import ReprVisitContext, VisitContext

ReprVisitContext.model_rebuild()
class TestProcessor(unittest.TestCase):
    def capture_output(self, func, *args):
        original = sys.stdout
        sys.stdout = io.StringIO()
        func(*args)
        output = sys.stdout.getvalue()
        sys.stdout = original
        return output

    def setUp(self):
        self.parser = ExprParser({})

    def test_assign(self):
        node = ast.parse("a = 2").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "int a = 2;\n", f"{s!r}")

        # Reassign
        node = ast.parse("a = 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "a = 3;\n", f"{s!r}")

        node = ast.parse("b = 2.0").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "float b = 2.0;\n", f"{s!r}")

        node = ast.parse("x = \"hi\"").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "string x = \"hi\";\n", f"{s!r}")

        node = ast.parse("c = a").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "int c = a;\n", f"{s!r}")

        node = ast.parse("d = [1]").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "vector<int> d = vector{1};\n", f"{s!r}")

        node = ast.parse("e = [1.0,2.0,3.0]").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "vector<float> e = vector{1.0, 2.0, 3.0};\n", f"{s!r}")

        node = ast.parse("g = (1,2.0, \"hi\")").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "tuple<int, float, string> g = make_tuple(1, 2.0, \"hi\");\n", f"{s!r}")

        node = ast.parse("h,i,j = 1,2,3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "auto [h,i,j] = make_tuple(1, 2, 3);\n", f"{s!r}")


    def test_pyfunc(self):
        node = ast.parse("min(1,2,3)").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "min({1, 2, 3});\n", f"{s!r}")

        node = ast.parse("min(1,2)").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "min(1, 2);\n", f"{s!r}")

        node = ast.parse("min([1,2])").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "min(vector{1, 2});\n", f"{s!r}")

        node = ast.parse("max(1,2,3)").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "max({1, 2, 3});\n", f"{s!r}")

    def test_arithmetic_operations(self):
        """Test arithmetic operations and operator precedence"""
        node = ast.parse("result = 1 + 2 * 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "int result = (1 + (2 * 3));\n", f"{s!r}")
        
        node = ast.parse("result = (1 + 2) * 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = ((1 + 2) * 3);\n", f"{s!r}")
        
        node = ast.parse("result = 2 ** 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = fastpow(2, 3);\n", f"{s!r}")
        
        node = ast.parse("result = 10 % 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = cmod(10, 3);\n", f"{s!r}")
        
        node = ast.parse("result = 10 // 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = (10 / 3);\n", f"{s!r}")

    def test_comparison_operations(self):
        """Test comparison operators in if statements"""
        node = ast.parse("if 1 > 2: pass").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "if (1 > 2) {\n}\n", f"{s!r}")
        
        node = ast.parse("if 1 <= 2: pass").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "if (1 <= 2) {\n}\n", f"{s!r}")
        
        node = ast.parse("if 1 == 2: pass").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "if (1 == 2) {\n}\n", f"{s!r}")
        
        node = ast.parse("if 1 != 2: pass").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "if (1 != 2) {\n}\n", f"{s!r}")

    def test_logical_operations(self):
        """Test logical operators"""
        node = ast.parse("result = True and False").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "bool result = (true && false);\n", f"{s!r}")
        
        node = ast.parse("result = True or False").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = (true || false);\n", f"{s!r}")
        
        node = ast.parse("result = not True").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = !true;\n", f"{s!r}")

    def test_augmented_assignment(self):
        """Test augmented assignment operators"""
        node = ast.parse("a += 5").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "a += 5;\n", f"{s!r}")
        
        node = ast.parse("a -= 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "a -= 3;\n", f"{s!r}")
        
        node = ast.parse("a *= 2").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "a *= 2;\n", f"{s!r}")
        
        node = ast.parse("a //= 2").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "a /= 2;\n", f"{s!r}")
        
        node = ast.parse("a %= 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "a %= 3;\n", f"{s!r}")

    def test_list_operations(self):
        """Test list operations and indexing"""
        node = ast.parse("arr = [1, 2, 3, 4, 5]").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "vector<int> arr = vector{1, 2, 3, 4, 5};\n", f"{s!r}")
        
        node = ast.parse("item = arr[0]").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertIn("item = arr[0];", s)
        
        node = ast.parse("arr[1] = 10").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "arr[1] = 10;\n", f"{s!r}")

    def test_nested_lists(self):
        """Test nested list structures"""
        node = ast.parse("matrix = [[1, 2], [3, 4]]").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "vector<vector<int>> matrix = vector{vector{1, 2}, vector{3, 4}};\n", f"{s!r}")
        
        node = ast.parse("three_d = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        expected = "vector<vector<vector<int>>> three_d = vector{vector{vector{1, 2}, vector{3, 4}}, vector{vector{5, 6}, vector{7, 8}}};\n"
        self.assertEqual(s, expected, f"{s!r}")

    def test_mixed_type_tuples(self):
        """Test tuples with mixed types"""
        node = ast.parse("data = (42, 3.14, True)").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "tuple<int, float, bool> data = make_tuple(42, 3.14, true);\n", f"{s!r}")
        
        node = ast.parse("coords = (1, 2)").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "tuple<int, int> coords = make_tuple(1, 2);\n", f"{s!r}")

    def test_string_operations(self):
        """Test string operations and concatenation"""
        node = ast.parse("message = 'Hello' + ' ' + 'World'").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "string message = ((\"Hello\" + \" \") + \"World\");\n", f"{s!r}")
        
        node = ast.parse("text = 'Python'").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "string text = \"Python\";\n", f"{s!r}")

    def test_boolean_values(self):
        """Test boolean literal conversion"""
        node = ast.parse("flag = True").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "bool flag = true;\n", f"{s!r}")
        
        # Test reassignment (should not include type)
        node = ast.parse("flag = False").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "flag = false;\n", f"{s!r}")

    def test_type_annotations(self):
        """Test type annotations"""
        node = ast.parse("x: int = 42").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "int x = 42;\n", f"{s!r}")
        
        node = ast.parse("numbers: list[int] = [1, 2, 3]").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "vector<int> numbers = vector{1, 2, 3};\n", f"{s!r}")

    def test_multiple_assignments(self):
        """Test multiple variable assignments"""
        node = ast.parse("a = b = c = 5").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        # Should handle multiple assignments correctly
        self.assertIn("= 5;", s)

    def test_control_flow_constructs(self):
        """Test control flow constructs like if/else"""
        node = ast.parse("if True:\n    pass\nelse:\n    pass").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertIn("if (true)", s)
        self.assertIn("else", s)
        
        node = ast.parse("while True:\n    pass").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertIn("while (true)", s)

    def test_basic_numeric_operations(self):
        """Test basic numeric operations with literals"""
        node = ast.parse("result = 5 + 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "int result = (5 + 3);\n", f"{s!r}")
        
        node = ast.parse("result = 5 - 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = (5 - 3);\n", f"{s!r}")
        
        node = ast.parse("result = 5 * 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = (5 * 3);\n", f"{s!r}")
        
        node = ast.parse("result = 5 / 3").body[0]
        s = Utils.capture_output(self.parser.visit, node)
        self.assertEqual(s, "result = (5 / 3);\n", f"{s!r}")


if __name__ == '__main__':
    unittest.main()
