import sys
import ast
import io
from copy import deepcopy

from collections import OrderedDict
from py2c.utils.linter import Linter
from py2c.utils.utils import Utils
from py2c.utils.constants import TAB
from py2c.utils.template import CPPTemplate
from py2c.core.structure import ReprVisitContext, VisitContext
from py2c.utils.logger import setup_logger


class ReprVisitor():
    MAP_VALUE = {
        "True": "true",
        "False": "false",
        "None": "nullptr",
    }
    def __init__(self, linter: Linter):
        self.linter = linter
        self.logger = setup_logger("py2cpp.visitor")

    def get_type_from_pyfunction(self, func_node: ast.Call, repr_ctx: ReprVisitContext) -> str:
        """
            Return the return pytype of a builtin function
        """
        func_name = func_node.func.id
        if func_name in Linter.TYPES:
            return func_name
        
        if func_name == "map":
            # TODO: Do lambda functions too
            return func_node.args[0].id
        elif func_name == "input":
            return "str"
        elif func_name in ["len", "int", "ord"]:
            return "int"
        elif func_name in ["min", "max"]:
            # Get the type of the first argument
            first_arg = func_node.args[0]
            return self.visit(first_arg, repr_ctx)
        elif func_name == "chr":
            return "char"

        # TODO: Add more
        return "Unknown"

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
        node_repr = repr(node.value)
        if node_repr in self.MAP_VALUE:
            return self.MAP_VALUE[node_repr]
        return node_repr.replace("\'", "\"")

    def visit_Name(self, node: ast.Name, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            try:
                return self.linter.get_var_type(node.id, repr_ctx.parser_ctx.scope)
            except KeyError:
                # During scanning phase, variables might not be defined yet
                # Return a placeholder type that can be resolved later
                if repr_ctx.parser_ctx.is_scanning:
                    return "Unknown"
                else:
                    raise
        return node.id

    def visit_Tuple(self, node: ast.Tuple, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
            )
            # Use list instead of pair for all tuples
            type_ = ["list"]
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
        
        final_type = self.linter.get_subscript_type(result, len(access), scope=repr_ctx.parser_ctx.scope)
        if repr_ctx.return_type:
            # Use string for all char and convert them down below
            # return "str" if final_type == "char" else final_type
            return final_type
        
        for acc in reversed(access):
            if acc == "-1":
                acc = f"{result}.size() - 1"
            result += f"[{acc}]"
        # if final_type == "char":
        #     return f"string(1, {result})"
        return result

    def visit_BinOp(self, node: ast.BinOp, repr_ctx: ReprVisitContext):
        if repr_ctx.parser_ctx.is_scanning:
            if repr_ctx.processor.should_scan_func(node.left, repr_ctx.parser_ctx):
                repr_ctx.processor.visit(node.left, repr_ctx.parser_ctx)
            if repr_ctx.processor.should_scan_func(node.right, repr_ctx.parser_ctx):
                repr_ctx.processor.visit(node.right, repr_ctx.parser_ctx)
        get_type_ctx = ReprVisitContext(
            return_type=True,
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        type_left = self.visit(node.left, get_type_ctx)
        type_right = self.visit(node.right, get_type_ctx)
        op_repr = self.visit_op(node.op)
        if repr_ctx.return_type:
            return self.linter.get_binop_type(type_left, type_right, op_repr)

        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        if isinstance(node.op, ast.Pow):
            template_name = CPPTemplate.FASTPOW.name
            Utils.template_uses.add(template_name)
            return f"{template_name.lower()}({self.visit(node.left, new_ctx)}, {self.visit(node.right, new_ctx)})"

        node_left_repr = self.visit(node.left, new_ctx)
        node_right_repr = self.visit(node.right, new_ctx)
        
        if isinstance(node.op, ast.Mult):
            if self.linter.is_list_repeatition(type_left, type_right, op_repr):
                if isinstance(type_left, list) and type_left[0] == "list":
                    list_type = type_left
                    int_type = type_right
                    list_repr = node_left_repr
                    int_repr = node_right_repr
                    list_node = node.left
                    int_node = node.right
                else:
                    list_type = type_right
                    int_type = type_left
                    list_repr = node_right_repr
                    int_repr = node_left_repr
                    list_node = node.right
                    int_node = node.left

                temp = deepcopy(list_node)
                while isinstance(temp, ast.List):
                    temp = temp.elts[0]
                default_val = self.visit(temp, new_ctx)

                if len(list_type) == 2:
                    return f"({int_repr}, {default_val}))"

                def build_recursive(cur_list_type):
                    if len(cur_list_type) == 2:
                        return f"vector<{cur_list_type[-1]}>(1, {default_val})"

                    return f"vector<{cur_list_type[0]}>(1, {build_recursive(cur_list_type[1:])})"

                return f"({int_repr}, {build_recursive(list_type[1:])})"

        return f"({node_left_repr} {op_repr} {node_right_repr})"

    def is_list_repeation_node(self, node: ast.BinOp, repr_ctx: ReprVisitContext) -> bool:
        """
            Check if the node is a list repeatition node
            e.g. [1, 2] * 3 or 3 * [1, 2]
        """
        if not isinstance(node.op, ast.Mult):
            return False

        get_type_ctx = ReprVisitContext(
            return_type=True,
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        type_left = self.visit(node.left, get_type_ctx)
        type_right = self.visit(node.right, get_type_ctx)

        return self.linter.is_list_repeatition(type_left, type_right, "*")

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
            if type_other == "int" and func_name == "str":
                return f"to_string({self.visit(node.args[0], new_ctx)})"
            return f"({Linter.TYPES[func_name]}) ({self.visit(node.args[0], new_ctx)})"
        if func_name == "ord":
            type_arg = self.visit(node.args[0], get_type_ctx)
            if type_arg == "char":
                return f"static_cast<int>({self.visit(node.args[0], new_ctx)})"
            if type_arg == "str":
                return f"static_cast<int>({self.visit(node.args[0], new_ctx)}.at(0))"

            raise ValueError(f"Cannot convert {type_arg} to int using ord()")

        if func_name == "chr":
            return f"static_cast<char>({self.visit(node.args[0], new_ctx)})"

        # This is not a builtin function, so we need to handle it
        return None
            
    # TODO: This shouldn't be here, we will move it back to processor.py
    def visit_Call(self, node: ast.Call, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            if isinstance(node.func, ast.Name):
                if node.func.id in self.linter.funcs:
                    return self.linter.funcs[node.func.id].return_pytype
                return self.get_type_from_pyfunction(node, repr_ctx)
            if isinstance(node.func, ast.Attribute):
                return self.linter.get_attr_type("Unknown", node.func.attr)
                
                self.logger.error("Call %s not implemented", node.func)
                raise NotImplementedError(f"Call {node.func} not implemented")

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

        self.logger.error("Attribute %s not implemented for %s", attr_name, node_name)
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
            self.linter.add_var("temp", "Unknown", scope=full_new_scope)
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
            element_type = self.visit(node.elts[0], new_ctx)
            if isinstance(element_type, list):
                return ["list"] + element_type
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
            ast.FloorDiv: "/",
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
        self.logger.error("Visit method not implemented for %s", type(node).__name__)
        raise NotImplementedError(
            f"Visit method not implemented for {type(node).__name__}")

    def visit_Dict(self, node: ast.Dict, repr_ctx: ReprVisitContext):
        if repr_ctx.return_type:
            new_ctx = ReprVisitContext(
                processor=repr_ctx.processor,
                return_type=True,
                parser_ctx=repr_ctx.parser_ctx,
                expr_node = repr_ctx.expr_node
            )
            key_type = self.visit(node.keys[0], new_ctx)
            value_type = self.visit(node.values[0], new_ctx)
            return ["dict", key_type, value_type]
        
        new_ctx = ReprVisitContext(
            processor=repr_ctx.processor,
            parser_ctx=repr_ctx.parser_ctx,
            expr_node = repr_ctx.expr_node
        )
        return f"{{{', '.join(f'{self.visit(k, new_ctx)}: {self.visit(v, new_ctx)}' for k, v in zip(node.keys, node.values))}}}"
