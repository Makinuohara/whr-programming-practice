"""Token definitions shared by the WHR lexer and parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class TokenKind:
    EOF = "EOF"
    IDENTIFIER = "IDENTIFIER"
    INTEGER = "INTEGER"
    STRING = "STRING"


# Keep keyword lexemes in their original spelling.  The lexer gives keyword
# tokens an upper-case kind while the parser compares lexemes so diagnostics
# can quote exactly what appeared in the source.
KEYWORDS = {
    "let",
    "shape",
    "form",
    "craft",
    "give",
    "when",
    "otherwise",
    "repeat",
    "while",
    "break",
    "continue",
    "true",
    "false",
    "null",
    "and",
    "or",
    "not",
}


@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    literal: Any
    line: int
    column: int

    @property
    def type(self) -> str:
        """Alias useful to small tooling scripts."""

        return self.kind

    def __repr__(self) -> str:
        return (
            f"Token({self.kind!r}, {self.lexeme!r}, {self.literal!r}, "
            f"{self.line}:{self.column})"
        )


TokenType = TokenKind
