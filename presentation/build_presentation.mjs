import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = process.env.WORKSPACE_DIR;
const skillDir = process.env.SKILL_DIR;
const runtimePython = process.env.RUNTIME_PYTHON;
const finalPptx = process.env.FINAL_PPTX;
if (!workspaceDir || !skillDir || !runtimePython || !finalPptx) {
  throw new Error("Set WORKSPACE_DIR, SKILL_DIR, RUNTIME_PYTHON and FINAL_PPTX");
}

const { applyPresentationChartFont, finalizePresentation } = await import(
  pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href,
);

const W = 1280;
const H = 720;
const FONT = "PingFang SC";
const MONO = "Menlo";
const C = {
  navy: "#0B172A",
  navy2: "#12243D",
  ink: "#172033",
  white: "#F7FAFC",
  muted: "#A9B7C8",
  teal: "#2DD4BF",
  tealDark: "#0F766E",
  orange: "#FB923C",
  blue: "#60A5FA",
  green: "#34D399",
  red: "#F87171",
  line: "#2B3D56",
};

const deck = Presentation.create({ slideSize: { width: W, height: H } });

function box(slide, x, y, w, h, fill, radius = 16, line = "none") {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: line === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: line, width: 1 },
    borderRadius: radius,
  });
}

function text(slide, value, x, y, w, h, size = 24, color = C.white, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = {
    typeface: opts.mono ? MONO : FONT,
    fontSize: size,
    bold: opts.bold ?? false,
    color,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    autoFit: "none",
  };
  return shape;
}

function rule(slide, x, y, w, color = C.line, height = 2) {
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: w, height },
    fill: color,
    line: { fill: "none", width: 0 },
  });
}

function base(title, index, accent = C.teal) {
  const slide = deck.slides.add();
  slide.background.fill = C.navy;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 12, height: H },
    fill: accent,
    line: { fill: "none", width: 0 },
  });
  text(slide, title, 68, 42, 1060, 58, 34, C.white, { bold: true });
  text(slide, String(index).padStart(2, "0"), 1160, 48, 60, 34, 16, C.muted, { align: "right", mono: true });
  rule(slide, 68, 112, 1152, C.line, 2);
  return slide;
}

function label(slide, value, x, y, w, color = C.teal) {
  const p = box(slide, x, y, w, 34, color, 17);
  text(slide, value, x, y + 4, w, 26, 15, C.navy, { bold: true, align: "center" });
  return p;
}

function metric(slide, value, caption, x, y, w, color = C.teal) {
  box(slide, x, y, w, 142, C.navy2, 18, C.line);
  text(slide, value, x + 18, y + 20, w - 36, 54, 38, color, { bold: true, align: "center" });
  text(slide, caption, x + 14, y + 82, w - 28, 38, 17, C.muted, { align: "center" });
}

function note(slide, value) {
  slide.speakerNotes.textFrame.setText(value);
}

// 1. Cover
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  s.shapes.add({ geometry: "rect", position: { left: 0, top: 0, width: 24, height: H }, fill: C.teal, line: { fill: "none", width: 0 } });
  text(s, "WHR", 88, 118, 420, 120, 78, C.teal, { bold: true, mono: true });
  text(s, "语言解释器与综合应用", 92, 246, 900, 82, 45, C.white, { bold: true });
  text(s, "从语言设计，到可运行、可测试、可复现、可讲解", 94, 350, 920, 46, 23, C.muted);
  rule(s, 94, 430, 820, C.orange, 4);
  text(s, "程序设计实践大作业  ·  WHR v1.0  ·  2026", 94, 470, 860, 38, 19, C.white);
  label(s, "解释器", 94, 566, 120);
  label(s, "64项黑盒测试", 232, 566, 170, C.blue);
  label(s, "267行应用", 420, 566, 146, C.orange);
  label(s, "Agent Skill", 584, 566, 150, C.green);
  note(s, "开场：这是一个完整的解释型脚本语言课程项目。核心不只是做出解释器，还要用黑盒测试、性能实验、开发指南和大型应用证明它能被可靠使用。");
}

