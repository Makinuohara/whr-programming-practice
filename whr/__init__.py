"""WHR language interpreter package.

The public entry points intentionally stay small.  The command line interface
is implemented in :mod:`whr.__main__`, while tests and future tooling can use
``parse_source`` and ``run_source`` directly.
"""

from .interpreter import Interpreter, run_source
from .parser import Parser, parse_source
from .token import Token, TokenKind

LANGUAGE_VERSION = "1.0"
INTERPRETER_VERSION = "0.1.0"
VERSION = f"WHR {LANGUAGE_VERSION} (interpreter {INTERPRETER_VERSION})"

__all__ = [
    "INTERPRETER_VERSION",
    "LANGUAGE_VERSION",
    "Parser",
    "Interpreter",
    "VERSION",
    "Token",
    "TokenKind",
    "parse_source",
    "run_source",
]
