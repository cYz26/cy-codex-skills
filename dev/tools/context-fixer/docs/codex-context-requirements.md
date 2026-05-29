# Codex Context Auditor 需求总结

> 状态：Context Fixer / Codex Context Lens 开发暂时 pending。本文保留为历史需求参考，之前规划或实现的功能不推荐作为新工作流继续使用；当前 Codex 上下文检查优先使用 DevFlow context-health。

> 版本：v1.0
> 日期：2026-05-21
> 目标平台：macOS + OpenAI Codex / Codex CLI
> 需求定位：面向 Codex 的上下文构成分析、上下文预算治理与优化建议系统

---

## 1. 一句话需求

构建一个面向 **Codex on macOS** 的上下文分析工具或工作流，用于分析每个 Codex session / turn / request 的上下文构成，而不仅仅是 token 总量。它需要识别并拆分 `AGENTS.md`、Skills、MCP tools、历史对话、文件读取、命令输出、diff/patch 等来源，定位上下文膨胀的主要原因，并给出可执行的优化建议。最终目标是建立一套 **Codex Context Budget** 机制，让每次调用尽可能只携带当前任务必要的信息，减少长期 session 的上下文包袱，提高 Codex 输出质量、稳定性和可控性。

建议产品名：

```text
Codex Context Auditor
Codex Context Budget Inspector
Codex Context Lens
```

本文后续统一使用 **Codex Context Lens** 作为方案名。

---

## 2. 背景与问题

在 Codex 驱动的软件开发工作流中，session 往往会持续很长时间，并逐步累积大量上下文，包括：

- 全局与项目级 `AGENTS.md`；
- Skills 元数据与被激活的 `SKILL.md`；
- MCP server / tool schemas；
- 用户与 assistant 历史消息；
- shell command 输出；
- 文件读取内容；
- diff / patch；
- 测试日志、构建日志、搜索结果；
- 多 Agent / subagent 的中间产物。

现有工具多能看到 token 总量、context window 百分比、session 历史或 API trace，但通常无法回答最关键的问题：

```text
当前上下文为什么这么重？
哪些内容是真正必要的？
哪些内容是历史包袱或噪音？
下一步应该优化 AGENTS.md、Skills、MCP，还是命令输出？
```

因此，需求重点不是“监控 token”，而是 **解释上下文构成，并驱动上下文治理**。

---

## 3. 需求边界

| 维度 | 要求 |
|---|---|
| 主要对象 | OpenAI Codex / Codex CLI |
| 目标系统 | macOS 优先，跨平台不是强要求 |
| 核心能力 | session 分析、上下文占用分析、上下文构成归因、优化建议 |
| 数据优先级 | 本地 Codex session JSONL、Codex 配置、AGENTS.md、Skills、MCP、可选 API trace |
| 隐私原则 | Local-first，默认不上传代码、prompt、trace、业务上下文 |
| 输出形态 | CLI 报告优先，后续可扩展本地 dashboard / Codex skill / plugin |
| 目标效果 | 让每次 Codex 调用的上下文包袱尽可能轻，只带当前任务必要信息 |

---

## 4. 用户核心诉求

用户希望看到的不是：

```text
当前 context 使用了 68%
```

而是：

```text
这 68% 里分别是什么？
AGENTS.md 占多少？
MCP tool schema 占多少？
历史对话占多少？
shell output 占多少？
file reads 占多少？
diff / patch 占多少？
哪些是 dead context？
哪些可以移到按需加载？
```

最终希望形成一套判断机制：

```text
什么时候应该 compact？
什么时候应该 fork / new session？
什么时候应该拆 AGENTS.md？
什么时候应该关闭 MCP？
什么时候应该把流程改成 Skill？
什么时候应该限制命令输出？
```

---

## 5. 上下文构成分析对象

### 5.1 Always-on Context

这类内容往往在 session 启动或每轮请求中默认存在，是最需要控制的“基础包袱”。

| 来源 | 关注点 | 优化方向 |
|---|---|---|
| Codex system / internal prompt | 固定内置指令，通常不可控 | 只做观测，不做直接优化 |
| `~/.codex/AGENTS.md` | 是否过长、是否被所有项目继承 | 只保留全局硬规则 |
| project `AGENTS.md` | 是否混入长流程、架构长文、示例代码 | 长流程迁移到 Skills / docs |
| nested `AGENTS.md` | 子目录规则是否层层叠加 | 控制覆盖粒度与重复内容 |
| Skills metadata | skill 数量、description 长度、是否全局过载 | 精简全局 skills，低频按项目启用 |
| MCP tool schemas | 默认启用 MCP 是否过多，tool schema 是否过大 | profile 化、按需启用、tool allowlist |
| Hooks 注入上下文 | hook 是否额外注入大量内容 | 控制 hook 输出大小 |

Codex 官方文档说明，Codex 会在启动时构建 `AGENTS.md` instruction chain，包含全局、项目和子目录层级，并受 `project_doc_max_bytes` 限制；这说明 `AGENTS.md` 是典型的 always-on context，需要纳入预算治理。
参考：https://developers.openai.com/codex/guides/agents-md

