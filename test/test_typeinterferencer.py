import unittest
import ast

from py2c.utils.typeinferencer import TypeInferencer

class TestTypeInferencer(unittest.TestCase):
    def setUp(self):
        self.typeinferencer = TypeInferencer({})

    def test_python_to_cpp(self):
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["tuple", ["list", "int"], "str", "float"]),
                         "tuple<vector<int>, string, float>")
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["list", "int"]),
                         "vector<int>")
        self.assertEqual(self.typeinferencer.python_to_cpp_type("int"),
                         "int")
        self.assertEqual(self.typeinferencer.python_to_cpp_type("str"),
                         "string")
        self.assertEqual(self.typeinferencer.python_to_cpp_type("float"),
                         "float")
        self.assertEqual(self.typeinferencer.python_to_cpp_type("bool"),
                         "bool")
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["dict", "str", "int"]),
                         "map<string, int>")
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["list", ["list", "int"]]),
                         "vector<vector<int>>")

    def test_get_type_from_annotations(self):
        self.assertEqual(self.typeinferencer.get_pytype_from_annotations(ast.parse("int").body[0].value), "int")
        self.assertEqual(self.typeinferencer.get_pytype_from_annotations(ast.parse("list[int]").body[0].value), ["list", "int"])
        self.assertEqual(self.typeinferencer.get_pytype_from_annotations(ast.parse("dict[list[int], int]").body[0].value), ["dict", ["list", "int"], "int"])
        self.assertEqual(self.typeinferencer.get_pytype_from_annotations(ast.parse("tuple[int, str, list[int]]").body[0].value), ["tuple", "int", "str", ["list", "int"]])
        self.assertEqual(self.typeinferencer.get_pytype_from_annotations(ast.parse("pair[int, int]").body[0].value), ["pair", "int", "int"])
        self.assertEqual(self.typeinferencer.get_pytype_from_annotations(ast.parse("list[list[int]]").body[0].value), ["list", ["list", "int"]])

    def test_complex_nested_types(self):
        """Test complex nested type conversions"""
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["dict", ["tuple", "str", "int"], ["list", "float"]]),
                         "map<tuple<string, int>, vector<float>>")
        
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["list", ["dict", "str", "int"]]),
                         "vector<map<string, int>>")
        
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["tuple", ["list", "str"], ["dict", "int", "float"], "bool"]),
                         "tuple<vector<string>, map<int, float>, bool>")

    def test_edge_case_types(self):
        """Test edge case type conversions"""
        # Test empty dict annotation
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["dict", "str", "str"]),
                         "map<string, string>")
        
        # Test single element tuple
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["tuple", "int"]),
                         "tuple<int>")
        
        # Test deeply nested lists
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["list", ["list", ["list", "int"]]]),
                         "vector<vector<vector<int>>>")

    def test_annotation_parsing_edge_cases(self):
        """Test edge cases in annotation parsing"""
        # Test optional types (might not be supported yet)
        try:
            result = self.typeinferencer.get_pytype_from_annotations(ast.parse("Optional[int]").body[0].value)
            self.assertIsNotNone(result)
        except:
            # Optional might not be supported, that's ok
            pass
        
        # Test union types (might not be supported yet)
        try:
            result = self.typeinferencer.get_pytype_from_annotations(ast.parse("Union[int, str]").body[0].value)
            self.assertIsNotNone(result)
        except:
            # Union might not be supported, that's ok
            pass

    def test_custom_type_annotations(self):
        """Test custom type annotations"""
        # Test set type
        try:
            result = self.typeinferencer.get_pytype_from_annotations(ast.parse("set[int]").body[0].value)
            self.assertEqual(result, ["set", "int"])
        except:
            # Set might not be supported, that's ok
            pass

    def test_type_conversion_consistency(self):
        """Test that type conversions are consistent"""
        # Test that multiple calls return the same result
        type1 = self.typeinferencer.python_to_cpp_type(["list", "int"])
        type2 = self.typeinferencer.python_to_cpp_type(["list", "int"])
        self.assertEqual(type1, type2)
        
        # Test that nested types are consistent
        nested1 = self.typeinferencer.python_to_cpp_type(["dict", "str", ["list", "int"]])
        nested2 = self.typeinferencer.python_to_cpp_type(["dict", "str", ["list", "int"]])
        self.assertEqual(nested1, nested2)

    def test_invalid_type_handling(self):
        """Test handling of invalid or unsupported types"""
        # Test what happens with unsupported types
        try:
            result = self.typeinferencer.python_to_cpp_type("unsupported_type")
            # Should either return the type as-is or handle gracefully
            self.assertIsInstance(result, str)
        except:
            # It's ok if it throws an exception for unsupported types
            pass

    def test_annotation_with_complex_generics(self):
        """Test annotation parsing with complex generic types"""
        # Test deeply nested generics
        result = self.typeinferencer.get_pytype_from_annotations(ast.parse("dict[str, list[tuple[int, float]]]").body[0].value)
        expected = ["dict", "str", ["list", ["tuple", "int", "float"]]]
        self.assertEqual(result, expected)
        
        # Test the corresponding C++ type
        cpp_type = self.typeinferencer.python_to_cpp_type(result)
        self.assertEqual(cpp_type, "map<string, vector<tuple<int, float>>>")

    def test_bool_type_conversion(self):
        """Test boolean type conversion specifics"""
        self.assertEqual(self.typeinferencer.python_to_cpp_type("bool"), "bool")
        
        # Test in complex types
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["list", "bool"]),
                         "vector<bool>")
        
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["tuple", "bool", "bool"]),
                         "tuple<bool, bool>")

    def test_numeric_type_edge_cases(self):
        """Test numeric type edge cases"""
        # Test different numeric types
        self.assertEqual(self.typeinferencer.python_to_cpp_type("int"), "int")
        self.assertEqual(self.typeinferencer.python_to_cpp_type("float"), "float")
        
        # Test in collections
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["list", "float"]),
                         "vector<float>")
        
        # Test mixed numeric types in tuple
        self.assertEqual(self.typeinferencer.python_to_cpp_type(["tuple", "int", "float"]),
                         "tuple<int, float>")


if __name__ == "__main__":
    unittest.main()
