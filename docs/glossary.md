# 词汇表

## 业务领域

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| API 网关 | API Gateway | 统一托管、发布、鉴权、监控和保护 API 的平台 |
| 控制面 | Control Plane | 管理网关、环境、资源、发布、权限和配置的系统 |
| 数据面 | Data Plane | 基于 APISIX 执行流量转发、认证、限流和插件逻辑的系统 |
| 网关 | Gateway | API 管理和发布的顶层业务实体 |
| 环境 | Stage | 网关的独立发布环境，如测试或生产 |
| 资源版本 | Resource Version | 一组可发布资源定义的版本化快照 |
| 发布 | Release | 将资源版本绑定到环境并生成下游配置的过程 |
| 发布事件 | Publish Event | Operator 向 Core API 上报的发布阶段和结果 |
| MCP 服务 | MCP Server | 将网关 API 或 Prompt 能力暴露为 Model Context Protocol 的服务 |

## 架构与数据

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| Dashboard | Dashboard | Django 控制面后端，负责业务模型和发布编排 |
| Dashboard Frontend | Dashboard Frontend | Vue 3 管理前端 |
| Core API | Core API | 面向数据面和 Operator 的高性能权限、公钥和事件 API |
| Operator | Operator | 监听控制面 etcd 并同步 APISIX etcd 的 Go 服务 |
| MCP Proxy | MCP Proxy | 将已发布网关定义转换为 MCP 工具和传输服务的 Go 服务 |
| etcd | etcd | 控制面与 Operator、Operator 与 APISIX 之间的配置存储和 watch 通道 |
| APISIX | Apache APISIX | BlueKing API Gateway 数据面的基础网关 |
| 单一事实源 | Single Source of Truth | 某类信息唯一可编辑且可验证的权威表示 |
| 数据边界 | Data Boundary | 外部输入被解析、鉴权并转换为内部类型的位置 |

## Harness Engineering

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| Harness Engineering | Harness Engineering | 为 Agent 提供上下文、工具、约束、状态和验证的运行环境工程 |
| 渐进式披露 | Progressive Disclosure | 从入口、导航到详情按任务需要逐层加载上下文 |
| 架构约束 | Architectural Constraint | 限制组件、层和依赖方向的可执行或可审查规则 |
| 熵管理 | Entropy Management | 持续控制文档、代码、架构和技术债漂移的机制 |
| 文档园艺 | Documentation Gardening | 扫描并修复文档与项目事实不一致的维护流程 |
| 开发地图 | Dev Map | 由 graphify 生成的代码概念和关系图谱 |
| Agent Loop | Agent Loop | 观察、推理、行动、验证和更新状态的执行循环 |
| 检查点 | Checkpoint | 多步骤任务中记录当前变更、证据和剩余工作的状态 |
| 任务漂移 | Task Drift | Agent 开始处理规格或授权范围外工作的现象 |

## 工具与协议

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| Skill | Agent Skill | 通过 `SKILL.md` 定义触发条件和执行流程的可复用能力 |
| MCP | Model Context Protocol | Agent 连接外部工具或数据源的协议 |
| BDD | Behavior-Driven Development | 使用 Given/When/Then 描述可执行行为规格的方法 |
| SDD | Spec-Driven Development | 以版本控制内规格、计划和任务驱动实现的开发方式 |
| OpenTelemetry | OTel | 统一生成和传输 Trace、Metric 等遥测数据的标准 |
| ADR | Architecture Decision Record | 记录架构决策背景、选择和后果的文档 |

## 工程实践

| 术语 | 英文 | 定义 |
|------|------|------|
| 外科式变更 | Surgical Change | 只修改解决当前任务所需的最小范围 |
| 回归测试 | Regression Test | 先复现缺陷、再证明修复有效并防止复发的测试 |
| 验证合同 | Verification Contract | 某组件完成变更前必须执行的命令和检查 |
| 来源归因 | Introduction Attribution | 评审时区分问题是否真实以及是否由当前 diff 引入 |
| 预设规范 | Standard Preset | Harness 治理源维护、接入仓只同步不手改的技术规范 |

---

*持续补充中——遇到新术语时请直接在对应分类下添加。*
