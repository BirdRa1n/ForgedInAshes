"""Points CustomIcon of every mod block/item that has its own icon (Mods/FerroEngrenagem/UIAtlases/ItemIconAtlas,
made by Art/feKinetic/render_icons.py) at that icon, with no tint. Re-run after adding icons.

Usage: python tools/apply_icons.py
"""
import re
from pathlib import Path

MOD = Path(__file__).resolve().parent.parent / "Mods" / "FerroEngrenagem"
icons = {p.stem for p in (MOD / "UIAtlases" / "ItemIconAtlas").glob("*.png")}
for f in ("blocks.xml", "items.xml"):
    path = MOD / "Config" / f
    s = path.read_text(encoding="utf-8")
    out, n = [], 0
    # each top-level <block name="..."> / <item name="..."> ... </block|item>
    pat = re.compile(r'(<(block|item) name="(fe[^"]*)"[^>]*>)(.*?)(</\2>)', re.S)
    pos = 0
    for m in pat.finditer(s):
        out.append(s[pos:m.start()])
        head, tag, name, body, end = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if name in icons:
            body = re.sub(r'\s*<property name="CustomIcon(Tint)?" value="[^"]*"\s*/>', "", body)
            indent = re.search(r'\n(\s*)<property', body)
            ind = indent.group(1) if indent else "\t\t"
            body = f'\n{ind}<property name="CustomIcon" value="{name}"/>\n{ind}<property name="CustomIconTint" value="ffffff"/>' + body
            n += 1
        out.append(head + body + end)
        pos = m.end()
    out.append(s[pos:])
    path.write_text("".join(out), encoding="utf-8")
    print(f, n, "icons applied")
