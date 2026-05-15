# Codex First 2D 游戏美术生成方案文档集

整理日期：2026-05-15

本文档集用于指导一个以 **Codex 为主控 Agent** 的 2D 游戏美术资产生成系统，目标引擎为：

- **Godot 4.x**：主生产引擎，适合中长期项目、TileMap、场景编辑、角色骨骼 / Cutout、调试预览。
- **Web 2D 引擎**：优先 **Phaser**，兼容 **PixiJS**，适合 Web 平台、快速原型、轻量部署和可视化回归。

## 文档目录

| 文件 | 内容 |
|---|---|
| `01_总体方案_架构与原则.md` | 整体架构、目标范围、核心原则、引擎定位 |
| `02_Codex多角色与Subagents实现.md` | 多角色如何在 Codex 中实现，哪些用 AGENTS.md、Skills、Scripts、Hooks、Subagents |
| `03_Skills仓库结构与模板.md` | 推荐仓库结构、Skills 列表、SKILL.md 模板、AGENTS.md 示例 |
| `04_2D资产生成管线.md` | 角色、敌人、VFX、地图、Tile、UI、Icon 的资产生成管线 |
| `05_Godot适配与导出规范.md` | Godot 资源导出、场景结构、AnimatedSprite2D / SpriteFrames / TileMapLayer 适配 |
| `06_Web引擎适配与导出规范.md` | Phaser / PixiJS 导出规范、loader、atlas、animation、preview scene |
| `07_QA验收与DebugProtocol.md` | 资产 QA、视觉回归、引擎 smoke test、失败签名库、Debug Protocol |
| `08_实施路线图与MVP.md` | Phase 0–4 路线图、最小可执行版本、验收标准 |
| `09_参考来源与调研依据.md` | 参考项目、文档、论文与引擎资料 |
| `Codex_First_2D_Game_Art_Pipeline_All_in_One.md` | 上述内容合并版，便于一次性阅读 |

## 一句话方案

> 不要把 AI 美术生成设计成“一句话直接出最终资产”。更可靠的方式是把它工程化：**Codex 负责规划和编排，图像模型负责原始视觉，本地脚本负责确定性处理，QA 负责阻断错误，Godot / Phaser / PixiJS 负责最终落地验证。**

## 推荐最小实现

```text
AGENTS.md
.agents/skills/
  art-bible/
  asset-spec/
  generate-sprite-raw/
  postprocess-sprite/
  qa-visual/
  export-godot/
  export-phaser/

tools/
  image/
  godot/
  web/

hooks/
  validate_spec.py
  check_frame_count.py
  check_alpha.py
  check_bbox_drift.py
  engine_smoke_test.sh
```

## 推荐最小资产验证集

```text
1 个主角 idle / run
1 个敌人 idle / walk
1 个 projectile
1 个 impact
1 个 prop pack
1 个小地图
1 个 Godot preview scene
1 个 Phaser preview scene
1 套 QA report
```


---

# 01. 总体方案：Codex First 2D 游戏美术生成架构与原则

## 1. 核心定位

本方案的目标不是让 AI 一次性生成完整、最终、生产级游戏美术包，而是建立一条可以持续迭代的资产工程流水线：

```text
Codex Orchestrator
  ↓
Art Bible / Asset Spec
  ↓
AI 原始图像生成
  ↓
确定性后处理
  ↓
QA / Visual Regression / Engine Smoke Test
  ↓
Godot / Phaser / PixiJS Handoff
```

核心定义：

> **Codex 是 2D 游戏美术资产生产的控制平面；图像模型是原始视觉生成器；本地脚本是确定性处理器；引擎运行结果是最终验收标准。**

---

## 2. 目标引擎

### 2.1 Godot 4.x

Godot 作为主生产引擎，重点适配：

- `AnimatedSprite2D`
- `SpriteFrames`
- `AnimationPlayer`
- `TileMapLayer`
- `Area2D`
- `StaticBody2D`
- `Sprite2D`
- `Skeleton2D`
- Cutout / bone-like 角色管线
- Preview scene / debug scene

适合：

| 场景 | 说明 |
|---|---|
| 中长期独立游戏项目 | 需要编辑器、场景树、调试、资源管理 |
| 俯视角 RPG / ARPG | TileMap、Area2D、StaticBody2D 适合地图和交互 |
| 横版动作游戏 | AnimatedSprite2D / AnimationPlayer / Cutout 都可用 |
| 生产级角色动画 | 可逐步走向骨骼 / Cutout / 手工修正 |

### 2.2 Web 2D 引擎

Web 平台优先适配：

| 引擎 | 定位 |
|---|---|
| **Phaser** | 首选 Web 游戏框架，适合玩法、资源加载、动画、TileMap、输入、物理 |
| **PixiJS** | 偏底层 2D 渲染库，适合轻量互动、嵌入式游戏、高性能视觉层 |
| **Godot Web Export** | 可作为补充，但不是本方案的首选轻量 Web 路线 |

---

## 3. 支持的游戏类型

| 游戏类型 | 适配度 | 说明 |
|---|---:|---|
| 横版动作 / 平台跳跃 | 高 | sprite sheet、VFX、TileMap 管线清晰 |
| 俯视角 RPG / ARPG | 高 | layered map、prop pack、collision / zones 需求明确 |
| 轻量 Roguelike | 高 | tile、怪物、道具、icon 都适合批量化 |
| Web 休闲游戏 | 高 | Phaser / PixiJS 与 atlas / sheet 管线匹配 |
| 卡牌 / 放置类 | 中高 | 更偏 UI、立绘、头像、VFX |
| 复杂格斗游戏 | 中低 | 对动作逻辑和逐帧质量要求极高，AI 原始产物需大量人工修正 |

---

## 4. 支持的资产类型

| 资产类型 | 推荐策略 | 输出 |
|---|---|---|
| 主角 | AI reference + cutout / bone / 手修 | parts、skeleton、preview |
| 普通敌人 | AI sprite sheet | PNG frames、sheet、atlas |
| Boss | reference + 分阶段生产 | body sheet、FX、parts |
| 技能特效 | AI sequence / sheet | VFX frames、atlas |
| Projectile | 小型循环帧 | 1xN / 2xN sheet |
| Impact | 短爆发帧 | frames + timing |
| 地图 | layered map pipeline | base、props、collision、zones |
| Tilemap | 规则化 tile + 拼接测试 | tileset、tile metadata |
| UI | AI mockup + 组件化重建 | icons、panels、nine-patch |
| Icon | AI 单体生成 + 统一风格 | transparent PNG |

---

## 5. 核心原则