### 5.2 Session Growth Context

这类内容随着 session 进行持续增长，通常是 context 膨胀的主要来源。

| 来源 | 典型问题 | 优化方向 |
|---|---|---|
| user messages | 长需求讨论不断累积 | checkpoint / compact |
| assistant messages | 方案探索、解释、长分析累积 | 阶段性总结，避免无限续聊 |
| shell command output | test/build/diff/grep 输出过长 | RTK、tail、failure-only、summary |
| file reads | 反复读取大文件或全量文件 | 片段读取、按需读取 |
| diff / patch | 大规模修改产生长 diff | 大 patch 后 checkpoint |
| MCP results | 外部工具返回大量内容 | 工具返回摘要化、limit 参数 |
| web/search/browser results | 检索结果过多 | 限制查询与结果数量 |
| subagent output | worker 返回过长中间过程 | 只返回结构化摘要与决策 |

---

## 6. 现有工具与需求差距

### 6.1 abtop

`abtop` 能实时监控 Claude Code、Codex CLI、OpenCode session，并显示 token usage、context window %、rate limits、child processes、open ports 等。它适合作为实时预警工具。
参考：https://github.com/graykode/abtop

但它的隐私设计决定了它不展示 prompt text 和 file contents，因此无法做上下文成分分析。它能回答：

```text
这个 session 上下文压力有多大？
```

不能回答：

```text
上下文为什么这么重？
```

### 6.2 Codex Trace

`Codex Trace` 读取 `~/.codex/sessions/` 下的 Codex CLI JSONL session 文件，能浏览 conversation、tool calls、token counts、command output、MCP tools、patches、web searches、image generation events 等。
参考：https://github.com/PixelPaw-Labs/codex-trace

它适合做 session 历史审计，但不一定能完整还原每次 API request 中的 system prompt、tool schemas 和真实 payload 构成。

### 6.3 claude-tap

`claude-tap` 是 local proxy + trace viewer，可以检查真实 API traffic，包括 system prompts、conversation history、tool schemas、tool calls、streaming responses、token usage 和 request diffs，并支持 Codex CLI。
参考：https://github.com/liaohch3/claude-tap

它最接近真实上下文构成分析，但属于高级诊断工具，trace 中可能包含敏感上下文，不适合默认常开。

### 6.4 ccusage

`ccusage` 支持 Codex 数据源，可以读取 `CODEX_HOME` 下的 Codex session JSONL，生成 daily、weekly、monthly、session usage 报表。
参考：https://ccusage.com/guide/codex/

它适合做 token / cost 聚合，但不做上下文来源归因。

### 6.5 RTK

`RTK` 是命令输出压缩工具，面向 AI coding tools 减少 shell command output token 消耗。
参考：https://github.com/rtk-ai/rtk

它不是分析工具，但可作为优化执行层，用于降低 shell output 对上下文的污染。

---

## 7. 功能需求

### FR-1：项目 Baseline Context 分析

扫描当前项目和用户环境，估算 always-on context 成本。

输入：

```text
~/.codex/config.toml
~/.codex/AGENTS.md
~/.codex/AGENTS.override.md
<repo>/AGENTS.md
<repo>/**/AGENTS.md
<repo>/.codex/config.toml
<repo>/.codex/hooks.json
<repo>/.agents/skills/**/SKILL.md
~/.agents/skills/**/SKILL.md
```

输出：

```text
Global AGENTS.md tokens
Project AGENTS.md tokens
Nested AGENTS.md tokens
Skills metadata count / estimated tokens
MCP servers enabled count
MCP schema risk level
Hook injection risk
```

### FR-2：Session JSONL 分析

读取 Codex session JSONL，分析 session 内上下文增长来源。

默认路径：

```text
~/.codex/sessions/**/*.jsonl
```

需要识别：

```text
user message
assistant message
tool call
tool result
bash command
bash output
MCP call
MCP output
apply_patch
file read/write
web search
image generation
token_count
```

### FR-3：Turn-level Delta 分析

分析每一轮调用新增上下文来源，定位 token spike。

示例输出：

```text
Turn 17:
+18,200 tokens from pnpm test output
+6,700 tokens from git diff
+2,900 tokens from assistant explanation
```

### FR-4：Request-level Payload 分析

可选导入 `claude-tap` trace，实现更精确的真实请求构成分析。

需要拆分：

```text
system prompt
messages
tools schema
tool results
streaming responses
token usage
adjacent request diff
```

### FR-5：Top Offenders 排序

输出最主要的上下文包袱来源。

示例：

```text
1. pnpm test full output: 18,400 tokens
2. context7 MCP schema: 8,900 tokens
3. repeated git diff: 7,300 tokens
4. project AGENTS.md workflow section: 3,800 tokens
```

### FR-6：优化建议生成

将分析结果转为可执行建议。

