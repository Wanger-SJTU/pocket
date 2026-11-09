# Agent Loop

经典 Agent Loop 框架骨架（Python，仅框架 + stub，可离线运行）。

五层抽象，每层只依赖接口，可独立替换实现：

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
python3 main.py          # stub LLM，无需 API key
python3 -m gateway.demo  # IM 消息进出全流程演示（EchoGateway）
```

接入真实 LLM：实现 `llm/client.py` 中的 `RealLLMClient`（见 TODO），在 `main.py` 替换注入。

## 目录结构

```
agent-loop/
├── main.py                 # 入口：装配 Config + LLMClient + Tools + Loop
├── config.py               # Config dataclass：max_steps、model、system_prompt 等
├── core/
│   ├── loop.py             # AgentLoop 主循环 + LoopResult
│   └── context.py          # Message / Context：会话历史管理与序列化
├── llm/
│   └── client.py           # LLMClient 抽象 + StubLLMClient（真实接入 TODO）
├── tools/
│   ├── base.py             # Tool 基类、ToolSpec、ToolRegistry
│   ├── examples.py         # 示例工具：read_file、run_command
│   └── memory_tools.py     # memory_write / memory_search 工具
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
- `FileMemory`：Markdown 文件存储（search TODO）
- 换向量库/SQLite 只需实现 `Memory` 接口

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

## 待实现点（TODO）

- `gateway/im/*`：真实 IM 适配器（事件解析、签名验签、token 管理、附件上传下载）
- `gateway/base.py`：异步 handler、背压/重试
- `llm/client.py`：真实 provider 适配器（消息/工具格式映射、响应归一化）
- `tools/base.py`：参数 jsonschema 校验、执行超时强制
- `tools/examples.py`：路径白名单、命令黑名单/沙箱
- `core/context.py`：超长工具输出截断、历史压缩
- `memory/`：FileMemory.search、LLM 摘要、loop 接近 token 上限自动 compact
- `harness/`：异步派发、poll/cancel 实现
