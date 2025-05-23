import sys
import ast


class ReprVisitor():
    def __init__(self, linter):
        self.linter = linter
        
    def visit(self, node: ast.AST, return_type=False, scope="global") -> str | list[str]:
        method_name = f"visit_{type(node).__name__}"
        visit_method = getattr(self, method_name, self.generic_visit)
        return visit_method(node, scope, return_type)

    def visit_Constant(self, node: ast.Constant, scope, return_type=False):
        if return_type:
            return type(node.value).__name__
        return repr(node.value)

    def visit_Name(self, node: ast.Name, scope, return_type=False):
        if return_type:
            return self.linter.get_var_type(node.id, scope)
        return node.id

    def visit_Tuple(self, node: ast.Tuple, scope, return_type=False):
        if return_type:
            return "tuple"
        return ",".join(self.visit(el) for el in node.elts)

    def visit_Subscript(self, node: ast.Subscript, scope, return_type=False):
        access = []
        cur = node
        while isinstance(cur, ast.Subscript):
            access.append(self.visit(cur.slice))
            cur = cur.value
        result = self.visit(cur)
        
        if return_type:
            return self.linter.get_subscript_type(result, len(access), scope=scope)
        
        for acc in reversed(access):
            if acc == "-1":
                acc = f"{result}.size() - 1"
            result += f"[{acc}]"
        return result

    def visit_BinOp(self, node: ast.BinOp, scope, return_type=False):
        if return_type:
            type_left = self.visit(node.left, scope=scope, return_type=True)
            type_right = self.visit(node.right, scope=scope, return_type=True)
            return self.linter.get_binop_type(type_left, type_right, self.visit_op(node.op))
        return f"({self.visit(node.left)} {self.visit_op(node.op)} {self.visit(node.right)})"

    def handle_pyfunc(self, node: ast.Call):
        func_name = self.visit(node.func)
        # Use size universally
        if func_name == "len":
            return f"{self.visit(node.args[0])}.size()"
        if func_name == "print":
            return f'cout << {" << ".join(self.visit(arg) for arg in node.args)} << "\\n"'
        return None
            
    def visit_Call(self, node: ast.Call, scope, return_type=False):
        if return_type:
            return self.linter.get_type_from_pyfunction(node)

        res = self.handle_pyfunc(node)
        if res is not None:
            return res

        return f"{self.visit(node.func)}({','.join(self.visit(arg) for arg in node.args)})"

    def visit_Attribute(self, node: ast.Attribute, scope, return_type=False):
        return f"{self.visit(node.value)}.{node.attr}"

    def visit_ListComp(self, node: ast.ListComp, scope, return_type=False):
        if return_type:
            elt_type = self.visit(node.elt, True)
            final = ["list"]
            if isinstance(elt_type, list):
                final += elt_type
            else:
                final.append(elt_type)
            return final
        # Replace python with c++ syntax
        # Go from list comprehension to a seperate for loop
        elt = self.visit(node.elt)
        parts = [self.visit(gen) for gen in node.generators]
        # return f"[{elt} for {', '.join(parts)}]"
        return "move(temp)"

    def visit_comprehension(self, node: ast.comprehension, scope, return_type=False):
        target = self.visit(node.target)
        iter_repr = self.visit(node.iter)
        filters = "".join(f" if {self.visit(cond)}" for cond in node.ifs)
        return f"{target} in {iter_repr}{filters}"

    def visit_IfExp(self, node: ast.IfExp, scope, return_type=False):
        if return_type:
            return self.visit(node.body, True)
        return f"({self.visit(node.test)})? ({self.visit(node.body)}) : ({self.visit(node.orelse)})"
        # return f"{self.visit(node.body)} if {self.visit(node.test)} else {self.visit(node.orelse)}"

    def visit_Compare(self, node: ast.Compare, scope, return_type=False):
        return f"{self.visit(node.left)} {self.visit_op(node.ops[0])} {self.visit(node.comparators[0])}"

    def visit_List(self, node: ast.List, scope, return_type=False):
        if return_type:
            if len(node.elts) == 2:
                return ["pair", self.visit(node.elts[0], True), self.visit(node.elts[1], True)]
            return ["list", self.visit(node.elts[0], True)]
        return f"{{{', '.join(self.visit(el) for el in node.elts)}}}"
    
    def visit_UnaryOp(self, node: ast.UnaryOp, scope, return_type=False):
        return f"{self.visit_op(node.op)}{self.visit(node.operand)}"    
    
    def visit_BoolOp(self, node: ast.BoolOp, scope, return_type=False):
        if return_type:
            return "bool"
        return f"({self.visit(node.values[0])} {self.visit_op(node.op)} {self.visit(node.values[1])})"

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
            ast.Not: "!",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.Pow: "**",
            ast.FloorDiv: "//",
            ast.LShift: "<<",
            ast.RShift: ">>",
            ast.BitOr: "|",
            ast.BitAnd: "&",
            ast.BitXor: "^",
            ast.Invert: "~",
            ast.Or: "||",
            ast.And: "&&",
        }
        return mp.get(type(op), f"<{type(op).__name__}>")
    
    def generic_visit(self, node: ast.AST, scope, return_type=False):
        raise NotImplementedError(
            f"Visit method not implemented for {type(node).__name__}")
