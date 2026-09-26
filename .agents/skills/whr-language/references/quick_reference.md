# WHR v1.0 quick reference

The authoritative contract is [the frozen specification](../../../../docs/language/01_WHR语言规范.md). This page is a compact lookup for an Agent; it intentionally omits the full EBNF.

## Statements

~~~whr
let count <- 0;
count <- count + 1;

shape Student {
    name;
    score;
}
let student <- form Student { name: "Alice", score: 95 };
student.score <- 96;

when student.score >= 60 {
    show("pass");
} otherwise {
    show("retry");
}

repeat while count < 3 {
    count <- count + 1;
}
~~~

Simple statements end with semicolons. Blocks create lexical scopes. A `let` inside a block can shadow an outer binding; assignment searches outward for the nearest existing binding.

## Expressions and values

Values are integer, string, boolean, null, array, shape, function, and shape_type. Arrays are zero-based and mutable. Structure declarations need at least one field; construction must provide each declared field exactly once.

Precedence from high to low is call/index/field, unary, `* / %`, `+ -`, comparison, equality, `and`, `or`, assignment. Assignment is right-associative. All other binary operators are left-associative.

`and` and `or` short-circuit, but every evaluated operand must have the required type. A condition is never coerced from an integer, string, array, or null. `+` accepts two integers or two strings; all other arithmetic operators accept integers.

## Functions and built-ins

~~~whr
craft sum(items) {
    let result <- 0;
    let i <- 0;
    repeat while i < len(items) {
        result <- result + items[i];
        i <- i + 1;
    }
    give result;
}
~~~

Calls require the exact number of user-function arguments. Reaching the end of a function or using `give;` returns null. Nested functions capture their declaration environment. Arrays and shape instances are passed by reference.

The deterministic standard library is:

- `show(values...)`: one space between values and one trailing newline;
- `read()` or `read(prompt)`: line input, EOF is null, prompt has no newline;
- `len(string_or_array)`;
- `push(array, value)` and `pop(array)`;
- `to_int(value)` with strict `-?[0-9]+` strings;
- `to_string(value)` and `type_of(value)`.

There is no file, network, time, random, module, or exception API.

## Text and errors

Direct strings passed to `show` are unquoted; strings nested in arrays and shapes use deterministic quoted text. Cycles render as `<cycle>`.

Use the CLI categories and exit codes as the debugging boundary:

~~~text
2 UsageError
65 LexError
66 ParseError
70 RuntimeError
74 IOError
~~~

Keep exact stderr and source location in black-box expectations. Do not replace an error assertion with a generic “nonzero” check.
