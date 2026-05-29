# Codex Context Lens 技术方案

> 状态：Context Fixer / Codex Context Lens 开发暂时 pending。本文保留为历史技术方案参考，之前规划或实现的功能不推荐作为新工作流继续使用；当前 Codex 上下文检查优先使用 DevFlow context-health。

> 版本：v1.0
> 日期：2026-05-21
> 目标平台：macOS + OpenAI Codex / Codex CLI
> 方案定位：组合现有工具 + 自研上下文归因引擎，构建本地优先的 Codex 上下文预算分析系统

---

## 1. 总体结论

现有工具各自覆盖了 Codex 上下文治理的一部分能力，但没有一个工具完整满足“上下文构成归因 + 优化建议”的闭环需求。

推荐方案：

```text
abtop                实时发现 context 压力
Codex Trace          复盘 Codex session JSONL 历史
ccusage              统计 token / cost / session usage
claude-tap           精确分析真实 API request payload
RTK                  降低 shell command output 噪音
codex-context 自研   负责上下文归因、预算分析、优化建议
```

最终构建一个本地优先工具：

```text
Codex Context Lens
```

它的核心职责不是重新实现 `abtop` 或 `Codex Trace`，而是补齐现有工具缺失的部分：

```text
多源数据采集
  ↓
上下文来源归因
  ↓
预算与健康度分析
  ↓
top offenders 排序
  ↓
优化建议生成
  ↓
沉淀成 AGENTS / Skills / MCP / hooks / profile 治理策略
```

---

## 2. 市面方案调研与角色分工

| 工具 / 能力 | 可复用点 | 不足 | 在本方案中的角色 |
|---|---|---|---|
| abtop | 实时显示 Codex session、token usage、context window %、rate limits、进程、端口 | 不显示 prompt text / file content，无法分析上下文构成 | Live Context Pressure Monitor |
| Codex Trace | 读取 `~/.codex/sessions/` JSONL，展示 conversation、tool calls、token counts、command output、MCP tools、patches 等 | 不完整还原真实 request payload / system prompt / tool schemas | Session History Analyzer |
| ccusage | 读取 Codex session JSONL，生成 daily / weekly / monthly / session usage 报表 | 不做上下文来源归因 | Usage / Cost Aggregator |
| claude-tap | local proxy + trace viewer，可看 system prompts、messages、tool schemas、tool calls、token usage、request diffs | trace 敏感，不适合默认常开 | Request Payload Microscope |
| RTK | 压缩 shell command output，降低 token 污染 | 不是分析工具 | Shell Output Noise Reducer |
| Codex Hooks | 可在 PreToolUse / PostToolUse / Stop 等阶段运行脚本 | 需要用户信任与配置；MVP 不宜过度依赖 | Online Collector / Governance Hook |
| Codex OTel | 可导出 API requests、tool usage、prompt length、token events 等 observability 数据 | 更偏组织级观测，不直接做 context composition | 可选 Observability Adapter |

关键依据：

- `abtop` README 说明它能监控 Claude Code、Codex CLI、OpenCode 的 token usage、context window %、rate limits、child processes、open ports，并且不展示 file contents 和 prompt text。参考：https://github.com/graykode/abtop
- `Codex Trace` 说明其读取 `~/.codex/sessions/`，并展示 Codex CLI conversations、tool calls、token counts、MCP tools、patches、web searches 等。参考：https://github.com/PixelPaw-Labs/codex-trace
- `claude-tap` 说明它可以检查真实 API traffic，包括 system prompts、conversation history、tool schemas、tool calls、streaming responses、token usage 和 request diffs，并支持 Codex CLI。参考：https://github.com/liaohch3/claude-tap
- `ccusage` Codex data source 说明其读取 `CODEX_HOME` 下的 Codex session JSONL。参考：https://ccusage.com/guide/codex/
- Codex Hooks 官方文档说明 Hooks 可用于 logging / analytics、prompt scanning、conversation summarization、validation checks，并支持 PreToolUse、PostToolUse、UserPromptSubmit、Stop 等事件。参考：https://developers.openai.com/codex/hooks
- Codex Advanced Configuration 文档说明 OTel 可导出 API requests、SSE/events、prompts、tool approvals/results 等事件。参考：https://developers.openai.com/codex/config-advanced

