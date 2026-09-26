# WHR 语言规范 v1.0

状态：**冻结（含勘误 1）**

规范版本：1.0

冻结日期：2026-09-26

## 1. 语言目标与特色

WHR 取自作者姓名拼音首字母，是一种动态类型、解释执行、面向脚本任务的通用语言。它有意采用容易阅读但不照搬某一种现存语言的语法组合：

- `let name <- value;` 使用左箭头表示数据流入变量；
- `shape` 声明结构类型，`form` 使用具名字段构造实例；
- `craft` 和 `give` 分别表示函数与返回；
- `when`、`otherwise` 和 `repeat while` 表示控制流；
- 花括号表示代码块，分号结束简单语句；
- 条件必须是布尔值，不进行隐式真假或数字/字符串转换。

WHR v1.0 只包含课程要求和综合应用需要的功能，不包含类、模块、异常捕获、并发、浮点数、文件 I/O 或宏。

## 2. 源文件与词法规则

### 2.1 文件

- 源文件扩展名为 `.whr`，编码必须是 UTF-8。
- 换行可以是 LF 或 CRLF；解释器统一按逻辑行计数。
- 空格、制表符和换行用于分隔词法单元，字符串内部除外。
- 标识符和关键字区分大小写。

### 2.2 注释

`#` 开始单行注释，直到换行或文件结束。字符串中的 `#` 是普通字符。WHR v1.0 没有块注释。

```whr
# 整行注释
let message <- "# 不是注释"; # 行尾注释
```

### 2.3 标识符

标识符匹配：

```text
[A-Za-z_][A-Za-z0-9_]*
```

中文可以出现在字符串和注释中，但 v1.0 的标识符只使用 ASCII 字母、数字和下划线，以保证源码和诊断在各平台一致。

### 2.4 关键字

以下单词不能作为标识符：

```text
let shape form craft give when otherwise repeat while
break continue true false null and or not
```

`show`、`read`、`len` 等内建函数名不是关键字，按普通标识符解析。

### 2.5 整数字面量

- 整数字面量由一个或多个十进制数字组成，例如 `0`、`42`、`2026`。
- 不允许前缀、分隔符或小数点。
- 负数不是单个字面量，而是一元负号作用于整数，例如 `-42`。
- 运行时整数为任意精度有符号整数，最终受宿主机器内存限制。

### 2.6 字符串字面量

字符串使用双引号。允许的转义只有：

| 写法 | 含义 |
|---|---|
| `\n` | 换行 |
| `\r` | 回车 |
| `\t` | 制表符 |
| `\"` | 双引号 |
| `\\` | 反斜杠 |

未知转义、未闭合字符串和字符串中的原始换行都是词法错误。字符串运行时保存 Unicode 文本。

### 2.7 运算符与分隔符

```text
<-  ==  !=  <=  >=
+   -   *   /   %
<   >
(   )   {   }   [   ]
,   ;   .   :
```

多字符运算符使用最长匹配原则，例如 `<-` 优先于 `<`。

## 3. 完整语法

以下 EBNF 是 WHR v1.0 的规范语法。`IDENTIFIER`、`INTEGER` 和 `STRING` 由词法规则产生，`EOF` 表示文件结束。

```ebnf
program          = declaration* EOF ;

declaration      = shapeDeclaration
                 | functionDeclaration
                 | variableDeclaration
                 | statement ;

shapeDeclaration = "shape" IDENTIFIER "{" fieldDeclaration+ "}" ;
fieldDeclaration = IDENTIFIER ";" ;

functionDeclaration
                 = "craft" IDENTIFIER "(" parameters? ")" block ;
parameters       = IDENTIFIER ( "," IDENTIFIER )* ;

variableDeclaration
                 = "let" IDENTIFIER "<-" expression ";" ;

statement        = whenStatement
                 | repeatStatement
                 | giveStatement
                 | breakStatement
                 | continueStatement
                 | block
                 | expressionStatement ;

whenStatement    = "when" expression block
                   ( "otherwise" "when" expression block )*
                   ( "otherwise" block )? ;

repeatStatement  = "repeat" "while" expression block ;
giveStatement    = "give" expression? ";" ;
breakStatement   = "break" ";" ;
continueStatement= "continue" ";" ;
block            = "{" declaration* "}" ;
expressionStatement
                 = expression ";" ;

expression       = assignment ;
assignment       = logicOr ( "<-" assignment )? ;
logicOr          = logicAnd ( "or" logicAnd )* ;
logicAnd         = equality ( "and" equality )* ;
equality         = comparison ( ( "==" | "!=" ) comparison )* ;
comparison       = term ( ( "<" | "<=" | ">" | ">=" ) term )* ;
term             = factor ( ( "+" | "-" ) factor )* ;
factor           = unary ( ( "*" | "/" | "%" ) unary )* ;
unary            = ( "-" | "not" ) unary | call ;

call             = primary ( "(" arguments? ")"
                            | "[" expression "]"
                            | "." IDENTIFIER )* ;
arguments        = expression ( "," expression )* ;

primary          = INTEGER
                 | STRING
                 | "true"
                 | "false"
                 | "null"
                 | arrayLiteral
                 | shapeInitializer
                 | IDENTIFIER
                 | "(" expression ")" ;

arrayLiteral     = "[" arguments? "]" ;
shapeInitializer = "form" IDENTIFIER "{" fieldInitializer
                   ( "," fieldInitializer )* ","? "}" ;
fieldInitializer = IDENTIFIER ":" expression ;
```

