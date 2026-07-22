# 架构约束（Architectural Constraints）

> 目标：保持组件边界和已有分层，禁止为了局部方便引入跨层或跨组件捷径。

## 1. 系统边界

```text
dashboard-front
  -> dashboard
     -> MySQL
     -> controller -> control-plane etcd
                         -> operator -> APISIX etcd
operator -> core-api -> MySQL
APISIX data plane -> core-api -> MySQL
dashboard -> MySQL -> mcp-proxy
```

| 组件 | 职责 | 主要边界 |
|------|------|---------|
| `dashboard-front` | 管理 UI | HTTP 调用 Dashboard |
| `dashboard` | 控制面、模型、发布编排 | MySQL、etcd、外部蓝鲸服务 |
| `operator` | 监听控制面 etcd，写 APISIX etcd | etcd、Core API |
| `core-api` | 权限、公钥、发布事件 API | HTTP、MySQL |
| `mcp-proxy` | 将已发布网关能力暴露为 MCP | HTTP/MCP、MySQL |
| `test-bdd` | 真实环境行为验证 | Dashboard Web/API |

禁止在组件间直接导入源码共享业务逻辑。共享契约必须通过已存在的 HTTP、etcd、数据库或生成接口表达。

## 2. 组件内依赖

### 2.1 Dashboard

`import-linter` 强制：

```text
apis -> biz -> controller -> service -> components -> apps -> core -> common -> utils
```

- `apis` 负责 HTTP 边界、序列化和响应组装。
- `biz` 负责业务用例、事务、权限决策和副作用编排。
- `controller` 负责发布编译、APISIX 转换和分发。
- `service` 只承载可复用的叶子能力，不用于绕过 `biz` 边界。
- `apps/core/common/utils` 依次承担持久化、领域、公共设施和底层工具。

### 2.2 Go 服务

- `core-api`：`pkg/api -> pkg/service -> pkg/cacheimpls -> pkg/database/dao -> pkg/database`。
- `operator`：watch/registry -> agent/timer -> committer -> synchronizer -> store；事件上报独立处理。
- `mcp-proxy`：HTTP/MCP handler 通过 service/infra 访问数据库和网关，不绕过认证、权限和中间件。
- 具体包边界以各组件 `AGENTS.md` 为准，不在根规范中创造统一但不存在的抽象。

### 2.3 Frontend

- 页面和布局通过 `services/source` 访问后端。
- HTTP、CSRF、缓存、取消和错误策略集中在 `services/http`。
- 全局状态放入 Pinia store；页面私有状态保留在组件或 composable。
- 遵循 `src/dashboard-front/AGENTS.md` 和组件现有模式。

## 3. 数据边界

| 边界 | 解析/验证位置 | 约束 |
|------|--------------|------|
| HTTP 请求 | View/Handler/Serializer | 外部输入先解析，再进入业务层 |
| 数据库记录 | DAO/ORM/Repository | 保持既有字段兼容和事务语义 |
| etcd 资源 | Dashboard controller / Operator registry | 校验版本、资源类型和 key 语义 |
| OpenAPI/MCP | mcp-proxy 加载与映射层 | 保持工具名、权限和传输协议兼容 |
| 前端响应 | services/types/bridge | 统一处理错误、空值和类型转换 |

不得用下游空值兜底掩盖上游契约错误；先定位值为何无效，再决定在哪个边界修复。

## 4. 可执行约束

| 编号 | 规则 | 现有执行方式 |
|------|------|-------------|
| ARCH-001 | Dashboard 禁止反向分层依赖 | `import-linter` |
| ARCH-002 | 跨组件不得建立源码级耦合 | 目录边界、Reviewer 检查 |
| ARCH-003 | API/发布/权限兼容性不得静默破坏 | 组件测试、定义一致性检查 |
| ARCH-004 | 自动生成文件不得手改 | 组件 codegen 命令和 diff 审查 |
| ARCH-005 | 组件命令必须从规定目录执行 | 最近的 `AGENTS.md` |

新增机器可执行规则时，错误信息应包含违规路径、允许方向、修复建议和本文链接。

## 5. 架构决策

仓库当前没有统一 `docs/adr/` 流程。重大跨组件边界、数据库迁移、公开 API 破坏性变更或发布链路调整，
应先在版本控制内记录设计/规格，并在用户确认后实施。是否建立统一 ADR 编号体系待团队确认。

## 检查清单

- [ ] 修改位于正确组件和正确层
- [ ] 未新增跨组件源码依赖或反向依赖
- [ ] 外部输入在系统边界完成解析和鉴权
- [ ] 数据库、HTTP、etcd、MCP 契约保持兼容
- [ ] 自动生成物通过生成命令更新
- [ ] 架构决策和迁移方案已获得所需确认
