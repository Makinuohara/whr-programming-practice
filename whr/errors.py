"""Error types and process-level error codes for WHR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


EXIT_SUCCESS = 0
EXIT_USAGE = 2
EXIT_LEX = 65
EXIT_PARSE = 66
EXIT_RUNTIME = 70
EXIT_IO = 74


@dataclass
class WHRError(Exception):
    """A user-facing WHR error with an optional source location."""

    message: str
    line: Optional[int] = None
    column: Optional[int] = None

    category = "WHRError"
    exit_code = EXIT_RUNTIME

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    def diagnostic(self, filename: str) -> str:
        if self.line is None or self.column is None:
            return f"{self.category}: {self.message}"
        return f"{filename}:{self.line}:{self.column}: {self.category}: {self.message}"


class UsageError(WHRError):
    category = "UsageError"
    exit_code = EXIT_USAGE


class LexError(WHRError):
    category = "LexError"
    exit_code = EXIT_LEX


class ParseError(WHRError):
    category = "ParseError"
    exit_code = EXIT_PARSE


class RuntimeError(WHRError):  # noqa: A001 - language-level name is intentional
    category = "RuntimeError"
    exit_code = EXIT_RUNTIME


class WHRIOError(WHRError):
    category = "IOError"
    exit_code = EXIT_IO


def error_at(error_type: type[WHRError], token: object, message: str) -> WHRError:
    """Construct an error at a token-like object without coupling modules."""

    return error_type(
        message,
        getattr(token, "line", None),
        getattr(token, "column", None),
    )
