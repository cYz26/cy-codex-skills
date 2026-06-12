# Godot Web 字体子集化指南（项目实战版）

该文档用于在保证字符覆盖的前提下，最大化降低 Web 包体。

## 1) 前置依赖

```bash
python3 -m pip install --user fonttools brotli
```

说明：
1. `fonttools` 提供 `pyftsubset`。
2. 输出 `woff2` 需要 `brotli`。

## 2) 字体下载与缓存（按需）

skill 不直接携带字体文件。先按需下载并缓存：

```bash
bash skills/godot-web-cjk-font-fix/scripts/fetch_font.sh noto-sans-cjk-sc-regular-otf
```

默认缓存目录：`~/.codex/cache/fonts`。  
可选环境变量：
1. `FONT_CACHE_DIR`：自定义缓存目录。
2. `FONT_SOURCE_URL`：覆盖默认下载地址（网络受限时使用镜像直链）。

## 3) 推荐入口（优先）

使用项目内脚本，而非手写命令：

```bash
make subset-font
```

该命令会：
1. 扫描 `scripts/**/*.gd`、`scenes/**/*.tscn`、`data/levels/**/*.json`。
2. 提取全部可打印字符到 `assets/fonts/glyphs_project_full.txt`。
3. 使用本地或缓存源字体生成 `assets/fonts/NotoSansSC-ProjectSubset.woff2`。

## 4) 底层命令（调试/迁移时使用）

```bash
python3 -m fontTools.subset "$HOME/.codex/cache/fonts/NotoSansCJKsc-Regular.otf" \
  --text-file="assets/fonts/glyphs_project_full.txt" \
  --output-file="assets/fonts/NotoSansSC-ProjectSubset.woff2" \
  --flavor=woff2 \
  --layout-features='*' \
  --glyph-names \
  --symbol-cmap \
  --legacy-cmap \
  --notdef-glyph \
  --notdef-outline \
  --recommended-glyphs \
  --name-IDs='*' \
  --name-legacy \
  --name-languages='*' \
  --no-hinting
```

说明：若源字体是 `.ttc`（集合字体），再追加 `--font-number=<index>`。

## 5) 覆盖检查（必须）

至少跑一次缺字检测，重点看符号字符：

```bash
python3 - <<'PY'
from pathlib import Path
from fontTools.ttLib import TTFont
font=TTFont("assets/fonts/NotoSansSC-ProjectSubset.woff2")
cmap=set()
for t in font["cmap"].tables:
    cmap.update(t.cmap.keys())
target=Path("scenes/main.tscn").read_text(encoding="utf-8")
missing=sorted({ch for ch in target if ch not in {'\n','\r','\t'} and ord(ch) not in cmap})
print("missing_count", len(missing))
print("missing_chars", "".join(missing))
PY
```

期望结果：`missing_count 0`。

## 6) 导出回归（必须）

```bash
make export-web
make web-smoke
```

手动验证时，重点检查教程文本里的符号序列：
1. `空格 → 叉号 → 印灵 → 空格`
2. `【提示】`、`【撤销】`、`【清空】`

## 7) 常见坑与修复

1. 仅按 Unicode 白名单提取字符，容易漏掉 `→`（U+2192）等符号。
2. 文案更新后未重跑 `make subset-font`，会出现新字缺失。
3. 下载地址不可达导致缓存字体不存在，需设置 `FONT_SOURCE_URL` 或切换网络。
4. 浏览器缓存旧资源，需强制刷新后复测。

## 8) 体积观测命令

```bash
du -sh build/web
du -h build/web/index.pck build/web/index.wasm build/web/index.js
```