| 原则 | 说明 |
|---|---|
| **Codex First** | Codex 负责编排、调用、检查、修复，而不是只写 prompt |
| **Spec First** | 所有资产生成前必须先有 `asset-spec.json` |
| **Art Bible Gate** | 没有美术规范，不允许批量生成 |
| **Deterministic Postprocess** | 透明化、切帧、对齐、图集、manifest 必须脚本化 |
| **Engine Truth** | 最终验收看 Godot / Phaser / PixiJS 中能否加载、播放、碰撞、预览 |
| **QA Before Accepted** | 任何资产进入 `accepted/` 前必须通过 QA |
| **Prototype / Production 双轨** | 原型可用 sprite sheet，生产主角应走 cutout / bone / 手修 |

---

## 6. 推荐总体流程

```text
1. 创建或更新 Art Bible
2. 建立 Asset Catalog
3. 为每个资产生成 asset-spec.json
4. 根据资产类型选择生成策略
5. 生成 raw image / raw sheet / raw map
6. 本地脚本后处理
7. 生成 frames / sheet / atlas / manifest / preview GIF
8. 运行 QA
9. 失败则 reprocess / regenerate / revise spec
10. 成功则导出 Godot / Phaser / PixiJS
11. 运行 engine smoke test
12. 进入 accepted asset bundle
```

---

## 7. 最重要的工程判断

### 不推荐

```text
一句 prompt 生成所有美术
一张 baked map 当 playable map
一个万能 agent 负责所有事情
生成者自己验收自己
所有角色都做成 subAgent
```

### 推荐

```text
Art Bible + Asset Spec
小型专用 Skills
确定性后处理脚本
少量 reviewer subAgents
QA hooks
Godot / Phaser / PixiJS preview scene
```


---

# 02. Codex 多角色与 Subagents 实现方案

## 1. 结论

多角色值得借鉴，但不应全部实现成 subAgents。

更合理的实现结构是：

```text
AGENTS.md / Rules 负责全局角色边界
Skills 负责可复用工作流
Scripts / Hooks 负责确定性处理和阻断
Subagents 只用于少数需要上下文隔离、独立评审或并行探索的角色
```

> **多角色 ≠ 全部 subAgents。Subagent 只是实现多角色的一种手段。**

---

## 2. 四层实现模型

| 层次 | 用途 | 适合放什么 |
|---|---|---|
| `AGENTS.md` / Rules | 全局角色协议、项目规范、目录约束 | Art Director / Technical Artist 的职责边界 |
| Skills | 可复用流程 | `asset-spec`、`generate-sprite-raw`、`qa-visual`、`export-godot` |
| Scripts / Hooks | 确定性执行和阻断 | 帧数、bbox、alpha、manifest、smoke test |
| Subagents | 独立上下文、独立评审、并行探索 | Art Review、Motion Review、Engine Review、Provenance Review |

---

## 3. 推荐角色集

| 角色 | 类型 | 是否建议 subAgent | 职责 |
|---|---|---:|---|
| Pipeline Orchestrator | 主控 | 否 | 拆任务、选 skill、管理阶段、输出计划 |
| Art Director | 评审型 | 建议作为 reviewer | Art Bible、风格一致性、色彩、比例、视角 |
| Technical Artist | 执行 + 评审 | 通常不用 | sprite layout、anchor、atlas、透明通道、cutout |
| Motion Reviewer | 评审型 | 建议 | 跑步、攻击、受击、idle 动作合理性 |
| Engine Integrator | 执行型 | 可选 reviewer | Godot / Phaser / PixiJS 导入和预览 |
| Asset QA | 脚本优先 | 可选 explainer | 帧数、bbox、alpha、命名、manifest、smoke test |
| Provenance Reviewer | 生产级可选 | 建议 | 授权、来源、IP 风险、生成记录 |

---

## 4. 哪些角色应该用 subAgent？

### 推荐做成 subAgent

| 角色 | 原因 |
|---|---|
| Art Director Reviewer | 需要独立审美判断，避免生成者自己验收自己 |
| Motion Reviewer | 需要检查动作逻辑和时序 |
| Engine Integrator Reviewer | 需要从运行时角度检查导出结果 |
| Provenance Reviewer | 版权、来源、第三方 IP 风险应独立评审 |
| QA Explainer | 脚本负责检测，subAgent 负责解释失败原因和修复建议 |

### 不建议做成 subAgent

| 任务 | 更适合 | 原因 |
|---|---|---|
| `asset-spec.json` 生成 | Skill | 结构化流程，重复性强 |
| 背景移除 | Script | 像素级确定性任务 |
| 切帧 / 对齐 / 图集打包 | Script | 必须可复现 |
| JSON schema 校验 | Hook | 不需要 LLM 判断 |
| Godot / Phaser 导出模板 | Skill + Script | 规则明确 |
| 文件命名检查 | Hook | 直接阻断错误即可 |

判断原则：

```text
需要独立判断 / 独立上下文 / 防止自我验收 → subAgent
需要稳定流程 / 结构化产物 → Skill
需要确定性处理 / 可测试结果 → Script / Hook
```

---

## 5. `AGENTS.md` 示例

```md
# Codex First 2D Art Pipeline

## Primary Role

Codex acts as the Pipeline Orchestrator.

Its job is to:
- read the Art Bible
- create or update asset specs
- select the correct skill
- run deterministic postprocessing scripts
- run QA
- export accepted assets to Godot and Web engines

## Role Modes

### Art Director Mode

Use this mode when:
- creating or updating Art Bible
- reviewing style consistency
- checking palette, outline, camera angle, proportion, visual readability

Do not:
- modify postprocessing scripts
- change engine export files directly

### Technical Artist Mode

Use this mode when:
- choosing sprite sheet layout
- defining frame size
- deciding anchor points
- splitting body animation and detached VFX
- defining atlas and manifest structure

### Motion Reviewer Mode

Use this mode when:
- reviewing run, idle, attack, hurt, death animations
- checking anticipation, contact, recovery
- checking foot sliding and pose readability

### Engine Integrator Mode

Use this mode when:
- exporting to Godot
- exporting to Phaser
- exporting to PixiJS
- creating preview scenes
- running engine smoke tests

### Asset QA Mode

Use scripts first.
Only use model judgment after deterministic checks have completed.

Required checks:
- frame count
- frame size
- alpha channel
- bbox drift
- anchor drift
- edge touch
- manifest schema
- engine smoke test
```

---

## 6. Reviewer Subagent 示例

### `art-director-reviewer.md`

