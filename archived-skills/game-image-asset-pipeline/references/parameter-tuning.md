# Parameter Tuning Guide

Use this guide when default script parameters do not produce clean results.

## Quick Start Presets

### Preset A: Plain Background + Bottom-Right Watermark

```bash
python3 scripts/build_icon.py input.png output.png \
  --size 256 \
  --bg-threshold 32 \
  --watermark-corners br \
  --wm-area-ratio 0.28 \
  --wm-value-threshold 205 \
  --wm-sat-threshold 42
```

### Preset B: Strong Background Residue

```bash
python3 scripts/build_icon.py input.png output.png \
  --size 256 \
  --bg-threshold 40 \
  --wm-dilate 2
```

### Preset C: Foreground Edge Over-Removed

```bash
python3 scripts/build_icon.py input.png output.png \
  --size 256 \
  --bg-threshold 24 \
  --wm-value-threshold 220
```

## Parameter Meanings

1. `--bg-threshold`
Controls color distance tolerance for background detection.
Higher value removes more background but may eat into foreground edges.

2. `--border-width`
Controls how many border pixels are sampled to estimate background color.
Use larger values when border noise exists.

3. `--watermark-corners`
Limits watermark detection to specific corners: `tl,tr,bl,br,all,none`.

4. `--wm-area-ratio`
Sets corner search region size as a ratio of image width/height.
Increase when watermark sits farther from edges.

5. `--wm-value-threshold`
Minimum brightness for watermark candidate pixels.
Increase to keep more highlights; decrease to remove more bright marks.

6. `--wm-sat-threshold`
Maximum saturation for watermark candidate pixels.
Increase to capture colored/gray watermark pixels; decrease to be conservative.

7. `--wm-min-component`
Minimum connected component area for removal.
Increase to ignore tiny highlights/noise.

8. `--wm-max-component-ratio`
Maximum connected component area ratio inside corner region.
Decrease when too much foreground is removed in corners.

9. `--wm-dilate`
Expands watermark mask edges to clean anti-aliased text contours.

10. `--padding`
Controls transparent margin in final square icon.
Typical icon values are `0.06` to `0.12`.

## Debug Strategy

Use this order when results are wrong:
1. Fix foreground clipping first (`--bg-threshold` down).
2. Fix leftover background second (`--bg-threshold` up).
3. Tune watermark removal third (`--wm-*` options).
4. Tune framing last (`--padding`, `--size`).
