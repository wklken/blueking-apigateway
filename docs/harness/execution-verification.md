# 执行与验证（Execution & Verification）

> 目标：以可复现证据完成任务，区分“执行过”与“验证通过”。

## 1. 执行循环

```text
观察 -> 明确成功标准 -> 读取上下文 -> 执行最小变更
     -> 运行最小验证 -> 检查 diff/范围 -> 更新状态
```

### 循环保护

| 信号 | 动作 |
|------|------|
| 需求有两个 materially different 的解释 | 停止并询问 |
| 连续 3 次没有新证据或进展 | 停止随机尝试，报告已排除项 |
| 修复范围跨越未验证组件边界 | 设置检查点并请求确认 |
| 需要凭据、生产资源或破坏性操作 | 停止并请求明确授权 |
| diff 出现无关文件 | 撤销范围外变化 |

## 2. 任务分类

| 类型 | 起点 | 完成证据 |
|------|------|---------|
| 分析 | 精确路径/日志/调用链 | 文件和符号引用 |
| 实现 | 明确行为和成功标准 | 测试、lint、diff |
| 调试 | 可复现症状或失败测试 | 先失败后通过的证据 |
| 评审 | 明确 revision/diff 范围 | finding 与引入归因分开 |
| 文档 | 当前代码和规则 | diff check、路径/引用检查 |
| 交付 | 已完成且已验证的 diff | commit、push、PR URL |

## 3. 组件验证合同

| 范围 | 命令根 | 最低要求 |
|------|-------|---------|
| `src/dashboard` | `src/dashboard` | 最近规则规定的 focused pytest；广泛变更运行 `uv run make edition-ee && uv run make lint-check`、`uv run make test` |
| `src/dashboard-front` | `src/dashboard-front` | `pnpm lint:eslint`；按变更运行 `pnpm build-only`/`pnpm type-check` |
| `src/core-api` | `src/core-api` | focused `go test`，然后 `make lint`、`make test` |
| `src/mcp-proxy` | `src/mcp-proxy` | focused Ginkgo，按范围运行 `make lint`、`make test`/`make integration` |
| `src/operator` | `src/operator` | focused Ginkgo，然后 `make test`；需要时 `make integration` |
| `test-bdd` | 仓库根 | 有真实环境凭据时运行 `make test-bdd` |
| 仅 Markdown | 仓库根/组件根 | `git diff --check`、引用检查、复读 |

最近的组件 `AGENTS.md` 是命令细节的权威来源。本表不替代其运行时和前置条件。

## 4. Bug 修复

1. 读取完整错误和堆栈。
2. 使用仓库支持的命令复现。
3. 先添加能失败的回归测试。
4. 运行测试确认确实失败且原因正确。
5. 实施最小修复。
6. 运行 focused test，再运行组件门禁。

无法写测试时必须说明架构限制、手工验证方式和剩余风险。

## 5. 检查清单

- [ ] 当前 root、branch、HEAD 和 worktree 与任务目标一致
- [ ] `git status` 和 diff 只包含任务范围
- [ ] 需求逐条有实现或文档对应
- [ ] 已运行目标组件要求的最小验证
- [ ] 跳过、失败、阻塞和外部依赖均显式报告
- [ ] 没有声称未实际运行的测试通过
- [ ] 文档、生成物、配置和引用已同步
- [ ] commit/push/PR 等外部动作在授权范围内

## 6. 检查点和记录

多步骤任务在以下时点记录“已变更、已验证、剩余事项”：

- 完成上下文和方案确认后
- 每个可独立验证的实现阶段后
- 遇到失败、范围扩大或方案变化前
- 提交、推送或创建 PR 前

日志至少保留命令、退出码、关键输出、工作目录和对应 revision；敏感值必须脱敏。