```md
# Art Director Reviewer

Purpose:
Review generated 2D art assets against the project Art Bible.

Input:
- art-bible.md
- asset-spec.json
- generated preview image or GIF
- qa-report.json

Output:
- art-review-report.md

Review dimensions:
- style consistency
- silhouette readability
- palette compliance
- outline consistency
- camera angle consistency
- proportion consistency
- whether the asset looks like the same game

Rules:
- Do not edit source files.
- Do not regenerate assets.
- Only produce review findings and accept/reject recommendation.
```

### `motion-reviewer.md`

```md
# Motion Reviewer

Purpose:
Review animation logic and readability.

Input:
- preview.gif
- animation manifest
- asset-spec.json

Output:
- motion-review-report.md

Check:
- idle loop stability
- run cycle foot alternation
- attack anticipation / contact / recovery
- hurt pose readability
- foot sliding
- weapon consistency
- frame timing

Rules:
- Do not edit images.
- Do not modify specs.
- Recommend whether to reprocess, regenerate, or revise spec.
```

---

## 7. 推荐执行流

```text
Codex Orchestrator
  ↓
读取 AGENTS.md + Art Bible
  ↓
调用 asset-spec Skill
  ↓
Technical Artist 视角检查 spec
  ↓
调用 generate-sprite-raw Skill
  ↓
调用 postprocess-sprite Skill
  ↓
调用 qa-visual Skill
  ↓
如果 QA 失败：
    reprocess 或 regenerate
  ↓
如果 QA 通过：
    启动 Art Director Reviewer subAgent
    启动 Motion Reviewer subAgent
  ↓
如果 reviewer 通过：
    调用 export-godot Skill
    调用 export-phaser Skill
  ↓
启动 Engine Integrator Reviewer subAgent
  ↓
进入 accepted/
```

---

## 8. 最小实现建议

第一版只保留：

```text
AGENTS.md
Skills:
  art-bible
  asset-spec
  generate-sprite-raw
  postprocess-sprite
  qa-visual
  export-godot
  export-phaser

Scripts:
  check_frame_count.py
  check_alpha.py
  check_bbox_drift.py
  check_anchor_drift.py

Subagents:
  art-director-reviewer
  motion-reviewer
```

后续再加：

```text
engine-integrator-reviewer
provenance-reviewer
qa-explainer
map-layout-reviewer
ui-reviewer
```


---

# 03. Skills、仓库结构与模板

## 1. 推荐仓库结构

```text
game-project/
  AGENTS.md

  .agents/
    skills/
      art-bible/
      asset-catalog/
      asset-spec/
      generate-sprite-raw/
      postprocess-sprite/
      generate-map-raw/
      postprocess-map/
      generate-ui-kit/
      generate-vfx/
      qa-visual/
      qa-engine/
      export-godot/
      export-phaser/
      export-pixi/
      provenance-check/

  .agents/
    subagents/
      art-director-reviewer.md
      motion-reviewer.md
      engine-integrator-reviewer.md
      provenance-reviewer.md

  rules/
    art.rules.md
    asset.rules.md
    godot.rules.md
    web.rules.md

  hooks/
    validate-spec.py
    validate-assets.py
    check-alpha.py
    check-bbox-drift.py
    check-frame-count.py
    godot-smoke-test.sh
    phaser-smoke-test.sh

  design/
    gdd/
    art/
      art-bible.md
      palette.json
      style-tokens.json
      negative-prompts.md

  assets/
    specs/
    raw/
    attempts/
    accepted/
    atlases/
    manifests/

  tools/
    image/
    godot/
    web/

  engine/
    godot/
    phaser/
    pixi/

  qa/
    reports/
    baselines/
    diffs/
    previews/
```

---

## 2. 必备 Skills

| Skill | 目标 | 输入 | 输出 |
|---|---|---|---|
| `art-bible` | 建立项目美术规范 | GDD / prompt / reference | `art-bible.md`、`palette.json` |
| `asset-catalog` | 生成资产清单 | GDD / 关卡设计 | `asset-catalog.json` |
| `asset-spec` | 生成资产规格 | 单个资产需求 | `asset-spec.json` |
| `generate-sprite-raw` | 生成原始 sprite sheet | asset spec | raw PNG |
| `postprocess-sprite` | 透明化、切帧、对齐 | raw PNG | frames、sheet、GIF、metrics |
| `generate-map-raw` | 生成地图原始层 | map spec | base、dressed、prop pack |
| `postprocess-map` | 拆 props、生成碰撞、zones | raw map outputs | map manifest |
| `generate-vfx` | 生成技能 / 命中特效 | vfx spec | VFX frames |
| `qa-visual` | 图像级 QA | frames / sheet | `qa-report.json` |
| `qa-engine` | 引擎级 QA | exported bundle | smoke test report |
| `export-godot` | 导出 Godot 资源 | accepted assets | `.tscn`、`.tres`、manifest |
| `export-phaser` | 导出 Phaser 资源 | accepted assets | atlas、JSON、TS loader |
| `export-pixi` | 导出 PixiJS 资源 | accepted assets | atlas、JSON、loader config |
| `provenance-check` | 检查来源 / 授权 / IP 风险 | manifest / prompt / refs | provenance report |

---

## 3. Skill 设计原则

### 3.1 单一职责

不要做：

```text
generate-everything/
```

推荐拆分为：

```text
asset-spec/
generate-sprite-raw/
postprocess-sprite/
qa-visual/
export-godot/
export-phaser/
```

### 3.2 输入输出明确

每个 Skill 必须声明：

```text
Input
Output
Do
Do not
Blocking rules
```

### 3.3 不要让 Skill 替代脚本

Skill 负责流程；脚本负责确定性处理。

例如：

| 任务 | 实现 |
|---|---|
| 生成 prompt plan | Skill |
| 去背景 | Script |
| 切帧 | Script |
| 生成 manifest | Script |
| 解释 QA 失败原因 | Skill / Reviewer |
| 拒绝不合格资产 | Hook |

---

## 4. `asset-spec` Skill 模板

```md
---
name: asset-spec
description: Create a machine-readable spec for one 2D game art asset before image generation.
---

Rules:
- Always read Art Bible first.
- Never generate image assets directly.
- Output asset-spec.json only.
- Specify engine targets: godot, phaser, pixi.
- Specify frame size, frame count, layout, anchor, collision role, export targets.
- Separate body animation from detached VFX.

Required output schema:
- id
- kind
- style_ref
- view
- track
- generation
- frame
- qa
- exports
```

---

## 5. `generate-sprite-raw` Skill 模板