---

## 3. 设计目标

### 3.1 核心目标

构建一个能回答以下问题的系统：

```text
当前 Codex session 为什么上下文这么重？
baseline context 里有哪些 always-on 包袱？
哪些 turn 造成 context spike？
哪些 tool / command / file / MCP 是 top offenders？
AGENTS.md、Skills、MCP、shell output 应该如何优化？
是否应该 compact / fork / new session？
```

### 3.2 非目标

MVP 阶段不做：

```text
不替代 Codex Trace 的完整 session viewer
不替代 abtop 的实时 TUI
不默认代理所有 Codex 请求
不默认上传任何数据到远端服务
不自动修改用户项目配置
```

---

## 4. 总体架构

```text
┌────────────────────────────────────────────┐
│              Codex Context Lens             │
├────────────────────────────────────────────┤
│  1. Data Collectors                         │
│     - Codex session JSONL importer          │
│     - Config / AGENTS / Skills scanner      │
│     - MCP scanner                           │
│     - claude-tap trace importer             │
│     - Codex hooks collector                 │
│     - optional ccusage / OTel adapter       │
│                                            │
│  2. Context Attribution Engine              │
│     - source classifier                     │
│     - token estimator                       │
│     - duplicate detector                    │
│     - dead context detector                 │
│     - per-turn delta calculator             │
│                                            │
│  3. Budget & Optimization Engine            │
│     - baseline budget                       │
│     - session growth budget                 │
│     - top offenders ranking                 │
│     - health score                          │
│     - optimization recommender              │
│                                            │
│  4. Interfaces                              │
│     - CLI report                            │
│     - Markdown / JSON export                │
│     - local dashboard                       │
│     - Codex skill / plugin                  │
│                                            │
│  5. External Helpers                        │
│     - abtop                                 │
│     - Codex Trace                           │
│     - ccusage                               │
│     - claude-tap                            │
│     - RTK                                   │
└────────────────────────────────────────────┘
```

---

## 5. 数据源设计

## 5.1 Static Baseline Scanner

负责扫描 session 启动时可能进入上下文的 always-on 内容。

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

输出示例：

```json
{
  "baseline": {
    "global_agents": {
      "path": "~/.codex/AGENTS.md",
      "bytes": 4200,
      "estimated_tokens": 1100
    },
    "project_agents": [
      {
        "path": "./AGENTS.md",
        "bytes": 14800,
        "estimated_tokens": 3900
      }
    ],
    "skills_index": {
      "count": 42,
      "estimated_tokens": 1800,
      "over_budget": false
    },
    "mcp_servers": [
      {
        "name": "context7",
        "enabled": true,
        "enabled_tools": null,
        "schema_tokens": "unknown_without_trace"
      }
    ]
  }
}
```

设计依据：

- Codex `AGENTS.md` 会从全局、项目根目录、当前工作目录路径逐层合并；默认 `project_doc_max_bytes` 为 32 KiB。参考：https://developers.openai.com/codex/guides/agents-md
- Codex Skills 使用 progressive disclosure：初始只放 skill name、description、path，完整 `SKILL.md` 仅在触发后加载；初始 skills list 有预算限制。参考：https://developers.openai.com/codex/skills
- Codex MCP 支持 `enabled=false`、`enabled_tools`、`disabled_tools` 等配置，可用于精简工具面。参考：https://developers.openai.com/codex/mcp

---

## 5.2 Session JSONL Importer

负责读取：

```text
~/.codex/sessions/**/*.jsonl
```

