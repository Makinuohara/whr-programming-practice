# Campus Survival

`main.whr` 是一个确定性的 WHR v1.0 校园生存模拟器。玩家输入姓名后进行六周生活，每周在五种行动中选择一种：学习、休息、社团、兼职、运动。能量、知识、金钱、压力、声望和健康会随行动变化，所有长期状态都由 `clamp` 限制在合理区间。

## 玩法

输入格式是七行：第一行是姓名，之后六行分别是每周选择。菜单选择必须输入字符串 `1` 到 `5`：

| 选择 | 行动 | 主要效果 |
|---|---|---|
| `1` | study | 增加知识，但消耗能量并增加压力 |
| `2` | rest | 恢复能量和健康，降低压力 |
| `3` | club | 增加知识和声望，消耗少量金钱 |
| `4` | part-time | 增加金钱，但消耗能量、健康和少量知识 |
| `5` | exercise | 恢复健康并降低压力 |

非法选择会提示重新选择，不推进周次；EOF 会输出结束提示并以成功状态结束。演示输入选择了五种行动中的全部五种，并完整完成六周。

## 设计

- `Player` 结构保存姓名、周次、六项状态、行动历史和成就数组。
- `ActionResult` 结构把行动名称和说明从行动函数传回主流程。
- `clamp` 与 `normalize_player` 负责状态边界；`contains`/`award` 负责成就去重。
- 五个行动由独立函数实现，`perform_action` 只按字符串菜单分派，因此非法菜单不会调用 `to_int`。
- `apply_event` 根据周次和当前状态触发考试周、社团展示、奖学金、疾病或辅导事件；不使用随机数、时间或外部 I/O。
- 结局由健康、压力、知识和声望决定：健康降到 0 或压力达到 70 会进入 Burnout；知识与声望足够时是 Campus leader；知识达到学术生存线时是 Academic survivor；其余情况是 Steady graduate。六次兼职、六次学习、六次休息分别可真实触发前三种替代结局中的 Burnout、Academic survivor、Steady graduate。

## WHR 功能映射

程序实际使用了 `shape`/`form`、数组与 `push`/`len`、函数与 `give`、`when`/`otherwise`、`repeat while`、`read`/`show`、显式 `to_string`、字符串比较和 EOF 的 `null` 判断。源文件中的有效 WHR 行由计数脚本检查，当前为 267 行。

## 运行

在仓库根目录执行：

```bash
python -m whr --check apps/campus_survival/main.whr
python -m whr apps/campus_survival/main.whr < apps/campus_survival/demo_input.txt
python scripts/count_whr_loc.py apps/campus_survival/main.whr --minimum 200
```

演示输出必须与 `demo_output.txt` 完全一致；它以实际运行结果为准。应用测试由真实子进程执行：

```bash
python -m unittest tests.test_application -v
```