```md
---
name: generate-sprite-raw
description: Generate raw opaque sprite sheets from an approved asset spec.
---

Rules:
- Read asset-spec.json first.
- Do not generate final transparent PNG directly.
- Use solid background for downstream removal.
- For body animation, keep detached VFX out of body sheet.
- For 4-frame body animation, prefer 2x2 layout.
- Keep feet or bottom anchor stable.
- Save prompt-used.txt and generation-meta.json.

Do not:
- create engine files
- mark assets accepted
- bypass QA
```

---

## 6. `postprocess-sprite` Skill 模板

```md
---
name: postprocess-sprite
description: Convert raw sprite sheets into transparent frames, aligned sheets, preview GIFs, and metrics.
---

Run scripts in order:
1. remove_bg.py
2. split_grid.py
3. align_frames.py
4. normalize_scale.py
5. export_sheet.py
6. export_gif.py
7. write_metrics.py

Output:
- frames/
- sheet-transparent.png
- preview.gif
- metrics.json

Blocking:
- if frame count mismatches spec
- if alpha channel missing
- if edge-touch frames exceed threshold
```

---

## 7. `qa-visual` Skill 模板

```md
---
name: qa-visual
description: Run deterministic QA checks for generated 2D art assets.
---

Run:
1. validate_spec.py
2. check_frame_count.py
3. check_alpha.py
4. check_bbox_drift.py
5. check_anchor_drift.py
6. check_edge_touch.py
7. write_qa_report.py

Output:
- qa-report.json
- diff image if baseline exists

Do not:
- modify source assets
- regenerate images
- mark asset as accepted if blocking checks fail
```

---

## 8. `export-godot` Skill 模板

```md
---
name: export-godot
description: Export accepted 2D art assets into Godot 4 resources and preview scenes.
---

Input:
- accepted frames / sheet
- asset-spec.json
- qa-report.json

Output:
- SpriteFrames .tres
- preview .tscn
- animation manifest
- import report

Rules:
- Do not export failed assets.
- Use bottom-center anchor for side-view characters.
- Generate a preview scene for each accepted animated asset.
```

---

## 9. `export-phaser` Skill 模板

```md
---
name: export-phaser
description: Export accepted 2D art assets into Phaser-compatible spritesheet, atlas, animation, and preload files.
---

Input:
- accepted frames / sheet / atlas
- asset-spec.json
- qa-report.json

Output:
- spritesheet or atlas
- phaser-anims.json
- preload.ts
- preview scene

Rules:
- frameWidth and frameHeight must match asset-spec.json.
- Do not export failed assets.
- Generate a browser preview scene.
```


---

# 04. 2D 资产生成管线

## 1. 总体流程

```text
Art Bible
  ↓
Asset Catalog
  ↓
Asset Spec
  ↓
Raw Generation
  ↓
Postprocess
  ↓
QA
  ↓
Engine Export
  ↓
Preview / Accepted
```

---

## 2. 角色资产

### 2.1 Prototype Track

用于快速验证玩法：

```text
asset-spec.json
  ↓
AI sprite sheet
  ↓
background removal
  ↓
frame split
  ↓
anchor alignment
  ↓
preview GIF
  ↓
Godot / Phaser preview
```

适合：

- 小怪
- 临时主角
- 低成本 NPC
- Game Jam
- 快速 gameplay demo

验收标准：

```text
能导入
能播放
视觉可接受
anchor 不严重漂移
没有明显透明残留
```

### 2.2 Production Track

用于主角、核心敌人、Boss：

```text
AI 角色参考图
  ↓
三视图 / 关键姿态
  ↓
parts extraction
  ↓
cutout / bone rig
  ↓
动作制作
  ↓
VFX 分离
  ↓
严格 QA
  ↓
engine preview
```

适合：

- 主角
- 核心敌人
- Boss
- 付费皮肤
- 重要 NPC
- 长期复用角色

---

## 3. 动作拆分策略

攻击动作不要生成成一张混合大图，而应拆成：

```text
hero_attack_body
slash_arc_fx
hit_impact_fx
```

原因：

- 防止角色本体被特效挤小
- 降低 bbox 漂移
- 维持 anchor 稳定
- 方便在引擎中独立调 timing
- 方便命中判定与视觉解耦

---

## 4. 推荐动画规格

| 动作 | Prototype 帧数 | Production 帧数 | loop | 备注 |
|---|---:|---:|---:|---|
| idle | 4–6 | 6–12 | 是 | 呼吸、轻微晃动 |
| run | 6–8 | 8–12 | 是 | 必须检查左右脚交替 |
| walk | 4–8 | 8–12 | 是 | 适合敌人 / NPC |
| jump | 3–5 | 5–8 | 否 | 起跳 / 空中 / 落地 |
| attack | 4–8 | 8–16 | 否 | anticipation / contact / recovery |
| hurt | 2–4 | 3–6 | 否 | 受击姿态要清晰 |
| death | 6–10 | 10–20 | 否 | 敌人可简化，Boss 要强化 |

---

## 5. VFX 资产

VFX 比角色更适合 AI sequence，因为一致性压力较小。

### 推荐拆分

```text
cast
projectile
impact
area_effect
screen_flash
debris
```

### 示例 VFX Bundle

```json
{
  "asset_id": "vfx_fireball_bundle",
  "type": "vfx_bundle",
  "items": [
    {"name": "cast", "layout": "2x3", "frames": 6},
    {"name": "projectile", "layout": "1x4", "frames": 4},
    {"name": "impact", "layout": "2x3", "frames": 6}
  ]
}
```

---

## 6. 地图资产

不要直接把 AI 生成的一张大图当 playable map。

推荐 layered map pipeline：

```text
ground-only base
  ↓
dressed reference
  ↓
prop pack
  ↓
prop extraction
  ↓
placement metadata
  ↓
collision metadata
  ↓
trigger zones
  ↓
engine scene
```

### 地图层级

| 层 | 内容 |
|---|---|
| ground | 地面、道路、水面、基础地形 |
| decoration | 草、石头、树叶、非交互装饰 |
| runtime_props | 宝箱、门、机关、可破坏物 |
| collision | 墙体、障碍、不可通行区域 |
| trigger_zones | 出口、遇敌区、剧情触发区 |
| foreground | 前景遮挡物 |

---

## 7. Tilemap 资产

推荐流程：

```text
确定 tile size
  ↓
生成基础 tile
  ↓
生成边缘 / 转角 / 过渡 tile
  ↓
拼接测试
  ↓
生成 tileset
  ↓
生成 tile metadata
  ↓
引擎导入
```

常用尺寸：

