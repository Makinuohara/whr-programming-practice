# WHR 性能实验

本目录比较两个语义等价的端到端脚本：

- `prime_count.whr` / `prime_count.py`：用试除法统计 `2..3000` 的素数个数；
- `container_update.whr` / `container_update.py`：构造 4000 元素数组，执行 6 轮索引更新并计算校验和。

两个程序使用相同的循环、条件、算术和数据访问结构，运行时输出固定校验值。Python 版本没有调用专用的素数库、向量化库或一次性聚合算法。

## 复现实验

先做短时 quick 实验，结果放入被 Git 忽略的临时目录：

```bash
python benchmarks/run_benchmarks.py \
  --repetitions 1 \
  --warmups 0 \
  --output benchmarks/results/tmp/quick.json \
  --report benchmarks/results/tmp/quick.md
```

正式实验使用默认的 7 次正式轮和 2 次预热：

```bash
python benchmarks/run_benchmarks.py
```

也可以显式指定交付文件：

```bash
python benchmarks/run_benchmarks.py \
  --repetitions 7 \
  --warmups 2 \
  --output benchmarks/results/benchmarks.json \
  --report benchmarks/results/benchmarks.md
```

驱动器先分别启动 WHR 与 Python 校验返回码、标准错误和标准输出；只有校验一致才进入预热和正式计时。正式轮次奇数轮先运行 WHR，偶数轮先运行 Python。每次运行都保存实现、阶段、轮次、纳秒耗时、stdout、stderr、退出码、超时标志和校验状态。

## 如何解释结果

计时通过独立子进程和 `perf_counter_ns` 完成，代表端到端墙钟时间，包含进程启动、文件读取、WHR 词法分析、解析和解释执行。因此 WHR/Python 倍率主要反映当前解释器实现的综合开销，不能外推成语言普遍性能结论，也不预设 WHR 必须快于 Python。

原始 JSON 保留完整轮次、环境快照、Git commit、参数和失败信息；Markdown 报告由同一份 JSON 自动生成。任何超时、非零退出、stderr 输出或校验不一致都会使命令返回非零，并且失败记录不会被计入成功统计。
