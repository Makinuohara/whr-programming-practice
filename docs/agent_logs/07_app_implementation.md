# 阶段 7 应用实现记录

日期：2026-09-26

执行者：独立应用开发 Agent

## 1. Skill 与项目约束

实现前实际阅读了：

- `.agents/skills/whr-language/SKILL.md`；
- `.agents/skills/whr-language/references/quick_reference.md`；
- `.agents/skills/whr-language/references/verification.md`；
- `docs/language/01_WHR语言规范.md`、`02_标准库.md`、`03_错误模型.md`；
- `PROJECT_STATUS.md`、`docs/stages/06_阶段报告.md`、`docs/agent_logs/06_skill_forward_test.md` 和开发指南。

因此程序只使用 WHR v1.0 已实现能力：`shape`/`form`、数组、`craft`/`give`、布尔条件、`when`/`otherwise`、`repeat while`、`read`/`show`、`len`/`push`、`to_string`。结构实例统一采用 `form Type { ... }`；菜单选择使用字符串比较，不对菜单输入调用 `to_int`；EOF 比较 `null` 并通过函数返回正常结束；没有随机数、时间、文件 I/O、模块或异常捕获。

## 2. 设计与实现

主文件是 `apps/campus_survival/main.whr`，计数脚本报告 **267 个有效 WHR 行**。`Player` 保存姓名、周次、六项状态、行动历史和成就；`ActionResult` 保存行动名和说明。五个行动函数分别修改状态并返回结果，`perform_action` 只接受字符串 `1` 至 `5`。

`normalize_player` 通过 `clamp` 限制能量、知识、压力、声望和健康在 0--100，金钱在 0--999。`apply_event` 按周次和状态确定性触发考试周、社团展示、奖学金、疾病或辅导事件。`update_achievements` 去重记录成就，`ending` 提供 Burnout、Campus leader、Academic survivor 和 Steady graduate 四类结局。

固定演示输入依次选择 study、rest、club、study、exercise、part-time，覆盖五种行动并完整完成六周。真实运行结局为：

```text
Ending: Campus leader ending
```

完整 stdout 保存在 `apps/campus_survival/demo_output.txt`，由实际命令输出后逐字保存；验收时用 `cmp` 比较。

## 3. 生成与修订记录

1. 先建立六周主流程、两个结构、五个行动、边界函数和事件链；只新增阶段 7 允许的目录和文件。
2. `--check` 通过后，用 `demo_input.txt` 真实运行，确认状态变化、事件顺序、历史和成就表示，再保存 `demo_output.txt`。
3. 新增标准库-only `scripts/count_whr_loc.py`，以非空且非纯 `#` 注释行作为有效行，支持 `--minimum`，低于门槛返回 1。
4. 新增 `tests/test_application.py`，使用真实 `python -m whr` 子进程精确比较演示 stdout/stderr/exit code，并覆盖计数器、核心语法、EOF 和非法菜单不推进周次。
5. 全量回归未发现需要返工的程序错误；最后一次验收使用下列实际结果。
6. 审查时将应用测试中的固定 `267` 数字改为匹配任意实际计数加 `minimum 200: PASS`，避免非功能性排版调整造成无谓失败；修改后重新运行应用测试和全量验收，结果仍通过。

## 4. 实际验证

```bash
python -m whr --check apps/campus_survival/main.whr
```

stdout/stderr 均为空，exit code `0`。

```bash
python -m whr apps/campus_survival/main.whr < apps/campus_survival/demo_input.txt
```

exit code `0`；stdout 为 2360 字节，与 `demo_output.txt` 的 `cmp` exit code `0`；stderr 为 0 字节。输出包含考试周、社团展示、奖学金和最终 `Campus leader ending`。

```bash
python scripts/count_whr_loc.py apps/campus_survival/main.whr --minimum 200
```

输出 `apps/campus_survival/main.whr: 267 effective WHR lines (minimum 200: PASS)`，exit code `0`。

额外用 `--minimum 300` 检查失败路径，输出 `FAIL`，脚本自身 exit code 为 `1`。

```bash
python -m unittest tests.test_application -v
```

6 个应用测试通过，exit code `0`。

```bash
python -m tests.run_all
```

64/64 黑盒用例通过，exit code `0`。

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

31 个测试通过，exit code `0`。

```bash
python -m compileall -q whr tests benchmarks
git diff --check
```

两条命令均无输出并返回 `0`。

## 5. 主审返工

主审发现原结局条件 `health <= 0 or stress >= 100` 在合法六周行动路径中不可达。实际运行原版本确认：六次兼职达到 `stress=72` 却得到 `Steady graduate`；六次学习得到 `Academic survivor`；六次休息得到 `Steady graduate`。

按主审建议做最小修订：只把 Burnout 的压力阈值从 `100` 调整为可解释的高压阈值 `70`，保留 `health <= 0` 条件，不改变任何行动数值或演示输入。修订后六次兼职真实得到 `Burnout ending`（`stress=72`、`health=84`），六次学习得到 `Academic survivor ending`，六次休息得到 `Steady graduate ending`；三次子进程运行均 exit code `0`、stderr 为空。

在 `tests/test_application.py` 增加三条真实子进程替代结局测试，并同步 README 说明阈值和可达路径。固定演示重新运行后 stdout 与既有 `demo_output.txt` 的 `cmp` 仍为 0，结局仍为 `Campus leader ending`，因此没有重写演示输出。

## 6. 范围与风险

- 本任务没有复制应用到 `tests/cases/`；应用测试直接启动入口文件，避免把整份应用当作黑盒样例重复维护。
- 非法菜单和 EOF 已由应用测试覆盖；演示输入中的姓名和六个菜单行是有效输入。若用户将非菜单文本作为菜单输入，程序仍按字符串菜单安全提示，不会触发转换错误。
- 状态、事件和结局完全确定性；不同输入会得到不同但可解释的结果，未声称穷举所有输入组合。
- 未修改解释器、冻结规范、根 README、`PROJECT_STATUS.md` 或阶段报告，未执行 Git 提交。
