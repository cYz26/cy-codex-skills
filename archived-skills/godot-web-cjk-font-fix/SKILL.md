---
name: godot-web-cjk-font-fix
description: 解决 Godot 4 Web 导出中文方块/乱码问题，并沉淀“随包字体 + 子集化 + 包体优化 + 回归验证”的可复用流程。适用于编辑器正常但 Web 显示异常、符号缺字、字体体积过大场景。
---

# Godot Web 中文字体修复与优化

当 Godot 导出 Web（HTML5）后出现中文方块、空白、符号乱码，或需要降低字体导致的包体积时，使用此 skill。

## 1) 触发条件与根因判断（必须先做）

确认至少命中以下两项：
1. 编辑器内中文正常，Web 导出后变方块/空白/乱码。
2. 项目未明确使用随包 CJK 字体，或仍依赖系统字体回退。
3. 替换字体后大部分中文正常，但个别符号（如 `→`、`✕`）显示异常（典型子集缺字）。

若命中，进入“随包字体 + 子集化”流程，不要先尝试用系统字体规避。

## 2) 基线修复策略（推荐做法）

1. 使用可分发开源字体，放入 `res://assets/fonts/`。
2. Web 运行时主动加载随包字体，避免浏览器/系统回退差异。
3. 字体优先输出 `woff2` 子集文件，减少首包下载体积。
4. 字体源文件不内置在 skill 中，使用时按需下载并缓存（默认 `~/.codex/cache/fonts`）。

推荐基线字体：
1. `Noto Sans CJK SC` / `Source Han Sans CN`（OFL）
2. 不推荐仅依赖系统字体（Web 环境不可控）

## 3) 当前工程落地路径（Godot 4）

1. 在 `scripts/main.gd` 维护 `WEB_PACKAGED_FONT_PATH` 指向随包字体。
2. 在 `_configure_runtime_ui()` 中仅在 `OS.has_feature("web")` 时注入 `theme.default_font`。
3. 避免把修复建立在系统回退之上；系统回退只可作为兜底，不可作为主路径。

## 4) 字体子集化与包体优化（核心）

默认顺序：
1. 先修“能显示”再修“更小”。
2. 若本地无源字体，先执行 `skills/godot-web-cjk-font-fix/scripts/fetch_font.sh` 下载并缓存。
3. 子集化优先复用工程脚本：`make subset-font`（`tools/font_subset.sh`）。
4. 子集字符提取必须覆盖工程中全部可打印字符，避免漏掉 `→` 这类符号。
5. 字体产物使用 `woff2`，同时保留 `glyphs_project_full.txt` 便于回溯与复现。

额外体积优化（和字体并行）：
1. 清理未运行时使用的素材目录（用 `.gdignore` 阻断导出扫描）。
2. 每轮优化后对比 `build/web`、`index.pck`、`index.wasm`，明确收益来自哪里。

子集化细节见：
1. `references/font-subsetting.md`

## 5) Web 验证（强制）

按顺序执行：
1. `make subset-font`（变更文案或字体后）
2. `make export-web`
3. `make web-smoke`

手动回归：
1. `cd build/web`
2. `python3 -m http.server 8000`
3. 打开 `http://127.0.0.1:8000/index.html`

验收清单：
1. 教程、设置、反馈弹层、主界面中文全部可读。
2. 符号类文案（如 `→`、`✕`、中文标点）无方块/乱码。
3. 导出产物中存在字体资源，浏览器网络面板无 404。

## 6) 故障排查顺序

若仍无法显示中文，按以下顺序排查：
1. 字体路径是否正确（`res://...`），并已生成 `.import`。
2. 是否有独立 `Theme` 覆盖运行时注入字体。
3. 子集字体是否缺字：优先检查 `scenes/*.tscn`、`scripts/*.gd` 的符号字符。
4. 文案更新后是否忘记重跑 `make subset-font`。
5. 缓存字体下载是否失败（网络或 URL 不可达）；必要时设置 `FONT_SOURCE_URL` 指向可访问直链。
6. 是否受浏览器缓存影响（强刷或版本号变更后复测）。

## 7) 交付输出要求（必须）

每次处理后必须输出：
1. 使用的字体文件与许可来源。
2. 字体应用方式（运行时全局注入/局部覆盖）。
3. `make subset-font`、`make export-web`、`make web-smoke` 结果。
4. 优化前后体积对比（至少 `build/web`、`index.pck`、`index.wasm`）。
