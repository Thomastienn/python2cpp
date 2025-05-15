import sys
import ast
class ReprVisitor():
    def __init__(self):
        pass
        
    def visit(self, node: ast.AST):
        method_name = f"visit_{type(node).__name__}"
        visit_method = getattr(self, method_name, self.generic_visit)
        return visit_method(node)

    def visit_Constant(self, node: ast.Constant):
        return repr(node.value)

    def visit_Name(self, node: ast.Name):
        return node.id

    def visit_Num(self, node: ast.Num):
        return str(node.n)

    def visit_Str(self, node: ast.Str):
        return repr(node.s)

    def visit_Tuple(self, node: ast.Tuple):
        return ",".join(self.visit(el) for el in node.elts)

    def visit_Subscript(self, node: ast.Subscript):
        access = []
        cur = node
        while isinstance(cur, ast.Subscript):
            access.append(self.visit(cur.slice))
            cur = cur.value
        result = self.visit(cur)
        for acc in reversed(access):
            result += f"[{acc}]"
        return result

    def visit_BinOp(self, node: ast.BinOp):
        return f"({self.visit(node.left)} {self.visit_op(node.op)} {self.visit(node.right)})"

    def visit_Call(self, node: ast.Call):
        return f"{self.visit(node.func)}({','.join(self.visit(arg) for arg in node.args)})"

    def visit_Attribute(self, node: ast.Attribute):
        return f"{self.visit(node.value)}.{node.attr}"

    def visit_ListComp(self, node: ast.ListComp):
        elt = self.visit(node.elt)
        parts = [self.visit(gen) for gen in node.generators]
        return f"[{elt} for {', '.join(parts)}]"

    def visit_comprehension(self, node: ast.comprehension):
        target = self.visit(node.target)
        iter_repr = self.visit(node.iter)
        filters = "".join(f" if {self.visit(cond)}" for cond in node.ifs)
        return f"{target} in {iter_repr}{filters}"

    def visit_IfExp(self, node: ast.IfExp):
        return f"{self.visit(node.body)} if {self.visit(node.test)} else {self.visit(node.orelse)}"

    def visit_Compare(self, node: ast.Compare):
        return f"{self.visit(node.left)} {self.visit_op(node.ops[0])} {self.visit(node.comparators[0])}"

    def visit_List(self, node: ast.List):
        return f"[{', '.join(self.visit(el) for el in node.elts)}]"
    
    def visit_UnaryOp(self, node: ast.UnaryOp):
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
    
    def generic_visit(self, node: ast.AST):
        raise NotImplementedError(
            f"Visit method not implemented for {type(node).__name__}")