补充语法约束：

1. 参数名、结构字段名和结构初始化字段名在各自列表内不得重复。
2. 结构声明和 `shapeInitializer` 都至少包含一个字段，因此 v1.0 不允许零字段结构。
3. 赋值左侧只能是变量、数组索引或结构字段访问，否则是语法错误。
4. `give` 只能出现在函数体内；`break` 和 `continue` 只能出现在循环体内。违反时为语法错误。
5. 单次函数声明和调用最多允许 255 个参数；超过限制是语法错误。

## 4. 值与类型

WHR 是动态类型语言：变量本身不声明类型，值具有运行时类型。

| 类型 | 示例 | 可变性 | 说明 |
|---|---|---|---|
| `integer` | `0`、`-7` | 不可变 | 任意精度有符号整数 |
| `string` | `"WHR"` | 不可变 | Unicode 字符串 |
| `boolean` | `true`、`false` | 不可变 | 条件判断专用 |
| `null` | `null` | 不可变 | 表示没有值 |
| `array` | `[1, "two"]` | 可变 | 有序、异构、零下标容器 |
| `shape` | `Student { name: "Li", score: 90 }` | 可变字段 | 具名结构实例 |
| `function` | `average` | 不可变 | 用户函数或内建函数 |
| `shape_type` | `Student` | 不可变 | 已声明的结构类型 |

WHR 不做隐式转换。例如 `"age=" + 18` 是运行时类型错误，必须写为 `"age=" + to_string(18)`。

## 5. 变量与作用域

### 5.1 声明

```whr
let count <- 0;
```

初始化表达式先在当前环境求值，成功后才创建变量。同一作用域内不允许重复声明同名变量、函数或结构类型。内层作用域可以遮蔽外层同名绑定。

### 5.2 词法作用域

- 程序最外层是全局作用域。
- 每个 `{ ... }` 块创建一个子作用域。
- 函数调用创建参数和局部变量作用域，其父作用域是函数声明时所在的环境。
- 因此用户函数采用词法作用域，并能捕获外层绑定。

```whr
let x <- 1;
{
    let x <- 2;
    show(x); # 2
}
show(x);     # 1
```

### 5.3 赋值

```whr
count <- count + 1;
items[0] <- 99;
student.score <- 100;
```

变量赋值从当前环境向外寻找最近的同名绑定。不存在的变量产生运行时错误。赋值表达式的结果是赋入的值，因此允许 `a <- b <- 0;`。

## 6. 表达式语义

### 6.1 求值顺序

表达式、函数实参、数组元素和结构字段初始化表达式都严格从左到右求值。除了 `and` 和 `or` 的短路规则外，不跳过求值。

### 6.2 优先级

从高到低：

1. 分组、调用、索引、字段访问；
2. 一元 `-`、`not`；
3. `*`、`/`、`%`；
4. `+`、`-`；
5. `<`、`<=`、`>`、`>=`；
6. `==`、`!=`；
7. `and`；
8. `or`；
9. 赋值 `<-`。

除赋值为右结合外，其余二元运算符均为左结合。

### 6.3 算术

| 运算 | 合法操作数 | 结果 |
|---|---|---|
| `-x` | integer | 相反数 |
| `a + b` | 两个 integer 或两个 string | 整数加法或字符串连接 |
| `a - b`、`a * b` | 两个 integer | 整数结果 |
| `a / b` | 两个 integer | 向负无穷取整的整数商 |
| `a % b` | 两个 integer | 与上述商对应的余数 |

除零和模零产生运行时错误。例：`7 / 2` 为 `3`，`-7 / 2` 为 `-4`，`-7 % 2` 为 `1`。

### 6.4 比较与相等

- `<`、`<=`、`>`、`>=` 只允许两个整数或两个字符串；字符串按 Unicode 码点词典序比较。
- `integer`、`string`、`boolean` 和 `null` 按类型和值相等。
- 不同类型的值不相等，不发生转换，例如 `1 == "1"` 为 `false`。
- 数组、结构实例、函数和结构类型按对象身份相等；两个内容相同但分别创建的数组并不相等。

### 6.5 布尔逻辑

`not`、`and`、`or` 的操作数必须为布尔值：

- `not value` 返回布尔取反；
- `left and right` 在 `left` 为 `false` 时不求值 `right`；
- `left or right` 在 `left` 为 `true` 时不求值 `right`。

WHR 没有“真值”隐式规则；`when 1 { ... }` 是运行时类型错误。

## 7. 数组

```whr
let values <- [10, "WHR", true];
show(values[0]);
values[1] <- "language";
push(values, 42);
```