| 风格 | tile size |
|---|---|
| 像素风 | 16×16 / 32×32 |
| 高清 2D | 64×64 / 128×128 |
| 等距地图 | 64×32 / 128×64 |

Tilemap 最重要的不是单个 tile 好不好看，而是：

```text
拼接是否连续
纹理密度是否一致
透视是否一致
边缘是否能复用
```

---

## 8. UI 资产

UI 不建议直接生成最终可交互界面。

推荐：

```text
AI UI mockup
  ↓
结构解析
  ↓
组件拆分
  ↓
engine-native UI 重建
```

输出：

| 类型 | Godot | Web |
|---|---|---|
| Button | Button / TextureButton | DOM / Phaser Image Button |
| Panel | NinePatchRect | nine-slice image |
| Icon | Texture2D | texture atlas |
| HUD | Control tree | Phaser / Pixi Container |
| Font | Label / Theme | webfont / bitmap font |

---

## 9. Icon 资产

Icon 是最适合 AI 批量生成的资产之一。

推荐规范：

```text
统一画布尺寸：128×128 / 256×256
统一描边
统一光源
统一背景策略
统一色板
统一命名
```

输出：

```text
icon_sword_fire.png
icon_potion_hp.png
icon_skill_dash.png
icon_status_poison.png
```

---

## 10. Asset Spec 示例

```json
{
  "id": "hero_knight_run",
  "kind": "character_body_action",
  "style_ref": "design/art/art-bible.md",
  "view": "side",
  "track": "prototype_sprite_sheet",
  "generation": {
    "raw_canvas": [1024, 1024],
    "layout": {
      "rows": 2,
      "cols": 4,
      "frame_count": 8
    },
    "background": "solid_chroma"
  },
  "frame": {
    "width": 256,
    "height": 256,
    "anchor": "bottom_center",
    "fps": 12,
    "loop": true
  },
  "qa": {
    "max_anchor_drift_px": 4,
    "max_bbox_scale_delta": 0.12,
    "allow_edge_touch": false
  },
  "exports": {
    "godot": {
      "resource": "SpriteFrames",
      "animation_name": "run"
    },
    "phaser": {
      "texture_key": "hero_knight_run",
      "frameWidth": 256,
      "frameHeight": 256
    },
    "pixi": {
      "atlas": true
    }
  }
}
```


---

# 05. Godot 适配与导出规范

## 1. Godot 定位

Godot 是本方案的主生产引擎，适合：

- 2D 场景编辑
- TileMap / TileMapLayer
- AnimatedSprite2D / SpriteFrames
- AnimationPlayer
- Area2D / StaticBody2D
- Skeleton2D / Cutout
- Preview scene / debug scene

---

## 2. 角色动画导出

### 2.1 输出目录

```text
engine/godot/assets/characters/hero/
  hero_run_sheet.png
  hero_run_frames/
  hero_spriteframes.tres
  hero.tscn
  hero_preview.tscn
  hero.animation_manifest.json
```

### 2.2 推荐节点结构

```text
Hero.tscn
  CharacterBody2D
    AnimatedSprite2D
    CollisionShape2D
    Marker2D weapon_socket
    Marker2D feet_anchor
```

### 2.3 Prototype Track

Prototype 阶段推荐：

```text
PNG frames / sprite sheet
  ↓
SpriteFrames
  ↓
AnimatedSprite2D
  ↓
preview scene
```

适合普通敌人、临时主角、VFX。

### 2.4 Production Track

Production 阶段推荐：

```text
parts
  ↓
Node2D hierarchy / Skeleton2D
  ↓
AnimationPlayer
  ↓
VFX overlay
  ↓
preview scene
```

适合主角、Boss、高复用角色。

---

## 3. 地图导出

### 3.1 推荐场景结构

```text
ForestRoute01.tscn
  Node2D
    TileMapLayer ground
    TileMapLayer decoration
    Node2D props
    StaticBody2D collision_blockers
    Area2D exit_zone_01
    Area2D encounter_zone_01
    CharacterBody2D debug_player
    Camera2D debug_camera
```

### 3.2 输出文件

```text
forest_route_01.tscn
forest_route_01_tileset.tres
forest_route_01_ground.png
forest_route_01_props/
forest_route_01_collision.json
forest_route_01_zones.json
forest_route_01_import_report.json
```

### 3.3 Map Manifest 示例

```json
{
  "id": "forest_route_01",
  "tile_size": 32,
  "layers": {
    "ground": "forest_ground.png",
    "decoration": "forest_decoration.png",
    "props": "props/"
  },
  "collision": [
    {"type": "rect", "x": 0, "y": 0, "w": 320, "h": 32},
    {"type": "poly", "points": [[100,100], [200,100], [200,140], [100,140]]}
  ],
  "zones": [
    {"id": "exit_north", "type": "exit", "x": 512, "y": 0, "w": 128, "h": 32},
    {"id": "encounter_grass_01", "type": "encounter", "x": 200, "y": 300, "w": 160, "h": 96}
  ]
}
```

---

## 4. Godot Exporter 职责

`export-godot` Skill / Script 应该负责：

```text
读取 asset-spec.json
读取 qa-report.json
确认 asset 已通过 QA
生成 SpriteFrames / AnimationPlayer 资源
生成 preview scene
生成 map scene
生成 import report
运行 Godot smoke test
```

不应该负责：

```text
重新生成图像
修改 Art Bible
修复原始 sprite
跳过 QA
```

---

## 5. Godot Smoke Test

检查项：

```text
Godot 项目能否打开
资源能否导入
SpriteFrames 能否播放
TileMapLayer 是否加载
Area2D / StaticBody2D 是否存在
debug scene 是否能运行
截图是否生成
```

示例输出：

```json
{
  "asset_id": "hero_knight_run",
  "godot_import_ok": true,
  "preview_scene_ok": true,
  "animation_playback_ok": true,
  "screenshot": "qa/previews/godot_hero_knight_run.png",
  "warnings": []
}
```

---

## 6. Godot 适配重点

| 事项 | 策略 |
|---|---|
| 坐标原点 | side-view 角色统一 bottom-center anchor |
| 像素比例 | 固定 pixels per unit / camera zoom |
| 动画 | Prototype 用 SpriteFrames，Production 可用 AnimationPlayer / Skeleton2D |
| 地图 | TileMapLayer + props + zones 分层 |
| 碰撞 | 不从图像猜测最终碰撞，必须 metadata 化 |
| 交互区 | Area2D 从 map manifest 生成 |
| 调试 | 每个 asset bundle 都生成 preview scene |
| accepted 规则 | 只有 QA 和 smoke test 都通过才进入 accepted |

