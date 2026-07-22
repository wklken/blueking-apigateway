# Harness Engineering 规范

> 本目录定义 BlueKing API Gateway 中 AI Agent 的上下文、架构边界、工具能力和验证要求。

## 项目画像

- **项目类型**：多组件代码仓（code-project）
- **核心技术栈**：Python/Django、Go、Vue 3/TypeScript、MySQL、etcd、APISIX、Playwright
- **Agent 场景**：代码分析、实现、调试、评审、测试、文档维护和 PR 交付
- **规则层级**：根 `AGENTS.md` 提供全局入口，组件 `AGENTS.md` 提供局部事实

## 规范导航

| 组件 | 文档 | 作用 |
|------|------|------|
| 上下文工程 | [context-engineering.md](context-engineering.md) | 知识来源、加载顺序、动态证据 |
| 架构约束 | [architectural-constraints.md](architectural-constraints.md) | 组件边界、依赖方向、数据边界 |
| 熵管理 | [entropy-management.md](entropy-management.md) | 文档一致性、技术债和漂移控制 |
| 工具能力 | [tooling.md](tooling.md) | Skill、MCP、CLI 与危险操作约束 |
| 执行与验证 | [execution-verification.md](execution-verification.md) | 任务循环、验证合同和完成条件 |

相关入口：

- [技术规范](../standards/README.md)
- [词汇表](../glossary.md)
- [迭代开发工作流](../workflow.md)

## 加载顺序

1. 读取根 `AGENTS.md`，确定项目边界和目标组件。
2. 读取目标路径最近的 `AGENTS.md`，确定运行时与验证命令。
3. 按任务读取本目录中对应的 Harness 组件。
4. 涉及技术栈规则时读取 `docs/standards/README.md` 选择对应规范。
5. 以当前代码、配置、测试和 CI 为最终事实；历史计划只能作为背景。

## 维护原则

- 架构、命令、目录或接口变化时，同一 PR 更新相关 Harness 文档。
- 预设技术规范由 Harness 预设库同步，不在本仓直接定制其正文。
- 文档中的路径、命令和引用必须可验证；无法验证的内容标记为待确认。
- 定期运行 Harness 文档巡检，简单漂移直接修复，架构语义变化由人工确认。

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-07-22 | 初始化 Harness Engineering 规范 |
