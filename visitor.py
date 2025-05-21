import sys
import ast
class ReprVisitor():
    def __init__(self, linter):
        self.linter = linter
        
    def visit(self, node: ast.AST, return_type=False):
        method_name = f"visit_{type(node).__name__}"
        visit_method = getattr(self, method_name, self.generic_visit)
        return visit_method(node, return_type)

    def visit_Constant(self, node: ast.Constant, return_type=False):
        if return_type:
            return type(node.value).__name__
        return repr(node.value)

    def visit_Name(self, node: ast.Name, return_type=False):
        if return_type:
            return self.linter.get_var_type(node.id)
        return node.id

    def visit_Tuple(self, node: ast.Tuple, return_type=False):
        if return_type:
            return "tuple"
        return ",".join(self.visit(el) for el in node.elts)

    def visit_Subscript(self, node: ast.Subscript, return_type=False):
        access = []
        cur = node
        while isinstance(cur, ast.Subscript):
            access.append(self.visit(cur.slice))
            cur = cur.value
        result = self.visit(cur)
        
        if return_type:
            print("DEBUG result: " , result, access, file=sys.stderr)
            print(self.linter.typed_nested_list, file=sys.stderr)
            return self.linter.get_subscript_type(result, len(access))
        
        for acc in reversed(access):
            result += f"[{acc}]"
        return result

    def visit_BinOp(self, node: ast.BinOp, return_type=False):
        if return_type:
            type_left = self.visit(node.left, True)
            type_right = self.visit(node.right, True)
            print(type_left, type_right, node.op, file=sys.stderr)
            return self.linter.get_binop_type(type_left, type_right, self.visit_op(node.op))
        return f"({self.visit(node.left)} {self.visit_op(node.op)} {self.visit(node.right)})"

    def visit_Call(self, node: ast.Call, return_type=False):
        return f"{self.visit(node.func)}({','.join(self.visit(arg) for arg in node.args)})"

    def visit_Attribute(self, node: ast.Attribute, return_type=False):
        return f"{self.visit(node.value)}.{node.attr}"

    def visit_ListComp(self, node: ast.ListComp, return_type=False):
        if return_type:
            elt_type = self.visit(node.elt, True)
            final = ["list"]
            if isinstance(elt_type, list):
                final += elt_type
            else:
                final.append(elt_type)
            return final
        elt = self.visit(node.elt)
        parts = [self.visit(gen) for gen in node.generators]
        return f"[{elt} for {', '.join(parts)}]"

    def visit_comprehension(self, node: ast.comprehension, return_type=False):
        target = self.visit(node.target)
        iter_repr = self.visit(node.iter)
        filters = "".join(f" if {self.visit(cond)}" for cond in node.ifs)
        return f"{target} in {iter_repr}{filters}"

    def visit_IfExp(self, node: ast.IfExp, return_type=False):
        if return_type:
            return self.visit(node.body, True)
        return f"{self.visit(node.body)} if {self.visit(node.test)} else {self.visit(node.orelse)}"

    def visit_Compare(self, node: ast.Compare, return_type=False):
        return f"{self.visit(node.left)} {self.visit_op(node.ops[0])} {self.visit(node.comparators[0])}"

    def visit_List(self, node: ast.List, return_type=False):
        return f"[{', '.join(self.visit(el) for el in node.elts)}]"
    
    def visit_UnaryOp(self, node: ast.UnaryOp, return_type=False):
        return f"{self.visit_op(node.op)}{self.visit(node.operand)}"    

    def visit_op(self, op):
        mp = {
            ast.UAdd: "-",
            ast.Add: "+",
            ast.Sub: "-",
            ast.USub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
            ast.Eq: "==",
            ast.Not: "not",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.And: "and",
            ast.Or: "or",
            ast.Pow: "**",
            ast.FloorDiv: "//",
            ast.LShift: "<<",
            ast.RShift: ">>",
            ast.BitOr: "|",
            ast.BitAnd: "&",
            ast.BitXor: "^",
            ast.Invert: "~"
        }
        return mp.get(type(op), f"<{type(op).__name__}>")
    
    def generic_visit(self, node: ast.AST, return_type=False):
        raise NotImplementedError(
            f"Visit method not implemented for {type(node).__name__}")
