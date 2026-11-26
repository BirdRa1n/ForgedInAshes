"""Builds the documentation artwork from the mod's own inventory icons (never game assets).

    python tools/gen_docs_art.py

Writes:
  docs/assets/banner.png          README hero (1600 x 520)
  docs/assets/social-preview.png  GitHub social preview (1280 x 640, Settings > General > Social preview)
  docs/assets/machines.png        icon showcase strip (1600 x 260)
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parent.parent
ICONS = REPO / "Mods" / "ForgedInAshes" / "UIAtlases" / "ItemIconAtlas"
OUT = REPO / "docs" / "assets"
FONTS = Path("C:/Windows/Fonts")

BG_TOP = (11, 13, 16)
BG_BOTTOM = (21, 24, 29)
BRASS = (232, 163, 61)
EMBER = (214, 92, 36)
TEXT = (232, 234, 237)
MUTED = (150, 158, 168)

HERO = ["feSteamTurbine", "feBoilerDrum", "feGearbox", "feFoundry", "feSteamEngine", "feAssembler", "feConveyor",
        "fePipe", "feCrusher", "feDynamo2"]
STRIP = ["feCrank", "feWaterWheel", "feShaft", "feGearbox", "feSpeedBox", "feClutch", "feElectricMotor", "feCoalEngine",
         "feSteamEngine", "feBoilerFirebox", "feBoilerDrum", "feSteamTurbine", "feDynamo2", "feCondenser", "fePipe",
         "feMechPump", "feTankLiquid", "feCompressor", "feConveyor", "feFunnel", "feMechArm", "feBeltSplitter",
         "feFoundry", "feCaster", "fePress", "feLathe", "feAmmoPress", "feAssembler", "feCrusher", "feRefinery",
         "feMechDrill", "feMechSaw", "feSignalLever", "feDisplayPanel"]


def font(name, size):
    for n in (name, "segoeuib.ttf", "arial.ttf"):
        p = FONTS / n
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def background(w, h):
    img = Image.new("RGB", (w, h), BG_TOP)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    # ember glow from the lower right, like a furnace mouth
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, r = int(w * 0.78), int(h * 1.05), int(h * 0.95)
    for i in range(r, 0, -6):
        k = (1 - i / r) ** 2
        gd.ellipse((cx - i * 1.6, cy - i, cx + i * 1.6, cy + i), fill=tuple(int(c * k * 0.55) for c in EMBER))
    img = _add(img, glow.filter(ImageFilter.GaussianBlur(40)))
    # faint blueprint grid
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, w, 40):
        d.line((x, 0, x, h), fill=(255, 255, 255, 9))
    for y in range(0, h, 40):
        d.line((0, y, w, y), fill=(255, 255, 255, 9))
    return img


def _add(a, b):
    from PIL import ImageChops
    return ImageChops.add(a, b)


def icon(name, size):
    p = ICONS / (name + ".png")
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    return im.resize((size, size), Image.LANCZOS)


def shadowed(base, im, xy, blur=10, offset=(0, 8), alpha=150):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].point(lambda v: v * alpha // 255))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(sh, (xy[0] + offset[0], xy[1] + offset[1]))
    base.alpha_composite(im, xy)


def title_block(img, x, y, title_size, sub, sub_size, tag):
    d = ImageDraw.Draw(img)
    f_tag = font("consolab.ttf", int(sub_size * 0.72))
    d.text((x, y), tag, font=f_tag, fill=BRASS)
    y += int(sub_size * 1.3)
    f_title = font("bahnschrift.ttf", title_size)
    # "Forged" in light, "InAshes" in brass
    d.text((x, y), "Forged", font=f_title, fill=TEXT)
    wf = d.textlength("Forged", font=f_title)
    d.text((x + wf, y), "InAshes", font=f_title, fill=BRASS)
    y += int(title_size * 1.12)
    f_sub = font("segoeui.ttf", sub_size)
    for line in sub:
        d.text((x, y), line, font=f_sub, fill=MUTED)
        y += int(sub_size * 1.35)
    # brass rule
    d.rectangle((x, y + 10, x + 120, y + 14), fill=BRASS)


def arc_of_icons(img, names, cx, cy, radius, size):
    n = len(names)
    for k, name in enumerate(names):
        a = math.radians(200 + k * (140 / max(1, n - 1)))
        x = int(cx + radius * math.cos(a) * 1.15)
        y = int(cy + radius * math.sin(a) * 0.55)
        s = int(size * (0.8 + 0.25 * math.sin(math.radians(k * 37))))
        im = icon(name, s)
        if im is not None:
            shadowed(img, im, (x - s // 2, y - s // 2))


def banner():
    w, h = 1600, 520
    img = background(w, h).convert("RGBA")
    # icon cluster on the right
    pos = [(1180, 150, 230), (1400, 120, 170), (1000, 300, 150), (1290, 340, 190), (1490, 300, 140),
           (1080, 110, 120), (960, 450, 100), (1530, 440, 100), (1150, 440, 110), (960, 180, 90)]
    for name, (x, y, s) in sorted(zip(HERO, pos), key=lambda t: t[1][2]):
        im = icon(name, s)
        if im is not None:
            shadowed(img, im, (x - s // 2, y - s // 2))
    title_block(img, 90, 120, 112, ["Industrial automation for 7 Days to Die.",
                                    "Torque, fluids, conveyors and steam power, built from scrap."], 30,
                "7 DAYS TO DIE  ·  MOD  ·  V3.4")
    img.convert("RGB").save(OUT / "banner.png", optimize=True)


def social():
    w, h = 1280, 640
    img = background(w, h).convert("RGBA")
    pos = [(960, 240, 250), (1150, 190, 170), (800, 420, 160), (1080, 450, 190), (1200, 400, 120),
           (850, 170, 120), (700, 520, 100), (1220, 560, 100), (950, 560, 110), (1235, 75, 80)]
    for name, (x, y, s) in sorted(zip(HERO, pos), key=lambda t: t[1][2]):
        im = icon(name, s)
        if im is not None:
            shadowed(img, im, (x - s // 2, y - s // 2))
    title_block(img, 70, 200, 96, ["Industrial automation", "for 7 Days to Die."], 34, "7 DAYS TO DIE  ·  MOD")
    img.convert("RGB").save(OUT / "social-preview.png", optimize=True)


def strip():
    cols, size, gap = 17, 78, 14
    rows = math.ceil(len(STRIP) / cols)
    w = 1600
    h = 60 + rows * (size + gap) + 20
    img = background(w, h).convert("RGBA")
    x0 = (w - (cols * size + (cols - 1) * gap)) // 2
    for k, name in enumerate(STRIP):
        r, c = divmod(k, cols)
        im = icon(name, size)
        if im is not None:
            shadowed(img, im, (x0 + c * (size + gap), 40 + r * (size + gap)), blur=6, offset=(0, 4))
    img.convert("RGB").save(OUT / "machines.png", optimize=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    banner()
    social()
    strip()
    print("docs art:", ", ".join(p.name for p in sorted(OUT.glob("*.png"))))
