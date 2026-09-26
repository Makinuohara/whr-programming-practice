# WHR 黑盒测试覆盖矩阵

`python -m tests.run_all` 是唯一的全量黑盒入口。下表把冻结规范的可观察行为映射到具体 `.whr` 用例；错误用例同时固定诊断文本和退出码。

| 规范能力 | 代表用例 |
|---|---|
| 整数、字符串、布尔、null | `types/literals.whr`、`types/strings_escapes.whr` |
| 算术、比较、相等、优先级 | `types/arithmetic.whr`、`types/precedence.whr`、`types/comparisons.whr` |
| 严格布尔和短路 | `types/booleans.whr`、`errors/strict_boolean.whr` |
| 变量、赋值、右结合 | `types/variables.whr`、`regression/assignment_chain.whr` |
| 空数组、嵌套数组、索引 | `arrays/empty_nested.whr`、`arrays/index_read_write.whr` |
| 数组别名、push/pop、长度 | `arrays/alias_and_builtins.whr` |
| 数组越界和下标类型 | `errors/array_bounds.whr`、`errors/array_index_type.whr` |
| 数组循环引用 | `arrays/cycle.whr` |
| shape/form、字段顺序 | `structs/construct_order.whr` |
| 字段读写和引用身份 | `structs/field_mutation.whr`、`structs/identity.whr` |
| 缺少/未知/重复字段 | `errors/shape_missing.whr`、`errors/shape_unknown.whr`、`errors/shape_duplicate.whr` |
| shape 字段错误 | `errors/field_access.whr` |
| show 格式 | `io/show_format.whr` |
| read 提示、普通输入、CRLF、空行、EOF | `io/read_prompt.whr`、`io/read_crlf.whr`、`io/read_blank.whr`、`io/read_eof.whr` |
| when/otherwise when/otherwise | `control_flow/when_chain.whr` |
| 标识符条件歧义回归 | `control_flow/identifier_condition.whr` |
| 0 次循环和多次循环 | `control_flow/zero_loop.whr`、`control_flow/count_loop.whr` |
| break/continue、嵌套循环 | `control_flow/break_continue.whr`、`control_flow/nested_loops.whr` |
| 普通函数和参数 | `functions/basic.whr` |
| 默认返回和显式 null | `functions/default_return.whr` |
| give、递归、嵌套函数 | `functions/recursion.whr`、`functions/nested.whr` |
| 词法闭包和闭包状态 | `functions/closure.whr`、`functions/closure_state.whr` |
| 数组/结构引用参数 | `functions/reference_args.whr` |
| 参数数量错误 | `errors/function_arity.whr` |
| LexError | `errors/lex_bad_character.whr`、`errors/lex_escape.whr` |
| ParseError | `errors/parse_missing_semicolon.whr`、`errors/parse_assignment.whr` |
| RuntimeError | `errors/undefined_name.whr`、`errors/division_zero.whr`、`errors/type_mismatch.whr` |
| IOError / CLI 隔离 | `tests.run_all` 的额外 CLI 检查与 `errors/` 源文件错误用例 |
| 完整综合行为 | `regression/language_tour.whr` |

除表中代表用例外，目录中还保留边界和回归样例；每个文件都是真实 CLI 子进程执行的独立黑盒样本。
