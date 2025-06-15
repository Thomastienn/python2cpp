import os
import sys
import ast
import pprint
import builtins
from copy import deepcopy

from py2c.utils.linter import Linter
from py2c.utils import constants
from py2c.core.visitor import ReprVisitor
from py2c.core.structure import VisitContext, ReprVisitContext, Function


# _original_print = builtins.print
# def print(*args, **kwargs):
#     # Extract file= if present, to pass as stream to pprint
#     stream = kwargs.pop('file', None)
#     # If exactly one argument, use pprint.pprint on it
#     if len(args) == 1:
#         pprint.pprint(args[0], stream=stream)
#     else:
#         # Multiple args: behave like regular print, including file=...
#         if stream is not None:
#             kwargs['file'] = stream
#         _original_print(*args, **kwargs)

class ExprParser:
    def __init__(self, funcs: dict[str, Function]):
        self.linter = Linter(funcs)
        self.repr = ReprVisitor(self.linter)
        self.allow_print = True
        self.debug = open((os.devnull if constants.PROD else "debug.out"), "w")
        self.num_for = 0

    def should_scan_func(self, node: ast.AST, visit_ctx: VisitContext):
        return isinstance(node, ast.Call) and \
            node.func.id in self.linter.funcs and \
            (self.linter.funcs[node.func.id].return_pytype is None) and \
            node.func.id != visit_ctx.scope[-1]

    def print_line(self, line: str, current_indent: int, end="\n"):
        if self.allow_print:
            print((constants.TAB * current_indent) + line, end=end)

    def visit_Str(self, string: str):
        if string == "DEBUG":
            print(string, file=self.debug)
            return
        raise RuntimeError("You are not suppose to end up here")
        
    def visit(self, node: ast.AST, visit_ctx: VisitContext = VisitContext()):
        if visit_ctx.allow_print is None:
            allow_print = self.allow_print
        else:
            allow_print = visit_ctx.allow_print
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)

        original = self.allow_print
        self.allow_print = allow_print
        
        # DEBUG STUFF
        print(str(self.linter.has_typed).replace('\'', '\"'), file=self.debug)
        print("-" * 5, file=self.debug)
        print(str(self.linter.typed_vars).replace('\'', '\"'), file=self.debug)
        print(visit_ctx, file=self.debug)
        print("VISITING: ", node, file=self.debug)
        print(self.linter.funcs, file=self.debug)
        print("-" * 20, file=self.debug)
        
        result = visitor(node, VisitContext(
            current_indent=visit_ctx.current_indent,
            allow_print=allow_print,
            scope=visit_ctx.scope,
            is_scanning=visit_ctx.is_scanning,
        ))
        self.allow_print = original
        return result

    def generic_visit(self, node, visit_ctx: VisitContext):
        print("NOT IMPLEMENTED: ",node, file=sys.stderr)
        return

    def find_type_func(self, func_node, visit_ctx: VisitContext):
        if isinstance(func_node.func, ast.Attribute):
            return self.linter.get_attr_type("Unknown", func_node.func.attr)

        func_name = func_node.func.id
        if func_name in self.linter.funcs:
            return self.visit(func_node, visit_ctx)

        get_type_ctx = ReprVisitContext(
            processor=self,
            return_type=True,
            parser_ctx=visit_ctx,
            expr_node=func_node
        )
        if func_name == "list":
            types_inside = []
            for arg in func_node.args:
                type_ = self.repr.visit(arg, get_type_ctx)
                types_inside.append(type_)

            return ["list"] + types_inside

        return self.repr.get_type_from_pyfunction(func_node, get_type_ctx)

    def set_type(self, name, scope):
        if self.allow_print:
            self.linter.set_has_type(name, scope)

    def unset_type(self, name, scope):
        if self.allow_print:
            self.linter.unset_has_type(name, scope)

    def visit_Assign(self, node: ast.Assign, visit_ctx: VisitContext):
        def already_declared(name, scope):
            # TODO: Check if we want to bubble up in the scope
            # Sometimes it's ambiguous
            
            if name is None:
                return False

            # if name == "tree":
            #     print(visit_ctx.scope, file=sys.stderr)
            #     print(self.linter.does_has_type(name, scope=scope), 
            #     self.linter.has_higher_scope_var(name, scope), file=sys.stderr)
            #     print("-" * 20, file=sys.stderr)

            return self.linter.does_has_type(name, scope=scope)

            # return self.linter.does_has_type(name, scope=scope) or \
            #     self.linter.has_higher_scope_var(name, scope)
        
        targets = node.targets
        value = node.value
        
        if isinstance(value, ast.Call):
            type_name_val = self.find_type_func(value, visit_ctx)
        else:
            repr_ctx = ReprVisitContext(
                return_type=True,
                processor=self,
                parser_ctx = visit_ctx,
                expr_node = node
            )
            type_name_val = self.repr.visit(value, repr_ctx) 

        get_name_ctx = ReprVisitContext(
            processor=self,
            parser_ctx = visit_ctx,
            expr_node = node
        )
        repr_ctx = ReprVisitContext(
            return_type=False,
            processor=self,
            parser_ctx=visit_ctx,
            pytype_assign_from = type_name_val,
            expr_node = node
        )
        value_str = self.repr.visit(value, repr_ctx)


        cpp_type = self.linter.python_to_cpp_type(type_name_val)
        for target in targets:
            repr_ctx = ReprVisitContext(
                processor=self,
                parser_ctx = visit_ctx,
                expr_node = node
            )
            target_str = self.repr.visit(target, repr_ctx)

            name = None
            while isinstance(target, ast.Subscript):
                target = target.value
                if isinstance(target, ast.Name):
                    name = target.id
                    
            # It's a tuple of variables
            is_unpacking = "," in target_str
            if is_unpacking:
                for target_s in target_str.split(","):
                    self.linter.add_var(target_s, type_name_val, scope=visit_ctx.scope)
            else:
                if name is None:
                    self.linter.add_var(target_str, type_name_val, scope=visit_ctx.scope)
                    
            if already_declared(target_str, visit_ctx.scope) or \
                already_declared(name, visit_ctx.scope):
                self.print_line(f"{target_str} = {value_str};", visit_ctx.current_indent)
            else:
                self.set_type(target_str, visit_ctx.scope)
                self.print_line(f"{'auto' if is_unpacking else cpp_type}{' [' if is_unpacking else ' '}{target_str}{']' if is_unpacking else ''} = {value_str};", visit_ctx.current_indent)
                if target_str == "temp":
                    self.unset_type(target_str, visit_ctx.scope)

        return "None"

    def visit_AugAssign(self, node: ast.AugAssign, visit_ctx: VisitContext):
        # self.print_line("AUG ASSIGN: ", current_indent, end="")
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        self.print_line(self.repr.visit(node.target, repr_ctx) + " " + \
                        self.repr.visit_op(node.op) + "= " + \
                        self.repr.visit(node.value, repr_ctx) + ";"
                        , visit_ctx.current_indent)
        return "None"

    def visit_Call(self, node: ast.Call, visit_ctx: VisitContext):
        if visit_ctx.is_scanning:
            for arg in node.args:
                if self.should_scan_func(arg, visit_ctx):
                    self.visit(arg, visit_ctx)

        repr_ctx = ReprVisitContext(
            processor=self,
            return_type=True,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        func_name: str = node.func.id
        if func_name not in self.linter.funcs:
            # Assuming this is a builtin function
            new_ctx = repr_ctx.copy()
            new_ctx.parser_ctx.scope = ["global"]
            return self.repr.get_type_from_pyfunction(node, new_ctx)
            
        func: Function = self.linter.funcs[func_name]
        if func.return_pytype is not None:
            return func.return_pytype

        # Now we know the type of parameters, put this in the info
        func_ast_obj = func._ast_object
        # TODO : Support nested scope
        # Now it assumes all functions are global
        for func_param, arg in zip(func_ast_obj.args.args, node.args):
            # Get the type from argument and pass it to parameter
            type_ = self.repr.visit(arg, repr_ctx)
            self.linter.add_var(func_param.arg, type_, scope=["global", func_name])

        # For keywords like a=1, b=(math.pi*2) something
        for arg, value in node.keywords:
            type_ = self.repr.visit(arg, repr_ctx)
            self.linter.add_var(arg, type_, scope=["global", func_name])

        # Now need to return the type by going to function definition
        new_ctx = VisitContext(
            current_indent=visit_ctx.current_indent,
            allow_print = False,
            scope=["global", func._ast_object.name],
            is_scanning=visit_ctx.is_scanning
        )
        return_type = self.visit(func._ast_object, new_ctx)
        func.return_pytype = return_type
        return return_type

    def find_first_return(self, node: ast.AST):
        if isinstance(node, ast.Return):
            return node
        if isinstance(node, (ast.If, ast.For, ast.While)):
            for expr in node.body:
                ret = self.find_first_return(expr)
                if ret is not None:
                    return ret
            return None
        
        return None
                          
    def visit_FunctionDef(self, node: ast.FunctionDef, visit_ctx: VisitContext):
        def pytype_arg(name):
            type_ = self.linter.get_var_type(name, scope=visit_ctx.scope)
            return type_
        def ctype_arg(name):
            return self.linter.python_to_cpp_type(pytype_arg(name))
        

        arguments = []
        for arg in node.args.args:
            arguments.append(ctype_arg(arg.arg) + " " + arg.arg)
            self.set_type(arg.arg, visit_ctx.scope)

        # GUESS WHAT THE RETURN TYPE IS
        expected_return_type = "None"
        walk_already = {node.name}
        for expr in node.body:
            return_node = self.find_first_return(expr)
            if return_node is not None:
                return_val = return_node.value
                if return_val is None:
                    continue

                if isinstance(return_val, ast.Call):
                    name_func = return_val.func.id
                    # Skip some type of recursion
                    if name_func in walk_already:
                        continue
                    walk_already.add(name_func)
                    if expected_return_type == "None":
                        new_scope = deepcopy(visit_ctx.scope)
                        new_scope.pop()
                        new_scope.append(name_func)
                        new_ctx = VisitContext(
                            current_indent = visit_ctx.current_indent + 1,
                            allow_print = False,
                            scope = new_scope,
                            is_scanning = visit_ctx.is_scanning
                        )
                        expected_return_type = self.visit(return_val, new_ctx)
                else:
                    if expected_return_type == "None":
                        repr_ctx = ReprVisitContext(
                            processor=self,
                            return_type=True,
                            parser_ctx=visit_ctx,
                            expr_node=node   
                        )
                        expected_return_type = self.repr.visit(return_val, repr_ctx)

            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                allow_print = False,
                scope = visit_ctx.scope,
                is_scanning = visit_ctx.is_scanning
            )
            self.visit(expr, new_ctx)
            
        # PRINT FORMAT FUCNTION
        self.print_line(f"{self.linter.python_to_cpp_type(expected_return_type)} {node.name}({', '.join(arguments)}) {{", visit_ctx.current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope = visit_ctx.scope,
                is_scanning = visit_ctx.is_scanning,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)
        
        self.linter.funcs[node.name].return_pytype = expected_return_type
        return expected_return_type

    def print_for_i(self, var: str, node: ast.Call, visit_ctx: VisitContext, save_type):
        """
            Print for i loop
            PARAMS
            node: ast.Call which is calling range() func
        """
        if save_type:
            self.linter.add_var(var, "int", scope=visit_ctx.scope+[f"for_{self.num_for}"])
        start = 0
        end = None
        step = 1
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        if len(node.args) == 0:
            raise RuntimeError("No arguments for range()")
        elif len(node.args) == 1:
            end = self.repr.visit(node.args[0], repr_ctx)
        elif len(node.args) == 2:
            start = self.repr.visit(node.args[0], repr_ctx)
            end = self.repr.visit(node.args[1], repr_ctx)
        elif len(node.args) == 3:
            start = self.repr.visit(node.args[0], repr_ctx)
            end = self.repr.visit(node.args[1], repr_ctx)
            step = self.repr.visit(node.args[2], repr_ctx)
        else:
            raise RuntimeError("Too many arguments for range()")
            
        assert end != None, "my badd, end of range should be parsed"
        add_str = f"{var}++" if step == 1 else f"{var} += {step}"
        self.print_line(f"for (int {var} = {start}; {var} < {end}; {add_str}) {{", visit_ctx.current_indent)

    def print_for_iter(self, var, node: ast.AST, visit_ctx: VisitContext, save_type):
        repr_ctx = ReprVisitContext(
            processor=self,
            return_type=True,
            parser_ctx = visit_ctx,
            expr_node=node
        )
        func_return_type = self.repr.visit(node, repr_ctx)
        repr_ctx_2 = ReprVisitContext(
            processor=self,
            parser_ctx = visit_ctx,
            expr_node=node
        )
        # We have to remove the parent type
        func_return_type = func_return_type[1:]
        if len(func_return_type) == 1:
            func_return_type = func_return_type[0]
        cpp_type = self.linter.python_to_cpp_type(func_return_type)
        if save_type:
            self.linter.add_var(var, func_return_type, scope=visit_ctx.scope+[f"for_{self.num_for}"])
        self.print_line(f"for ({cpp_type} {var} : {self.repr.visit(node, repr_ctx_2)}) {{", visit_ctx.current_indent)

    def print_forloop(self, node: ast.For, visit_ctx: VisitContext, save_type=True):
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        target_visited = self.repr.visit(node.target, repr_ctx)
        if isinstance(node.iter, ast.Call) and node.iter.func.id == "range":
            self.print_for_i(target_visited, node.iter, visit_ctx, save_type)
        else:
            self.print_for_iter(target_visited, node.iter, visit_ctx, save_type)

    def visit_For(self, node: ast.For, visit_ctx: VisitContext):
        # self.print_line(f"for ({self.repr.visit(node.target)} in {self.repr.visit(node.iter)}) {{", visit_ctx.current_indent)
        self.num_for += 1
        self.print_forloop(node, visit_ctx)

        # Add this target to the scope linter
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
            
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope = visit_ctx.scope,
                is_scanning = visit_ctx.is_scanning,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

    def visit_If(self, node: ast.If, visit_ctx: VisitContext):
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx = visit_ctx,
            expr_node=node
        )
        self.print_line(
            f"if ({self.repr.visit(node.test, repr_ctx)}) {{", visit_ctx.current_indent)

        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope=visit_ctx.scope,
                is_scanning=visit_ctx.is_scanning,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

        if node.orelse:
            # self.print_line("ELSE EXP:", current_indent)
            self.print_line("else {", visit_ctx.current_indent)
            for expr in node.orelse:
                new_ctx = VisitContext(
                    current_indent = visit_ctx.current_indent + 1,
                    scope=visit_ctx.scope,
                    is_scanning=visit_ctx.is_scanning,
                )
                self.visit(expr, new_ctx)
            self.print_line("}", visit_ctx.current_indent)
        # self.print_line("END", current_indent)

    def visit_Return(self, node: ast.Return, visit_ctx: VisitContext):
        if node.value is None:
            self.print_line("return;", visit_ctx.current_indent)
            return
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        self.print_line(f"return {self.repr.visit(node.value, repr_ctx)};", visit_ctx.current_indent)

    def visit_While(self, node: ast.While, visit_ctx: VisitContext):
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx = visit_ctx,
            expr_node=node
        )
        self.print_line(
            f"while ({self.repr.visit(node.test, repr_ctx)}) {{", visit_ctx.current_indent)
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope=visit_ctx.scope,
                is_scanning=visit_ctx.is_scanning,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

    def visit_Expr(self, node: ast.Expr, visit_ctx: VisitContext):
        if visit_ctx.is_scanning:
            if self.should_scan_func(node.value, visit_ctx):
                self.visit(node.value, visit_ctx)
            for arg in node.value.args:
                if self.should_scan_func(arg, visit_ctx):
                    self.visit(arg, visit_ctx)
                
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        value = self.repr.visit(node.value, repr_ctx)
        self.print_line(value + ";", visit_ctx.current_indent)
        return type(value).__name__

    def visit_Pass(self, node: ast.Pass, visit_ctx: VisitContext):
        pass

    def visit_Load(self, node: ast.Load, visit_ctx: VisitContext):
        pass

    def visit_Store(self, node: ast.Store, visit_ctx: VisitContext):
        pass

# Usage example:

# repr = ReprVisitor()
# printer = ASTPrinter(repr)
# tree = ast.parse(your_code_string)
# for node in tree.body:
#     printer.visit(node)