// 2. Requirement-to-evidence map
{
  const s = base("作业要求，全部落到可检查证据", 2);
  const rows = [
    ["解释器", "词法→语法→AST→执行", "python -m whr"],
    ["自动测试", "64 个进程级黑盒用例", "python -m tests.run_all"],
    ["性能比较", "2 负载 × 2 实现 × 7 轮", "JSON 原始结果 + 报告"],
    ["人类与 AI 指南", "4 份指南 + 项目 Skill", "独立 Agent 前向验证"],
    ["200+ 行应用", "校园生存模拟器", "267 有效行 + 4 条结局"],
  ];
  const table = s.tables.add({ rows: 6, columns: 3, left: 78, top: 150, width: 1120, height: 430, values: [["评分项", "实现证据", "现场检查"], ...rows] });
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 3 }).assign({ fill: C.tealDark, textStyle: { typeface: FONT, fontSize: 20, bold: true, color: C.white }, anchor: "middle" });
  table.cells.block({ row: 1, column: 0, rowCount: 5, columnCount: 3 }).assign({ fill: C.navy2, textStyle: { typeface: FONT, fontSize: 18, color: C.white }, anchor: "middle" });
  text(s, "关键原则：每一项交付物都有命令、数据或 Git 历史可以复核。", 82, 612, 1100, 40, 21, C.orange, { bold: true, align: "center" });
  note(s, "按评分项讲：解释器20分、测试20分、性能10分、文档20分、Agent应用30分。每一项都对应仓库里的文件和可现场运行的命令。");
}

// 3. Language design
{
  const s = base("WHR 的语言设计：简单、明确、又有自己的辨识度", 3, C.orange);
  box(s, 70, 146, 590, 470, C.navy2, 18, C.line);
  label(s, "一段代码看懂核心语法", 92, 164, 220, C.orange);
  const code = [
    "form Student { name, score }",
    "craft grade(student) {",
    "  when student.score >= 60 {",
    "    give \"pass\"",
    "  } otherwise { give \"retry\" }",
    "}",
    "let roster <- []",
    "push(roster, Student { \"Ada\", 92 })",
    "say grade(roster[0])",
  ].join("\n");
  text(s, code, 96, 220, 530, 340, 19, C.white, { mono: true });
  const features = [
    ["<-", "赋值方向清晰"],
    ["form", "声明结构类型"],
    ["craft / give", "定义函数 / 返回值"],
    ["when / otherwise", "分支控制"],
    ["repeat while", "循环控制"],
  ];
  features.forEach(([k, v], i) => {
    const y = 164 + i * 88;
    text(s, k, 720, y, 210, 44, 24, i === 0 ? C.orange : C.teal, { bold: true, mono: true });
    text(s, v, 900, y + 2, 285, 42, 20, C.white);
    if (i < features.length - 1) rule(s, 720, y + 58, 460, C.line, 1);
  });
  text(s, "语义选择：动态类型、词法作用域、严格布尔条件、短路逻辑。", 716, 580, 480, 52, 18, C.muted);
  note(s, "WHR 没有照搬现有语言。它用 form、craft、give、when、repeat while 和左箭头赋值形成自己的表面语法；内部语义选择则追求容易解释和测试。");
}