- 数组可以为空、可以混合类型并可以嵌套。
- 下标从 0 开始，必须是整数。
- 负下标不表示从末尾计数；任何小于 0 或大于等于长度的下标都产生运行时错误。
- 索引只适用于数组；v1.0 不支持字符串索引。
- `push`、`pop` 和索引赋值会原地修改数组，别名能观察到修改。

## 8. 结构类型与实例

```whr
shape Student {
    name;
    score;
}

let s <- form Student { name: "Alice", score: 95 };
s.score <- 96;
show(s.name);
```

- 结构声明在当前作用域创建一个 `shape_type` 绑定。
- 构造时必须且只能为声明中的每个字段提供一次值；顺序可以不同。
- 缺少字段、重复字段或未知字段均为运行时错误。
- 字段读取或赋值只适用于结构实例，字段必须存在。
- v1.0 不支持给实例动态添加字段，也不支持结构方法或继承。

## 9. 控制流

### 9.1 分支

```whr
when score >= 90 {
    show("A");
} otherwise when score >= 60 {
    show("pass");
} otherwise {
    show("fail");
}
```

条件必须为布尔值。解释器从上到下测试条件，只执行第一个为 `true` 的分支；没有匹配且没有 `otherwise` 时不执行任何分支。

### 9.2 循环

```whr
let i <- 0;
repeat while i < 3 {
    i <- i + 1;
    when i == 2 { continue; }
    show(i);
}
```

每轮先计算条件；条件必须为布尔值。`break` 立即离开最近一层循环；`continue` 立即开始最近一层循环的下一次条件判断。

## 10. 函数

```whr
craft factorial(n) {
    when n <= 1 { give 1; }
    give n * factorial(n - 1);
}

show(factorial(5)); # 120
```

- 函数声明在当前作用域绑定函数名，并捕获声明环境。
- 调用时实参数量必须和形参数量完全一致，内建函数的可变参数规则除外。
- 参数按值传递；对于数组和结构实例，传递的值是对象引用，因此函数内修改对象对调用者可见。
- `give expression;` 返回表达式结果；`give;` 返回 `null`。
- 函数执行到末尾没有 `give` 时也返回 `null`。
- 支持递归和嵌套函数。没有尾调用优化，递归深度受宿主 Python 限制。

## 11. 输入输出与内建函数

WHR v1.0 的完整内建函数见 [标准库](02_标准库.md)。核心 I/O 行为：

```whr
let name <- read("name: ");
show("hello", name);
```

- `read()` 从标准输入读取一行，移除末尾的 `\n` 和可选 `\r`；遇到 EOF 返回 `null`。
- `read(prompt)` 先把提示原样写入标准输出且不换行，再读取一行。
- `show()` 输出一个空行。
- `show(a, b, ...)` 用一个空格分隔参数，在末尾输出一个换行。
- 输出使用确定性的 WHR 文本表示，便于黑盒测试。

## 12. 文本表示

直接传给 `show` 的字符串不带引号；嵌套在数组或结构中的字符串带双引号并使用规范转义。

| 值 | 输出文本 |
|---|---|
| `true` / `false` / `null` | `true` / `false` / `null` |
| 整数 | 十进制形式 |
| 直接字符串 `"hi"` | `hi` |
| 数组 `[1, "x"]` | `[1, "x"]` |
| 结构实例 | `Student{name: "Alice", score: 95}` |
| 用户函数 | `<craft name>` |
| 内建函数 | `<builtin name>` |
| 结构类型 | `<shape Student>` |

结构字段按照声明顺序显示。直接或间接包含自身的数组/结构使用 `<cycle>` 代替递归部分，保证输出能够结束。

## 13. 规范勘误记录

### 勘误 1：结构构造增加 `form`（2026-09-26）

最初草案使用 `Student { name: "Alice" }`。阶段 2 解析器主审发现，该写法与无括号控制流 `when ok { ... }` 在 `IDENTIFIER` 后产生不可接受的语法歧义。正式写法改为 `form Student { name: "Alice" }`。这使结构构造和控制流块可由一个 Token 明确区分，也增强了 WHR 的自身语法特色。

## 14. 错误与进程约定

完整约定见 [错误模型](03_错误模型.md)。原则如下：

- 第一个未处理错误终止当前程序，不继续执行后续语句。
- 错误写入标准错误，正常输出写入标准输出。
- 诊断格式为 `文件:行:列: 类别: 说明`。
- 成功退出码为 0；命令用法、词法、语法、运行时和文件 I/O 错误使用不同非零退出码。
- WHR v1.0 没有用户级异常捕获，因此运行时错误总会传播到 CLI。

## 15. 命令行接口

```text
python -m whr [--check] FILE
python -m whr --version
```

- 默认模式解析并执行一个文件。
- `--check` 只做词法和语法检查，不执行程序；成功时不输出内容。
- `--version` 输出语言和解释器版本。
- v1.0 不提供 REPL、从 `-c` 执行源码或多文件模块系统。

## 16. 确定性与实现自由

在相同源码和相同标准输入下，WHR v1.0 程序应产生相同的标准输出、标准错误类别和退出码。宿主实现可以自由组织内部类和模块，但不能改变本规范可观察到的行为。