解析对象：

```text
session metadata
turn id
timestamp
user message
assistant message
tool call
tool result
bash command
command output
MCP call
MCP output
apply_patch
file read/write
web search
image generation
token_count
model_context_window
```

统一事件模型：

```ts
type ContextEvent = {
  sessionId: string;
  turnId?: string;
  timestamp: string;
  sourceType:
    | "user_message"
    | "assistant_message"
    | "tool_call"
    | "tool_output"
    | "bash_command"
    | "bash_output"
    | "mcp_call"
    | "mcp_output"
    | "patch"
    | "file_read"
    | "web_search"
    | "image_generation"
    | "token_count";
  rawSizeBytes: number;
  estimatedTokens: number;
  hash: string;
  path?: string;
  command?: string;
  mcpServer?: string;
  mcpTool?: string;
};
```

---

## 5.3 claude-tap Trace Importer

导入 `claude-tap` 生成的 JSONL trace，实现 request-level 精确分析。

重点解析：

```text
request.system
request.messages
request.tools
request.tool_choice
response.usage
streaming chunks
request diff
```

输出示例：

```json
{
  "request_id": "req_xxx",
  "turn_id": "turn_xxx",
  "composition": {
    "system_prompt": 18200,
    "messages": 92000,
    "tools_schema": 28400,
    "tool_results": 41000,
    "total_input_tokens": 181000
  }
}
```

这是从“估算版上下文构成”升级到“精确 request payload 构成”的关键模块。

---

## 5.4 Hook Collector

Codex Hooks 可作为在线采集器，尤其适合记录 Bash / MCP / apply_patch 输出大小。

建议先只记录，不改变行为。

示例 `config.toml`：

```toml
[[hooks.PostToolUse]]
matcher = "^Bash$"

[[hooks.PostToolUse.hooks]]
type = "command"
command = "/usr/local/bin/codex-context-hook post-tool-use"
timeout = 30
statusMessage = "Recording context audit event"
```

采集字段：

```text
tool_name
tool_input.command
tool_response_size
exit_code
output_hash
estimated_tokens
session_id
turn_id
cwd
```

Hooks 官方支持 PreToolUse、PostToolUse、UserPromptSubmit、Stop 等事件，适合做 deterministic script 集成。参考：https://developers.openai.com/codex/hooks

---

## 6. 核心归因模型

### 6.1 Context Source Taxonomy

```ts
type ContextSourceType =
  | "system_internal"
  | "global_agents"
  | "project_agents"
  | "nested_agents"
  | "skill_metadata"
  | "skill_body"
  | "mcp_schema"
  | "user_history"
  | "assistant_history"
  | "tool_call_args"
  | "tool_result"
  | "bash_output"
  | "file_content"
  | "patch_diff"
  | "web_result"
  | "image_result"
  | "dead_context";
```

### 6.2 Token Estimation Strategy

MVP 可以采用两层策略：

```text
Level 1：估算 token
- 按 tokenizer 或字符长度估算
- 适合 AGENTS.md、Skills、session JSONL、shell output

Level 2：精确 token
- 从 Codex token_count event 或 claude-tap response.usage 获取
- 适合 request-level payload 分析
```

### 6.3 Accuracy Model

| 分析层级 | 精度 | 数据来源 |
|---|---|---|
| Estimated Composition | 中 | 文件扫描 + session JSONL |
| Request Payload Composition | 高 | claude-tap trace |
| Official Internal Composition | 最高 | 需要 Codex 官方支持，目前不可得 |

MVP 应先实现 **估算版 + 可解释归因**，再通过 trace importer 增强精确度。

---

## 7. Budget Analyzer 设计

### 7.1 Baseline Budget

目标：分析空 session / session 启动阶段已经背了多少内容。

包含：

```text
AGENTS.md
skills metadata
MCP config / tool schema
hooks injected context
model instructions
```

