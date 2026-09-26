from __future__ import annotations

import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

from whr.ast_nodes import Binary, FunctionDeclaration, Program, RepeatStatement, VariableDeclaration
from whr.errors import LexError, ParseError, RuntimeError
from whr.interpreter import run_source
from whr.lexer import tokenize
from whr.token import TokenKind
from whr.parser import parse_source


ROOT = pathlib.Path(__file__).resolve().parents[1]


class Phase2Tests(unittest.TestCase):
    def run_program(self, source: str) -> str:
        output = io.StringIO()
        run_source(source, stdout=output)
        return output.getvalue()

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "whr", *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_lexer_positions_comments_and_escape_errors(self) -> None:
        tokens = tokenize('let x <- 12;\n  show("ok");')
        self.assertEqual((tokens[0].kind, tokens[0].line, tokens[0].column), ("LET", 1, 1))
        self.assertEqual((tokens[1].lexeme, tokens[1].line, tokens[1].column), ("x", 1, 5))
        self.assertEqual((tokens[2].lexeme, tokens[2].line, tokens[2].column), ("<-", 1, 7))
        self.assertEqual((tokens[5].lexeme, tokens[5].line, tokens[5].column), ("show", 2, 3))
        self.assertEqual(tokens[-1].kind, TokenKind.EOF)
        self.assertEqual(
            [token.lexeme for token in tokenize("# c\r\nshow(1); # d\r\n")],
            ["show", "(", "1", ")", ";", ""],
        )
        with self.assertRaises(LexError):
            tokenize('show("bad\\q");')
        with self.assertRaises(LexError):
            tokenize("let x <- １２;")

    def test_parser_covers_tour_precedence_and_context_checks(self) -> None:
        source = """
        shape Student { name; }
        craft f(x) { give x; }
        let student <- form Student { name: "WHR" };
        """
        program = parse_source(source)
        self.assertIsInstance(program, Program)
        self.assertTrue(any(isinstance(node, FunctionDeclaration) for node in program.declarations))

        declaration = parse_source("let answer <- 2 + 3 * 4;").declarations[0]
        self.assertIsInstance(declaration, VariableDeclaration)
        self.assertIsInstance(declaration.initializer, Binary)
        self.assertEqual(declaration.initializer.operator.lexeme, "+")
        self.assertEqual(declaration.initializer.right.operator.lexeme, "*")
        with self.assertRaises(ParseError):
            parse_source("break;")
        with self.assertRaises(ParseError):
            parse_source("shape Empty {}")

    def test_named_conditions_are_not_confused_with_form_initializers(self) -> None:
        source = 'let ok <- true; when ok { show("yes"); }'
        self.assertEqual(self.run_program(source), "yes\n")
        parsed = parse_source("let point <- form Point { x: 1 };")
        self.assertEqual(parsed.declarations[0].initializer.name, "Point")

    def test_values_assignment_scope_and_arrays(self) -> None:
        source = """
        let x <- 1;
        {
            let x <- 2;
            show(x);
        }
        x <- x + 4;
        let values <- [1, "two", true];
        values[0] <- 9;
        show(x, values[0], values);
        """
        self.assertEqual(self.run_program(source), '2\n5 9 [9, "two", true]\n')

    def test_expression_and_control_flow(self) -> None:
        self.assertEqual(self.run_program('show(2 + 3 * 4, -7 / 2, -7 % 2);'), "14 -4 1\n")
        source = """
        let i <- 0;
        repeat while i < 5 {
            i <- i + 1;
            when i == 2 { continue; }
            when i == 4 { break; }
            show(i);
        }
        """
        self.assertEqual(self.run_program(source), "1\n3\n")

    def test_strict_boolean_short_circuit_and_show(self) -> None:
        self.assertEqual(self.run_program("show(false and missing, true or missing);"), "false true\n")
        self.assertEqual(self.run_program("show();"), "\n")
        with self.assertRaises(RuntimeError):
            self.run_program("show(1 and true);")
        with self.assertRaises(RuntimeError):
            self.run_program("when 1 { show(1); }")

    def test_cli_version_check_hello_and_errors(self) -> None:
        version = self.run_cli("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("WHR 1.0", version.stdout)

        check = self.run_cli("--check", "examples/language_tour.whr")
        self.assertEqual((check.returncode, check.stdout, check.stderr), (0, "", ""))
        hello = self.run_cli("examples/hello.whr")
        self.assertEqual((hello.returncode, hello.stdout, hello.stderr), (0, "Hello from WHR\n", ""))

        with tempfile.NamedTemporaryFile("w", suffix=".whr", encoding="utf-8", dir=ROOT, delete=False) as handle:
            handle.write("show(missing);\n")
            filename = pathlib.Path(handle.name)
        try:
            result = self.run_cli(str(filename))
        finally:
            filename.unlink()
        self.assertEqual(result.returncode, 70)
        self.assertIn("RuntimeError", result.stderr)
        self.assertIn("undefined name 'missing'", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

        usage = self.run_cli()
        self.assertEqual(usage.returncode, 2)
        self.assertIn("UsageError", usage.stderr)
