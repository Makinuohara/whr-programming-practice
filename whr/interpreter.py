"""Stage 2 tree-walk interpreter for WHR."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Optional, TextIO

from . import ast_nodes as ast
from .builtins import BuiltinFunction, _is_integer, show, stringify, type_name
from .environment import Environment
from .errors import RuntimeError
from .parser import parse_source


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class GiveSignal(Exception):
    """Reserved for the function runtime completed in stage 3."""

    def __init__(self, value: Any):
        self.value = value


@dataclass(frozen=True)
class FunctionStub:
    """A parsed user function, kept as a value until the function stage."""

    declaration: ast.FunctionDeclaration


@dataclass(frozen=True)
class ShapeStub:
    """A parsed shape declaration, kept as a value until the shape stage."""

    declaration: ast.ShapeDeclaration


class Interpreter:
    """Execute the stage-2 subset of a parsed WHR program."""

    def __init__(self, stdout: Optional[TextIO] = None, stdin: Optional[TextIO] = None):
        self.stdout = stdout if stdout is not None else sys.stdout
        self.stdin = stdin if stdin is not None else sys.stdin
        self.environment = Environment()
        self._install_builtins()

    def _install_builtins(self) -> None:
        synthetic = type("BuiltinToken", (), {"line": 1, "column": 1})()
        self.environment.define("show", BuiltinFunction("show"), synthetic)

    def interpret(self, program: ast.Program) -> None:
        for declaration in program.declarations:
            self._execute(declaration)

    def _execute(self, node: ast.Node) -> None:
        if isinstance(node, ast.VariableDeclaration):
            value = self._evaluate(node.initializer)
            self.environment.define(node.name, value, node.token)
            return
        if isinstance(node, ast.ExpressionStatement):
            self._evaluate(node.expression)
            return
        if isinstance(node, ast.Block):
            self._execute_block(node, Environment(self.environment))
            return
        if isinstance(node, ast.WhenStatement):
            for branch in node.branches:
                condition = self._evaluate(branch.condition)
                self._require_boolean(condition, branch.condition.token)
                if condition:
                    self._execute_block(branch.body, Environment(self.environment))
                    return
            if node.otherwise is not None:
                self._execute_block(node.otherwise, Environment(self.environment))
            return
        if isinstance(node, ast.RepeatStatement):
            while True:
                condition = self._evaluate(node.condition)
                self._require_boolean(condition, node.condition.token)
                if not condition:
                    return
                try:
                    self._execute_block(node.body, Environment(self.environment))
                except ContinueSignal:
                    continue
                except BreakSignal:
                    return
        if isinstance(node, ast.BreakStatement):
            raise BreakSignal()
        if isinstance(node, ast.ContinueStatement):
            raise ContinueSignal()
        if isinstance(node, ast.GiveStatement):
            # Parser rejects this at top level, but keeping the guard makes
            # the AST API safe for callers that construct nodes themselves.
            raise RuntimeError("'give' cannot execute before function support", node.token.line, node.token.column)
        if isinstance(node, ast.FunctionDeclaration):
            self.environment.define(node.name, FunctionStub(node), node.token)
            return
        if isinstance(node, ast.ShapeDeclaration):
            self.environment.define(node.name, ShapeStub(node), node.token)
            return
        raise RuntimeError("unsupported statement", node.token.line, node.token.column)

    def _execute_block(self, block: ast.Block, environment: Environment) -> None:
        previous = self.environment
        try:
            self.environment = environment
            for declaration in block.declarations:
                self._execute(declaration)
        finally:
            self.environment = previous

    def _evaluate(self, node: ast.Node) -> Any:
        if isinstance(node, ast.Literal):
            return node.value
        if isinstance(node, ast.Variable):
            return self.environment.get(node.name, node.token)
        if isinstance(node, ast.ArrayLiteral):
            return [self._evaluate(element) for element in node.elements]
        if isinstance(node, ast.ShapeInitializer):
            raise RuntimeError(
                "shape initialization is not available in interpreter stage 2",
                node.token.line,
                node.token.column,
            )
        if isinstance(node, ast.Unary):
            operand = self._evaluate(node.operand)
            if node.operator.lexeme == "-":
                if not _is_integer(operand):
                    raise RuntimeError(
                        f"- expects integer, got {type_name(operand)}",
                        node.operator.line,
                        node.operator.column,
                    )
                return -operand
            self._require_boolean(operand, node.operator, operator="not")
            return not operand
        if isinstance(node, ast.Binary):
            return self._evaluate_binary(node)
        if isinstance(node, ast.Assignment):
            return self._evaluate_assignment(node)
        if isinstance(node, ast.Index):
            return self._read_index(node)
        if isinstance(node, ast.FieldAccess):
            raise RuntimeError(
                "shape field access is not available in interpreter stage 2",
                node.token.line,
                node.token.column,
            )
        if isinstance(node, ast.Call):
            return self._evaluate_call(node)
        raise RuntimeError("unsupported expression", node.token.line, node.token.column)

    def _evaluate_binary(self, node: ast.Binary) -> Any:
        operator = node.operator.lexeme
        left = self._evaluate(node.left)
        if operator == "and":
            self._require_boolean(left, node.operator, operator="and")
            if not left:
                return False
            right = self._evaluate(node.right)
            self._require_boolean(right, node.operator, operator="and")
            return right
        if operator == "or":
            self._require_boolean(left, node.operator, operator="or")
            if left:
                return True
            right = self._evaluate(node.right)
            self._require_boolean(right, node.operator, operator="or")
            return right

        right = self._evaluate(node.right)
        if operator in {"+", "-", "*", "/", "%"}:
            return self._arithmetic(operator, left, right, node.operator)
        if operator in {"<", "<=", ">", ">="}:
            return self._comparison(operator, left, right, node.operator)
        if operator in {"==", "!="}:
            result = self._equal(left, right)
            return not result if operator == "!=" else result
        raise RuntimeError(
            f"unknown operator '{operator}'", node.operator.line, node.operator.column
        )

    def _arithmetic(self, operator: str, left: Any, right: Any, token: object) -> Any:
        if operator == "+" and isinstance(left, str) and isinstance(right, str):
            return left + right
        if not _is_integer(left) or not _is_integer(right):
            raise RuntimeError(
                f"{operator} expects two integers"
                + (" or two strings" if operator == "+" else "")
                + f", got {type_name(left)} and {type_name(right)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )
        if operator == "+":
            return left + right
        if operator == "-":
            return left - right
        if operator == "*":
            return left * right
        if operator == "/":
            if right == 0:
                raise RuntimeError("division by zero", token.line, token.column)
            return left // right
        if operator == "%":
            if right == 0:
                raise RuntimeError("modulo by zero", token.line, token.column)
            return left % right
        raise AssertionError("unreachable")

    def _comparison(self, operator: str, left: Any, right: Any, token: object) -> bool:
        same_integer = _is_integer(left) and _is_integer(right)
        same_string = isinstance(left, str) and isinstance(right, str)
        if not (same_integer or same_string):
            raise RuntimeError(
                f"{operator} expects two integers or two strings, "
                f"got {type_name(left)} and {type_name(right)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        if operator == ">":
            return left > right
        return left >= right

    def _equal(self, left: Any, right: Any) -> bool:
        if type_name(left) != type_name(right):
            return False
        if isinstance(left, (list, FunctionStub, BuiltinFunction, ShapeStub)):
            return left is right
        return left == right

    def _evaluate_assignment(self, node: ast.Assignment) -> Any:
        if isinstance(node.target, ast.Variable):
            value = self._evaluate(node.value)
            return self.environment.assign(node.target.name, value, node.token)
        if isinstance(node.target, ast.Index):
            container = self._evaluate(node.target.object)
            index = self._evaluate(node.target.index)
            value = self._evaluate(node.value)
            self._check_index(container, index, node.target.token)
            container[index] = value
            return value
        raise RuntimeError(
            "shape field assignment is not available in interpreter stage 2",
            node.token.line,
            node.token.column,
        )

    def _read_index(self, node: ast.Index) -> Any:
        container = self._evaluate(node.object)
        index = self._evaluate(node.index)
        self._check_index(container, index, node.token)
        return container[index]

    def _check_index(self, container: Any, index: Any, token: object) -> None:
        if not isinstance(container, list):
            raise RuntimeError(
                f"index expects array, got {type_name(container)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )
        if not _is_integer(index):
            raise RuntimeError(
                f"array index expects integer, got {type_name(index)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )
        if index < 0 or index >= len(container):
            raise RuntimeError(
                f"array index {index} out of range for length {len(container)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )

    def _evaluate_call(self, node: ast.Call) -> Any:
        callee = self._evaluate(node.callee)
        arguments = [self._evaluate(argument) for argument in node.arguments]
        if isinstance(callee, BuiltinFunction) and callee.name == "show":
            show(arguments, self.stdout)
            return None
        raise RuntimeError(
            f"value of type {type_name(callee)} is not callable",
            node.token.line,
            node.token.column,
        )

    def _require_boolean(
        self, value: Any, token: object, *, operator: str = "condition"
    ) -> None:
        if not isinstance(value, bool):
            raise RuntimeError(
                f"{operator} expects boolean, got {type_name(value)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )


def run_source(
    source: str,
    *,
    stdout: Optional[TextIO] = None,
    stdin: Optional[TextIO] = None,
) -> None:
    """Parse and execute one source string (useful for tests and tooling)."""

    program = parse_source(source)
    Interpreter(stdout=stdout, stdin=stdin).interpret(program)
