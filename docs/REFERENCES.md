# 参考资料（References）

> 约定：研究或借鉴的外部文章/论文，发现后把引用登记在本文件，按主题分组。
> 完整抓取的译文/原文存在 collections 仓（/home/wanger/codes/collections/0.raw/），这里只放索引与"对框架的启发"。

## 执行前确认（ReviewGate / pre-execution review）

- **show-me-you-want（/smyw）** — Box @ Monad Foundation, 2026-11-10
  - 推文：https://x.com/BoxMrChen/status/2120142200776565085
  - 仓库：https://github.com/nishuzumi/show-me-you-want-skill
  - 存档：collections 0.raw/x/2026-11-10-show-me-you-want-skill.md
  - **启发**：`core/review.py` 的 ReviewGate——在工具执行前把计划（工具+参数）可视化/交给 reviewer 审查，deny 反馈喂回模型修正，替代"改完再返工"。

## Agent 通用架构

- **Building Effective Agents** — Anthropic, 2024
  - https://www.anthropic.com/research/building-effective-agents
  - **启发**：Agent vs workflow 的边界；工具调用与编排的最小组合原则（本框架的 AgentLoop 保持单层循环、扩展点外挂的思路与此一致）。

- **Effective Harnesses for Long-Running Agents** — Anthropic
  - https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - **启发**：跨上下文窗口的长期任务靠进度文件 + Git 历史 + 明确交接；对应本框架 memory/ 层与 context.py 的职责划分方向。

## 记忆与上下文管理（memory/ 层的扩展方向）

- **MemGPT: Towards LLMs as Operating Systems** — Packer et al., UC Berkeley, 2023
  - https://arxiv.org/abs/2310.08560
  - **启发**：OS 式分层内存管理；窗口是 RAM、记忆在窗口外分页换入换出。memory/base.py 的接口设计可向 MemGPT 的 main/external context 收敛。

- **Agentic Memory, Context Management and Retrieval Systems** — Aman (@beingamanFF), 2026-11-11
  - 推文：https://x.com/beingamanFF/status/2120166577530376642
  - 存档：collections 0.raw/x/2026-11-11-agentic-memory-context-retrieval-notes.md
  - **启发**：上下文失败四模式（poisoning/distraction/confusion/clash）→ 记忆需要 update/delete 语义；write/select/compress/isolate 四动作可作为 memory/ 层接口的分类参照。

- **Generative Agents** — Park et al., Stanford, 2023
  - https://arxiv.org/abs/2304.03442
  - **启发**：记忆 + 反思 + 规划的行为循环；"反思"对应本框架可扩展的 dreaming/整理 pass。

## 个性化 Agent（长期方向）

- **Toward Personalized LLM-Powered Agents** — 2026 综述
  - https://arxiv.org/abs/2602.22680
  - **启发**：个性化 Agent 四组件——用户画像、长期记忆、任务规划、实际执行；可作为 Config/装配层的长期演进检查表。