输出：

```text
Baseline Context: 21,400 estimated tokens
- Global AGENTS.md: 1,120
- Project AGENTS.md: 6,800
- Skill metadata: 1,700
- MCP schemas: 11,400
- Hooks context: 900
```

### 7.2 Session Growth Budget

目标：分析 session 过程中哪些来源让上下文变重。

包含：

```text
history messages
tool outputs
file reads
patches
test logs
MCP results
```

输出：

```text
Session Growth:
- Bash output: 38,000 tokens
- File reads: 19,000 tokens
- Patches: 13,000 tokens
- Assistant history: 12,000 tokens
- User history: 8,000 tokens
```

### 7.3 Per-turn Delta

目标：定位上下文突增点。

输出：

```text
Turn 17: +31,000 tokens
- pnpm test output: +18,200
- git diff output: +6,700
- assistant explanation: +2,900
- file read: +3,200
```

### 7.4 Top Offenders

输出：

```text
1. pnpm test full output       18,200 tokens
2. context7 MCP tools schema   12,400 tokens
3. repeated git diff            8,700 tokens
4. project AGENTS.md            5,600 tokens
5. stale design discussion      4,900 tokens
```

---

## 8. Optimization Engine 设计

把诊断结果转成具体优化建议。

| 发现 | 建议 |
|---|---|
| `AGENTS.md` > 8k tokens | 拆分：硬规则留在 `AGENTS.md`，长流程迁移到 Skills |
| Skills 数量过多 | 精简全局 skills，只保留高频；项目相关 skills 放 repo 内 |
| MCP schema 占比高 | 默认关闭重 MCP，用 profile 按需启用 |
| Bash output 占比高 | 引入 RTK，或改用 `tail` / `--reporter` / failure-only |
| `git diff` 重复出现 | 使用 `git diff --stat` 或限定文件范围 |
| test output 过长 | 使用 failure-only / tail / compact reporter |
| dead context 高 | checkpoint + compact / fork / new session |
| per-turn delta 异常 | 标记具体 turn、command、tool call |
| compact 后仍重 | baseline 层过大，优先治理 AGENTS / MCP / skills |

---

## 9. CLI 设计

建议先实现 CLI，后实现 dashboard。

```bash
# 扫描当前项目 baseline
codex-context audit --project .

# 分析所有 Codex sessions，列出最重的
codex-context sessions --top 20

# 分析某个 session
codex-context inspect ~/.codex/sessions/2026/05/21/rollout-xxx.jsonl

# 导入 claude-tap trace，做 request-level 分析
codex-context trace import ./traces/codex-run.jsonl

# 生成优化建议
codex-context recommend --project .

# 输出 Markdown 报告
codex-context report --project . --format markdown > context-report.md

# 输出 JSON 给 dashboard
codex-context audit --project . --json > context-report.json

# 检查配置健康度
codex-context doctor
```

---

## 10. Dashboard 设计

Dashboard 后置实现，可基于 CLI JSON 输出构建。

### 10.1 Overview

```text
Current Project Context Health

Baseline Context: 21,400 estimated tokens
Average Session Growth: 8,200 tokens / turn
Top Risk: MCP schema + shell output
Recommended Action: Disable context7 in default profile
```

### 10.2 Baseline Composition

展示：

```text
Global AGENTS.md
Project AGENTS.md
Nested AGENTS.md
Skill metadata
MCP schemas
Hooks injected context
```

### 10.3 Session Timeline

展示每个 turn 的上下文增量：

```text
Turn 1   +2,100
Turn 2   +4,500
Turn 3   +31,000  ← spike
Turn 4   +3,200
```

### 10.4 Top Offenders

```text
Type            Source                Tokens       Action
bash_output     pnpm test              18,200       use tail / reporter
mcp_schema      context7               12,400       move to research profile
agents          ./AGENTS.md             5,600       split to skills
patch_diff      large refactor diff     4,900       checkpoint after patch
```