// 4. Architecture
{
  const s = base("解释器架构：一条可逐层讲清的执行流水线", 4);
  const stages = [
    ["源码", ".whr"], ["词法器", "Token"], ["解析器", "AST"], ["解释器", "求值"], ["环境", "作用域"], ["结果", "stdout"],
  ];
  const xs = [60, 250, 440, 630, 820, 1010];
  const shapes = [];
  stages.forEach(([a, b], i) => {
    const p = box(s, xs[i], 220, 150, 120, i === 3 ? C.tealDark : C.navy2, 18, i === 3 ? C.teal : C.line);
    shapes.push(p);
    text(s, a, xs[i] + 10, 244, 130, 35, 22, C.white, { bold: true, align: "center" });
    text(s, b, xs[i] + 10, 288, 130, 28, 16, C.muted, { align: "center", mono: true });
  });
  for (let i = 0; i < shapes.length - 1; i += 1) {
    s.shapes.add({ geometry: "rightArrow", position: { left: xs[i] + 154, top: 264, width: 32, height: 30 }, fill: C.orange, line: { fill: "none", width: 0 } });
  }
  text(s, "每层只做一件事", 94, 430, 280, 38, 24, C.teal, { bold: true });
  text(s, "Lexer 识别词法；Parser 按优先级生成 AST；Interpreter 在 Environment 中执行节点。", 94, 480, 1030, 54, 21, C.white);
  text(s, "优点：结构清晰、错误定位明确、特别适合课程验收时逐层演示。", 94, 555, 1030, 48, 20, C.orange, { bold: true });
  note(s, "执行从源代码开始。词法器把字符变成 Token，解析器构建 AST，解释器遍历 AST，并通过 Environment 保存变量和闭包作用域。最终输出到标准输出。");
}

// 5. Runtime semantics
{
  const s = base("运行时语义：从基本类型到闭包", 5, C.blue);
  const items = [
    ["基本值", "整数 · 字符串 · 布尔 · none", C.blue],
    ["容器", "数组创建、索引、更新、push/pop", C.teal],
    ["结构", "form 声明、字段读取与赋值", C.orange],
    ["函数", "参数、返回、递归、词法闭包", C.green],
  ];
  items.forEach(([a, b, color], i) => {
    const y = 150 + i * 112;
    box(s, 86, y, 1080, 86, C.navy2, 16, C.line);
    s.shapes.add({ geometry: "ellipse", position: { left: 108, top: y + 20, width: 44, height: 44 }, fill: color, line: { fill: "none", width: 0 } });
    text(s, a, 180, y + 18, 190, 40, 23, C.white, { bold: true });
    text(s, b, 390, y + 21, 720, 38, 20, C.muted);
  });
  text(s, "严格布尔：when 与 repeat while 只接受 true / false", 88, 620, 1070, 36, 19, C.orange, { bold: true, align: "center" });
  note(s, "语言支持作业要求中的整数、字符串、数组、结构、输入输出、控制流和函数。额外实现了递归与词法闭包。严格布尔条件可避免 0、空字符串等隐式真假带来的歧义。");
}

// 6. Errors and CLI
{
  const s = base("错误不是崩溃：统一诊断、稳定退出码", 6, C.red);
  const cols = [
    ["LexError", "非法字符、字符串未闭合", "源位置"],
    ["ParseError", "语法结构不完整", "期望 Token"],
    ["RuntimeError", "类型、索引、字段、调用错误", "运行位置"],
  ];
  cols.forEach(([name, desc, tag], i) => {
    const x = 70 + i * 395;
    box(s, x, 160, 350, 210, C.navy2, 18, C.line);
    text(s, name, x + 24, 188, 300, 42, 25, i === 0 ? C.orange : i === 1 ? C.blue : C.red, { bold: true, mono: true });
    text(s, desc, x + 24, 248, 300, 58, 19, C.white);
    label(s, tag, x + 24, 316, 120, C.muted);
  });
  box(s, 110, 430, 1060, 150, "#09111F", 14, C.line);
  text(s, "$ python -m whr bad.whr", 138, 452, 800, 30, 19, C.teal, { mono: true });
  text(s, "RuntimeError [line 4, column 9]: array index 5 out of range", 138, 500, 940, 34, 21, C.white, { mono: true });
  text(s, "退出码：0 成功 · 1 语言错误 · 2 命令行错误", 138, 548, 880, 30, 17, C.muted);
  note(s, "解释器把错误分成词法、语法和运行时三层，统一带行列位置，并规定稳定退出码。这样黑盒测试可以同时验证标准输出、标准错误和退出码。");
}

