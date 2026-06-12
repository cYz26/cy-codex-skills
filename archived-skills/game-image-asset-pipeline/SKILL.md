---
name: game-image-asset-pipeline
description: Convert text-to-image outputs into game-ready transparent assets by removing plain backgrounds, removing corner watermarks/logos, trimming to subject bounds, and exporting fixed-size PNGs. Use when Codex needs to transform AI-generated artwork into icons, avatars, or sprite-ready assets with strict size and padding requirements (for example 256x256 UI icons).
---

# Game Image Asset Pipeline

Use this skill to turn generated images into clean game assets quickly and repeatedly.

## 1) Lock Target Asset Spec

Before running any script, confirm:
1. Output size (for example `256x256`, `512x512`)
2. Output format (`PNG` with alpha)
3. Framing rule (tight crop vs extra padding)
4. Whether watermark/logo cleanup is required

Only run watermark removal on images you are allowed to modify.

## 2) Run Baseline Pipeline

Use:

```bash
python3 scripts/build_icon.py INPUT_IMAGE OUTPUT_IMAGE \
  --size 256 \
  --watermark-corners br
```

Default behavior:
1. Estimate plain background color from border pixels
2. Remove connected background region
3. Remove bright low-saturation corner watermark components
4. Crop to remaining non-transparent subject
5. Resize and center to square transparent canvas

## 3) Tune Parameters When Needed

Use these first-line adjustments:
1. Increase `--bg-threshold` when background residue remains
2. Decrease `--bg-threshold` when foreground edges are cut
3. Increase `--wm-value-threshold` to remove fewer bright regions
4. Increase `--wm-sat-threshold` to remove more grayscale watermark pixels
5. Change `--watermark-corners` (`tl,tr,bl,br,all,none`) based on watermark position
6. Use `--padding` to control empty margin in final icon

If watermark overlaps the character itself, do not over-clean with thresholds; keep the script conservative and perform manual retouch for that region.

## 4) Validate Output

After generation, verify:
1. Output size matches spec exactly
2. Transparent background has no halo in game UI
3. Watermark is gone or below visibility threshold
4. Subject is centered and not clipped

## Resource Map

1. `scripts/build_icon.py`: end-to-end icon conversion script (Pillow only).
2. `references/parameter-tuning.md`: parameter decision guide and scenario presets.
