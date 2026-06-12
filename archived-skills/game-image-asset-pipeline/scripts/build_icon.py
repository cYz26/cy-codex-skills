#!/usr/bin/env python3
"""
Convert AI-generated images into game-ready icon PNGs.

Pipeline:
1) Remove connected plain background from image borders.
2) Remove bright low-saturation corner watermarks.
3) Crop to non-transparent content.
4) Resize and center onto a square transparent canvas.
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path
from typing import Iterable

from PIL import Image

VALID_CORNERS = {"tl", "tr", "bl", "br"}


def parse_corners(raw: str) -> list[str]:
    text = raw.strip().lower()
    if not text or text == "none":
        return []
    if text == "all":
        return ["tl", "tr", "bl", "br"]

    corners: list[str] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        if token not in VALID_CORNERS:
            raise ValueError(
                f"Unsupported corner '{token}'. Use one of: tl,tr,bl,br,all,none."
            )
        if token not in corners:
            corners.append(token)
    return corners


def median(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2


def estimate_border_color(img: Image.Image, border_width: int) -> tuple[int, int, int]:
    w, h = img.size
    bw = max(1, min(border_width, min(w, h) // 2))
    px = img.load()
    rs: list[int] = []
    gs: list[int] = []
    bs: list[int] = []

    for x in range(w):
        for y in range(bw):
            r, g, b, _ = px[x, y]
            rs.append(r)
            gs.append(g)
            bs.append(b)
        for y in range(h - bw, h):
            r, g, b, _ = px[x, y]
            rs.append(r)
            gs.append(g)
            bs.append(b)

    for y in range(bw, h - bw):
        for x in range(bw):
            r, g, b, _ = px[x, y]
            rs.append(r)
            gs.append(g)
            bs.append(b)
        for x in range(w - bw, w):
            r, g, b, _ = px[x, y]
            rs.append(r)
            gs.append(g)
            bs.append(b)

    return median(rs), median(gs), median(bs)


def build_connected_background_mask(
    img: Image.Image, bg_rgb: tuple[int, int, int], threshold: int
) -> bytearray:
    w, h = img.size
    px = img.load()
    total = w * h
    threshold_sq = max(0, threshold) ** 2

    candidate = bytearray(total)
    idx = 0
    br, bg, bb = bg_rgb
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                candidate[idx] = 1
            else:
                dr = r - br
                dg = g - bg
                db = b - bb
                if dr * dr + dg * dg + db * db <= threshold_sq:
                    candidate[idx] = 1
            idx += 1

    background = bytearray(total)
    queue: deque[int] = deque()

    def enqueue(x: int, y: int) -> None:
        i = y * w + x
        if candidate[i] and not background[i]:
            background[i] = 1
            queue.append(i)

    for x in range(w):
        enqueue(x, 0)
        enqueue(x, h - 1)
    for y in range(h):
        enqueue(0, y)
        enqueue(w - 1, y)

    while queue:
        i = queue.popleft()
        x = i % w
        y = i // w

        if x > 0:
            j = i - 1
            if candidate[j] and not background[j]:
                background[j] = 1
                queue.append(j)
        if x < w - 1:
            j = i + 1
            if candidate[j] and not background[j]:
                background[j] = 1
                queue.append(j)
        if y > 0:
            j = i - w
            if candidate[j] and not background[j]:
                background[j] = 1
                queue.append(j)
        if y < h - 1:
            j = i + w
            if candidate[j] and not background[j]:
                background[j] = 1
                queue.append(j)

    return background


def apply_alpha_mask(img: Image.Image, mask: bytearray) -> int:
    w, h = img.size
    px = img.load()
    changed = 0
    for i, flagged in enumerate(mask):
        if not flagged:
            continue
        x = i % w
        y = i // w
        r, g, b, a = px[x, y]
        if a != 0:
            px[x, y] = (r, g, b, 0)
            changed += 1
    return changed


def corner_bounds(corner: str, w: int, h: int, area_ratio: float) -> tuple[int, int, int, int]:
    cw = max(1, min(w, int(round(w * area_ratio))))
    ch = max(1, min(h, int(round(h * area_ratio))))

    if corner == "tl":
        return 0, 0, cw, ch
    if corner == "tr":
        return w - cw, 0, w, ch
    if corner == "bl":
        return 0, h - ch, cw, h
    return w - cw, h - ch, w, h


def collect_watermark_mask(
    img: Image.Image,
    corners: Iterable[str],
    area_ratio: float,
    value_threshold: int,
    sat_threshold: int,
    min_component: int,
    max_component_ratio: float,
) -> bytearray:
    w, h = img.size
    px = img.load()
    total = w * h
    mask = bytearray(total)
    area_ratio = max(0.05, min(area_ratio, 0.5))
    max_component_ratio = max(0.001, min(max_component_ratio, 0.5))

    for corner in corners:
        x0, y0, x1, y1 = corner_bounds(corner, w, h, area_ratio)
        rw = x1 - x0
        rh = y1 - y0
        region_size = rw * rh
        if region_size == 0:
            continue

        candidate = bytearray(region_size)
        for ly in range(rh):
            gy = y0 + ly
            for lx in range(rw):
                gx = x0 + lx
                r, g, b, a = px[gx, gy]
                if a == 0:
                    continue
                vmax = max(r, g, b)
                if vmax < value_threshold:
                    continue
                vmin = min(r, g, b)
                sat = 0 if vmax == 0 else int((vmax - vmin) * 255 / vmax)
                if sat <= sat_threshold:
                    candidate[ly * rw + lx] = 1

        visited = bytearray(region_size)
        max_component = max(min_component, int(round(region_size * max_component_ratio)))

        for start in range(region_size):
            if not candidate[start] or visited[start]:
                continue

            queue: deque[int] = deque([start])
            visited[start] = 1
            component: list[int] = []

            while queue:
                i = queue.popleft()
                component.append(i)
                lx = i % rw
                ly = i // rw

                if lx > 0:
                    j = i - 1
                    if candidate[j] and not visited[j]:
                        visited[j] = 1
                        queue.append(j)
                if lx < rw - 1:
                    j = i + 1
                    if candidate[j] and not visited[j]:
                        visited[j] = 1
                        queue.append(j)
                if ly > 0:
                    j = i - rw
                    if candidate[j] and not visited[j]:
                        visited[j] = 1
                        queue.append(j)
                if ly < rh - 1:
                    j = i + rw
                    if candidate[j] and not visited[j]:
                        visited[j] = 1
                        queue.append(j)

            area = len(component)
            if area < min_component or area > max_component:
                continue

            for local_i in component:
                lx = local_i % rw
                ly = local_i // rw
                gx = x0 + lx
                gy = y0 + ly
                global_i = gy * w + gx
                mask[global_i] = 1

    return mask


def dilate_mask(mask: bytearray, w: int, h: int, iterations: int) -> bytearray:
    result = bytearray(mask)
    for _ in range(max(0, iterations)):
        expanded = bytearray(result)
        for i, flagged in enumerate(result):
            if not flagged:
                continue
            x = i % w
            y = i // w
            for dy in (-1, 0, 1):
                ny = y + dy
                if ny < 0 or ny >= h:
                    continue
                for dx in (-1, 0, 1):
                    nx = x + dx
                    if nx < 0 or nx >= w:
                        continue
                    expanded[ny * w + nx] = 1
        result = expanded
    return result


def render_square_icon(img: Image.Image, size: int, padding: float) -> Image.Image:
    if size <= 0:
        raise ValueError("--size must be a positive integer.")
    if not (0.0 <= padding < 0.5):
        raise ValueError("--padding must be between 0.0 (inclusive) and 0.5 (exclusive).")

    alpha_bbox = img.getchannel("A").getbbox()
    if not alpha_bbox:
        raise ValueError("No visible foreground after processing. Adjust thresholds and retry.")

    cropped = img.crop(alpha_bbox)
    cw, ch = cropped.size

    target_inner = max(1, int(round(size * (1.0 - 2.0 * padding))))
    scale = min(target_inner / cw, target_inner / ch)
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))

    resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ox = (size - nw) // 2
    oy = (size - nh) // 2
    canvas.alpha_composite(resized, (ox, oy))
    return canvas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a transparent square game icon from an AI-generated image."
    )
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output PNG path")
    parser.add_argument("--size", type=int, default=256, help="Output square size (default: 256)")
    parser.add_argument(
        "--padding",
        type=float,
        default=0.08,
        help="Transparent padding ratio around subject, 0.0~<0.5 (default: 0.08)",
    )
    parser.add_argument(
        "--bg-threshold",
        type=int,
        default=32,
        help="Background color distance threshold (default: 32)",
    )
    parser.add_argument(
        "--border-width",
        type=int,
        default=4,
        help="Border sampling width in pixels for background estimation (default: 4)",
    )
    parser.add_argument(
        "--keep-background",
        action="store_true",
        help="Skip automatic background removal",
    )
    parser.add_argument(
        "--watermark-corners",
        default="br",
        help="Corners to clean watermark: tl,tr,bl,br,all,none (default: br)",
    )
    parser.add_argument(
        "--wm-area-ratio",
        type=float,
        default=0.28,
        help="Per-corner search area ratio (default: 0.28)",
    )
    parser.add_argument(
        "--wm-value-threshold",
        type=int,
        default=205,
        help="Watermark brightness threshold (default: 205)",
    )
    parser.add_argument(
        "--wm-sat-threshold",
        type=int,
        default=42,
        help="Watermark saturation upper bound (default: 42)",
    )
    parser.add_argument(
        "--wm-min-component",
        type=int,
        default=25,
        help="Minimum connected component size for watermark removal (default: 25)",
    )
    parser.add_argument(
        "--wm-max-component-ratio",
        type=float,
        default=0.10,
        help="Max component ratio within corner region (default: 0.10)",
    )
    parser.add_argument(
        "--wm-dilate",
        type=int,
        default=1,
        help="Mask dilation iterations for anti-aliased edges (default: 1)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        corners = parse_corners(args.watermark_corners)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    image = Image.open(input_path).convert("RGBA")
    width, height = image.size
    bg_removed = 0
    wm_removed = 0

    if not args.keep_background:
        bg_rgb = estimate_border_color(image, args.border_width)
        bg_mask = build_connected_background_mask(image, bg_rgb, args.bg_threshold)
        bg_removed = apply_alpha_mask(image, bg_mask)

    if corners:
        wm_mask = collect_watermark_mask(
            image,
            corners=corners,
            area_ratio=args.wm_area_ratio,
            value_threshold=args.wm_value_threshold,
            sat_threshold=args.wm_sat_threshold,
            min_component=args.wm_min_component,
            max_component_ratio=args.wm_max_component_ratio,
        )
        wm_mask = dilate_mask(wm_mask, width, height, args.wm_dilate)
        wm_removed = apply_alpha_mask(image, wm_mask)

    try:
        icon = render_square_icon(image, size=args.size, padding=args.padding)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    icon.save(output_path, format="PNG")

    print(f"[OK] Wrote: {output_path}")
    print(f"[INFO] background_pixels_removed={bg_removed}")
    print(f"[INFO] watermark_pixels_removed={wm_removed}")
    print(f"[INFO] output_size={args.size}x{args.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
