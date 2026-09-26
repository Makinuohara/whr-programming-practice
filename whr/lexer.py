"""Lexer for WHR v1.0.

The lexer is deliberately independent from the parser.  Every token records
its one-based line and column so both parser and runtime diagnostics can point
back to the source program.
"""

from __future__ import annotations

from typing import Any

from .errors import LexError
from .token import KEYWORDS, Token, TokenKind


_ONE_CHAR_TOKENS = {
    "(": "LEFT_PAREN",
    ")": "RIGHT_PAREN",
    "{": "LEFT_BRACE",
    "}": "RIGHT_BRACE",
    "[": "LEFT_BRACKET",
    "]": "RIGHT_BRACKET",
    ",": "COMMA",
    ";": "SEMICOLON",
    ".": "DOT",
    ":": "COLON",
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "<": "LESS",
    ">": "GREATER",
}


_TWO_CHAR_TOKENS = {
    "<-": "ASSIGN",
    "==": "EQUAL_EQUAL",
    "!=": "BANG_EQUAL",
    "<=": "LESS_EQUAL",
    ">=": "GREATER_EQUAL",
}


class Lexer:
    """Convert WHR source text into a list of tokens."""

    def __init__(self, source: str):
        self.source = source
        self._start = 0
        self._current = 0
        self._line = 1
        self._column = 1
        self._token_line = 1
        self._token_column = 1
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self._at_end():
            self._start = self._current
            self._token_line = self._line
            self._token_column = self._column
            self._scan_token()
        self.tokens.append(
            Token(TokenKind.EOF, "", None, self._line, self._column)
        )
        return self.tokens

    def scan_tokens(self) -> list[Token]:
        """Compatibility spelling used by some lexer clients."""

        return self.tokenize()

    def _at_end(self) -> bool:
        return self._current >= len(self.source)

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self.source[self._current]

    def _peek_next(self) -> str:
        if self._current + 1 >= len(self.source):
            return "\0"
        return self.source[self._current + 1]

    def _advance(self) -> str:
        char = self.source[self._current]
        self._current += 1
        self._column += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._at_end() or self.source[self._current] != expected:
            return False
        self._current += 1
        self._column += 1
        return True

    def _scan_token(self) -> None:
        char = self._advance()

        if char in " \t\f\v":
            return
        if char == "\n":
            self._line += 1
            self._column = 1
            return
        if char == "\r":
            if self._peek() == "\n":
                self._current += 1
            self._line += 1
            self._column = 1
            return
        if char == "#":
            while not self._at_end() and self._peek() not in "\r\n":
                self._advance()
            return
        if char == '"':
            self._string()
            return
        if self._is_ascii_digit(char):
            self._number()
            return
        if self._is_identifier_start(char):
            self._identifier()
            return

        if char == "!":
            if self._match("="):
                self._add_token("BANG_EQUAL")
            else:
                self._lex_error("unexpected character '!'")
            return
        if char == "=":
            if self._match("="):
                self._add_token("EQUAL_EQUAL")
            else:
                self._lex_error("unexpected character '='; use '==' for equality")
            return

        if char in "<>":
            pair = char + self._peek()
            if pair in _TWO_CHAR_TOKENS:
                self._advance()
                self._add_token(_TWO_CHAR_TOKENS[pair])
            else:
                self._add_token(_ONE_CHAR_TOKENS[char])
            return

        if char in _ONE_CHAR_TOKENS:
            self._add_token(_ONE_CHAR_TOKENS[char])
            return

        self._lex_error(f"unexpected character {char!r}")

    def _is_identifier_start(self, char: str) -> bool:
        return char == "_" or ("A" <= char <= "Z") or ("a" <= char <= "z")

    def _is_identifier_part(self, char: str) -> bool:
        return self._is_identifier_start(char) or self._is_ascii_digit(char)

    def _is_ascii_digit(self, char: str) -> bool:
        return "0" <= char <= "9"

    def _identifier(self) -> None:
        while self._is_identifier_part(self._peek()):
            self._advance()
        text = self.source[self._start : self._current]
        kind = text.upper() if text in KEYWORDS else TokenKind.IDENTIFIER
        self._add_token(kind)

    def _number(self) -> None:
        while self._is_ascii_digit(self._peek()):
            self._advance()
        text = self.source[self._start : self._current]
        self._add_token(TokenKind.INTEGER, int(text))

    def _string(self) -> None:
        value: list[str] = []
        escapes = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            '"': '"',
            "\\": "\\",
        }
        while not self._at_end():
            char = self._advance()
            if char == '"':
                self._add_token(TokenKind.STRING, "".join(value))
                return
            if char in "\r\n":
                self._lex_error("unterminated string")
            if char == "\\":
                if self._at_end():
                    self._lex_error("unterminated string")
                escaped = self._advance()
                if escaped not in escapes:
                    self._lex_error(f"unknown escape '\\{escaped}'")
                value.append(escapes[escaped])
            else:
                value.append(char)
        self._lex_error("unterminated string")

    def _add_token(self, kind: str, literal: Any = None) -> None:
        lexeme = self.source[self._start : self._current]
        self.tokens.append(
            Token(kind, lexeme, literal, self._token_line, self._token_column)
        )

    def _lex_error(self, message: str) -> None:
        raise LexError(message, self._token_line, self._token_column)


def tokenize(source: str) -> list[Token]:
    """Convenience wrapper used by the parser and tests."""

    return Lexer(source).tokenize()
