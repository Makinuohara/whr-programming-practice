"""Built-in function values and deterministic WHR text formatting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TextIO

from .values import ShapeInstance, ShapeType, UserFunction


@dataclass(frozen=True)
class BuiltinFunction:
    """A named host function exposed through the WHR global environment."""

    name: str


def type_name(value: Any) -> str:
    """Return the language-level type name for a runtime value."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if _is_integer(value):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, (BuiltinFunction, UserFunction)):
        return "function"
    if isinstance(value, ShapeType):
        return "shape_type"
    if isinstance(value, ShapeInstance):
        return "shape"
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
    """Render a value according to WHR's deterministic text representation."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if _is_integer(value):
        return str(value)
    if isinstance(value, str):
        return value if direct_string else f'"{_format_string(value)}"'
    if seen is None:
        seen = set()
    if isinstance(value, list):
        identity = id(value)
        if identity in seen:
            return "<cycle>"
        seen.add(identity)
        result = "[" + ", ".join(
            stringify(item, seen=seen) for item in value
        ) + "]"
        seen.remove(identity)
        return result
    if isinstance(value, ShapeInstance):
        identity = id(value)
        if identity in seen:
            return "<cycle>"
        seen.add(identity)
        result = value.shape_type.name + "{" + ", ".join(
            f"{field}: {stringify(value.fields[field], seen=seen)}"
            for field in value.shape_type.fields
        ) + "}"
        seen.remove(identity)
        return result
    if isinstance(value, UserFunction):
        return f"<craft {value.name}>"
    if isinstance(value, BuiltinFunction):
        return f"<builtin {value.name}>"
    if isinstance(value, ShapeType):
        return f"<shape {value.name}>"
    return str(value)


def show(values: list[Any], stdout: TextIO) -> None:
    """Write values separated by one space and terminated by one newline."""

    stdout.write(" ".join(stringify(value, direct_string=True) for value in values) + "\n")
    stdout.flush()