### 10.5 Recommendations

```text
[High] Disable context7 in default profile
[High] Move project workflow section from AGENTS.md to skill
[Medium] Add RTK wrapper for test/diff commands
[Medium] Create checkpoint after implementation phase
```

---

## 11. Codex 配置治理建议

### 11.1 Profile 分层

Codex Advanced Configuration 支持 profiles，并支持 `codex --profile <name>` 切换；也支持 `--config` dot notation 覆盖嵌套值，例如 `mcp_servers.context7.enabled=false`。参考：https://developers.openai.com/codex/config-advanced

建议配置：

```toml
[profiles.light]
model = "gpt-5.5"

[profiles.research]
model = "gpt-5.5"
mcp_servers.context7.enabled = true

[profiles.design]
model = "gpt-5.5"
mcp_servers.figma.enabled = true

[profiles.deep-review]
model = "gpt-5.5"
model_reasoning_effort = "high"
```

默认使用：

```bash
codex --profile light
```

需要文档检索时：

```bash
codex --profile research
```

### 11.2 AGENTS.md 瘦身规则

`AGENTS.md` 只保留：

```text
项目硬规则
核心命令
目录导航
不可违反的约束
```

移出：

```text
长流程
低频 SOP
架构长文
示例代码
历史决策
模板
```

迁移目标：

```text
.agents/skills/*
docs/decisions/*
docs/architecture/*
```

### 11.3 Skills 设计规则

Codex Skills 使用 progressive disclosure：初始上下文只包含 skill name、description、path，完整 `SKILL.md` 在触发后加载。参考：https://developers.openai.com/codex/skills

建议：

```text
全局 skills：只保留高频通用能力
项目 skills：只放当前项目相关能力
实验 skills：不要默认启用
低频 skills：保留在仓库，但 disabled
```

### 11.4 MCP 治理规则

Codex MCP 配置支持 `enabled=false`、`enabled_tools`、`disabled_tools` 和 per-tool approval mode。参考：https://developers.openai.com/codex/mcp

建议：

```text
默认 profile 不启用重 MCP
research / design / github profile 按需启用
优先使用 enabled_tools allowlist
对高风险或高输出工具设置 approval_mode = prompt
```

---

## 12. Hooks 集成方案

### 12.1 旁路审计 Hook

只记录，不改变 Codex 行为。

```toml
[[hooks.PostToolUse]]
matcher = "^Bash$"

[[hooks.PostToolUse.hooks]]
type = "command"
command = "/usr/local/bin/codex-context-hook post-tool-use"
timeout = 30
statusMessage = "Recording context audit event"
```

### 12.2 命令输出治理 Hook

第二阶段再做可选治理：

```text
如果 Bash 输出超过阈值：
  - 保留错误摘要
  - 保留最后 N 行
  - 保留 failed tests
  - 丢弃重复 warning
  - 输出 compact result 给 Codex
```

注意：MVP 不应过度依赖 hook 改写行为，优先做离线分析和建议。

---

## 13. 技术选型

建议 MVP 使用：

| 模块 | 技术 |
|---|---|
| CLI | TypeScript / Node.js |
| JSONL parser | Node streams |
| TOML parser | `@iarna/toml` 或同类库 |
| token estimate | tokenizer 库或字符估算 |
| local DB | SQLite |
| report | Markdown + JSON |
| dashboard | React + Vite，后置 |
| desktop app | Tauri，后置 |
| hooks | Node 或 Python 单文件脚本 |
| trace import | claude-tap JSONL adapter |

选择 TypeScript 的原因：

```text
数据解析和报告生成开发效率高
方便与 React dashboard 共用类型
Codex session JSONL / config / report 处理不需要 Rust 起步
后续性能瓶颈再把 collector / parser 局部 Rust 化
```

---

