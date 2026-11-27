"""Reachability audit: can a player really get every item, starting from what the world gives?

check_coverage.py only asks "does a recipe or a process make X?". This asks the stronger question: starting from
what the world hands out (loot, block drops / harvest, animal harvest, traders' basics), and repeating until nothing
changes, which items can actually be made, counting that

  - a recipe needs all its ingredients, its crafting station (a block that is itself reachable) and its tool;
  - a chain process (Data/fe_processes.xml) needs its machine block, its item inputs and its fluid inputs
    (a fluid is available when some reachable process outputs it, or it comes from the world: water, latex,
    crude oil from the pump, steam from boilers / engines);

and reports what stays out of reach. Vanilla items that the game never hands to players (dev, admin, quest,
"NoTranslate" helpers...) are filtered with --all to show everything.

Usage: python tools/check_reach.py [--all] [--why ITEM]
"""
import re
import sys
from collections import defaultdict

from lxml import etree

import fe_common as fe

WORLD_FLUIDS = {"water", "latex", "crude_oil", "steam"}
# stations that need no block: hand crafting and the player's backpack
NO_STATION = {"", None}


def names_in_loot(root):
    out = set()
    for el in root.iter("item"):
        n = el.get("name")
        if n:
            out.add(n)
    return out


def drops(root):
    out = set()
    for el in root.iter("drop"):
        n = el.get("name")
        if n:
            out.add(n)
    return out


def main():
    blocks, _ = fe.patched("blocks.xml")
    items, _ = fe.patched("items.xml")
    recipes, _ = fe.patched("recipes.xml")
    loot = fe.load_vanilla("loot.xml").getroot()
    ents = fe.load_vanilla("entityclasses.xml").getroot()
    traders = fe.load_vanilla("traders.xml").getroot()
    procs = etree.parse(str(fe.MOD_DIR / "Data" / "fe_processes.xml")).getroot()

    block_names = {b.get("name") for b in blocks.getroot().iter("block")}
    item_names = {i.get("name") for i in items.getroot().iter("item")}

    world = set()
    world |= names_in_loot(loot)
    world |= drops(blocks.getroot())
    world |= drops(ents)
    world |= names_in_loot(traders)
    # filling an empty container at water (bucket, jar): items:Change_item_to
    for el in items.getroot().iter("property"):
        if el.get("name") == "Change_item_to" and el.get("value"):
            world.add(el.get("value"))
    # producer blocks (chicken coop, apiary, dew collector): block property OutputTypes, {type,..,item,item2,..}
    producers = {}
    for b in blocks.getroot().iter("block"):
        for el in b.iter("property"):
            if el.get("name") == "OutputTypes":
                outs = set()
                for grp in re.findall(r"\{([^}]*)\}", el.get("value") or ""):
                    f = grp.split(",")
                    if len(f) > 6:
                        outs |= {f[5], f[6]}
                producers[b.get("name")] = outs

    rec = []
    for r in recipes.getroot().iter("recipe"):
        if "salvageScrap" in (r.get("tags") or ""):
            continue
        ins = [i.get("name") for i in r.iter("ingredient") if int(i.get("count", "1") or 1) > 0]
        rec.append((r.get("name"), ins, r.get("craft_area"), r.get("craft_tool")))

    pro = []
    for p in procs.iter("process"):
        if p.get("planned") == "true":
            continue
        ins = [n for n in (p.get("input") or "").split(",") if n]
        fin = [n for n in (p.get("fluid_in") or "").split(",") if n]
        outs = [n for n in (p.get("output"), p.get("extra")) if n]
        fout = [n for n in (p.get("fluid_out") or "").split(",") if n]
        pro.append((p.get("id"), p.get("machine"), ins, fin, outs, fout))
    fluid_items = {}
    for f in procs.iter("fluid"):
        if f.get("item"):
            fluid_items[f.get("name")] = f.get("item")

    have = set(world)
    fluids = set(WORLD_FLUIDS)
    how = {}
    changed = True
    while changed:
        changed = False
        for blk, outs in producers.items():
            if blk in have:
                for o in outs - have:
                    have.add(o)
                    how[o] = "produced by " + blk
                    changed = True
        for out, ins, area, tool in rec:
            if out in have:
                continue
            if area not in NO_STATION and area not in have:
                continue
            if tool and tool not in have:
                continue
            if all(i in have for i in ins):
                have.add(out)
                how[out] = "recipe@" + (area or "hand")
                changed = True
        for pid, mach, ins, fin, outs, fout in pro:
            if mach not in have or not all(i in have for i in ins) or not all(f in fluids for f in fin):
                continue
            for o in outs:
                if o not in have:
                    have.add(o)
                    how[o] = "process " + pid
                    changed = True
            for f in fout:
                if f not in fluids:
                    fluids.add(f)
                    changed = True
                    if f in fluid_items and fluid_items[f] not in have:
                        have.add(fluid_items[f])
                        how[fluid_items[f]] = "bottled " + f

    if "--why" in sys.argv:
        x = sys.argv[sys.argv.index("--why") + 1]
        print(x, "->", how.get(x, "world" if x in world else "NOT REACHABLE"))
        for out, ins, area, tool in rec:
            if out == x:
                print("  recipe @", area, "tool", tool, "| missing:",
                      [i for i in ins if i not in have] + ([area] if area and area not in have else []))
        for pid, mach, ins, fin, outs, fout in pro:
            if x in outs:
                print("  process", pid, "| missing:", [i for i in ins if i not in have] +
                      ([mach] if mach not in have else []) + [f for f in fin if f not in fluids])
        return 0

    made = {r[0] for r in rec} | {o for p in pro for o in p[4]}
    # things somebody wants: recipe ingredients, process inputs, stations, machines
    wanted = set()
    for out, ins, area, tool in rec:
        wanted |= set(ins)
        if area:
            wanted.add(area)
        if tool:
            wanted.add(tool)
    for pid, mach, ins, fin, outs, fout in pro:
        wanted |= set(ins)
        wanted.add(mach)
    unreach_made = sorted(n for n in made if n not in have)
    # unit_iron, unit_clay...: the vanilla forge's internal smelting units (the forge is hidden by the mod, D1)
    unreach_wanted = sorted(n for n in wanted if n not in have and n not in made and not n.startswith("unit_"))
    dead_fluids = sorted({f for p in pro for f in p[3]} - fluids)
    print(f"world sources: {len(world)} names; reachable: {len(have)} items/blocks; fluids: {len(fluids)}")
    print(f"made by a recipe/process but NOT reachable: {len(unreach_made)}")
    for n in unreach_made:
        print("   ", n)
    print(f"needed as ingredient/station but never made nor found: {len(unreach_wanted)}")
    for n in unreach_wanted:
        print("   ", n)
    print(f"fluids asked for but never available: {len(dead_fluids)} {dead_fluids}")
    return 1 if (unreach_made or unreach_wanted or dead_fluids) else 0


if __name__ == "__main__":
    sys.exit(main())
