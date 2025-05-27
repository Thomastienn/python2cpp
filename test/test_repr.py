import sys, io
import unittest
import ast
from py2c.core.processor import ExprParser
from py2c.core.structure import ReprVisitContext, VisitContext

ReprVisitContext.model_rebuild()
class TestRepr(unittest.TestCase):
    def setUp(self):
        self.parser = ExprParser({})

    def tearDown(self):
        self.parser.debug.close()

    def test_handle_pyfunc(self):
        self.parser.visit(ast.parse("a_tuple = (1,2,3)").body[0], VisitContext(
            allow_print = False
        ))
        node = ast.parse("len(a_tuple)").body[0].value
        s = self.parser.repr.handle_pyfunc(node, ReprVisitContext(
            processor=self.parser,
            parser_ctx=VisitContext(
                allow_print = True
            )
        ))
        assert s == "tuple_size<decltype(a_tuple)>::value", f"{s!r}"

if __name__ == "__main__":
    unittest.main()
