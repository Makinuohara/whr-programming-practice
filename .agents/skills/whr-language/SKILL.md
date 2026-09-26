---
name: whr-language
description: Use when writing, debugging, reviewing, or testing WHR .whr programs in this repository.
---

# WHR language skill

Use this skill for WHR source files and WHR-facing tests. It is intentionally project-local: do not assume that WHR has features from Python, JavaScript, or another language.

## Before editing

- Read the frozen [language specification](../../../docs/language/01_WHR语言规范.md), [standard library](../../../docs/language/02_标准库.md), and [error model](../../../docs/language/03_错误模型.md).
- Use `form Type { ... }` for structure construction. The old `Type { ... }` spelling is not valid WHR v1.0.
- Conditions must be boolean. Do not rely on truthiness.
- Do not insert implicit conversions; use `to_int` or `to_string` explicitly.
- Stay inside the small deterministic standard library. WHR v1.0 has no file I/O, modules, exceptions, random numbers, time, floats, or third-party packages.

## Required workflow

1. Turn the request into fixed inputs, outputs, state, and boundary cases.
2. Write or update the `.whr` program and keep output deterministic.
3. Run `python -m whr --check FILE` before executing it.
4. Run the program with the specified input and inspect stdout, stderr, and exit code.
5. Run the relevant black-box case, then the full `python -m tests.run_all` suite when the change is complete.
6. Report actual commands and results; do not hide failures or claim an unrun check passed.

Read [quick_reference.md](references/quick_reference.md) for syntax and semantic reminders, and [verification.md](references/verification.md) for the project's validation commands and failure triage.