---

## 7. 推荐 Godot 导出标准

### 角色

```text
assets/accepted/characters/<id>/
  frames/
  sheet.png
  preview.gif
  asset-spec.json
  qa-report.json
  godot/
    <id>_spriteframes.tres
    <id>_preview.tscn
    import-report.json
```

### 地图

```text
assets/accepted/maps/<id>/
  ground.png
  props/
  map-manifest.json
  collision.json
  zones.json
  qa-report.json
  godot/
    <id>.tscn
    <id>_tileset.tres
    import-report.json
```


---

# 06. Web 引擎适配与导出规范：Phaser / PixiJS

## 1. Web 引擎定位

Web 端建议分两层：

| 引擎 | 定位 |
|---|---|
| Phaser | 首选 Web 游戏框架，适合 gameplay、资源加载、动画、输入、物理、TileMap |
| PixiJS | 底层 2D 渲染库，适合轻量互动、高性能视觉层、UI-heavy 场景 |

---

## 2. Phaser 适配方案

### 2.1 角色动画导出

输出目录：

```text
engine/phaser/public/assets/characters/hero/
  hero_run_sheet.png
  hero_run.json
  hero_anims.json
```

示例 loader：

```ts
this.load.spritesheet("hero_run", "assets/characters/hero/hero_run_sheet.png", {
  frameWidth: 256,
  frameHeight: 256
});
```

示例 animation config：

```ts
this.anims.create({
  key: "hero_run",
  frames: this.anims.generateFrameNumbers("hero_run", { start: 0, end: 7 }),
  frameRate: 12,
  repeat: -1
});
```

---

## 3. Phaser 地图导出

输出：

```text
forest_route_01_tileset.png
forest_route_01_tilemap.json
forest_route_01_objects.json
forest_route_01_scene.ts
```

Phaser scene 结构：

```text
Scene
  preload()
  create()
    tilemap
    ground layer
    decoration layer
    collision layer
    object layer
    trigger zones
```

### Object Layer 示例

```json
{
  "objects": [
    {
      "id": "exit_north",
      "type": "exit",
      "x": 512,
      "y": 0,
      "width": 128,
      "height": 32
    },
    {
      "id": "encounter_grass_01",
      "type": "encounter",
      "x": 200,
      "y": 300,
      "width": 160,
      "height": 96
    }
  ]
}
```

---

## 4. Phaser Exporter 职责

`export-phaser` Skill / Script 应该负责：

```text
读取 asset-spec.json
读取 qa-report.json
确认 asset 已通过 QA
生成 spritesheet / atlas
生成 phaser-anims.json
生成 preload.ts
生成 preview scene
运行 browser smoke test
```

不应该：

```text
直接修改 raw image
跳过 QA
手写不符合 spec 的 frameWidth / frameHeight
```

---

## 5. PixiJS 适配方案

PixiJS 适合：

- 嵌入网页的小型互动内容
- 高性能 2D 渲染
- 自定义渲染层
- 视觉动效强、玩法较轻的场景

输出：

```text
atlas.png
atlas.json
pixi-loader.ts
pixi-preview.ts
```

示例结构：

```ts
import { Application, Assets, AnimatedSprite } from "pixi.js";

const app = new Application();
await app.init({ width: 800, height: 600 });

const sheet = await Assets.load("assets/hero_atlas.json");
const frames = [
  sheet.textures["hero_run_0.png"],
  sheet.textures["hero_run_1.png"],
  sheet.textures["hero_run_2.png"],
  sheet.textures["hero_run_3.png"]
];

const anim = new AnimatedSprite(frames);
anim.animationSpeed = 0.2;
anim.play();

app.stage.addChild(anim);
```

---

## 6. Web Smoke Test

### Phaser

检查：

```text
npm build 是否通过
texture 是否 preload
spritesheet / atlas 是否解析
animation 是否创建
scene 是否启动
canvas 是否渲染
截图是否生成
```

### PixiJS

检查：

```text
bundle 是否构建
atlas 是否加载
textures 是否可访问
animation frames 是否存在
container 是否渲染
截图是否生成
```

---

## 7. Web 端视觉回归

推荐使用 browser screenshot baseline：

```text
启动 preview scene
等待资源加载完成
截取 canvas
与 baseline 对比
输出 diff
```

QA 输出：

```json
{
  "asset_id": "hero_knight_run",
  "web_engine": "phaser",
  "build_ok": true,
  "scene_start_ok": true,
  "texture_load_ok": true,
  "animation_playback_ok": true,
  "screenshot": "qa/previews/phaser_hero_knight_run.png",
  "pixel_diff_ratio": 0.012
}
```

---

## 8. Phaser / PixiJS 选择建议

| 场景 | 推荐 |
|---|---|
| 完整 Web 游戏 | Phaser |
| TileMap / Arcade Physics | Phaser |
| 轻量互动页面 | PixiJS |
| 强视觉渲染 + 自定义逻辑 | PixiJS |
| AI Coding 友好快速原型 | Phaser |
| 资产预览工具 | Phaser 或 PixiJS 均可 |

---

## 9. Web 导出标准

### Phaser

```text
assets/accepted/characters/<id>/
  frames/
  sheet.png
  preview.gif
  asset-spec.json
  qa-report.json
  phaser/
    spritesheet.png
    anims.json
    preload.ts
    preview-scene.ts
    smoke-report.json
```

### PixiJS

```text
assets/accepted/characters/<id>/
  frames/
  atlas.png
  atlas.json
  asset-spec.json
  qa-report.json
  pixi/
    loader.ts
    preview.ts
    smoke-report.json
```


---

# 07. QA 验收与 Debug Protocol

## 1. QA 是核心竞争力

真正让 Codex First 2D 美术生成系统可用的，不是 prompt，而是：

```text
asset-spec schema
alpha edge check
frame count check
bbox drift check
anchor drift check
visual regression
engine smoke test
failure signature library
```

---

## 2. 三层验收

```text
Asset QA
  ↓
Visual Regression
  ↓
Engine Smoke Test
```

### 2.1 Asset QA

检查文件级资产是否合格：

```text
PNG 是否存在
尺寸是否正确
透明通道是否存在
帧数是否正确
命名是否正确
manifest 是否合法
bbox 是否稳定
anchor 是否稳定
```

### 2.2 Visual Regression

对比：

```text
accepted baseline
current output
diff image
pixel diff ratio
SSIM / MSE / embedding similarity
```

### 2.3 Engine Smoke Test

最终必须验证：

