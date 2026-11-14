# Agent Loop

经典 Agent Loop 框架骨架（Python，仅框架 + stub，可离线运行）。

六层抽象，每层只依赖接口，可独立替换实现：

```
┌────────────────────────────────────────────────────┐
│                   Gateway (IM 接入)                 │
│   feishu / telegram / slack (stub) · EchoGateway    │
└──────────────────────┬─────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────┐
│              AgentLoop (core/loop.py)               │
│   感知 → LLM 决策 → 执行工具 → 结果喂回 → 循环       │
│                                                     │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Context │  │ LLMClient│  │ Tools + Harness    │  │
│  │ +Memory │  │ stub/real│  │ dispatch_task      │  │
│  └─────────┘  └──────────┘  └────────────────────┘  │
└────────────────────────────────────────────────────┘
```

## 快速开始

```bash
cd /home/wanger/codes/agent-loop
python3 main.py          # 无 API key 时自动用 stub LLM
python3 -m gateway.demo  # IM 消息进出全流程演示（EchoGateway）
```

接入真实 LLM（任何 OpenAI 兼容端点：GLM / DeepSeek / OpenAI / 本地 vllm）——
编辑 `~/.agent-loop/config.json`（模板见仓库 `config.example.json`）：

```json
{
  "llm": {
    "api_key": "your-key",
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "model": "glm-4.6"
  }
}
```

```bash
python3 main.py                        # 自动切换 RealLLMClient
AGENT_TASK="另一个任务" python3 main.py   # 换任务（env 覆盖文件里的 task）
```

配置解析规则：

- 文件搜索顺序：`AGENT_LOOP_CONFIG` 环境变量指定路径 > `~/.agent-loop/config.json`（用户级）> 仓库根 `config.json`（项目级覆盖，已 gitignore）
- 环境变量永远覆盖文件值（`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`），key 可以只放 env、其余放文件
- 文件里还可配 `task` / `max_steps` / `temperature` / `context_token_limit` / `review.enabled`
- 文件缺失或损坏不是错误：告警后回退默认值 + stub，任务仍可运行

离线验证真实 HTTP 代码路径（无需 key）：

```bash
python3 -m examples.mock_llm_server &   # 本地 OpenAI 兼容 mock（脚本化工具调用）
LLM_API_KEY=x LLM_BASE_URL=http://127.0.0.1:8642/v4 python3 main.py
```

## 目录结构

```
agent-loop/
├── main.py                 # 入口：装配 Config + LLMClient + Tools + Loop
├── config.py               # Config dataclass + JSON 配置加载（~/.agent-loop/config.json）
├── config.example.json     # 配置模板（真实配置在 home，不入库）
├── core/
│   ├── loop.py             # AgentLoop 主循环 + LoopResult
│   └── context.py          # Message / Context：会话历史管理与序列化
├── llm/
│   └── client.py           # LLMClient 抽象 + StubLLMClient + RealLLMClient（OpenAI 兼容）
├── tools/
│   ├── base.py             # Tool 基类、ToolSpec、ToolRegistry（校验 + 超时强制）
│   ├── examples.py         # 示例工具：read_file（根目录防护）、run_command（黑名单 → 沙盒）
│   └── memory_tools.py     # memory_write / memory_search 工具
├── sandbox/                # 沙盒层：命令执行的第二道墙
│   ├── base.py             # Sandbox 抽象、SandboxResult、SandboxUnavailable
│   ├── local.py            # LocalSandbox：workspace 白名单 + env 白名单 + rlimits + 进程组 kill
│   ├── docker_backend.py   # DockerSandbox：docker run --rm --network none（CLI 子进程，无第三方依赖）
│   └── factory.py          # create_sandbox：按 config 选后端，docker 不可用降级 local
├── harness/                # 外部 harness 调度层
│   ├── base.py             # Harness 抽象、HarnessResult、HarnessRegistry
│   ├── adapters.py         # ClaudeCode / Codex / OpenClaw stub（TODO: CLI 接入）
│   ├── local.py            # LocalAgentLoopHarness：agent 调度 agent
│   └── dispatch_tool.py    # dispatch_task 工具
├── memory/                 # 长期记忆层
│   ├── base.py             # Memory 抽象：write/search/read/delete + compact
│   ├── implementations.py  # InMemoryMemory（可跑）+ FileMemory（TODO: search）
│   └── summarizer.py       # Summarizer 接口（上下文压缩，LLM 摘要 TODO）
└── gateway/                # IM 接入层
    ├── base.py             # Gateway 抽象 + IncomingMessage/OutgoingMessage
    ├── im/                 # feishu / telegram / slack stub（TODO: 真实接入）
    ├── router.py           # chat_id → AgentLoop 会话映射（多会话隔离）
    └── demo.py             # EchoGateway 离线演示
```

## 分层说明

### 1. Core Loop（core/）

```
任务输入 ──► 感知（构建 Context）──► LLMClient(messages+tools)
                ▲                          │ ToolCall
                │                          ▼
        tool message 喂回 ◄────────── ToolRegistry 执行
        循环直到：模型返回纯文本答案 / 达到 max_steps / 出错
```

### 2. Harness 调度层（harness/）

