"""Command-line implementation for ``python -m whr``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from . import VERSION
from .errors import WHRError, WHRIOError, UsageError
from .interpreter import Interpreter
from .lexer import tokenize
from .parser import Parser


def _usage_error(message: str) -> int:
    print(f"UsageError: {message}", file=sys.stderr)
    return UsageError.exit_code


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise WHRIOError(f"file is not valid UTF-8: {error}") from error
    except OSError as error:
        raise WHRIOError(str(error)) from error


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    check_only = False
    if not args:
        return _usage_error("expected a source file")
    if args == ["--version"]:
        print(VERSION)
        return 0
    if args[0] == "--check":
        check_only = True
        args = args[1:]
    if len(args) != 1:
        return _usage_error("expected exactly one source file")
    if args[0].startswith("-"):
        return _usage_error(f"unknown option '{args[0]}'")

    filename = args[0]
    path = Path(filename)
    try:
        source = _read_source(path)
        program = Parser(tokenize(source)).parse()
        if not check_only:
            Interpreter().interpret(program)
        return 0
    except WHRError as error:
        if isinstance(error, WHRIOError):
            print(f"{filename}: IOError: {error.message}", file=sys.stderr)
        else:
            print(error.diagnostic(filename), file=sys.stderr)
        return error.exit_code
    except Exception:
        # The default CLI deliberately never exposes a Python traceback.
        print(
            f"{filename}:1:1: RuntimeError: internal interpreter error",
            file=sys.stderr,
        )
        return 70