```text
Godot / Phaser / PixiJS 能否导入
动画能否播放
地图能否加载
碰撞 / 触发区是否存在
preview scene 是否可运行
截图是否生成
```

---

## 3. QA 指标

| 指标 | 说明 | 阻断级别 |
|---|---|---|
| `frame_count` | 实际帧数必须等于 spec | blocking |
| `frame_size` | 每帧尺寸必须符合 spec | blocking |
| `empty_frame_count` | 不允许空帧 | blocking |
| `edge_touch_frames` | 主体不能贴边或出界 | blocking / warning |
| `bbox_area_variance` | bbox 面积变化不能过大 | warning / blocking |
| `anchor_drift_px` | 脚底 / 中心 anchor 漂移不能过大 | blocking |
| `alpha_edge_noise` | 透明边缘不能有明显残留 | warning / blocking |
| `component_count` | 防止主体被切碎 | warning |
| `body_scale_delta` | 防止角色忽大忽小 | blocking |
| `naming_convention` | 命名必须符合规则 | blocking |
| `manifest_schema` | manifest 必须通过 schema | blocking |
| `engine_smoke` | 引擎预览必须可运行 | blocking |

---

## 4. QA Report 示例

```json
{
  "asset_id": "hero_knight_idle",
  "attempt_id": "2026-05-15T1030Z_a2",
  "status": "fail",
  "checks": {
    "frame_count": "pass",
    "frame_size": "pass",
    "alpha_channel": "pass",
    "edge_touch_frames": 1,
    "empty_frames": 0,
    "anchor_drift_px_max": 6,
    "body_scale_delta_max": 0.18,
    "bbox_area_variance": 0.22,
    "engine_smoke": {
      "godot_import_ok": true,
      "phaser_load_ok": true
    }
  },
  "failure_signatures": [
    "body_shrunk_due_to_wide_fx",
    "frame_3_edge_touch"
  ],
  "recommended_action": "Regenerate body-only attack sheet and split slash arc into separate FX asset."
}
```

---

## 5. 常见失败签名库

| Failure Signature | 可能原因 | 首个自动响应 | 何时人工介入 |
|---|---|---|---|
| `magenta_halo` | 背景阈值过低、边缘清理不足 | 提高 threshold / despill | 细节被清理吃掉 |
| `edge_touch_frames` | 主体太大或漂移到 cell 边缘 | 拒绝并重新生成 | 一次 reprocess + 一次 regenerate 后仍失败 |
| `body_shrunk_due_to_wide_fx` | detached FX 被包含进 body sheet | 将 FX 拆成独立资产 | gameplay 需要宽 runtime cells |
| `single_row_body_drift` | body sequence 使用了原始 `1xN` sheet | 改用 2x2 / 2x3 / 3x3 | 引擎必须单行时，QC 后再组装 |
| `prop_pack_cell_crop` | pack 分类错误 | 改成 one-by-one 或 wide cell | prop 需要特殊碰撞或编辑 |
| `flat_map_as_playable` | runtime objects 被烘焙进 scenery | 重新生成 clean foundation | 确认只做背景图 |
| `phaser_frame_mismatch` | frameWidth / frameHeight 不匹配 | 从 spec 重新生成 loader config | atlas source 不一致 |
| `godot_missing_nodes` | exporter 未输出必要节点 | 重跑 scene export | 项目 scene 架构特殊 |

---

## 6. Debug Protocol

固定顺序：

```text
1. 如果失败是纯后处理问题，先 reprocess 一次
2. 如果失败来自原始生成，regenerate 一次
3. 如果同类失败出现两次，升级为 spec review
4. 如果 spec 不清楚，回到 Art Bible / GDD
5. 最后一个 accepted asset 冻结为 baseline，绝不静默覆盖
6. 每个 accepted / rejected attempt 都记录 diff 和 prompt
```

---

## 7. Accepted 规则

资产进入 `accepted/` 前必须满足：

```text
asset-spec.json 存在且通过 schema
raw / processed / frames / preview 存在
qa-report.json status = pass
Art Director Reviewer 通过，若适用
Motion Reviewer 通过，若适用
Godot / Phaser / PixiJS smoke test 至少一个目标通过
没有 blocking provenance risk
```

---

## 8. 失败处理策略

### 8.1 Reprocess

适用：

```text
透明残留
切帧错误
anchor 对齐问题
padding 不足
图集打包错误
```

### 8.2 Regenerate

适用：

```text
角色身份漂移
动作逻辑错误
身体比例变化
主体被裁切
地图层级混乱
```

### 8.3 Revise Spec

适用：

```text
连续两次生成失败
帧数 / layout 不合理
资产类型分类错误
body / FX 混在一起
地图目标不清楚
```

### 8.4 Human Review

适用：

```text
主角生产级资产
Boss 动画
商业发布资产
版权 / IP 风险
重要 UI 风格
```


---

# 08. 实施路线图与最小可执行版本

## 1. 实施总目标

先验证一条窄而完整的闭环，而不是一开始生成大量资产。

目标闭环：

```text
Art Bible
  ↓
Asset Spec
  ↓
Raw Generation
  ↓
Postprocess
  ↓
QA
  ↓
Godot Export
  ↓
Phaser Export
  ↓
Preview / Regression
```

---

## 2. Phase 0：工程骨架

### 目标

建立 Codex-native control plane。

### 交付物

```text
AGENTS.md
.agents/skills/
rules/
hooks/
asset-spec schema
art-bible template
qa-report schema
provenance schema
```

### 成功标准

| 项 | 标准 |
|---|---|
| Codex 角色协议 | AGENTS.md 可读、边界清晰 |
| Skills | 至少 5 个核心 Skill 可发现 |
| Hooks | spec / asset / qa 基础校验可运行 |
| Schema | asset-spec 和 qa-report 可验证 |
| 目录 | raw / attempts / accepted 明确分离 |

---

## 3. Phase 1：Sprite Pipeline

### 目标

验证角色 / 敌人 / VFX 的 sprite 生成与后处理。

### 资产范围

```text
hero_idle
hero_run
slime_idle
slime_walk
fireball_projectile
fireball_impact
```

### 交付物

```text
raw sheets
transparent frames
aligned sheets
preview GIFs
qa reports
Godot SpriteFrames
Phaser spritesheet / anims
```

### 成功标准

```text
所有 accepted assets 通过 frame / alpha / bbox / anchor QA
Godot preview scene 可播放
Phaser preview scene 可播放
```

---

## 4. Phase 2：Map Pipeline

### 目标

验证 layered map 生成与引擎导出。

### 资产范围

```text
forest_route_01
ground-only base
dressed reference
prop pack
collision zones
exit zones
```

