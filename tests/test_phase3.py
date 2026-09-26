from __future__ import annotations

import io
import pathlib
import subprocess
import sys
import unittest

from whr.errors import ParseError, RuntimeError
from whr.interpreter import run_source
from whr.parser import parse_source


ROOT = pathlib.Path(__file__).resolve().parents[1]


class Phase3Tests(unittest.TestCase):
    def run_program(self, source: str, stdin: str = "") -> str:
        stdout = io.StringIO()
        run_source(source, stdout=stdout, stdin=io.StringIO(stdin))
        return stdout.getvalue()

    def test_functions_default_return_recursion_and_closure(self) -> None:
        source = """
        craft add(a, b) { give a + b; }
        craft empty() {}
        craft factorial(n) {
            when n <= 1 { give 1; }
            give n * factorial(n - 1);
        }
        craft make_adder(base) {
            craft add_to(value) { give base + value; }
            give add_to;
        }
        let add_five <- make_adder(5);
        show(add(2, 3), empty(), factorial(5), add_five(7));
        """
        self.assertEqual(self.run_program(source), "5 null 120 12\n")

    def test_function_parameter_count_and_lexical_capture(self) -> None:
        source = """
        let outside <- 10;
        craft read_outside() { give outside; }
        {
            let outside <- 20;
            show(read_outside());
        }
        """
        self.assertEqual(self.run_program(source), "10\n")
        with self.assertRaisesRegex(RuntimeError, r"add expects 2 argument\(s\), got 1"):
            self.run_program("craft add(a, b) { give a + b; } add(1);")

    def test_shape_construction_field_order_read_write_and_identity(self) -> None:
        source = """
        shape Point { x; label; }
        let p <- form Point { label: "first", x: 1 };
        let alias <- p;
        let other <- form Point { x: 1, label: "first" };
        p.x <- 9;
        show(p, p.x, p == alias, p == other, type_of(p), type_of(Point));
        """
        self.assertEqual(
            self.run_program(source),
            'Point{x: 9, label: "first"} 9 true false shape shape_type\n',
        )

    def test_shape_field_errors_are_runtime_errors(self) -> None:
        with self.assertRaisesRegex(RuntimeError, r"missing field 'y'"):
            self.run_program("shape P { x; y; } let p <- form P { x: 1 };")
        with self.assertRaisesRegex(RuntimeError, r"unknown field 'z'"):
            self.run_program("shape P { x; } let p <- form P { x: 1, z: 2 };")
        with self.assertRaisesRegex(RuntimeError, r"shape 'P' has no field 'z'"):
            self.run_program("shape P { x; } let p <- form P { x: 1 }; show(p.z);")
        with self.assertRaises(ParseError):
            parse_source("shape Empty {}")

    def test_all_standard_library_functions(self) -> None:
        source = """
        let values <- [1, "two"];
        show(len(values), len("你好"), push(values, true), pop(values), values);
        show(to_int("-42"), to_string(7), type_of(7), type_of("x"),
             type_of(true), type_of(null), type_of(values), type_of(show));
        """
        self.assertEqual(
            self.run_program(source),
            '2 2 3 true [1, "two"]\n-42 7 integer string boolean null array function\n',
        )

    def test_read_prompt_and_eof(self) -> None:
        self.assertEqual(
            self.run_program('let name <- read("name: "); show(name);', "Alice\r\n"),
            "name: Alice\n",
        )
        self.assertEqual(self.run_program("show(read());", ""), "null\n")
        with self.assertRaisesRegex(RuntimeError, r"read expects string prompt"):
            self.run_program("read(1);")

    def test_conversion_and_collection_errors(self) -> None:
        with self.assertRaisesRegex(RuntimeError, r"cannot convert \+1 to integer"):
            self.run_program('to_int("+1");')
        with self.assertRaisesRegex(RuntimeError, r"pop expects a non-empty array"):
            self.run_program("pop([]);")
        with self.assertRaisesRegex(RuntimeError, r"len expects string or array"):
            self.run_program("len(1);")

    def test_array_and_shape_cycles_have_terminating_output(self) -> None:
        source = """
        let values <- [null];
        values[0] <- values;
        shape Node { value; next; }
        let node <- form Node { value: 1, next: null };
        node.next <- node;
        show(values, node, to_string(node));
        """
        self.assertEqual(
            self.run_program(source),
            "[<cycle>] Node{value: 1, next: <cycle>} "
            "Node{value: 1, next: <cycle>}\n",
        )

    def test_arrays_and_shapes_are_passed_by_reference(self) -> None:
        source = """
        shape Box { value; }
        craft mutate(items, box) {
            push(items, 3);
            box.value <- box.value + 1;
        }
        let items <- [1, 2];
        let box <- form Box { value: 4 };
        mutate(items, box);
        show(items, box.value);
        """
        self.assertEqual(self.run_program(source), "[1, 2, 3] 5\n")

    def test_language_tour_cli_output_is_deterministic(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "whr", "examples/language_tour.whr"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout,
            "student: WHR\n"
            "scores: [92, 88, 96, 100]\n"
            "average: 94\n"
            "level: excellent\n",
        )
        self.assertEqual(result.stderr, "")
        self.assertNotIn("Traceback", result.stderr)
