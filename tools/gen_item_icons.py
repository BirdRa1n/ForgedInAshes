"""Item icons with the LOCAL SDXL (F:\\IA, ComfyUI): no Blender modelling, no cloud tokens.

For each line of Art/feIcons/prompts.txt (<item>|<description>|<seed>) without an icon yet (or all with --force):
SDXL draws the object on a plain white background (F:\\IA\\saida\\icones\\<item>.png, kept to pick / redo), the white
connected to the border is cut away, the object is cropped, padded and scaled to the game's 160 x 160 transparent
icon in Mods/FerroEngrenagem/UIAtlases/ItemIconAtlas/<item>.png. Then run tools/apply_icons.py.

    F:\\IA\\iniciar_comfyui.bat            (leave it open)
    python tools/gen_item_icons.py [--force] [--only feTire,feRim] [--passos 24]
"""
import argparse
import os
import sys

from PIL import Image, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IA = os.environ.get("FE_IA", r"F:\IA")
sys.path.insert(0, os.path.join(IA, "fe_ia"))
import fe_ia  # noqa: E402  (ComfyUI client: grafo_sdxl, executar, baixar)

ICONS = os.path.join(REPO, "Mods", "FerroEngrenagem", "UIAtlases", "ItemIconAtlas")
RAW = os.path.join(IA, "saida", "icones")
STYLE = ("game inventory icon of a {d}, single isolated object, centered, whole object visible, three-quarter view "
         "from above, worn used post-apocalyptic look, gritty realistic, soft even studio light, sharp, "
         "isolated on a flat solid pure {bg} background, chroma key background")
NEG = fe_ia.NEG_CONCEITO + ", hands, people, table, floor, scene, gradient background, two objects, cut off"


def key_of(desc):
    """Chroma key colour: green, or magenta for things that are green themselves."""
    return "magenta" if "green" in desc else "green"


def cut_out(src, dst, bg, size=160, margin=0.06, loose=False):
    """Removes the background: its colour is measured on the image border (SDXL paints the "chroma" background
    muted and with shadows), then every pixel connected to the border whose chromaticity is close to it (darker =
    a shadow on it, still background) is cut. Crops, pads to a square, scales to the icon."""
    im = Image.open(src).convert("RGB").resize((512, 512), Image.LANCZOS)
    w, h = im.size
    px = im.load()

    def chroma(c):
        t = c[0] + c[1] + c[2] + 1e-3
        return (c[0] / t, c[1] / t, c[2] / t)
    border = [px[x, y] for x in range(0, w, 4) for y in (0, 1, h - 2, h - 1)] +              [px[x, y] for y in range(0, h, 4) for x in (0, 1, w - 2, w - 1)]
    border.sort(key=lambda c: c[1] - (c[0] + c[2]) / 2)
    ref = border[len(border) // 2]
    rc = chroma(ref)
    rsat = max(rc) - min(rc)

    def is_bg(c):
        cc = chroma(c)
        d = abs(cc[0] - rc[0]) + abs(cc[1] - rc[1]) + abs(cc[2] - rc[2])
        if loose:                                       # a pale "floor" SDXL drew under the object
            return d < 0.7 * rsat + 0.05 and sum(c) < sum(ref) * 2.4 + 60
        return d < 0.45 * rsat + 0.03 and sum(c) < sum(ref) * 1.6 + 40
    bgmask = bytearray(w * h)
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        i = y * w + x
        if bgmask[i] or not is_bg(px[x, y]):
            continue
        bgmask[i] = 1
        if x > 0: stack.append((x - 1, y))
        if x < w - 1: stack.append((x + 1, y))
        if y > 0: stack.append((x, y - 1))
        if y < h - 1: stack.append((x, y + 1))
    # background caught inside a hole (a tyre, a ring): the same colour, stricter, anywhere
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if not bgmask[i]:
                c = px[x, y]
                cc = chroma(c)
                if abs(cc[0] - rc[0]) + abs(cc[1] - rc[1]) + abs(cc[2] - rc[2]) < 0.12 * rsat + 0.01 and                         abs(sum(c) - sum(ref)) < 60:
                    bgmask[i] = 1
    alpha = Image.frombytes("L", (w, h), bytes(0 if m else 255 for m in bgmask))
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    # despill: the background colour bleeding on the object's edge
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if bg == "green" and g > max(r, b):
                px[x, y] = (r, max(r, b), b)
            elif bg == "magenta" and min(r, b) > g:
                px[x, y] = (g + (r - min(r, b)), g, g + (b - min(r, b)))
    rgba = im.copy()
    rgba.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 60 else 0).getbbox()
    if not box:
        raise RuntimeError("nothing left after the background cut")
    rgba = rgba.crop(box)
    side = int(max(rgba.size) * (1 + 2 * margin))
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(rgba, ((side - rgba.size[0]) // 2, (side - rgba.size[1]) // 2), rgba)
    sq = sq.resize((size, size), Image.LANCZOS)
    sq.save(dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--passos", type=int, default=24)
    ap.add_argument("--recut", action="store_true", help="only redo the cut from the saved SDXL images")
    ap.add_argument("--loose", action="store_true", help="looser background cut (a pale floor under the object)")
    a = ap.parse_args()
    only = {s for s in a.only.split(",") if s}
    if not a.recut and not fe_ia.servidor_ok():
        raise SystemExit("ComfyUI is not running: start F:\\IA\\iniciar_comfyui.bat")
    os.makedirs(RAW, exist_ok=True)
    done = 0
    for line in open(os.path.join(REPO, "Art", "feIcons", "prompts.txt"), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        item, desc, seed = line.split("|")
        if only and item not in only:
            continue
        dst = os.path.join(ICONS, item + ".png")
        raw = os.path.join(RAW, item + ".png")
        if os.path.exists(dst) and not (a.force or only or a.recut):
            continue
        if not a.recut or not os.path.exists(raw):
            saidas, t = fe_ia.executar(fe_ia.grafo_sdxl(STYLE.format(d=desc, bg=key_of(desc)), NEG, 1024, 1024, int(seed), a.passos,
                                                         6.5, False, "fe/icone_" + item))
            fe_ia.baixar(next(fe_ia._arquivos(saidas)), raw)
        cut_out(raw, dst, key_of(desc), loose=a.loose)
        done += 1
        print("[icon]", item, flush=True)
    print("icons made:", done)


if __name__ == "__main__":
    main()