| 发现 | 建议 |
|---|---|
| AGENTS.md 过长 | 将长流程迁移到 Skills |
| MCP schema 过大 | 默认关闭 MCP，使用 profile 按需启用 |
| shell output 过大 | 使用 RTK / tail / failure-only |
| file reads 过大 | 使用范围读取和目录索引 |
| diff 重复出现 | 使用 `git diff --stat` 或限定文件 |
| dead context 高 | checkpoint + compact / fork / new session |

### FR-7：报告生成

支持输出：

```text
Markdown
JSON
可选 HTML dashboard
```

### FR-8：Codex Workflow 集成

支持作为：

```text
CLI 工具
Codex Skill
Codex Plugin
Codex Hooks 辅助采集器
```

---

## 8. 非功能需求

| 类型 | 要求 |
|---|---|
| 隐私 | 默认本地运行，不上传 session、代码、prompt、trace |
| 安全 | trace 文件标记敏感，不默认分享 |
| 兼容性 | 优先支持 macOS + Codex CLI |
| 可解释性 | 所有 token 归因必须能追溯到具体文件、turn、tool call 或 trace request |
| 可渐进实现 | 先估算，再通过 trace 增强精确度 |
| 低侵入 | MVP 不改变 Codex 行为，只做离线分析 |
| 可扩展 | 后续支持 hooks、dashboard、profile 建议、自动治理 |

---

## 9. 关键指标

### 9.1 Baseline 指标

```text
baseline_context_tokens
agents_tokens
skills_metadata_tokens
mcp_schema_tokens
hooks_context_tokens
```

### 9.2 Session 指标

```text
session_total_tokens
session_growth_rate
tokens_per_turn
largest_turn_delta
bash_output_tokens
file_read_tokens
patch_tokens
mcp_result_tokens
```

### 9.3 健康阈值建议

| 指标 | 建议阈值 | 处理建议 |
|---|---:|---|
| baseline context | > 20k tokens | 检查 AGENTS / MCP / skills |
| context window usage | > 60% | 开始关注 |
| context window usage | > 75% | 准备 checkpoint / compact |
| context window usage | > 85% | 强制 compact / fork / new session |
| shell output 占比 | > 20% | 命令输出限流 |
| MCP/tool schema 占比 | > 15% | profile 化或关闭低频 MCP |
| AGENTS.md 占比 | > 10% | 拆分到 Skills / docs |

---

## 10. 理想报告样例

```text
Codex Context Composition Report

Project:
- path: ~/projects/my-app
- sessions analyzed: 42
- current risk: High

Baseline Context:
- global AGENTS.md: 1,120 tokens
- project AGENTS.md: 6,800 tokens
- skill metadata: 1,700 tokens
- MCP schemas: 11,400 tokens

Session Growth:
- user messages: 8,000 tokens
- assistant messages: 12,000 tokens
- bash output: 38,000 tokens
- file reads: 19,000 tokens
- patches/diffs: 13,000 tokens

Top Offenders:
1. pnpm test full output: 18,400 tokens
2. context7 MCP schema: 8,900 tokens
3. repeated git diff: 7,300 tokens
4. AGENTS.md workflow section: 3,600 tokens

Recommendations:
- Move long workflow sections from AGENTS.md into Skills.
- Disable context7 in default profile; enable it only in research profile.
- Use RTK or tail/failure-only output for test and diff commands.
- Create checkpoint and compact after the current implementation phase.
```

---

## 11. 成功标准

MVP 成功标准：

- 能扫描当前项目的 `AGENTS.md`、Skills、MCP 配置；
- 能读取并解析 Codex session JSONL；
- 能按来源估算 token；
- 能输出 session top offenders；
- 能生成 Markdown 报告；
- 能给出至少 5 类可执行优化建议；
- 不依赖外部服务，不上传敏感数据。

完整版本成功标准：

- 支持导入 `claude-tap` trace 做 request-level 精确分析；
- 支持 Codex hooks 采集工具调用与输出大小；
- 支持 dashboard 展示 baseline、timeline、offenders、recommendations；
- 支持生成 profile / AGENTS / Skills / MCP 优化建议；
- 可作为 Codex Skill / Plugin 被 Codex 调用。

---

## 12. 参考资料

- OpenAI Codex AGENTS.md 文档：https://developers.openai.com/codex/guides/agents-md
- OpenAI Codex Skills 文档：https://developers.openai.com/codex/skills
- OpenAI Codex MCP 文档：https://developers.openai.com/codex/mcp
- OpenAI Codex Hooks 文档：https://developers.openai.com/codex/hooks
- OpenAI Codex Advanced Configuration / OTel：https://developers.openai.com/codex/config-advanced
- abtop：https://github.com/graykode/abtop
- Codex Trace：https://github.com/PixelPaw-Labs/codex-trace
- claude-tap：https://github.com/liaohch3/claude-tap
- ccusage Codex guide：https://ccusage.com/guide/codex/
- RTK：https://github.com/rtk-ai/rtk
