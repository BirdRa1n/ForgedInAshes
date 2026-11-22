"""Find every way a player can obtain (or use) an item in vanilla Data/Config.

Usage:
  python tools/find_sources.py <itemName> [<itemName> ...] [--mod]
  python tools/find_sources.py --search "short iron pipe"

  --mod     search the files with the mod's patches applied
  --uses    list every recipe that uses the item as an ingredient
  --search  look up item/block keys by their English name (Localization.csv)

Sections: recipe output, ingredient use, loot, block drops (Harvest/Destroy/
Fall, incl. tool_category Disassemble = salvage), traders, quests,
progression unlocks, and a catch-all of any other attribute mentioning it.
"""
import csv
import difflib
import re
import sys

import fe_common as fe

FILES = ["recipes.xml", "loot.xml", "blocks.xml", "items.xml", "traders.xml",
         "quests.xml", "progression.xml", "entityclasses.xml", "buffs.xml",
         "gameevents.xml", "challenges.xml"]


def mentions(value: str, name: str) -> bool:
    return value == name or name in re.split(r"[,\s]+", value)


def ancestor_named(e, tag):
    for a in e.iterancestors():
        if a.tag == tag:
            return a.get("name") or a.get("id") or ""
    return ""


def load(rel, use_mod):
    if use_mod:
        return fe.patched(rel)[0]
    return fe.load_vanilla(rel)


def report(name, trees):
    out = []
    add = lambda sec, txt: out.append((sec, txt))

    r = trees["recipes.xml"].getroot()
    for rec in r.iter("recipe"):
        area = rec.get("craft_area") or "(inventory)"
        if rec.get("name") == name:
            ing = ", ".join(f"{g.get('name')} x{g.get('count', '1')}" for g in rec.iter("ingredient"))
            add("recipe (produces)", f"count={rec.get('count', '1')} area={area} "
                f"tool={rec.get('craft_tool', '')} <- {ing}")
        for g in rec.iter("ingredient"):
            if g.get("name") == name:
                add("recipe (ingredient)", f"{rec.get('name')} @ {area} uses x{g.get('count', '1')}")

    for it in trees["loot.xml"].getroot().iter("item"):
        if it.get("name") == name:
            parent = it.getparent()
            add("loot", f"{parent.tag} '{parent.get('name')}' count={it.get('count', '')} "
                f"prob={it.get('prob', '')} template={it.get('loot_prob_template', '')}")

    for d in trees["blocks.xml"].getroot().iter("drop"):
        if d.get("name") == name:
            add("block drop", f"{ancestor_named(d, 'block')} event={d.get('event')} "
                f"tool={d.get('tool_category') or '-'} count={d.get('count', '')} prob={d.get('prob', '1')}")

    for it in trees["traders.xml"].getroot().iter("item"):
        if it.get("name") == name:
            parent = it.getparent()
            where = parent.get("name") or ancestor_named(it, "trader_info") or parent.tag
            add("trader", f"{parent.tag} '{where}' count={it.get('count', '')} prob={it.get('prob', '')}")

    for rw in trees["quests.xml"].getroot().iter("reward"):
        if mentions(rw.get("id", ""), name) or mentions(rw.get("value", ""), name):
            add("quest reward", f"quest '{ancestor_named(rw, 'quest')}' type={rw.get('type')} "
                f"id={rw.get('id')} value={rw.get('value')}")

    for ue in trees["progression.xml"].getroot().iter("unlock_entry", "display_entry"):
        if mentions(ue.get("item", ""), name) or mentions(ue.get("recipes", ""), name):
            add("progression unlock", f"{ancestor_named(ue, 'crafting_skill')} {ue.tag} "
                f"item={ue.get('item')} recipes={ue.get('recipes', '')}")

    # Catch-all: any other attribute in any file that mentions the name.
    covered = {("recipes.xml", "recipe"), ("recipes.xml", "ingredient"), ("loot.xml", "item"),
               ("blocks.xml", "drop"), ("traders.xml", "item"), ("quests.xml", "reward"),
               ("progression.xml", "unlock_entry"), ("progression.xml", "display_entry")}
    for f, t in trees.items():
        for e in t.getroot().iter():
            if not isinstance(e.tag, str) or (f, e.tag) in covered:
                continue
            if f in ("items.xml", "blocks.xml") and e.tag in ("item", "block") and e.get("name") == name:
                add("definition", f"{f}: <{e.tag} name='{name}'>")
                continue
            for k, val in e.attrib.items():
                if k != "name" or e.tag not in ("item", "block"):
                    if mentions(val, name):
                        owner = ancestor_named(e, "item") or ancestor_named(e, "block") or ""
                        add("other mention", f"{f}: {owner} <{e.tag} {k}='{val[:80]}'>")
                        break
    return out


def search(text):
    loc = fe.vanilla_config() / "Localization.csv"
    words = text.lower()
    with loc.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            eng = (row.get("english") or "")
            if (words in eng.lower() and row.get("File") in ("items", "blocks")
                    and not row["Key"].endswith("Desc")):
                print(f"{row['Key']:<40} [{row['File']}] {eng}")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--search" in sys.argv:
        search(" ".join(args))
        return 0
    if not args:
        print(__doc__)
        return 2
    use_mod = "--mod" in sys.argv
    trees = {f: load(f, use_mod) for f in FILES if (fe.vanilla_config() / f).exists()}
    known = {e.get("name") for f in ("items.xml", "blocks.xml")
             for e in trees[f].getroot() if isinstance(e.tag, str)}
    for name in args:
        print(f"===== {name}" + ("  (with mod patches)" if use_mod else ""))
        if name not in known:
            close = difflib.get_close_matches(name, [k for k in known if k], n=5)
            print(f"  !! '{name}' is not an item/block name. Close: {', '.join(close) or '-'}")
        rows = report(name, trees)
        if "--uses" not in sys.argv:
            uses = [r for r in rows if r[0] == "recipe (ingredient)"]
            rows = [r for r in rows if r[0] != "recipe (ingredient)"]
            if uses:
                rows.append(("recipe (ingredient)", f"used in {len(uses)} recipe(s); --uses lists them"))
        if not rows:
            print("  (no sources or uses found)")
        last = None
        for sec, txt in rows:
            if sec != last:
                print(f"  [{sec}]")
                last = sec
            print(f"    {txt}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