// 7. Testing
{
  const s = base("测试策略：从 .whr 源程序到进程结果的黑盒验证", 7, C.green);
  metric(s, "64 / 64", "黑盒用例通过", 76, 148, 250, C.green);
  metric(s, "31 / 31", "Python 单元/集成测试", 348, 148, 250, C.blue);
  metric(s, "0", "正式验证失败", 620, 148, 250, C.orange);
  metric(s, "1 条命令", "运行全部黑盒测试", 892, 148, 300, C.teal);
  const table = s.tables.add({
    rows: 2,
    columns: 8,
    left: 76,
    top: 344,
    width: 1116,
    height: 122,
    values: [
      ["类型", "数组", "结构", "I/O", "控制流", "函数", "错误", "回归+CLI"],
      ["8", "5", "5", "6", "6", "8", "22", "4"],
    ],
  });
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 8 }).assign({ fill: C.tealDark, textStyle: { typeface: FONT, fontSize: 17, bold: true, color: C.white }, anchor: "middle" });
  table.cells.block({ row: 1, column: 0, rowCount: 1, columnCount: 8 }).assign({ fill: C.navy2, textStyle: { typeface: MONO, fontSize: 24, bold: true, color: C.white }, anchor: "middle" });
  text(s, "每个用例声明期望 stdout / stderr / exit code；测试驱动器启动真实解释器进程。", 82, 510, 1090, 50, 20, C.white, { align: "center" });
  text(s, "这证明的是用户看到的行为，而不是内部函数“碰巧通过”。", 82, 578, 1090, 42, 22, C.orange, { bold: true, align: "center" });
  note(s, "重点解释黑盒：测试不是直接调用解释器内部函数，而是像用户一样执行 .whr 文件，检查 stdout、stderr 和退出码。64个用例覆盖所有功能和错误分支。");
}

// 8. Benchmark
{
  const s = base("性能测试：公平、留痕，也诚实面对差距", 8, C.orange);
  const chart = s.charts.add("bar", {
    position: { left: 70, top: 150, width: 700, height: 380 },
    categories: ["素数统计", "容器更新"],
    series: [
      { name: "WHR", values: [102.773, 136.348], fill: C.orange },
      { name: "Python", values: [15.040, 17.408], fill: C.teal },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 90 },
    hasLegend: true,
    legend: { position: "bottom", textStyle: { typeface: FONT, fontSize: 16, fill: C.white } },
    yAxis: { title: "端到端中位数 / ms", min: 0, numberFormatCode: "0", textStyle: { typeface: FONT, fontSize: 14, fill: C.muted } },
    xAxis: { textStyle: { typeface: FONT, fontSize: 15, fill: C.white } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: FONT, fontSize: 14, fill: C.white } },
    chartFill: C.navy,
    plotAreaFill: C.navy,
  });
  applyPresentationChartFont(chart, { fontFamily: FONT });
  metric(s, "6.83×", "素数统计倍率", 830, 176, 300, C.orange);
  metric(s, "7.83×", "容器更新倍率", 830, 342, 300, C.orange);
  text(s, "2 次预热 · 7 轮正式计时 · 交替执行顺序 · 0 失败", 100, 566, 1060, 36, 19, C.teal, { bold: true, align: "center" });
  text(s, "结论：树遍历解释器更慢；数据用于定位代价，不掩饰结果。", 100, 616, 1060, 36, 19, C.white, { align: "center" });
  note(s, "数据来自保留的 JSON 原始结果。每个工作负载两次预热、七轮正式计时，并交替 WHR 与 Python 的顺序。WHR 慢约6.83倍和7.83倍，主要包含进程启动、解析和树遍历解释开销。");
}