把子任务派发给外部 coding harness（Claude Code、Codex、OpenClaw、或另一个 AgentLoop）：

```python
from harness import create_default_registry
from harness.local import LocalAgentLoopHarness
from harness.dispatch_tool import DispatchTaskTool

harnesses = create_default_registry()
harnesses.register(LocalAgentLoopHarness(shared_loop=existing_loop))
tool_registry.register(DispatchTaskTool(harnesses))
```

- `Harness.submit(task, context) -> HarnessResult`：同步派发
- 异步（`submit_async`/`poll`/`cancel`）已留接口，实现为 TODO
- stub 适配器返回 `FAILED` + 提示；真实接入只需实现 CLI/SDK 调用

### 3. Memory 层（memory/）

可插拔记忆后端，通过工具暴露给模型：

```python
from memory.implementations import InMemoryMemory
from tools.memory_tools import build_memory_tools

memory = InMemoryMemory()
for tool in build_memory_tools(memory):
    tool_registry.register(tool)
```

- `InMemoryMemory`：关键词匹配打分，可直接跑
- `FileMemory`：Markdown 文件存储 + 关键词检索（front matter 元数据）
- 换向量库/SQLite 只需实现 `Memory` 接口
- 上下文接近 token 上限（`Config.context_token_limit > 0`）时，loop 自动调用
  `HeuristicSummarizer` 压缩旧历史（保留 system + 最近 N 条）

### 4. Gateway 层（gateway/）

IM 消息进 → Agent → 回复出，核心循环不变：

```
IM 平台 ──事件──► Gateway（标准化 IncomingMessage）
                       │ on_message
                       ▼
              GatewayRouter.resolve(chat_id) ──► AgentLoop（每会话一个）
                       │
              LoopResult.output ──► gateway.send() ──► IM 平台
```

各平台接入要点已写在 stub docstring 中：

| 平台 | 收流方式 | 关键点 |
|---|---|---|
| 飞书 | webhook（`url_verification` 握手）或 WebSocket 长连接 | `event_id` 去重、`tenant_access_token` + `/im/v1/messages` |
| Telegram | webhook（secret token）或 `getUpdates` 长轮询 | chat.id、`sendMessage`/`sendDocument` |
| Slack | Events API（签名验证）或 Socket Mode | `<@UBOT>` 前缀剥离、`thread_ts`、`chat.postMessage` |

接真实 IM 只需实现对应 Gateway 的 `parse_event` + `send`，其余全复用。

### 5. Sandbox 层（sandbox/）

工具命令执行的双闸结构：黑名单是第一道闸（便宜的阵线，拦明显破坏性字符串），
沙盒是第二道墙（即使黑名单漏拦也困得住）。工具只依赖 `Sandbox` 接口，
后端在装配时选择，与 memory/harness 同一风格：

```python
from sandbox import create_sandbox

sandbox = create_sandbox(config_sandbox_settings, workspace_root="workspace")
# backend="docker" 但 daemon 不可用时自动降级为 local（带 warning）
```

```python
result = sandbox.run(cmd, cwd=None, env=None, timeout=30.0)
result.stdout / result.stderr / result.exit_code / result.timed_out / result.backend
```

三个后端：

| backend | 隔离手段 | 适用 |
|---|---|---|
| `local` | cwd 白名单（workspace 内）+ env 白名单（防宿主 secrets 泄漏）+ rlimits（CPU/内存/文件大小/进程数）+ 超时进程组 kill | 默认；零依赖 |
| `docker` | `docker run --rm --network none --memory/--cpus/--pids-limit`，workspace 挂载（可只读），容器内 nobody 用户，超时 `docker kill` | 最强墙；daemon 缺失抛 `SandboxUnavailable` 自动降级 |
| `off` | 无隔离（开发专用；黑名单仍是唯一闸） | 仅可信环境调试 |

config（见 `config.example.json` 的 `sandbox` 节）：

```json
{
  "sandbox": {
    "backend": "local",
    "workspace_root": "workspace",
    "image": "python:3.12-slim",
    "readonly": false,
    "limits": {"cpu_seconds": 10, "memory_mb": 256, "file_size_mb": 64, "max_processes": 1024}
  }
}
```

已知边界（写在代码注释里）：Linux 的 RLIMIT_NPROC 是 per-UID 而非 per-sandbox，
宿主机进程多时上限必须高于当前进程数，否则子进程 fork 全挂；要硬性 per-sandbox
进程上限请用 docker 后端（`--pids-limit` 是容器级的）。

验证：`python3 tests/test_sandbox.py`（或 pytest），覆盖超时 kill、workspace 白名单拒绝、
env 过滤、docker 不可用降级、容器内执行与容器超时 kill。

## 待实现点（TODO）

- `gateway/im/*`：真实 IM 适配器（事件解析、签名验签、token 管理、附件上传下载）
- `gateway/base.py`：异步 handler、背压/重试
- `memory/`：LLM 摘要（当前 HeuristicSummarizer 为抽取式）、向量/BM25 检索
- `harness/`：异步派发、poll/cancel 实现
- `llm/client.py`：流式输出（streaming）、多 choice、token 用量统计上报
