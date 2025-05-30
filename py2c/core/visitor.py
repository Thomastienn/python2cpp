import sys
import ast
import io
from collections import OrderedDict
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
        return repr(node.value).replace("\'", "\"")

    def visit_Name(self, node: ast.Name, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            return self.linter.get_var_type(node.id, repr_ctx.parser_ctx.scope)
        return node.id

    def visit_Tuple(self, node: ast.Tuple, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
            )
            if len(node.elts) == 2:
                return ["pair", self.visit(node.elts[0], new_ctx), self.visit(node.elts[1], new_ctx)]
            type_ = ["tuple"]
            for el in node.elts:
                type_.append(self.visit(el, new_ctx))
            return type_
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx = repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        # This is only when we want to store variables
        if isinstance(node.elts[0], ast.Name) and isinstance(node.elts[0].ctx, ast.Store):
            return ",".join(self.visit(el, new_ctx) for el in node.elts)
        # Define this as a pair now
        if len(node.elts) == 2:
            return f"{{{self.visit(node.elts[0], new_ctx)}, {self.visit(node.elts[1], new_ctx)}}}"
            
        return f"make_tuple({', '.join(self.visit(el, new_ctx) for el in node.elts)})"

    def visit_Subscript(self, node: ast.Subscript, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor = repr_ctx.processor,
            parser_ctx = repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
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
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
            )
            type_left = self.visit(node.left, new_ctx)
            type_right = self.visit(node.right, new_ctx)
            return self.linter.get_binop_type(type_left, type_right, self.visit_op(node.op))
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        if isinstance(node.op, ast.Pow):
            template_name = CPPTemplate.FASTPOW.name
            Utils.template_uses.add(template_name)
            return f"{template_name.lower()}({self.visit(node.left, new_ctx)}, {self.visit(node.right, new_ctx)})"

        return f"({self.visit(node.left, new_ctx)} {self.visit_op(node.op)} {self.visit(node.right, new_ctx)})"

    def handle_pyfunc(self, node: ast.Call, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        get_type_ctx = ReprVisitContext(
            return_type=True,
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        func_name = self.visit(node.func, new_ctx)
        # Use size universally
        if func_name == "len":
            # Figure the type of this value
            type_ = self.visit(node.args[0], get_type_ctx)
            if isinstance(type_, list) and type_[0] == "tuple":
                return f"tuple_size<decltype({self.visit(node.args[0], new_ctx)})>::value"
            return f"{self.visit(node.args[0], new_ctx)}.size()"
        if func_name == "print":
            return f'cout << {" << ".join(self.visit(arg, new_ctx) for arg in node.args)} << "\\n"'
        if func_name == "input":
            template_name: str = CPPTemplate.CINPUT.name
            Utils.template_uses.add(template_name)
            return f"{template_name.lower()}()"
        if func_name == "map":
            # We can use a for loop if it's just casting values
            arg1 = self.visit(node.args[0], new_ctx)
            arg2 = self.visit(node.args[1], new_ctx)
            if arg1 in Linter.TYPES:
                context_node = repr_ctx.expr_node
                type_arg2 = self.visit(ast.parse(arg2).body[0].value, get_type_ctx)
                cpp_type_arg2 = self.linter.python_to_cpp_type(type_arg2)
                result = "[&] {\n"
                result += f"{TAB * (repr_ctx.parser_ctx.current_indent+1)}vector<{arg1}>temp;\n"
                result += f"{TAB * (repr_ctx.parser_ctx.current_indent+1)}{cpp_type_arg2} arg2 = {arg2};\n"
                result += f"{TAB * (repr_ctx.parser_ctx.current_indent+1)}for (int i = 0; i < arg2.size(); i++){{\n"

                cast_node = ast.parse(f"{arg1}(arg2[i])").body[0].value
                self.linter.add_var("arg2", type_arg2, scope=repr_ctx.parser_ctx.scope)
                result += f"{TAB * (repr_ctx.parser_ctx.current_indent+2)}temp.push_back({self.visit(cast_node, new_ctx)});\n"
                result += f"{TAB * (repr_ctx.parser_ctx.current_indent+1)}}}\n"
                if isinstance(context_node, ast.Assign) and isinstance(context_node.targets[0], ast.Tuple):
                    vec_i_str = [f"temp[{i}]" for i in range(len(context_node.targets[0].elts))]
                    result += f"{TAB * (repr_ctx.parser_ctx.current_indent+1)}return make_tuple({', '.join(vec_i_str)});\n"
                else:
                    result += f"{TAB * (repr_ctx.parser_ctx.current_indent+1)}return temp;\n"
                    
                result += f"{TAB * (repr_ctx.parser_ctx.current_indent)}}}()"
                return result
            
            # When we need to use lambda
            template_name: str = CPPTemplate.CMAP.name
            Utils.template_uses.add(template_name)
            return f"{template_name.lower()}({self.visit(node.args[0], new_ctx)}, {self.visit(node.args[1], new_ctx)})"
        if func_name in Linter.TYPES:
            type_other = self.visit(node.args[0], get_type_ctx)
            if type_other == "str" and func_name == "int":
                return f"stoi({self.visit(node.args[0], new_ctx)})"
            return f"({func_name}) ({self.visit(node.args[0], new_ctx)})"
        return None
            
    def visit_Call(self, node: ast.Call, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            if node.func.id in self.linter.funcs:
                return self.linter.funcs[node.func.id].return_pytype
            return self.linter.get_type_from_pyfunction(node)

        res = self.handle_pyfunc(node, repr_ctx)
        if res is not None:
            return res

        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        result_str = self.visit(node.func, new_ctx)
        # TODO: This not fixing it. We need a better way
        if not isinstance(node.func, ast.Attribute):
            result_str += f"({', '.join(self.visit(arg, new_ctx) for arg in node.args)})"
        return result_str

    def handle_pyattr(self, node_name:str, attr_name: str):
        if attr_name == "sort":
            # TODO: Handle key of sort (use lambda func)
            return f"sort({node_name}.begin(), {node_name}.end())"
        
        if attr_name == "append":
            return f"{node_name}.push_back"

        if attr_name == "split":
            func_name = CPPTemplate.CSPLIT.name
            Utils.template_uses.add(func_name)
            return f"{func_name.lower()}({node_name})"

        raise NotImplementedError

    def visit_Attribute(self, node: ast.Attribute, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            # We need to know the type of the one using this attribute first
            new_ctx = ReprVisitContext(
                return_type=True,
                processor=repr_ctx.processor,
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
            )
            type_ = self.visit(node.value, new_ctx)
            return self.linter.get_attr_type(type_, node.attr)
            
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        node_name = self.visit(node.value, new_ctx)
        try:
            result = self.handle_pyattr(node_name, node.attr)
            return result
        except NotImplementedError:
            return f"{self.visit(node.value, new_ctx)}.{node.attr}"

    def visit_ListComp(self, node: ast.ListComp, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
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
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )

        result = "[&] {\n"
        local_indent = repr_ctx.parser_ctx.current_indent + 1
        # FOR LOOPS AND IF STATEMENTS
        gens_str = ""
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
            gens_str += Utils.capture_output(repr_ctx.processor.print_forloop, for_node, proc_ctx)
            local_indent += 1 + len(gen.ifs)

        # BODY
        def assign_to():
            last_scope = repr_ctx.parser_ctx.scope[-1]
            new_scope = "lambda0"
            if last_scope.startswith("lambda"):
                new_scope = f"lambda{int(last_scope[len('lambda'):]) + 1}"
            full_new_scope = repr_ctx.parser_ctx.scope + [new_scope]

            # WARNING: This is a hack, fix in the future
            self.linter.add_var("temp", "This doesn't matter", scope=full_new_scope)
            repr_ctx.processor.visit(ast.Assign(
                targets=[ast.Name(id="temp", ctx=ast.Store())],
                value=node.elt
            ), VisitContext(
                current_indent=local_indent,
                scope=full_new_scope
            ))
            temp_type = self.linter.get_var_type("temp", scope=full_new_scope)
            self.linter.remove_var("temp", scope=full_new_scope)
            return temp_type
            
        assign_body, temp_type = Utils.capture_output(assign_to, include_return=True)
        if not isinstance(temp_type, list):
            temp_type = [temp_type]
        parent_type = ["list"] + temp_type
        cpp_type = self.linter.python_to_cpp_type(parent_type)
        result += f"{TAB * (repr_ctx.parser_ctx.current_indent+1)}{cpp_type} parent;\n"
        result += gens_str
        result += assign_body
        result += f"{TAB * local_indent}parent.push_back(temp);\n"

        # CLOSING BRACKETS
        for ind in range(local_indent-1, repr_ctx.parser_ctx.current_indent,-1):
            result += TAB * ind + "}\n"
            
        result += f"{TAB * ind}return parent;\n"
        result += TAB * repr_ctx.parser_ctx.current_indent + "}()"
        return result

    def visit_comprehension(self, node: ast.comprehension, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
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
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
            )
            return self.visit(node.body, new_ctx)
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        return f"({self.visit(node.test, new_ctx)})? ({self.visit(node.body, new_ctx)}) : ({self.visit(node.orelse, new_ctx)})"
        # return f"{self.visit(node.body)} if {self.visit(node.test)} else {self.visit(node.orelse)}"

    def visit_Compare(self, node: ast.Compare, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        return f"{self.visit(node.left, new_ctx)} {self.visit_op(node.ops[0])} {self.visit(node.comparators[0], new_ctx)}"

    def visit_List(self, node: ast.List, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
            )
            if len(node.elts) == 2:
                return ["pair", self.visit(node.elts[0], new_ctx), self.visit(node.elts[1], new_ctx)]
            return ["list", self.visit(node.elts[0], new_ctx)]

        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        return f"{{{', '.join(self.visit(el, new_ctx) for el in node.elts)}}}"

    def visit_UnaryOp(self, node: ast.UnaryOp, repr_ctx: ReprVisitContext):
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        return f"{self.visit_op(node.op)}{self.visit(node.operand, new_ctx)}"    

    def visit_BoolOp(self, node: ast.BoolOp, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            return "bool"
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
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
