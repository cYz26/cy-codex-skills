# Codex Profile Switcher

Codex 双模式切换方案：在官方 OpenAI 订阅模式与 DeepSeek API 模式之间切换。DeepSeek 模式通过本地 CCX 代理接入，方案参考 DeepSeek 的 Codex 接入说明和 CCX 的 Codex compatibility 能力。

- DeepSeek Codex 参考：https://github.com/deepseek-ai/awesome-deepseek-agent/blob/main/docs/codex.md
- CCX 参考：https://github.com/BenedictKing/ccx

## 架构

```text
Codex CLI/App  <->  CCX (127.0.0.1:3688)  <->  DeepSeek API
      |
      +-------- official OpenAI subscription
```

- `CCX`：本地协议转换代理，负责 Codex Responses 请求到 DeepSeek OpenAI Chat 入口的兼容转换。
- `switch-profile.sh`：在 DeepSeek 与官方订阅之间切换；默认同时照顾 CLI profile overlay 和 Desktop App 需要的 base config。

## 目录结构

```text
dev/tools/codex-profile-switch/
├── README.md
├── switch-profile.sh
├── profiles/
│   ├── deepseek/
│   │   ├── config.openai.toml
│   │   ├── models_catalog.json
│   │   └── model.txt
│   └── official/
│       └── model.txt
├── ccx/
│   ├── .env.example
│   └── config.example.json
└── tests/
    └── test_switch_profile.py
```

## 运行时文件

| 文件 | 作用 |
|------|------|
| `~/.codex/config.toml` | Codex 主配置。`deepseek` 会切到 CCX，`official` 会恢复官方快照。 |
| `~/.codex/deepseek.config.toml` | Codex `--profile deepseek` 使用的 DeepSeek overlay。 |
| `~/.codex/profiles/deepseek/models_catalog.json` | DeepSeek/CCX 模型目录，overlay 通过 `model_catalog_json` 指向它。 |
| `~/.codex/profiles/official/config.toml` | 切到 DeepSeek 前保存的官方配置快照。 |
| `~/Dev/agents-dev/ccx/backend-go/.env` | CCX 环境变量。 |
| `~/Dev/agents-dev/ccx/backend-go/.config/config.json` | CCX 渠道配置。 |

## 快速开始

```bash
# 首次配置 CCX 与 DeepSeek profile
dev/tools/codex-profile-switch/switch-profile.sh setup-deepseek

# 如果已经创建快捷方式，后续可以直接用 codex-profile
codex-profile status

# 查看状态
dev/tools/codex-profile-switch/switch-profile.sh status
```

## 命令行快捷方式

推荐把脚本注册成 `codex-profile`：

```bash
mkdir -p ~/.local/bin
ln -sf /Users/cy/Dev/agents-dev/cy-codex-skills/dev/tools/codex-profile-switch/switch-profile.sh ~/.local/bin/codex-profile
```

确认 `~/.local/bin` 在 `PATH` 后，日常直接运行 `codex-profile deepseek` 或 `codex-profile official`。

CCX 代理需要运行在 `127.0.0.1:3688`：

```bash
cd ~/Dev/agents-dev/ccx/backend-go
../dist/ccx-go
```

## 使用方式

### 日常切换

```bash
# 切到 DeepSeek API 模式，CLI/App 都生效
codex-profile deepseek

# 切回官方订阅模式
codex-profile official
```

`deepseek` 会生成 `~/.codex/deepseek.config.toml`，并把 `~/.codex/config.toml` 切到 CCX provider。`official` 会删除生成的 overlay，并在 base config 当前是 CCX 模式时恢复官方快照。

指定 Codex 侧模型别名时，provider 仍固定为 `ccx`：

```bash
codex-profile deepseek gpt-5.5
```

CLI runtime commands 也可以显式使用 profile overlay：

```bash
codex --profile deepseek
```

### 只生成 CLI overlay

如果不想改 `~/.codex/config.toml`，使用 `--cli-only`：

```bash
codex-profile deepseek --cli-only
codex --profile deepseek
```

