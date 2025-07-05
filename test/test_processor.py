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


if __name__ == '__main__':
    unittest.main()
