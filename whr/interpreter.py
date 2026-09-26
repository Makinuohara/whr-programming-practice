"""Tree-walk interpreter for the complete WHR v1.0 runtime."""

from __future__ import annotations

import re
import sys
from typing import Any, Optional, TextIO

from . import ast_nodes as ast
from .builtins import BuiltinFunction, _is_integer, show, stringify, type_name
from .environment import Environment
from .errors import RuntimeError
from .parser import parse_source
from .values import ShapeInstance, ShapeType, UserFunction


class BreakSignal(Exception):
    """Internal control-flow signal for the nearest loop."""


class ContinueSignal(Exception):
    """Internal control-flow signal for the nearest loop."""


class GiveSignal(Exception):
    """Internal control-flow signal carrying a function return value."""

    def __init__(self, value: Any):
        super().__init__()
        self.value = value


# Compatibility aliases for code written against the stage-2 placeholders.
FunctionStub = UserFunction
ShapeStub = ShapeType


class Interpreter:
    """Execute a parsed WHR program using lexical environments."""

    def __init__(self, stdout: Optional[TextIO] = None, stdin: Optional[TextIO] = None):
        self.stdout = stdout if stdout is not None else sys.stdout
        self.stdin = stdin if stdin is not None else sys.stdin
        self.environment = Environment()
        self._install_builtins()

    def _install_builtins(self) -> None:
        synthetic = type("BuiltinToken", (), {"line": 1, "column": 1})()
        for name in (
            "show",
            "read",
            "len",
            "push",
            "pop",
            "to_int",
            "to_string",
            "type_of",
        ):
            self.environment.define(name, BuiltinFunction(name), synthetic)

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
            value = None if node.value is None else self._evaluate(node.value)
            raise GiveSignal(value)
        if isinstance(node, ast.FunctionDeclaration):
            function = UserFunction(node, self.environment)
            self.environment.define(node.name, function, node.token)
            return
        if isinstance(node, ast.ShapeDeclaration):
            shape_type = ShapeType(node.name, tuple(node.fields), node)
            self.environment.define(node.name, shape_type, node.token)
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
            return self._evaluate_shape_initializer(node)
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
            return self._read_field(node)
        if isinstance(node, ast.Call):
            return self._evaluate_call(node)
        raise RuntimeError("unsupported expression", node.token.line, node.token.column)

    def _evaluate_shape_initializer(self, node: ast.ShapeInitializer) -> ShapeInstance:
        shape_value = self.environment.get(node.name, node.token)
        if not isinstance(shape_value, ShapeType):
            raise RuntimeError(
                f"value of type {type_name(shape_value)} is not a shape type",
                node.token.line,
                node.token.column,
            )

        evaluated: dict[str, Any] = {}
        for field in node.fields:
            # Parser has already rejected duplicate field names.  Keeping the
            # assignment explicit preserves source-order evaluation.
            evaluated[field.name] = self._evaluate(field.value)

        declared = set(shape_value.fields)
        unknown = [name for name in evaluated if name not in declared]
        missing = [name for name in shape_value.fields if name not in evaluated]
        if unknown or missing:
            details: list[str] = []
            if missing:
                if len(missing) == 1:
                    details.append(f"missing field '{missing[0]}'")
                else:
                    details.append("missing fields " + ", ".join(f"'{name}'" for name in missing))
            if unknown:
                if len(unknown) == 1:
                    details.append(f"unknown field '{unknown[0]}'")
                else:
                    details.append("unknown fields " + ", ".join(f"'{name}'" for name in unknown))
            raise RuntimeError(
                f"invalid fields for shape '{shape_value.name}': " + "; ".join(details),
                node.token.line,
                node.token.column,
            )

        values = {name: evaluated[name] for name in shape_value.fields}
        return ShapeInstance(shape_value, values)

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
        if isinstance(
            left,
            (list, BuiltinFunction, UserFunction, ShapeType, ShapeInstance),
        ):
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
        if isinstance(node.target, ast.FieldAccess):
            instance = self._evaluate(node.target.object)
            value = self._evaluate(node.value)
            self._write_field(instance, node.target.name, value, node.target.token)
            return value
        raise RuntimeError(
            "invalid assignment target", node.token.line, node.token.column
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

    def _read_field(self, node: ast.FieldAccess) -> Any:
        instance = self._evaluate(node.object)
        self._require_shape_instance(instance, node.token)
        if node.name not in instance.fields:
            self._missing_field(instance, node.name, node.token)
        return instance.fields[node.name]

    def _write_field(
        self, instance: Any, name: str, value: Any, token: object
    ) -> None:
        self._require_shape_instance(instance, token)
        if name not in instance.fields:
            self._missing_field(instance, name, token)
        instance.fields[name] = value

    def _require_shape_instance(self, value: Any, token: object) -> None:
        if not isinstance(value, ShapeInstance):
            raise RuntimeError(
                f"field access expects shape, got {type_name(value)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )

    def _missing_field(self, instance: ShapeInstance, name: str, token: object) -> None:
        raise RuntimeError(
            f"shape '{instance.shape_type.name}' has no field '{name}'",
            getattr(token, "line", None),
            getattr(token, "column", None),
        )

    def _evaluate_call(self, node: ast.Call) -> Any:
        callee = self._evaluate(node.callee)
        arguments = [self._evaluate(argument) for argument in node.arguments]
        return self._call_value(callee, arguments, node.token)

    def _call_value(self, callee: Any, arguments: list[Any], token: object) -> Any:
        if isinstance(callee, BuiltinFunction):
            return self._call_builtin(callee.name, arguments, token)
        if isinstance(callee, UserFunction):
            return self._call_user_function(callee, arguments, token)
        raise RuntimeError(
            f"value of type {type_name(callee)} is not callable",
            getattr(token, "line", None),
            getattr(token, "column", None),
        )

    def _call_user_function(
        self, function: UserFunction, arguments: list[Any], token: object
    ) -> Any:
        self._require_argument_count(function.name, len(function.parameters), len(arguments), token)
        call_environment = Environment(function.closure)
        for name, value in zip(function.parameters, arguments):
            call_environment.define(name, value, token)

        previous = self.environment
        try:
            self.environment = call_environment
            try:
                for declaration in function.declaration.body.declarations:
                    self._execute(declaration)
            except GiveSignal as signal:
                return signal.value
            return None
        finally:
            self.environment = previous

    def _call_builtin(self, name: str, arguments: list[Any], token: object) -> Any:
        if name == "show":
            show(arguments, self.stdout)
            return None
        if name == "read":
            if len(arguments) not in (0, 1):
                raise RuntimeError(
                    f"read expects 0 or 1 argument(s), got {len(arguments)}",
                    getattr(token, "line", None),
                    getattr(token, "column", None),
                )
            return self._builtin_read(arguments, token)
        if name == "len":
            self._require_argument_count(name, 1, len(arguments), token)
            value = arguments[0]
            if isinstance(value, (str, list)):
                return len(value)
            raise RuntimeError(
                f"len expects string or array, got {type_name(value)}",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )
        if name == "push":
            self._require_argument_count(name, 2, len(arguments), token)
            array = arguments[0]
            if not isinstance(array, list):
                raise RuntimeError(
                    f"push expects array, got {type_name(array)}",
                    getattr(token, "line", None),
                    getattr(token, "column", None),
                )
            array.append(arguments[1])
            return len(array)
        if name == "pop":
            self._require_argument_count(name, 1, len(arguments), token)
            array = arguments[0]
            if not isinstance(array, list):
                raise RuntimeError(
                    f"pop expects array, got {type_name(array)}",
                    getattr(token, "line", None),
                    getattr(token, "column", None),
                )
            if not array:
                raise RuntimeError(
                    "pop expects a non-empty array",
                    getattr(token, "line", None),
                    getattr(token, "column", None),
                )
            return array.pop()
        if name == "to_int":
            self._require_argument_count(name, 1, len(arguments), token)
            return self._builtin_to_int(arguments[0], token)
        if name == "to_string":
            self._require_argument_count(name, 1, len(arguments), token)
            value = arguments[0]
            return value if isinstance(value, str) else stringify(value)
        if name == "type_of":
            self._require_argument_count(name, 1, len(arguments), token)
            return type_name(arguments[0])
        raise RuntimeError(
            f"unknown builtin '{name}'",
            getattr(token, "line", None),
            getattr(token, "column", None),
        )

    def _builtin_read(self, arguments: list[Any], token: object) -> Optional[str]:
        if arguments:
            prompt = arguments[0]
            if not isinstance(prompt, str):
                raise RuntimeError(
                    f"read expects string prompt, got {type_name(prompt)}",
                    getattr(token, "line", None),
                    getattr(token, "column", None),
                )
            self.stdout.write(prompt)
            self.stdout.flush()
        line = self.stdin.readline()
        if line == "":
            return None
        if line.endswith("\n"):
            line = line[:-1]
            if line.endswith("\r"):
                line = line[:-1]
        elif line.endswith("\r"):
            line = line[:-1]
        return line

    def _builtin_to_int(self, value: Any, token: object) -> int:
        if _is_integer(value):
            return value
        if isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value):
            return int(value)
        raise RuntimeError(
            f"cannot convert {stringify(value, direct_string=True)} to integer",
            getattr(token, "line", None),
            getattr(token, "column", None),
        )

    def _require_argument_count(
        self, name: str, expected: int, actual: int, token: object
    ) -> None:
        if expected != actual:
            raise RuntimeError(
                f"{name} expects {expected} argument(s), got {actual}",
                getattr(token, "line", None),
                getattr(token, "column", None),
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
