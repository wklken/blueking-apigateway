# 技术规范

> 本目录由 Harness Engineering 预设同步。预设文件以治理源为唯一事实源，不在本仓直接修改正文。

## 加载策略

Agent 先读取根和组件 `AGENTS.md` 确认任务范围，再按涉及的技术栈加载对应规范。
组件现有代码、测试、配置和最近的组件规则优先于通用骨架；发现冲突时记录证据并回到预设源修正。

## 已启用规范

| 类别 | 规范 | 适用范围 | 级别 |
|------|------|---------|------|
| 安全 | [security-bk-redlines.md](security-bk-redlines.md) | 全部代码组件 | Level 1：必选预设 |
| 代码评审 | [quality-code-review.md](quality-code-review.md) | 全部代码组件 | Level 1：必选预设 |
| 前端 | [frontend-vue3.md](frontend-vue3.md) | `src/dashboard-front` | Level 1：Vue 3 精确预设 |
| 接口 | [api-generic.md](api-generic.md) | REST/OpenAPI、HTTP/MCP、etcd 契约 | Level 2：通用骨架 |
| 后端 | [backend-generic.md](backend-generic.md) | Python/Django 与 Go 服务 | Level 2：通用骨架 |

## 选择依据

- `src/dashboard-front/package.json` 和 `vite.config.ts` 明确使用 Vue 3 + TypeScript + Vite。
- 仓库没有 `.proto` 文件；Go 模块中的 `grpc-gateway` 为依赖信号，不能代表统一的接口定义方式。
- 后端同时包含 Python/Django 和多个 Go 服务，现有预设库没有覆盖该组合的单一精确预设。
- 项目属于代码仓，因此安全红线和代码评审规范为必选项。

## 待完善

- `api-generic.md` 尚未形成 BlueKing API Gateway 的 REST/OpenAPI、MCP 和 etcd 契约专用预设。
- `backend-generic.md` 尚未形成 Django 控制面与 Go 服务组合的专用预设。
- 完善时应修改 Harness 治理源的 `assets/standards/` 和 `index.yaml`，再重新同步，不直接编辑本目录中的预设文件。

## 使用检查

- [ ] 只加载当前任务涉及的技术规范
- [ ] 组件局部规则与通用预设冲突时，以可验证的组件事实为准
- [ ] 安全、鉴权、输入校验和敏感信息规则未被降级
- [ ] 自动生成代码和公开契约遵循组件 codegen/兼容流程
- [ ] 预设更新通过 Harness 同步而非本地手改
