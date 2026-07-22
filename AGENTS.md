# AGENTS.md

## 项目概述

BlueKing API Gateway 控制面是多组件 monorepo，负责网关配置、发布、权限、
可观测性和 MCP 服务。根规则适用于整个仓库；进入组件后，以最近的
`AGENTS.md` 补充或覆盖组件运行时、架构和验证要求。

## 目录结构

```text
.
├── docs/                    # 开发文档、Harness 规范、技术规范
├── specs/                   # SDD 规格与任务文档
├── src/
│   ├── core-api/            # Go 核心 API，读取 MySQL
│   ├── dashboard/           # Python/Django 控制面
│   ├── dashboard-front/     # Vue 3 管理前端
│   ├── esb/                 # 已废弃，默认忽略
│   ├── mcp-proxy/           # Go MCP 代理
│   └── operator/            # Go etcd/APISIX 同步服务
├── test/                    # 旧 E2E 测试
└── test-bdd/                # Playwright BDD 测试
```

## 工作规则

- 修改前读取目标文件、相关调用方、最近测试和最近的 `AGENTS.md`。
- 组件内任务保持在组件边界内；只有经验证的生产者/消费者链路才允许跨组件修改。
- 多 worktree 场景先执行 `git rev-parse --show-toplevel`、
  `git status --short --branch`、`git rev-parse HEAD` 和
  `git worktree list --porcelain`，确认目标 checkout。
- 不猜测路径、API、命令或测试结果；不确定时先读取或执行验证。
- 只修改任务必需内容，不做顺手重构、批量格式化或无关清理。
- 评审发现分别回答“问题是否真实”和“是否由选定 diff 引入”。
- `src/esb` 已废弃，除非用户明确指定，否则不读取、不修改。

## 系统关系

```text
dashboard-front -> dashboard -> MySQL
dashboard -> controller -> etcd -> operator -> APISIX etcd
operator -> core-api -> MySQL
APISIX data plane -> core-api -> MySQL
dashboard -> MySQL -> mcp-proxy
```

跨组件通过 HTTP、etcd 或数据库契约协作，禁止为方便而建立源码级反向依赖。

## 组件入口与验证

| 组件 | 入口规范 | 命令根 |
|------|---------|-------|
| Dashboard | `src/dashboard/AGENTS.md` | `src/dashboard` |
| Dashboard Frontend | `src/dashboard-front/AGENTS.md` | `src/dashboard-front` |
| Core API | `src/core-api/AGENTS.md` | `src/core-api` |
| MCP Proxy | `src/mcp-proxy/AGENTS.md` | `src/mcp-proxy` |
| Operator | `src/operator/AGENTS.md` | `src/operator` |
| BDD | `test-bdd/AGENTS.md` | 仓库根 / `test-bdd` |

根 Makefile 只提供需要真实环境凭据的 `make test-bdd`。代码变更必须执行目标组件
`AGENTS.md` 规定的 lint/test；仅 Markdown 变更执行 `git diff --check`、引用检查和复读，
不运行无关组件测试。

## 关键规范

- [Harness 总览](docs/harness/README.md)
- [上下文工程](docs/harness/context-engineering.md)
- [架构约束](docs/harness/architectural-constraints.md)
- [熵管理](docs/harness/entropy-management.md)
- [工具能力](docs/harness/tooling.md)
- [执行与验证](docs/harness/execution-verification.md)
- [技术规范](docs/standards/README.md)
- [词汇表](docs/glossary.md)

## 开发工作流

本项目使用 `workflow-agent` 按 [`docs/workflow.md`](docs/workflow.md) 定义的步骤推进迭代开发。workflow-agent 启动时主动感知当前状态（首次执行、崩溃恢复、错误暂停、重新开始），无需用户输入特定指令。不允许跳过工作流步骤或自行决定开发流程。
