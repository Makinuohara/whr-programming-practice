"""Count effective WHR source lines.

An effective line is non-empty and does not consist only of a ``#`` comment.
The checker intentionally does not parse WHR; syntax validation belongs to the
interpreter's ``--check`` mode.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def count_effective_lines(path: Path) -> int:
    """Return non-empty, non-comment-only source line count for *path*."""

    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="WHR source file to count")
    parser.add_argument(
        "--minimum",
        type=int,
        default=None,
        help="required minimum effective line count; exit 1 when unmet",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.minimum is not None and args.minimum < 0:
        print("count_whr_loc: --minimum must be non-negative", file=sys.stderr)
        return 2

    try:
        count = count_effective_lines(args.path)
    except (OSError, UnicodeError) as error:
        print(f"count_whr_loc: cannot read {args.path}: {error}", file=sys.stderr)
        return 2

    if args.minimum is None:
        print(f"{args.path}: {count} effective WHR lines")
        return 0

    result = "PASS" if count >= args.minimum else "FAIL"
    print(f"{args.path}: {count} effective WHR lines (minimum {args.minimum}: {result})")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