这种模式只更新 `~/.codex/deepseek.config.toml`，不会修改 base config。当前 Codex CLI 的 `--profile` 不适用于 `codex app`，所以 Desktop App 要走 DeepSeek 时使用默认的 `codex-profile deepseek`。

### 兼容旧命令

`activate-deepseek` 仍保留为兼容入口，但日常不需要再单独运行。默认 `codex-profile deepseek` 已经包含 Desktop App 所需的 base config 激活。

## DeepSeek Codex 配置

生成的 `~/.codex/deepseek.config.toml` 形如：

```toml
model = "ccx"
model_provider = "ccx"
model_context_window = 1000000
model_max_output_tokens = 384000
model_reasoning_effort = "high"
model_catalog_json = "/Users/you/.codex/profiles/deepseek/models_catalog.json"

[model_providers.ccx]
name = "CCX"
base_url = "http://127.0.0.1:3688/v1"
wire_api = "responses"
```

关键点：

- `model_provider` 固定为 `ccx`，这是 Codex 路由到本地 CCX 的 provider id。
- `model` 可以是 `ccx` 或 `gpt-5.5` 等由 CCX `modelMapping` 接收的别名。
- `model_reasoning_effort` 使用当前 Codex catalog 可解析的 `high`。
- `model_catalog_json` 指向运行时 catalog，确保 `ccx` 模型 slug 能被当前 Codex 解析。

## CCX 配置

`ccx/config.example.json` 使用 Responses 渠道转 OpenAI Chat 上游：

| 配置项 | 值 |
|--------|-----|
| `serviceType` | `openai` |
| `baseUrl` | `https://api.deepseek.com` |
| `modelMapping.ccx` | `deepseek-v4-pro` |
| `reasoningParamStyle` | `reasoning_effort` |
| `normalizeNonstandardChatRoles` | `true` |
| `codexToolCompat` | `true` |
| `passbackThinkingBlocks` | `false` |

`passbackThinkingBlocks` 必须保持 `false`，否则可能把 reasoning 内容投影为 `content[].thinking`，导致 DeepSeek OpenAI 入口拒绝请求。

## 验证

```bash
bash -n dev/tools/codex-profile-switch/switch-profile.sh
python3 -m unittest discover -s dev/tools/codex-profile-switch/tests
python3 -m json.tool dev/tools/codex-profile-switch/profiles/deepseek/models_catalog.json >/dev/null
python3 -m json.tool dev/tools/codex-profile-switch/ccx/config.example.json >/dev/null
codex -c 'model_catalog_json="dev/tools/codex-profile-switch/profiles/deepseek/models_catalog.json"' debug models >/dev/null
```

也可以验证已生成的运行时 profile：

```bash
dev/tools/codex-profile-switch/switch-profile.sh deepseek
dev/tools/codex-profile-switch/switch-profile.sh validate
```

## 迁移旧方案

旧方案如果已经把 `~/.codex/config.toml` 改成 CCX 模式，运行：

```bash
dev/tools/codex-profile-switch/switch-profile.sh official
```

如果没有官方快照，使用历史备份恢复：

```bash
dev/tools/codex-profile-switch/switch-profile.sh restore ~/.codex/config.toml.bak-<timestamp>-before-official
```

## 常见问题

### `codex --profile deepseek app` 可以用吗？

当前不可以。`--profile` 只适用于 Codex runtime commands，例如 `codex`、`codex exec`、`codex review`。Desktop App 使用默认的 `codex-profile deepseek` 切换 base config。

### 为什么还有 `--cli-only`？

这是给只想临时运行 `codex --profile deepseek`、不希望影响 Desktop App 或默认 `codex` 启动的场景。日常切换使用 `codex-profile deepseek` 和 `codex-profile official`。

### 切回官方后还有 CCX 在运行怎么办？

CCX 进程可以继续运行，不会影响官方订阅模式。官方模式是否使用 DeepSeek 由 Codex config 决定，不由 CCX 是否运行决定。
