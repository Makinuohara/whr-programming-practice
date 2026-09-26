"""Lexical environments used by the tree-walk interpreter."""

from __future__ import annotations

from typing import Any, Optional

from .errors import RuntimeError


class Environment:
    """A single lexical scope linked to its enclosing environment."""

    def __init__(self, enclosing: Optional["Environment"] = None):
        self.values: dict[str, Any] = {}
        self.enclosing = enclosing

    def define(self, name: str, value: Any, token: object) -> None:
        if name in self.values:
            raise RuntimeError(
                f"name '{name}' is already declared in this scope",
                getattr(token, "line", None),
                getattr(token, "column", None),
            )
        self.values[name] = value

    def get(self, name: str, token: object) -> Any:
        if name in self.values:
            return self.values[name]
        if self.enclosing is not None:
            return self.enclosing.get(name, token)
        raise RuntimeError(
            f"undefined name '{name}'",
            getattr(token, "line", None),
            getattr(token, "column", None),
        )
    def assign(self, name: str, value: Any, token: object) -> Any:
        if name in self.values:
            self.values[name] = value
            return value
        if self.enclosing is not None:
            return self.enclosing.assign(name, value, token)
        raise RuntimeError(
            f"undefined name '{name}'",
            getattr(token, "line", None),
            getattr(token, "column", None),
        )
