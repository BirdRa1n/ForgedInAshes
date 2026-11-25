"""Tileable conveyor belt band textures (Art/feFx/belt_band_Albedo.png, belt_band_Normal.png), made by code so they
tile exactly: u = across the belt (0..1 = the 0.32 m band), v = along the travel, one tile = 0.25 m = two molded
cross cleats (0.125 m apart, the old cleat spacing). Belt.cs (BeltShape) scrolls the texture offset with the belt
speed, so the whole band moves, cleats and dirt with it.

    python Art/feFx/make_belt_band.py
"""
import os

import numpy as np
from PIL import Image

W, H = 256, 512                       # u x v
OUT = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7102)


def tile_noise(scale_u, scale_v, octaves=4):
    """Periodic value noise (wraps in both directions)."""
    acc = np.zeros((H, W))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gu, gv = scale_u * 2 ** o, scale_v * 2 ** o
        g = rng.random((gv, gu))
        ys = np.linspace(0, gv, H, endpoint=False)
        xs = np.linspace(0, gu, W, endpoint=False)
        y0 = np.floor(ys).astype(int)
        x0 = np.floor(xs).astype(int)
        fy = (ys - y0)[:, None]
        fx = (xs - x0)[None, :]
        fy = fy * fy * (3 - 2 * fy)
        fx = fx * fx * (3 - 2 * fx)
        y1, x1 = (y0 + 1) % gv, (x0 + 1) % gu
        a = g[y0][:, x0]
        b = g[y0][:, x1]
        c = g[y1][:, x0]
        d = g[y1][:, x1]
        acc += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
        tot += amp
        amp *= 0.5
    return acc / tot


v = (np.arange(H) + 0.5)[:, None] / H          # 0..1 along the travel (one tile)
u = (np.arange(W) + 0.5)[None, :] / W          # 0..1 across
height = np.zeros((H, W))
# two molded chevron cleats per tile (pointing along the travel, like real chevron belts)
for c0 in (0.25, 0.75):
    centre = c0 + 0.10 * np.abs(u - 0.5)       # chevron: the sides trail behind the middle
    d = np.abs(((v - centre + 0.5) % 1.0) - 0.5)
    rib = np.clip(1.0 - d / 0.018, 0, 1)
    rib = rib ** 0.6 * (np.abs(u - 0.5) < 0.44)  # stops short of the belt edges
    height = np.maximum(height, rib)
# edges: a slightly raised bead along both sides
height = np.maximum(height, 0.35 * np.clip(1 - np.minimum(u, 1 - u) / 0.025, 0, 1))
grain = tile_noise(16, 32, 4)
height += 0.06 * (grain - 0.5)

# albedo: worn black rubber, dusty in the low parts, the cleat tops polished a bit lighter, scuffs along the travel
dust = tile_noise(4, 8, 5)
scuff = tile_noise(64, 4, 2)                    # streaks along v
base = 0.030 + 0.02 * (grain - 0.5)
col = np.stack([base, base, base * 0.95], -1)
low = (1 - np.clip(height * 2.5, 0, 1))[..., None]
col = col + low * np.clip(dust - 0.50, 0, 1)[..., None] * np.array([0.20, 0.17, 0.13]) * 0.6
# the cleats: worn, lighter tops and dark dirt caught along their feet
col = col + np.clip(height - 0.55, 0, 1)[..., None] * 0.16
foot = np.clip(height, 0, 1) * (height < 0.5)
col = col * (1 - 0.6 * foot[..., None])
col = col + (np.clip(scuff - 0.62, 0, 1) * 0.15)[..., None] * np.array([0.30, 0.28, 0.25])
col = np.clip(col, 0, 1)
Image.fromarray((col ** (1 / 2.2) * 255).astype(np.uint8), "RGB").save(os.path.join(OUT, "belt_band_Albedo.png"))

# normal map (OpenGL / Unity: +Y up) from the height, wrapping at the borders
k = 2.2
dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * k
dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * k
n = np.stack([-dx, dy, np.ones_like(dx)], -1)
n /= np.linalg.norm(n, axis=-1, keepdims=True)
Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(os.path.join(OUT, "belt_band_Normal.png"))
print("belt band textures ->", OUT)