// 9. Agent skill
{
  const s = base("让 Agent 会写 WHR：指南不是摆设，而是可验证接口", 9, C.green);
  const steps = [
    ["01", "读规范", "语法与错误模型"],
    ["02", "按模板实现", "任务、约束、验收"],
    ["03", "本地验证", "--check 与真实运行"],
    ["04", "交付证据", "源码、输出、修改记录"],
  ];
  const nodes = [];
  steps.forEach(([n, a, b], i) => {
    const x = 70 + i * 300;
    const p = box(s, x, 192, 240, 180, C.navy2, 18, C.line);
    nodes.push(p);
    text(s, n, x + 20, 210, 58, 38, 20, C.teal, { bold: true, mono: true });
    text(s, a, x + 22, 258, 196, 40, 24, C.white, { bold: true, align: "center" });
    text(s, b, x + 20, 316, 200, 32, 16, C.muted, { align: "center" });
  });
  for (let i = 0; i < nodes.length - 1; i += 1) {
    s.shapes.add({ geometry: "rightArrow", position: { left: 314 + i * 300, top: 267, width: 48, height: 30 }, fill: C.green, line: { fill: "none", width: 0 } });
  }
  box(s, 154, 450, 970, 118, "#0B2A27", 16, C.tealDark);
  text(s, "独立前向测试", 182, 474, 210, 34, 21, C.green, { bold: true });
  text(s, "新 Agent 只读取项目 Skill，就独立完成结构体、数组、函数与循环示例，并通过真实解释器。", 392, 472, 690, 58, 19, C.white);
  text(s, "证据：.agents/skills/whr-language/ + docs/agent_logs/06_skill_forward_test.md", 182, 590, 930, 30, 16, C.muted, { mono: true });
  note(s, "我把语言使用方法封装成项目级 Skill。为了避免自证循环，又让一个独立 Agent 只读 Skill 完成新程序并运行通过，证明文档足以指导编程。");
}

// 10. Application
{
  const s = base("267 行综合应用：校园生存模拟器", 10, C.orange);
  text(s, "玩家连续 6 周选择行动，在绩点、精力、压力、人脉与金币之间权衡。", 78, 138, 1100, 40, 21, C.white, { align: "center" });
  const stats = [["GPA", C.blue], ["ENERGY", C.green], ["STRESS", C.red], ["SOCIAL", C.teal], ["COINS", C.orange]];
  stats.forEach(([v, color], i) => {
    const x = 78 + i * 225;
    box(s, x, 216, 190, 74, C.navy2, 14, C.line);
    text(s, v, x + 10, 236, 170, 32, 19, color, { bold: true, align: "center", mono: true });
  });
  const flow = ["菜单输入", "行动结算", "随机事件", "状态约束", "结局判定"];
  const nodes = [];
  flow.forEach((v, i) => {
    const x = 52 + i * 246;
    const p = box(s, x, 376, 190, 86, i === 4 ? C.tealDark : C.navy2, 14, i === 4 ? C.teal : C.line);
    nodes.push(p);
    text(s, v, x + 10, 400, 170, 34, 20, C.white, { bold: true, align: "center" });
  });
  for (let i = 0; i < nodes.length - 1; i += 1) {
    s.shapes.add({ geometry: "rightArrow", position: { left: 246 + i * 246, top: 404, width: 42, height: 28 }, fill: C.orange, line: { fill: "none", width: 0 } });
  }
  metric(s, "267", "有效 WHR 代码行", 136, 520, 280, C.orange);
  metric(s, "4", "可达结局均有测试", 500, 520, 280, C.green);
  metric(s, "6", "应用级自动测试", 864, 520, 280, C.blue);
  note(s, "应用共有267个有效代码行，综合使用了结构、数组、函数、分支、循环和输入输出。主智能体审查时发现一个结局不可达，返工后四种结局都增加了真实子进程测试。");
}

