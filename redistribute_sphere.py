#!/usr/bin/env python3
"""
Replace UMAP-derived x/y/z coordinates (which all cluster in one hemisphere)
with Fibonacci sphere positions so all 171 emotion points are evenly spread
across the full sphere surface.

The ordering is preserved: point at index i keeps its label / metadata.
All extra fields (zh_label, short_en, nearest_neighbors, …) are kept intact.
"""
import json
import math
from pathlib import Path

LAYOUT_FILE = Path("emotion_sphere_layout.json")


def fibonacci_sphere(n: int) -> list[tuple[float, float, float]]:
    """
    Sunflower / Fibonacci lattice on unit sphere.
    Returns n points uniformly distributed on S^2.
    """
    golden = math.pi * (3.0 - math.sqrt(5.0))   # golden angle ≈ 2.399963
    pts = []
    for i in range(n):
        y = 1.0 - (i / (n - 1)) * 2.0           # y goes from +1 to -1
        r = math.sqrt(max(0.0, 1.0 - y * y))
        theta = golden * i
        x = math.cos(theta) * r
        z = math.sin(theta) * r
        pts.append((x, y, z))
    return pts


def main():
    layout = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))
    n = len(layout)
    print(f"Redistributing {n} points onto Fibonacci sphere …")

    new_coords = fibonacci_sphere(n)

    for i, item in enumerate(layout):
        x, y, z = new_coords[i]
        item["x"] = round(x, 8)
        item["y"] = round(y, 8)
        item["z"] = round(z, 8)

    LAYOUT_FILE.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")

    # Quick distribution check
    import math as m
    xs = [item["x"] for item in layout]
    ys = [item["y"] for item in layout]
    zs = [item["z"] for item in layout]
    print(f"x: [{min(xs):.3f}, {max(xs):.3f}]")
    print(f"y: [{min(ys):.3f}, {max(ys):.3f}]")
    print(f"z: [{min(zs):.3f}, {max(zs):.3f}]")
    print(f"Saved → {LAYOUT_FILE}")


if __name__ == "__main__":
    main()
