"""Stage-2 built-in functions and deterministic value formatting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TextIO


@dataclass(frozen=True)
class BuiltinFunction:
    name: str


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, BuiltinFunction):
        return "function"
    # The two marker classes are imported lazily to keep this module usable by
    # the interpreter without a circular import.
    from .interpreter import FunctionStub, ShapeStub

    if isinstance(value, FunctionStub):
        return "function"
    if isinstance(value, ShapeStub):
        return "shape_type"
    return "value"


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _format_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def stringify(
    value: Any,
    *,
    direct_string: bool = False,
    seen: Optional[set[int]] = None,
) -> str:
    """Return deterministic WHR text for values used by ``show``."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if _is_integer(value):
        return str(value)
    if isinstance(value, str):
        return value if direct_string else f'"{_format_string(value)}"'
    if isinstance(value, list):
        if seen is None:
            seen = set()
        identity = id(value)
        if identity in seen:
            return "<cycle>"
        seen.add(identity)
        result = "[" + ", ".join(
            stringify(item, seen=seen) for item in value
        ) + "]"
        seen.remove(identity)
        return result
    if isinstance(value, BuiltinFunction):
        return f"<builtin {value.name}>"
    from .interpreter import FunctionStub, ShapeStub

    if isinstance(value, FunctionStub):
        return f"<craft {value.declaration.name}>"
    if isinstance(value, ShapeStub):
        return f"<shape {value.declaration.name}>"
    return str(value)


def show(values: list[Any], stdout: TextIO) -> None:
    stdout.write(" ".join(stringify(value, direct_string=True) for value in values) + "\n")
    stdout.flush()
