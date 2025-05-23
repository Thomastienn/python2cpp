import sys
import ast
from py2c.core.structure import ReprVisitContext


class ReprVisitor():
    def __init__(self, linter):
        self.linter = linter
        
    def visit(self, node: ast.AST, visit_ctx: ReprVisitContext) -> str | list[str]:
        method_name = f"visit_{type(node).__name__}"
        visit_method = getattr(self, method_name, self.generic_visit)
        return visit_method(node, visit_ctx)

    def visit_Constant(self, node: ast.Constant, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            return type(node.value).__name__
        return repr(node.value)

    def visit_Name(self, node: ast.Name, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            return self.linter.get_var_type(node.id, visit_ctx.scope)
        return node.id

    def visit_Tuple(self, node: ast.Tuple, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            return "tuple"
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return ",".join(self.visit(el, new_ctx) for el in node.elts)

    def visit_Subscript(self, node: ast.Subscript, visit_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor = visit_ctx.processor,
        )
        access = []
        cur = node
        while isinstance(cur, ast.Subscript):
            access.append(self.visit(cur.slice, new_ctx))
            cur = cur.value
        result = self.visit(cur, new_ctx)
        
        if visit_ctx.return_type:
            return self.linter.get_subscript_type(result, len(access), scope=visit_ctx.scope)
        
        for acc in reversed(access):
            if acc == "-1":
                acc = f"{result}.size() - 1"
            result += f"[{acc}]"
        return result

    def visit_BinOp(self, node: ast.BinOp, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            new_ctx = ReprVisitContext(
                scope=visit_ctx.scope,
                return_type=True,
                processor=visit_ctx.processor
            )
            type_left = self.visit(node.left, new_ctx)
            type_right = self.visit(node.right, new_ctx)
            return self.linter.get_binop_type(type_left, type_right, self.visit_op(node.op))
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"({self.visit(node.left, new_ctx)} {self.visit_op(node.op)} {self.visit(node.right, new_ctx)})"

    def handle_pyfunc(self, node: ast.Call, visit_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        func_name = self.visit(node.func, new_ctx)
        # Use size universally
        if func_name == "len":
            return f"{self.visit(node.args[0], new_ctx)}.size()"
        if func_name == "print":
            return f'cout << {" << ".join(self.visit(arg, new_ctx) for arg in node.args)} << "\\n"'
        return None
            
    def visit_Call(self, node: ast.Call, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            return self.linter.get_type_from_pyfunction(node)

        res = self.handle_pyfunc(node, visit_ctx)
        if res is not None:
            return res

        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"{self.visit(node.func, new_ctx)}({','.join(self.visit(arg, new_ctx) for arg in node.args)})"

    def visit_Attribute(self, node: ast.Attribute, visit_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"{self.visit(node.value, new_ctx)}.{node.attr}"

    def visit_ListComp(self, node: ast.ListComp, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=visit_ctx.processor,
                return_type=True
            )
            elt_type = self.visit(node.elt, new_ctx)
            final = ["list"]
            if isinstance(elt_type, list):
                final += elt_type
            else:
                final.append(elt_type)
            return final
        # Replace python with c++ syntax
        # Go from list comprehension to a seperate for loop
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        elt = self.visit(node.elt, new_ctx)
        parts = [self.visit(gen, new_ctx) for gen in node.generators]
        # return f"[{elt} for {', '.join(parts)}]"
        return "move(temp)"

    def visit_comprehension(self, node: ast.comprehension, visit_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        target = self.visit(node.target, new_ctx)
        iter_repr = self.visit(node.iter, new_ctx)
        filters = "".join(f" if {self.visit(cond, new_ctx)}" for cond in node.ifs)
        return f"{target} in {iter_repr}{filters}"

    def visit_IfExp(self, node: ast.IfExp, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=visit_ctx.processor,
                return_type=True
            )
            return self.visit(node.body, new_ctx)
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"({self.visit(node.test, new_ctx)})? ({self.visit(node.body, new_ctx)}) : ({self.visit(node.orelse, new_ctx)})"
        # return f"{self.visit(node.body)} if {self.visit(node.test)} else {self.visit(node.orelse)}"

    def visit_Compare(self, node: ast.Compare, visit_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"{self.visit(node.left, new_ctx)} {self.visit_op(node.ops[0])} {self.visit(node.comparators[0], new_ctx)}"

    def visit_List(self, node: ast.List, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=visit_ctx.processor,
                return_type=True
            )
            if len(node.elts) == 2:
                return ["pair", self.visit(node.elts[0], new_ctx), self.visit(node.elts[1], new_ctx)]
            return ["list", self.visit(node.elts[0], new_ctx)]

        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"{{{', '.join(self.visit(el, new_ctx) for el in node.elts)}}}"
    
    def visit_UnaryOp(self, node: ast.UnaryOp, visit_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"{self.visit_op(node.op)}{self.visit(node.operand, new_ctx)}"    
    
    def visit_BoolOp(self, node: ast.BoolOp, visit_ctx: ReprVisitContext):
        if visit_ctx.return_type:
            return "bool"
        new_ctx = ReprVisitContext(
            processor=visit_ctx.processor
        )
        return f"({self.visit(node.values[0], new_ctx)} {self.visit_op(node.op)} {self.visit(node.values[1], new_ctx)})"

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
    
    def generic_visit(self, node: ast.AST, visit_ctx: ReprVisitContext):
        raise NotImplementedError(
            f"Visit method not implemented for {type(node).__name__}")