// 11. Git and reproducibility
{
  const s = base("可复现交付：阶段文档、语义提交、统一验收", 11, C.blue);
  const commits = [
    ["e130fe8", "总体计划"], ["528d0aa", "冻结规范"], ["024d53c", "完整运行时"],
    ["d4ec034", "黑盒测试"], ["f5c0428", "正式性能结果"], ["9c29553", "开发指南"], ["1cd05b7", "267行应用"],
  ];
  commits.forEach(([hash, desc], i) => {
    const x = 70 + i * 164;
    s.shapes.add({ geometry: "ellipse", position: { left: x + 56, top: 230, width: 28, height: 28 }, fill: i === commits.length - 1 ? C.orange : C.teal, line: { fill: "none", width: 0 } });
    if (i < commits.length - 1) rule(s, x + 84, 242, 136, C.line, 4);
    text(s, hash, x + 10, 282, 124, 28, 15, C.white, { bold: true, align: "center", mono: true });
    text(s, desc, x, 324, 144, 46, 16, C.muted, { align: "center" });
  });
  box(s, 110, 430, 1060, 130, C.navy2, 18, C.line);
  text(s, "$ python scripts/check_project.py", 146, 456, 740, 34, 23, C.teal, { mono: true, bold: true });
  text(s, "一次检查：交付物 · CLI · 黑盒 · 单元测试 · LOC · 性能证据 · PPT", 146, 510, 940, 32, 18, C.white);
  text(s, "每阶段至少一个 Git 提交，规范、实现、测试和文档可以沿历史回看。", 100, 600, 1080, 36, 19, C.orange, { bold: true, align: "center" });
  note(s, "Git 历史按阶段提交，可以看到项目如何从计划、规范、解释器逐步发展到测试、性能、指南和应用。最终使用 check_project.py 一条命令做总验收。");
}

// 12. Close and demo order
{
  const s = base("现场演示顺序：5 分钟证明项目闭环", 12, C.teal);
  const items = [
    ["1", "运行 language_tour.whr", "证明核心语法"],
    ["2", "运行 64 项黑盒测试", "证明完整性"],
    ["3", "演示校园生存模拟器", "证明综合使用"],
    ["4", "展示性能 JSON 与报告", "证明实验可复现"],
    ["5", "执行统一项目检查", "证明交付闭环"],
  ];
  items.forEach(([n, a, b], i) => {
    const y = 142 + i * 92;
    text(s, n, 98, y + 4, 48, 44, 30, C.teal, { bold: true, mono: true, align: "center" });
    text(s, a, 180, y, 490, 42, 23, C.white, { bold: true });
    text(s, b, 738, y + 3, 380, 38, 19, C.muted);
    if (i < items.length - 1) rule(s, 180, y + 58, 940, C.line, 1);
  });
  text(s, "结论：WHR 不只是“能跑”，而是有规范、有证据、能复现、能扩展。", 90, 622, 1100, 48, 23, C.orange, { bold: true, align: "center" });
  note(s, "结束时按这五步现场演示。最终结论是：WHR形成了从语言设计到解释器、测试、实验、文档和应用的完整工程闭环。");
}

const stagingDir = path.join(workspaceDir, ".build", "presentation");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(finalPptx), { recursive: true });
const candidatePath = path.join(stagingDir, "candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 12,
  requiredNativeTableOwnerSlides: [2, 7],
  requiredNativeChartOwnerSlides: [8],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
};
const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: finalPptx,
  pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "2",
    "--require-native-table-slide", "7",
  ],
  requiredNativeTableOwnerSlides: requirements.requiredNativeTableOwnerSlides,
  requiredNativeChartOwnerSlides: requirements.requiredNativeChartOwnerSlides,
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
  fontPolicy: { basis: "design", families: [FONT, MONO] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, `${path.basename(finalPptx)}.validation.json`),
});
console.log(JSON.stringify({ finalPptx, result }, null, 2));