### 交付物

```text
map-manifest.json
props/
collision.json
zones.json
Godot map scene
Phaser tilemap scene
smoke reports
```

### 成功标准

```text
不是 flat baked map
props 可独立编辑
collision / zones 可加载
Godot / Phaser preview 可运行
```

---

## 5. Phase 3：Production Character Pipeline

### 目标

建立主角 / Boss 的生产级轨道。

### 内容

```text
character reference
三视图
cutout parts
bone / skeleton branch
AnimationPlayer / Skeleton2D
VFX overlay
manual polish loop
```

### 成功标准

```text
主角身份稳定
动作可复用
body / FX 分离
可导入 Godot
可生成 Web preview
```

---

## 6. Phase 4：CI / Regression

### 目标

让资产管线具备持续集成能力。

### 内容

```text
asset validation
visual regression
engine smoke test
release bundle
provenance report
failure signature library
```

### 成功标准

```text
PR 中坏资产会被阻断
accepted baseline 不会被静默覆盖
失败原因可诊断
release bundle 可重复构建
```

---

## 7. 最小可执行版本 MVP

### 7.1 资产范围

```text
1 个主角 idle / run
1 个敌人 idle / walk
1 个 projectile
1 个 impact
1 个 prop pack
1 个小地图
1 个 Godot preview
1 个 Phaser preview
1 套 QA report
```

### 7.2 目录范围

```text
assets/specs/
  hero_idle/
  hero_run/
  slime_idle/
  slime_walk/
  fireball_projectile/
  fireball_impact/
  forest_props/
  forest_route_01/

assets/accepted/
  characters/
  vfx/
  props/
  maps/

engine/godot/
  preview_project/

engine/phaser/
  preview_project/

qa/reports/
```

### 7.3 必备 Skills

```text
art-bible
asset-spec
generate-sprite-raw
postprocess-sprite
qa-visual
export-godot
export-phaser
```

### 7.4 必备 Scripts

```text
validate_spec.py
remove_bg.py
split_grid.py
align_frames.py
check_frame_count.py
check_alpha.py
check_bbox_drift.py
check_anchor_drift.py
build_godot_preview.py
build_phaser_preview.py
```

---

## 8. 里程碑验收

| 里程碑 | 验收标准 |
|---|---|
| M0 | 仓库结构、AGENTS.md、Skills skeleton 完成 |
| M1 | hero_run 从 spec 到 Godot / Phaser preview 跑通 |
| M2 | VFX bundle 从 spec 到 preview 跑通 |
| M3 | small map 从 layered spec 到 Godot / Phaser preview 跑通 |
| M4 | QA 失败能自动进入 reprocess / regenerate / revise spec 分支 |
| M5 | accepted bundle 可重复构建并通过 smoke test |

---

## 9. 推荐开发顺序

```text
1. 先写 schema，不先写 prompt
2. 先做 postprocess，不先追求高质量图
3. 先跑通一个 hero_run，不批量生成十个角色
4. 先做 Godot + Phaser 两个 preview，不先做完整游戏
5. 先做 QA gate，再做美术扩展
6. 先记录失败签名，再优化 prompt
```

---

## 10. 最终形态

```text
Codex Orchestrator
  + 精简多角色治理
  + 小型专用 Skills
  + 确定性后处理脚本
  + QA Hooks
  + Godot / Phaser / PixiJS Exporters
  + Failure Signature Library
  + Release Bundle Builder
```

一句话：

> 先做一条可复现、可验收、可导入的窄管线，再扩大资产类型和风格覆盖。


---

# 参考来源与调研依据

> 本文档集整理日期：2026-05-15
> 说明：本文档中的方案综合了用户前序调研、公开项目、引擎文档和相关研究论文。链接用于后续复核，不代表完整依赖清单。

## 核心参考项目

- [agent-sprite-forge](https://github.com/0x0funky/agent-sprite-forge)
  Codex-first 2D sprite / map 资产生成思路，重点参考：原始图像生成 + 本地确定性后处理 + metadata + Godot map handoff。

- [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)
  多角色 agents、skills、hooks、rules、templates 的工作室化组织方式，重点参考：Art Bible gate、Asset Spec gate、质量门禁和路径规则。

- [OpenGame: Open Agentic Coding for Games](https://arxiv.org/abs/2604.18394)
  重点参考：Template Skill、Debug Skill、执行验证、Build Health / Visual Usability / Intent Alignment 评估思路。

## Codex / Agent Skills 相关

- [OpenAI Codex Skills 文档](https://developers.openai.com/codex/skills)
- [OpenAI Codex Best Practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Image Generation 文档](https://developers.openai.com/api/docs/guides/image-generation)
- [Skills in Codex 公开报道](https://www.itpro.com/software/development/openais-skills-in-codex-service-aims-to-supercharge-agent-efficiency-for-developers)

## Godot 相关

- [Godot AnimatedSprite2D](https://docs.godotengine.org/en/stable/classes/class_animatedsprite2d.html)
- [Godot SpriteFrames](https://docs.godotengine.org/en/stable/classes/class_spriteframes.html)
- [Godot TileMapLayer](https://docs.godotengine.org/en/stable/classes/class_tilemaplayer.html)
- [Godot 2D Skeletons](https://docs.godotengine.org/en/stable/tutorials/animation/2d_skeletons.html)
- [Godot Cutout Animation](https://docs.godotengine.org/en/stable/tutorials/animation/cutout_animation.html)

## Web 引擎相关

- [Phaser Docs](https://docs.phaser.io/)
- [Phaser LoaderPlugin spritesheet](https://docs.phaser.io/api-documentation/class/loader-loaderplugin#spritesheet)
- [Phaser Animations](https://docs.phaser.io/phaser/concepts/animations)
- [PixiJS Docs](https://pixijs.com/)
- [PixiJS AnimatedSprite](https://pixijs.download/dev/docs/scene.AnimatedSprite.html)

## 2D 角色动画 / Sprite 研究

- [APES: Articulated Part Extraction from Sprite Sheets](https://arxiv.org/abs/2206.02015)
- [Fast Sprite Decomposition from Animated Graphics](https://arxiv.org/abs/2408.03923)
- [SPRITETOMESH: Automatic Mesh Generation for 2D Skeletal Animation](https://arxiv.org/abs/2602.21153)

## Web 游戏视觉 QA / 回归

- [Automated Visual Testing of HTML5 Canvas Games](https://arxiv.org/abs/2208.02335)
- [VLM-assisted visual bug detection for HTML5 canvas games](https://arxiv.org/abs/2501.09236)


---
