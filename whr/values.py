"""Runtime value objects used by the complete WHR interpreter.

The interpreter keeps the syntax tree separate from runtime values.  In
particular, a user function stores both its declaration and the environment in
which it was declared, while a shape instance stores its shape type and its
field values.  ``eq=False`` is intentional: arrays, functions, shape types and
shape instances use object identity for WHR equality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

from . import ast_nodes as ast

if TYPE_CHECKING:
    from .environment import Environment


@dataclass(eq=False)
class UserFunction:
    declaration: ast.FunctionDeclaration
    closure: "Environment"

    @property
    def name(self) -> str:
        return self.declaration.name

    @property
    def parameters(self) -> list[str]:
        return self.declaration.parameters


@dataclass(eq=False)
class ShapeType:
    name: str
    fields: tuple[str, ...]
    declaration: Optional[ast.ShapeDeclaration] = None


@dataclass(eq=False)
class ShapeInstance:
    shape_type: ShapeType
    fields: dict[str, Any]
