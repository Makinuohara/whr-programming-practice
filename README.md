# WHR 语言课程设计

WHR 是一个为“程序设计实践”大作业设计的解释型通用脚本语言。本仓库包含语言规范、解释器、黑盒测试、性能对比、面向人和编程 Agent 的开发指南、一个不少于 200 行的 WHR 应用、开发记录以及验收 PPT。

当前状态：**WHR v1.0 已完成，统一验收 47/47 项通过。**

## 推荐入口

- [总体设计与阶段计划](docs/00_总体设计与阶段计划.md)
- [需求与交付物追踪矩阵](docs/00_需求与交付物追踪矩阵.md)
- [项目状态](PROJECT_STATUS.md)
- [Agent 协作规则](AGENTS.md)
- [WHR v1.0 语言规范](docs/language/01_WHR语言规范.md)
- [WHR v1.0 标准库](docs/language/02_标准库.md)
- [WHR v1.0 错误模型](docs/language/03_错误模型.md)
- [WHR 快速开始](docs/guides/01_快速开始.md)
- [WHR 开发指南](docs/guides/02_开发指南.md)
- [校园生存模拟器](apps/campus_survival/README.md)
- [最终演示材料](presentation/README.md)
- [验收讲稿](presentation/验收讲稿.md)
- [常见问答](presentation/常见问答.md)

## 技术路线

- 解释器实现：Python 3.11+，只依赖标准库
- WHR 源文件后缀：`.whr`
- 执行入口：`python -m whr <file.whr>`
- 解释模型：词法分析 → 递归下降语法分析 → AST → 树遍历解释执行
- 测试方式：WHR 黑盒用例 + Python 测试驱动器，一个命令运行全部测试
- 示例应用：命令行“校园生存模拟器”，WHR 源码不少于 200 个有效代码行

## 一键验收

```bash
python scripts/check_project.py
```

该命令检查全部必交文件，并运行解释器示例、64 项黑盒测试、31 项 Python 测试、应用行数与演示、正式性能 JSON 完整性检查。命令返回 0 才表示项目通过最终验收。
