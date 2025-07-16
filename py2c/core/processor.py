"""
Python AST Expression Parser and Processor

This module contains the core ExprParser class responsible for processing Python
Abstract Syntax Tree (AST) nodes and converting them to C++ equivalents. It handles
various Python constructs including:

- Variable assignments and declarations
- Function definitions and calls
- Control flow statements (if, for, while)
- Data structures (lists, tuples, dictionaries)
- Expressions and operators
- Type inference and management

The ExprParser works in conjunction with the Linter and ReprVisitor classes to
perform semantic analysis and code generation.

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

import os
import sys
import ast
import pprint
import builtins
from copy import deepcopy

from py2c.utils.linter import Linter
from py2c.utils import constants
from py2c.utils.scope_handler import ScopeHandler
from py2c.core.visitor import ReprVisitor
from py2c.core.structure import VisitContext, ReprVisitContext, Function
from py2c.utils.logger import setup_logger
from py2c.core.errors import ErrorUsage, UserError, ParserError, LinterError, VisitorError


class ExprParser:
    """
    Main AST processor for converting Python expressions to C++ code.
    
    This class is responsible for traversing Python AST nodes and generating
    equivalent C++ code. It handles type inference, scope management, and
    code generation for various Python constructs.
    
    Attributes:
        linter (Linter): Type checking and variable management system
        repr (ReprVisitor): Expression representation visitor
        allow_print (bool): Whether to output generated code
        num_for (int): Counter for for loop nesting levels
        logger (Logger): Logging instance for debug output
    """
    
    def __init__(self, funcs: dict[str, Function]):
        """
        Initialize the expression parser.
        
        Args:
            funcs (dict[str, Function]): Dictionary mapping function names to Function objects
        """
        self.linter = Linter(funcs)
        self.repr = ReprVisitor(self.linter)
        self.allow_print = True
        # Debug output now handled by logging
        self.num_for = 0
        self.logger = setup_logger("py2cpp.processor")

    def should_scan_func(self, node: ast.AST, visit_ctx: VisitContext):
        """
        Check if a function call should be scanned during the pre-processing phase.
        
        Args:
            node (ast.AST): The AST node to check
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            bool: True if the function should be scanned, False otherwise
        """
        return isinstance(node, ast.Call) and \
            isinstance(node.func, ast.Name) and node.func.id in self.linter.funcs and \
            (self.linter.funcs[node.func.id].return_pytype is None) and \
            node.func.id not in visit_ctx.scope

    def print_line(self, line: str, current_indent: int, end="\n"):
        """
        Print a line of C++ code with proper indentation.
        
        Args:
            line (str): The line of code to print
            current_indent (int): Current indentation level
            end (str): Line ending character (default: newline)
        """
        if self.allow_print:
            print((constants.TAB * current_indent) + line, end=end)
        else:
            self.logger.debug("%s%s", constants.TAB * current_indent, line)

    def visit_Str(self, string: str, visit_ctx: VisitContext):
        if string == "DEBUG":
            self.logger.debug("Debug info - has_typed: %s", self.linter.has_typed)
            self.logger.debug("Debug info - typed_vars: %s", self.linter.typed_vars)
            self.logger.debug("Debug info - funcs: %s", self.linter.funcs)
            return
        raise ErrorUsage("You are not supposed to end up here")
        
    def visit(self, node: ast.AST, visit_ctx: VisitContext = VisitContext()):
        """
        Visit an AST node and dispatch to the appropriate visitor method.
        
        This is the main entry point for processing AST nodes. It uses dynamic
        dispatch to call the appropriate visit_* method based on the node type.
        
        Args:
            node (ast.AST): The AST node to visit
            visit_ctx (VisitContext): Context information for the visit
        
        Returns:
            Any: The result of the visitor method (usually a type string)
        """
        if visit_ctx.allow_print is None:
            allow_print = self.allow_print
        else:
            allow_print = visit_ctx.allow_print
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)

        original = self.allow_print
        self.allow_print = allow_print
        
        # Debug logging
        self.logger.debug("has_typed: %s", str(self.linter.has_typed).replace('\'', '\"'))
        self.logger.debug("typed_vars: %s", str(self.linter.typed_vars).replace('\'', '\"'))
        self.logger.debug("visit_ctx: %s", visit_ctx)
        self.logger.debug("visiting: %s", node)
        self.logger.debug("funcs: %s", self.linter.funcs)
        
        result = visitor(node, VisitContext(
            current_indent=visit_ctx.current_indent,
            allow_print=allow_print,
            scope=ScopeHandler.additional_scope(node=node, current_scope=visit_ctx.scope, linter=self.linter),
            is_scanning=visit_ctx.is_scanning,
        ))
        self.allow_print = original
        return result

    def generic_visit(self, node, visit_ctx: VisitContext):
        """
        Default visitor method for unimplemented AST nodes.
        
        Args:
            node (ast.AST): The unimplemented AST node
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            None: Always returns None after logging the error
        """
        self.logger.error("NOT IMPLEMENTED: %s", node)
        return

    def set_type(self, name, scope):
        """
        Mark a variable as having its type set (for code generation).
        
        Args:
            name (str): Variable name
            scope (list[str]): Scope path where the variable is located
        """
        if self.allow_print:
            self.linter.set_has_type(name, scope)

    def unset_type(self, name, scope):
        """
        Mark a variable as not having its type set.
        
        Args:
            name (str): Variable name
            scope (list[str]): Scope path where the variable is located
        """
        if self.allow_print:
            self.linter.unset_has_type(name, scope)

    def already_declared(self, name, visit_ctx: VisitContext):
        """
        Check if a variable has already been declared in the current scope.
        
        Args:
            name (str): Variable name to check
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            bool: True if the variable has been declared, False otherwise
        """
        # TODO: Check if we want to bubble up in the scope
        # Sometimes it's ambiguous

        if name is None:
            return False

        # Check if variable has been actually declared/printed in current context or parent scopes
        if visit_ctx.is_scanning:
            try:
                self.linter.get_var_type(name, scope=visit_ctx.scope)
                return True
            except LinterError:
                return False

        return self.linter.does_has_type(name, scope=visit_ctx.scope)

    def visit_AnnAssign(self, node: ast.AnnAssign, visit_ctx: VisitContext):
        """
        Handle annotated assignments like `a: int = 1`
        """
        type_ = self.linter.get_pytype_from_annotations(node.annotation)
        target = node.target

        repr_ctx = ReprVisitContext(
            processor=self,
            return_type=False,
            parser_ctx=visit_ctx,
            expr_node=node
        )

        target_str = self.repr.visit(target, repr_ctx)
        value_str = self.repr.visit(node.value, repr_ctx)

        if self.already_declared(target.id, visit_ctx):
            self.print_line(f"{target_str} = {value_str};", visit_ctx.current_indent)
        else:
            self.linter.add_var(target_str, type_, scope=visit_ctx.scope)
            self.set_type(target_str, visit_ctx.scope)
            self.print_line(f"{self.linter.python_to_cpp_type(type_)} {target_str} = {value_str};", visit_ctx.current_indent)

    def visit_Assign(self, node: ast.Assign, visit_ctx: VisitContext):
        """
        Handle Python assignment statements and convert them to C++.
        
        This method processes various types of assignments including:
        - Simple assignments (a = 1)
        - Tuple unpacking (a, b = (1, 2))
        - Subscript assignments (arr[0] = value)
        - Multiple assignments (a = b = 1)
        
        Args:
            node (ast.Assign): The assignment AST node
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            str: Always returns "None" as assignments don't return values
        """
        targets = node.targets
        value = node.value

        type_var_err = None
        try:
            if isinstance(value, ast.Call):
                type_name_val = self.repr.visit(value, ReprVisitContext(
                    processor=self,
                    return_type=True,
                    parser_ctx=visit_ctx,
                    expr_node=node
                ))
            else:
                repr_ctx = ReprVisitContext(
                    return_type=True,
                    processor=self,
                    parser_ctx=visit_ctx,
                    expr_node=node
                )
                type_name_val = self.repr.visit(value, repr_ctx)
            cpp_type = self.linter.python_to_cpp_type(type_name_val)
        except (LinterError, VisitorError) as e:
            type_var_err = e

        repr_ctx = ReprVisitContext(
            return_type=False,
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        value_str = self.repr.visit(value, repr_ctx)

        for target in targets:
            repr_ctx = ReprVisitContext(
                processor=self,
                parser_ctx=visit_ctx,
                expr_node=node
            )
            target_str = self.repr.visit(target, repr_ctx)

            name = None
            original_target = target
            while isinstance(target, ast.Subscript):
                target = target.value
            if isinstance(target, ast.Name):
                name = target.id
            # For simple variable assignments (not subscripts), set name from target_str
            elif isinstance(original_target, ast.Name):
                name = original_target.id
                    
            # It's a tuple of variables
            is_unpacking = "," in target_str
            
            if isinstance(original_target, ast.Subscript):
                # For subscript assignments, just assign without declaring
                self.print_line(f"{target_str} = {value_str};", visit_ctx.current_indent)
            elif is_unpacking:
                # Check if all variables in the tuple are already declared
                target_vars = [var.strip() for var in target_str.split(",")]
                all_declared = all(self.already_declared(var, visit_ctx) for var in target_vars)
                
                
                if all_declared:
                    # All variables are already declared, use tie for assignment
                    self.print_line(f"tie({target_str}) = {value_str};", visit_ctx.current_indent)
                else:
                    # Theres an error with the type
                    if type_var_err is not None:
                        raise ParserError(str(type_var_err))
                    # At least one variable is new
                    # This is destructuring assignment
                    real_element_type = type_name_val[1:]
                    if len(real_element_type) == 1:
                        real_element_type = real_element_type[0]

                    for target_s in target_vars:
                        if not self.already_declared(target_s, visit_ctx):
                            self.linter.add_var(target_s, real_element_type, scope=visit_ctx.scope)
                            self.set_type(target_s, visit_ctx.scope)
                    self.print_line(f"auto [{target_str}] = {value_str};", visit_ctx.current_indent)
            elif self.already_declared(target_str, visit_ctx) or \
                self.already_declared(name, visit_ctx):
                self.print_line(f"{target_str} = {value_str};", visit_ctx.current_indent)
            else:
                if type_var_err is not None:
                    raise ParserError(str(type_var_err))
                # Single variable, not declared yet
                self.linter.add_var(target_str, type_name_val, scope=visit_ctx.scope)
                self.set_type(target_str, visit_ctx.scope)

                repr_ctx = ReprVisitContext(
                    processor=self,
                    parser_ctx=visit_ctx,
                    expr_node=node
                )
                assign_repr = "" if (isinstance(value, ast.BinOp) and self.repr.is_list_repeation_node(value, repr_ctx)) else " = "
                self.print_line(f"{cpp_type} {target_str}{assign_repr}{value_str};", visit_ctx.current_indent)
                if target_str == "temp":
                    self.unset_type(target_str, visit_ctx.scope)

        return "None"

    def visit_AugAssign(self, node: ast.AugAssign, visit_ctx: VisitContext):
        """
        Handle augmented assignment statements (+=, -=, *=, etc.).
        
        Args:
            node (ast.AugAssign): The augmented assignment AST node
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            str: Always returns "None" as augmented assignments don't return values
        """
        # if visit_ctx.is_scanning:
        #     if self.should_scan_func(node.value, visit_ctx):
        #         self.visit(node.value, visit_ctx)

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

    # This suppose to be in visitor 
    # (i dont want to move it becauses it might break everything)
    # TODO: Try to move it to visitor 
    # Before that, need lots of unit tests
    def visit_Call(self, node: ast.Call, visit_ctx: VisitContext):
        """
        Handle function call expressions and determine return types.
        
        This method processes function calls during the scanning phase to
        infer return types and manage function signatures.
        
        Args:
            node (ast.Call): The function call AST node
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            str: The inferred return type of the function call
        """
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

        new_visitctx = visit_ctx.copy()
        # During scanning phase, user functions are typically in global scope
        # Try to find the function scope, but handle case where it doesn't exist yet
        try:
            new_visitctx.scope = self.linter.find_scope_by_var(func_name, findFunc=True, scope=visit_ctx.scope)
        except LinterError:
            # If function not found in scope system yet (during scanning), assume global scope
            if func.user_func:
                new_visitctx.scope = ["global"]
            else:
                new_visitctx.scope = visit_ctx.scope

        arg_repr_ctx = ReprVisitContext(
            processor=self,
            return_type=True,
            parser_ctx=new_visitctx,
            expr_node=node
        )

        for func_param, arg in zip(func_ast_obj.args.args, node.args):
            # Get the type from argument and pass it to parameter
            type_ = self.repr.visit(arg, arg_repr_ctx)
            if not isinstance(arg, ast.Call):
                self.linter.add_var(func_param.arg, type_, scope=repr_ctx.parser_ctx.scope,is_param=True)

        # For keywords like a=1, b=(math.pi*2) something
        for arg, value in node.keywords:
            type_ = self.repr.visit(arg, arg_repr_ctx)
            if not isinstance(arg, ast.Call):
                self.linter.add_var(arg, type_, scope=repr_ctx.parser_ctx.scope, is_param=True)

        # Now need to return the type by going to function definition
        # Use the scope we determined earlier
        new_ctx = VisitContext(
            current_indent=visit_ctx.current_indent,
            allow_print = False,
            scope=new_visitctx.scope,
            is_scanning=visit_ctx.is_scanning
        )

        return_type = self.visit(func._ast_object, new_ctx)
        func.return_pytype = return_type
        return return_type

    def find_first_return(self, node: ast.AST):
        """
        Find the first return statement in an AST node.
        
        Args:
            node (ast.AST): The AST node to search
        
        Returns:
            ast.Return | None: The first return statement found, or None
        """
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
        """
        Process function definitions and convert them to C++ function declarations.
        
        This method handles:
        - Function parameter type inference
        - Return type inference from return statements
        - Function body processing
        - Scope management for function parameters
        
        Args:
            node (ast.FunctionDef): The function definition AST node
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            str: The inferred return type of the function
        """
        # print(visit_ctx, file=sys.stderr)
        
        # Ensure the function scope exists in the linter
        # Initialize the nested scope path if it doesn't exist
        cur_scope = self.linter.typed_vars
        for s in visit_ctx.scope:
            if s not in cur_scope:
                cur_scope[s] = {}
            cur_scope = cur_scope[s]
        
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
                        # Try to find function scope, but handle case where it doesn't exist yet
                        try:
                            func_scope = self.linter.find_scope_by_var(name_func, findFunc=True, scope=visit_ctx.scope)
                        except LinterError:
                            # If function not found in scope system yet, assume global scope
                            func_scope = ["global"]
                        
                        new_ctx = VisitContext(
                            current_indent = visit_ctx.current_indent + 1,
                            allow_print = False,
                            scope = func_scope,
                            is_scanning = visit_ctx.is_scanning
                        )
                        expected_return_type = self.visit(return_val, new_ctx)
                        self.linter.funcs[node.name].return_pytype = expected_return_type
                else:
                    if expected_return_type == "None":
                        repr_ctx = ReprVisitContext(
                            processor=self,
                            return_type=True,
                            parser_ctx=visit_ctx,
                            expr_node=node   
                        )
                        expected_return_type = self.repr.visit(return_val, repr_ctx)
                        self.linter.funcs[node.name].return_pytype = expected_return_type

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
        
        if expected_return_type == "None":
            self.linter.funcs[node.name].return_pytype = expected_return_type
        return expected_return_type

    def print_for_i(self, var: str, node: ast.Call, visit_ctx: VisitContext, save_type, node_for: ast.For):
        """
        Generate C++ code for a range-based for loop (for i in range(...)).
        
        This method converts Python's range() function calls into equivalent
        C++ for loops with proper start, end, and step values.
        
        Args:
            var (str): Loop variable name
            node (ast.Call): The range() function call AST node
            visit_ctx (VisitContext): Current visiting context
            save_type (bool): Whether to save variable type information
            node_for (ast.For): The original for loop AST node
        
        Raises:
            UserError: If range() has invalid number of arguments
            ParserError: If end value cannot be determined
        """
        # if visit_ctx.is_scanning:
        #     for arg in node.args:
        #         if self.should_scan_func(arg, visit_ctx):
        #             self.visit(arg, visit_ctx)
        if save_type:
            # Create the for loop scope
            for_scope_name = f"for_{id(node_for)}"
            new_scope = visit_ctx.scope + [for_scope_name]
            self.linter.add_var(var, "int", scope=new_scope)
        start = 0
        end = None
        step = 1
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        if len(node.args) == 0:
            raise UserError("No arguments for range()")
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
            raise UserError("Too many arguments for range()")
            
        if end is None:
            raise ParserError("my badd, end of range should be parsed")

        add_str = f"{var}++" if step == "1" else f"{var} += {step}"
        compare_sign = "<" if int(step) > 0 else ">"
        self.print_line(f"for (int {var} = {start}; {var} {compare_sign} {end}; {add_str}) {{", visit_ctx.current_indent)

    def print_for_iter(self, var, node: ast.AST, visit_ctx: VisitContext, save_type, node_for: ast.For):
        """
        Generate C++ code for iterator-based for loops (for item in iterable).
        
        This method converts Python's iterator-based for loops into equivalent
        C++ range-based for loops, handling type inference for the loop variable.
        
        Args:
            var (str): Loop variable name
            node (ast.AST): The iterable expression AST node
            visit_ctx (VisitContext): Current visiting context
            save_type (bool): Whether to save variable type information
            node_for (ast.For): The original for loop AST node
        """
        new_ctx = visit_ctx.copy()
        new_ctx.scope = new_ctx.scope[:-1]
        repr_ctx = ReprVisitContext(
            processor=self,
            return_type=True,
            parser_ctx = new_ctx,
            expr_node=node
        )
        iter_return_type = self.repr.visit(node, repr_ctx)
        repr_ctx_2 = ReprVisitContext(
            processor=self,
            parser_ctx = visit_ctx,
            expr_node=node
        )
        if iter_return_type == "str":
            iter_return_type = "char"
        else:
            # This is assuming this is a loop over iterator
            # We need handle for string too
            # We have to remove the parent type
            iter_return_type = iter_return_type[1:]
            if len(iter_return_type) == 1:
                iter_return_type = iter_return_type[0]
        cpp_type = self.linter.python_to_cpp_type(iter_return_type)
        if save_type:
            # Create the for loop scope
            for_scope_name = f"for_{id(node_for)}"
            new_scope = visit_ctx.scope + [for_scope_name]
            self.linter.add_var(var, iter_return_type, scope=new_scope)
        self.print_line(f"for ({cpp_type} {var} : {self.repr.visit(node, repr_ctx_2)}) {{", visit_ctx.current_indent)

    def print_forloop(self, node: ast.For, visit_ctx: VisitContext, save_type=True):
        """
        Generate C++ code for Python for loops.
        
        This method dispatches to the appropriate loop handler based on whether
        the loop uses range() or iterates over an iterable.
        
        Args:
            node (ast.For): The for loop AST node
            visit_ctx (VisitContext): Current visiting context
            save_type (bool): Whether to save variable type information
        """
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        target_visited = self.repr.visit(node.target, repr_ctx)
        if isinstance(node.iter, ast.Call) and node.iter.func.id == "range":
            self.print_for_i(target_visited, node.iter, visit_ctx, save_type, node)
        else:
            self.print_for_iter(target_visited, node.iter, visit_ctx, save_type, node)

    def visit_For(self, node: ast.For, visit_ctx: VisitContext):
        """
        Process Python for loops and convert them to C++.
        
        This method handles both range-based and iterator-based for loops,
        managing scope creation and variable declarations.
        
        Args:
            node (ast.For): The for loop AST node
            visit_ctx (VisitContext): Current visiting context
        """
        # self.print_line(f"for ({self.repr.visit(node.target)} in {self.repr.visit(node.iter)}) {{", visit_ctx.current_indent)
        self.num_for += 1
        self.print_forloop(node, visit_ctx)

        # Add this target to the scope linter
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        
        # Create a new scope for the for loop
        for_scope_name = f"for_{id(node)}"
        new_scope = visit_ctx.scope + [for_scope_name]
            
        for expr in node.body:
            new_ctx = VisitContext(
                current_indent = visit_ctx.current_indent + 1,
                scope = new_scope,
                is_scanning = visit_ctx.is_scanning,
            )
            self.visit(expr, new_ctx)
        self.print_line("}", visit_ctx.current_indent)

    def visit_If(self, node: ast.If, visit_ctx: VisitContext):
        """
        Process Python if statements and convert them to C++.
        
        This method handles if-elif-else constructs, converting the test
        conditions and body statements to equivalent C++ code.
        
        Args:
            node (ast.If): The if statement AST node
            visit_ctx (VisitContext): Current visiting context
        """
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
        """
        Process Python return statements and convert them to C++.
        
        Args:
            node (ast.Return): The return statement AST node
            visit_ctx (VisitContext): Current visiting context
        """
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
        """
        Process Python while loops and convert them to C++.
        
        Args:
            node (ast.While): The while loop AST node
            visit_ctx (VisitContext): Current visiting context
        """
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
        """
        Process Python expression statements.
        
        Args:
            node (ast.Expr): The expression statement AST node
            visit_ctx (VisitContext): Current visiting context
        
        Returns:
            str: The type name of the expression value
        """
        repr_ctx = ReprVisitContext(
            processor=self,
            parser_ctx=visit_ctx,
            expr_node=node
        )
        value = self.repr.visit(node.value, repr_ctx)
        self.print_line(value + ";", visit_ctx.current_indent)
        return type(value).__name__

    def visit_Break(self, node: ast.Break, visit_ctx: VisitContext):
        """
        Process Python break statements.
        
        Args:
            node (ast.Break): The break statement AST node
            visit_ctx (VisitContext): Current visiting context
        """
        if visit_ctx.is_scanning:
            return
        self.print_line("break;", visit_ctx.current_indent)

    def visit_Continue(self, node: ast.Continue, visit_ctx: VisitContext):
        """
        Process Python continue statements.
        
        Args:
            node (ast.Continue): The continue statement AST node
            visit_ctx (VisitContext): Current visiting context
        """
        if visit_ctx.is_scanning:
            return
        self.print_line("continue;", visit_ctx.current_indent)

    def visit_Pass(self, node: ast.Pass, visit_ctx: VisitContext):
        """
        Process Python pass statements (no-op).
        
        Args:
            node (ast.Pass): The pass statement AST node
            visit_ctx (VisitContext): Current visiting context
        """
        pass

    def visit_Load(self, node: ast.Load, visit_ctx: VisitContext):
        """
        Process AST Load context (no action needed).
        
        Args:
            node (ast.Load): The load context AST node
            visit_ctx (VisitContext): Current visiting context
        """
        pass

    def visit_Store(self, node: ast.Store, visit_ctx: VisitContext):
        """
        Process AST Store context (no action needed).
        
        Args:
            node (ast.Store): The store context AST node
            visit_ctx (VisitContext): Current visiting context
        """
        pass

# Usage example:

# repr = ReprVisitor()
# printer = ASTPrinter(repr)
# tree = ast.parse(your_code_string)
# for node in tree.body:
#     printer.visit(node)
