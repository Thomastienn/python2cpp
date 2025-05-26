import sys
import ast
import io
from py2c.utils.linter import Linter
from py2c.utils.utils import Utils
from py2c.utils.constants import TAB
from py2c.utils.template import CPPTemplate
from py2c.core.structure import ReprVisitContext, VisitContext


class ReprVisitor():
    def __init__(self, linter: Linter):
        self.linter = linter

    def call_print_parser(self, text:str, repr_ctx: ReprVisitContext, indent=None, end="\n"):
        if indent is None:
            indent = repr_ctx.parser_ctx.current_indent
        repr_ctx.processor.print_line(text, indent, end=end)
        
    def visit(self, node: ast.AST, repr_ctx: ReprVisitContext) -> str | list[str]:
        method_name = f"visit_{type(node).__name__}"
        visit_method = getattr(self, method_name, self.generic_visit)
        return visit_method(node, repr_ctx)

    def visit_Constant(self, node: ast.Constant, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            return type(node.value).__name__
        return repr(node.value)

    def visit_Name(self, node: ast.Name, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            return self.linter.get_var_type(node.id, repr_ctx.parser_ctx.scope)
        return node.id

    def visit_Tuple(self, node: ast.Tuple, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            return "tuple"
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx = repr_ctx.parser_ctx
        )
        return ",".join(self.visit(el, new_ctx) for el in node.elts)

    def visit_Subscript(self, node: ast.Subscript, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor = repr_ctx.processor,
            parser_ctx = repr_ctx.parser_ctx
        )
        access = []
        cur = node
        while isinstance(cur, ast.Subscript):
            access.append(self.visit(cur.slice, new_ctx))
            cur = cur.value
        result = self.visit(cur, new_ctx)
        
        if repr_ctx.return_type:
            return self.linter.get_subscript_type(result, len(access), scope=repr_ctx.parser_ctx.scope)
        
        for acc in reversed(access):
            if acc == "-1":
                acc = f"{result}.size() - 1"
            result += f"[{acc}]"
        return result

    def visit_BinOp(self, node: ast.BinOp, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                return_type=True,
                processor=repr_ctx.processor,
                parser_ctx=repr_ctx.parser_ctx
            )
            type_left = self.visit(node.left, new_ctx)
            type_right = self.visit(node.right, new_ctx)
            return self.linter.get_binop_type(type_left, type_right, self.visit_op(node.op))
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        if isinstance(node.op, ast.Pow):
            template_name = CPPTemplate.FASTPOW.name
            Utils.template_uses.add(template_name)
            return f"{template_name.lower()}({self.visit(node.left, new_ctx)}, {self.visit(node.right, new_ctx)})"

        return f"({self.visit(node.left, new_ctx)} {self.visit_op(node.op)} {self.visit(node.right, new_ctx)})"

    def handle_pyfunc(self, node: ast.Call, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        func_name = self.visit(node.func, new_ctx)
        # Use size universally
        if func_name == "len":
            return f"{self.visit(node.args[0], new_ctx)}.size()"
        if func_name == "print":
            return f'cout << {" << ".join(self.visit(arg, new_ctx) for arg in node.args)} << "\\n"'
        if func_name == "input":
            template_name: str = CPPTemplate.CINPUT.name
            Utils.template_uses.add(template_name)
            return f"{template_name.lower()}()"
        if func_name in Linter.TYPES:
            return f"({func_name}) ({self.visit(node.args[0], new_ctx)})"
        return None
            
    def visit_Call(self, node: ast.Call, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            return self.linter.get_type_from_pyfunction(node)

        res = self.handle_pyfunc(node, repr_ctx)
        if res is not None:
            return res

        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        return f"{self.visit(node.func, new_ctx)}({', '.join(self.visit(arg, new_ctx) for arg in node.args)})"

    def visit_Attribute(self, node: ast.Attribute, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        return f"{self.visit(node.value, new_ctx)}.{node.attr}"

    def visit_ListComp(self, node: ast.ListComp, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx
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
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )

        
        result = "[&] {\n"
        local_indent = repr_ctx.parser_ctx.current_indent + 1

        # FOR LOOPS AND IF STATEMENTS
        for gen in node.generators:
            assert isinstance(gen, ast.comprehension), "Generator is not comprehension"
            for_node = ast.For(
                target = gen.target,
                iter = gen.iter,
                body = [],
                orelse = []
            )
            proc_ctx = VisitContext(
                current_indent=local_indent,
                scope=repr_ctx.parser_ctx.scope
            )
            original_output = sys.stdout
            sys.stdout = io.StringIO()
            repr_ctx.processor.print_forloop(for_node, proc_ctx)
            result += sys.stdout.getvalue()
            sys.stdout = original_output

            local_indent += 1 + len(gen.ifs)

        # BODY
        # TODO : Find what this assign to.
        original_output = sys.stdout
        sys.stdout = io.StringIO()
        cur_scope = "lambda"
        cur_num = 0
        while cur_scope in self.linter.typed_vars:
            cur_scope = f"lambda_{cur_num}"
            cur_num += 1
        repr_ctx.processor.visit(ast.Assign(
            targets=[ast.Name(id="temp", ctx=ast.Store())],
            value=node.elt
        ), VisitContext(
            current_indent=local_indent,
            scope="lambda"
        ))
        result += sys.stdout.getvalue()
        sys.stdout = original_output
        
        # CLOSING BRACKETS
        for ind in range(local_indent-1, repr_ctx.parser_ctx.current_indent,-1):
            result += TAB * ind + "}\n"


        result += TAB * repr_ctx.parser_ctx.current_indent + "}()"
        
        return result

    def visit_comprehension(self, node: ast.comprehension, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        target = self.visit(node.target, new_ctx)
        iter_repr = self.visit(node.iter, new_ctx)
        filters = "".join(f" if {self.visit(cond, new_ctx)}" for cond in node.ifs)
        return f"{target} in {iter_repr}{filters}"

    def visit_IfExp(self, node: ast.IfExp, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx
            )
            return self.visit(node.body, new_ctx)
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        return f"({self.visit(node.test, new_ctx)})? ({self.visit(node.body, new_ctx)}) : ({self.visit(node.orelse, new_ctx)})"
        # return f"{self.visit(node.body)} if {self.visit(node.test)} else {self.visit(node.orelse)}"

    def visit_Compare(self, node: ast.Compare, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        return f"{self.visit(node.left, new_ctx)} {self.visit_op(node.ops[0])} {self.visit(node.comparators[0], new_ctx)}"

    def visit_List(self, node: ast.List, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx
            )
            if len(node.elts) == 2:
                return ["pair", self.visit(node.elts[0], new_ctx), self.visit(node.elts[1], new_ctx)]
            return ["list", self.visit(node.elts[0], new_ctx)]

        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        return f"{{{', '.join(self.visit(el, new_ctx) for el in node.elts)}}}"
    
    def visit_UnaryOp(self, node: ast.UnaryOp, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
        )
        return f"{self.visit_op(node.op)}{self.visit(node.operand, new_ctx)}"    
    
    def visit_BoolOp(self, node: ast.BoolOp, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            return "bool"
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx
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
            ast.Pow: "**", # This should use a template
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
    
    def generic_visit(self, node: ast.AST, repr_ctx: ReprVisitContext):
        raise NotImplementedError(
            f"Visit method not implemented for {type(node).__name__}")
