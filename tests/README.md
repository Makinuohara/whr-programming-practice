# WHR 黑盒测试

黑盒测试不导入解释器内部类，而是为每个 `.whr` 用例启动一次真实命令：

```bash
python -m tests.run_all
```

测试驱动器从 `tests/cases/` 递归发现 `.whr` 文件。每个源文件可以有同名配套文件：

| 文件 | 含义 | 缺失时的默认值 |
|---|---|---|
| `case.stdout` | 精确标准输出 | 空字符串 |
| `case.stderr` | 精确标准错误 | 空字符串 |
| `case.json` | JSON 元数据 | `stdin=""`、`exit_code=0`、默认超时 |

JSON 可以包含：

```json
{
  "stdin": "Alice\n",
  "exit_code": 70,
  "tags": ["runtime", "error"],
  "timeout": 5
}
```

测试会精确比较 stdout、stderr 和退出码；超时直接失败。失败时显示期望值与实际值的 unified diff。报告包含发现总数、通过/失败数量和按目录分类的统计；没有用例时返回非零退出码。

常用辅助命令：

```bash
python -m tests.run_all --list
python -m tests.run_all --filter functions
python -m unittest discover -s tests -p 'test_*.py'
```

分类目录分别对应基本类型、数组、结构、输入输出、控制流、函数、错误和回归场景。错误用例的 `.stderr` 和 `.json` 是完整固定期望，不使用“只判断失败”的宽松断言。

由于缺失源文件无法作为 `.whr` 用例保存，runner 还额外执行一个文件不存在的 CLI 检查，固定验证 `IOError` 和退出码 74。
