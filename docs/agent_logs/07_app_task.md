# 阶段 7 应用任务记录

日期：2026-09-26

执行角色：独立应用开发 Agent（共享 WHR 仓库）

## 任务

使用项目 Skill 开发 `apps/campus_survival/main.whr` 校园生存模拟器。程序读取玩家姓名，运行至少六周；每周显示状态并提供学习、休息、社团、兼职、运动五种行动；记录状态、行动历史、成就和结局。

## 交付物

- `apps/campus_survival/main.whr`：有效 WHR 代码不少于 200 行；
- `apps/campus_survival/README.md`：玩法、设计、功能映射和运行说明；
- `apps/campus_survival/demo_input.txt` 与 `demo_output.txt`：固定演示输入和真实运行输出；
- `scripts/count_whr_loc.py`：标准库-only 的有效行计数器，支持 `--minimum`；
- `tests/test_application.py`：真实子进程、精确演示输出、EOF/非法菜单、有效行数和核心语法检查；
- `docs/agent_logs/07_app_implementation.md`：设计、修订、验证和实际结果记录。

## 硬约束

- 先读取 `.agents/skills/whr-language/SKILL.md`、路由速查/验证文档、冻结语言规范、标准库、错误模型和当前阶段文档；
- 结构构造使用 `form Type { ... }`，条件只使用布尔值，字符串菜单比较不调用 `to_int`；
- 不使用随机数、时间、文件 I/O、网络、模块或异常捕获；事件必须由周次和状态确定；
- EOF 正常结束，非法菜单不推进周次；状态通过 `clamp` 保持在合理范围；
- 不修改解释器、冻结规范、根 README、`PROJECT_STATUS.md` 或阶段报告；不提交 Git。

## 验收命令

```bash
python -m whr --check apps/campus_survival/main.whr
python -m whr apps/campus_survival/main.whr < apps/campus_survival/demo_input.txt
python scripts/count_whr_loc.py apps/campus_survival/main.whr --minimum 200
python -m unittest tests.test_application -v
python -m tests.run_all
python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q whr tests benchmarks
git diff --check
```

完成报告必须给出实际有效行数、演示结局、stdout/stderr/exit code、测试结果和未验证风险；没有运行的命令不得声称通过。