## 14. 数据库草案

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  started_at TEXT,
  last_activity_at TEXT,
  project_path TEXT,
  model TEXT
);

CREATE TABLE context_events (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  turn_id TEXT,
  timestamp TEXT,
  source_type TEXT NOT NULL,
  raw_size_bytes INTEGER,
  estimated_tokens INTEGER,
  hash TEXT,
  path TEXT,
  command TEXT,
  mcp_server TEXT,
  mcp_tool TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE baseline_items (
  id TEXT PRIMARY KEY,
  project_path TEXT,
  source_type TEXT NOT NULL,
  path TEXT,
  raw_size_bytes INTEGER,
  estimated_tokens INTEGER,
  hash TEXT
);

CREATE TABLE recommendations (
  id TEXT PRIMARY KEY,
  project_path TEXT,
  severity TEXT,
  category TEXT,
  title TEXT,
  detail TEXT,
  evidence_json TEXT,
  created_at TEXT
);
```

---

## 15. 报告样例

```md
# Codex Context Report

## Summary

- Project: my-app
- Sessions analyzed: 42
- Current risk: High
- Main offenders:
  1. Bash output
  2. MCP schema
  3. Project AGENTS.md
  4. Repeated diffs

## Baseline Context

| Source | Tokens | Ratio | Action |
|---|---:|---:|---|
| Global AGENTS.md | 1,120 | 5% | OK |
| Project AGENTS.md | 6,800 | 31% | Split to skills |
| Skill metadata | 1,700 | 8% | Review low-frequency skills |
| MCP schemas | 11,400 | 52% | Move to profiles |
| Hooks context | 900 | 4% | OK |

## Session Growth

| Source | Tokens | Ratio | Action |
|---|---:|---:|---|
| Bash output | 38,000 | 42% | Use RTK / tail |
| File reads | 19,000 | 21% | Read narrower ranges |
| Patches | 13,000 | 14% | Checkpoint after large patch |
| Assistant history | 12,000 | 13% | Compact |
| User history | 8,000 | 9% | Compact |

## Top Offenders

1. `pnpm test` full output: 18,400 tokens
2. `git diff` repeated 4 times: 9,200 tokens
3. `context7` MCP schema: 8,900 tokens
4. `AGENTS.md` workflow section: 3,600 tokens

## Recommendations

- Move long workflow sections from AGENTS.md into Skills.
- Disable context7 in default profile; enable it only in research profile.
- Add RTK or command-output hook for test/diff commands.
- Create checkpoint and compact after the current implementation phase.
- Replace repeated `git diff` with `git diff --stat` unless full diff is required.
```

---

## 16. 实施路线图

### Phase 0：手工组合验证，1–2 天

目标：确认数据源可用。

动作：

```bash
abtop
codex-trace
bunx ccusage codex session --json
claude-tap --tap-client codex
```

验证：

```text
Codex session JSONL 字段结构
token_count / model_context_window 是否稳定
claude-tap trace 是否能拿到 tools/messages
AGENTS.md / skills / MCP 扫描路径
```

### Phase 1：Offline CLI MVP，3–5 天

实现：

```text
codex-context audit
codex-context sessions
codex-context inspect
codex-context report
```

能力：

```text
扫描 AGENTS.md
扫描 Skills metadata
扫描 MCP config
读取 Codex JSONL
按 source type 归类
输出 top offenders
输出 Markdown 报告
```

### Phase 2：Trace Importer，2–3 天

实现：

```text
codex-context trace import <claude-tap-jsonl>
```

能力：

```text
解析 request messages
解析 tools schema
比较 adjacent request diff
输出 request-level context composition
```

### Phase 3：Codex Hook Collector，3–5 天

实现：

```text
PostToolUse audit hook
PreToolUse command risk hook
Stop checkpoint reminder hook
```

能力：

```text
实时记录 tool output
识别大输出命令
在 Stop 时提示 checkpoint / compact
可选输出 RTK / tail 建议
```

### Phase 4：Local Dashboard，1–2 周

实现：

```text
codex-context dashboard
```

页面：

```text
Overview
Baseline
Sessions
Turn Timeline
Top Offenders
Recommendations
Profiles
```

### Phase 5：Codex Skill / Plugin 化，1 周

打包为：

```text
.agents/skills/context-audit/SKILL.md
.codex-plugin/plugin.json
hooks/hooks.json
bin/codex-context
```

让 Codex 可直接调用：

```text
$context-audit 分析当前项目的上下文包袱，并给出 AGENTS/Skills/MCP 优化建议
```

---

## 17. 风险与应对

| 风险 | 说明 | 应对 |
|---|---|---|
| session JSONL 格式变化 | Codex CLI 版本升级可能改变字段 | 做多版本 parser，保留 raw event |
| token 估算不精确 | tokenizer 与实际模型计数存在偏差 | 标注 estimated，trace 导入时校准 |
| trace 敏感 | claude-tap trace 包含真实 prompt / code | 默认本地，报告脱敏，trace 不自动分享 |
| MCP schema 难以静态获取 | config 只能看到 server，不能直接知道 tool schema | 通过 trace 或 MCP tools/list 获取 |
| Hook 行为不稳定 | 用户可能未信任 hooks 或项目不 trusted | MVP 以离线分析为主 |
| 自动优化有风险 | 自动改 AGENTS/MCP 可能破坏项目流程 | 只生成 patch 建议，不默认应用 |

---

## 18. MVP 验收标准

MVP 必须满足：

- 可以扫描当前项目 baseline context；
- 可以读取 Codex session JSONL；
- 可以按 source type 聚合估算 token；
- 可以列出 top context offenders；
- 可以输出 Markdown 报告；
- 可以给出 AGENTS / Skills / MCP / shell output / compact 相关建议；
- 默认不上传任何数据。

MVP 不要求：

- 不要求实时 dashboard；
- 不要求 hooks 全自动治理；
- 不要求精确拆出 Codex internal system prompt；
- 不要求替代 abtop / Codex Trace；
- 不要求 100% 精确 token 计数。

---

## 19. 最终推荐落地版本

最现实的落地组合：

```text
abtop
+ Codex Trace
+ ccusage
+ claude-tap
+ RTK
+ 自研 codex-context CLI
```

其中：

```text
abtop：实时看到哪个 session 变重
Codex Trace：复盘 session 内发生了什么
ccusage：看长期 token / cost 趋势
claude-tap：必要时看真实 API payload
RTK：减少 shell output 污染
codex-context：做上下文构成归因和优化建议
```

最终形成闭环：

```text
发现 context 压力
  ↓
分析上下文构成
  ↓
定位 top offenders
  ↓
生成优化建议
  ↓
治理 AGENTS / Skills / MCP / shell output
  ↓
checkpoint + compact / new session
```

---

## 20. 参考资料

- OpenAI Codex AGENTS.md 文档：https://developers.openai.com/codex/guides/agents-md
- OpenAI Codex Skills 文档：https://developers.openai.com/codex/skills
- OpenAI Codex MCP 文档：https://developers.openai.com/codex/mcp
- OpenAI Codex Hooks 文档：https://developers.openai.com/codex/hooks
- OpenAI Codex Advanced Configuration / Profiles / OTel：https://developers.openai.com/codex/config-advanced
- abtop：https://github.com/graykode/abtop
- Codex Trace：https://github.com/PixelPaw-Labs/codex-trace
- claude-tap：https://github.com/liaohch3/claude-tap
- ccusage Codex guide：https://ccusage.com/guide/codex/
- RTK：https://github.com/rtk-ai/rtk
- Grafana OpenAI Codex OTel integration：https://grafana.com/docs/grafana-cloud/monitor-infrastructure/integrations/integration-reference/integration-openai-codex/
