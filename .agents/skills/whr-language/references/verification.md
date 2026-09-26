# WHR verification workflow

## Single-file checks

From the repository root:

~~~bash
python -m whr --version
python -m whr --check path/to/program.whr
python -m whr path/to/program.whr
~~~

For input-driven programs, make the input explicit:

~~~bash
printf 'Alice\n' | python -m whr path/to/program.whr
~~~

Record stdout, stderr, and the process exit code. A successful --check does not execute the program and cannot catch runtime type, input, or boundary errors.

## Black-box cases

A case consists of a .whr source and optional same-stem .stdout, .stderr, and .json files under tests/cases/. JSON can specify stdin, exit_code, tags, and timeout.

Run one category while iterating:

~~~bash
python -m tests.run_all --filter functions
python -m tests.run_all --filter errors
~~~

Run the complete suite before handoff:

~~~bash
python -m tests.run_all
python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q whr tests benchmarks
git diff --check
~~~

## Triage rules

1. LexError: inspect the character, string delimiter, escape, encoding, and comment boundary.
2. ParseError: inspect semicolons, braces, form, and whether the statement is legal in the current function or loop.
3. RuntimeError: display type_of(value) and reduce the program to the smallest failing expression.
4. IOError/UsageError: verify the file path, UTF-8 encoding, and CLI argument count.
5. If a change alters an exact error or output, preserve the old failing case until the specification and expected behavior have been reviewed.

The final report should name the files changed, the commands actually run, the observed output/exit codes, and any remaining unsupported requirement.
