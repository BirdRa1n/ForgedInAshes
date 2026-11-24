"""F8.0: validate Mods/FerroEngrenagem/Data/fe_processes.xml (the chain craft, PLANO_CRAFT.md).

Checks:
  - every item / machine / fluid a process names exists (game + mod, after the mod's patches) or is declared in the
    file; a declared one that is not planned must exist in the game data;
  - a non-planned process uses only things that exist now (the DLL runs it);
  - kinds, numbers and molds make sense (a cast has a mold that accepts its metal);
  - every planned item is made by some process, every chain step is a known process id, and a chain's last step
    makes its product.

Usage: python tools/check_processes.py
"""
import re
import sys
from pathlib import Path

from lxml import etree

import fe_common as fe

FILE = fe.MOD_DIR / "Data" / "fe_processes.xml"
KINDS = {"melt", "cast", "press", "turn", "crush", "wash", "mix", "dry", "distill", "spin", "assemble", "sequence"}
BASE_FLUIDS = set()


def base_fluids():
    src = (fe.REPO / "src" / "FerroEngrenagem" / "FluidNetwork.cs").read_text(encoding="utf-8")
    return set(re.findall(r'public const string \w+ = "(\w+)";', src))


def split(v):
    return [x for x in (v or "").split(",") if x]


def main():
    problems = []
    items_tree, _ = fe.patched("items.xml")
    blocks_tree, _ = fe.patched("blocks.xml")
    game_items = {e.get("name") for e in items_tree.iter("item")}
    game_blocks = {e.get("name") for e in blocks_tree.iter("block")}
    fluids = {f: False for f in base_fluids()}

    root = etree.parse(str(FILE)).getroot()
    items, machines = {}, {}
    for e in root.iter("fluid"):
        fluids[e.get("name")] = e.get("planned") == "true"
    for e in root.iter("machine"):
        machines[e.get("name")] = e.get("planned") == "true"
        if e.get("planned") != "true" and e.get("name") not in game_blocks:
            problems.append("machine %s is not planned but not in blocks.xml" % e.get("name"))
    for e in root.iter("item"):
        items[e.get("name")] = e.get("planned") == "true"
        if e.get("planned") != "true" and e.get("name") not in game_items:
            problems.append("item %s is not planned but not in items.xml" % e.get("name"))
        for m in split(e.get("metals")):
            if m not in fluids:
                problems.append("item %s: mold metal %s is not a fluid" % (e.get("name"), m))

    def item_state(n):
        """None = unknown, True = planned only, False = exists now"""
        if n in game_items:
            return False
        return items.get(n)

    procs = {}
    made = set()
    for p in root.iter("process"):
        pid = p.get("id")
        where = "process %s" % pid
        if not pid or pid in procs:
            problems.append("%s: missing or duplicate id" % where)
        procs[pid] = p
        planned = p.get("planned") == "true"
        if p.get("kind") not in KINDS:
            problems.append("%s: unknown kind %s" % (where, p.get("kind")))
        m = p.get("machine")
        if m not in machines:
            problems.append("%s: machine %s not declared" % (where, m))
        elif machines[m] and not planned:
            problems.append("%s: runs on planned machine %s but is not planned" % (where, m))
        ins, counts = split(p.get("input")), split(p.get("count"))
        if ins and len(ins) != len(counts):
            problems.append("%s: %d inputs but %d counts" % (where, len(ins), len(counts)))
        for n in ins + split(p.get("output")) + split(p.get("mold")):
            st = item_state(n)
            if st is None:
                problems.append("%s: item %s unknown (not in the game, not declared)" % (where, n))
            elif st and not planned:
                problems.append("%s: uses planned item %s but is not planned" % (where, n))
        for f in split(p.get("fluid_in")) + split(p.get("fluid_out")):
            if f not in fluids:
                problems.append("%s: fluid %s unknown" % (where, f))
        if p.get("fluid_in") and not p.get("liters"):
            problems.append("%s: fluid_in without liters" % where)
        if p.get("fluid_out") and not p.get("out_liters"):
            problems.append("%s: fluid_out without out_liters" % where)
        if not (p.get("output") or p.get("fluid_out")):
            problems.append("%s: makes nothing" % where)
        if p.get("kind") == "cast":
            mold = root.find("item[@name='%s']" % p.get("mold"))
            if mold is None:
                problems.append("%s: cast without a declared mold" % where)
            elif p.get("fluid_in") not in split(mold.get("metals")):
                problems.append("%s: mold %s does not take %s" % (where, p.get("mold"), p.get("fluid_in")))
        try:
            float(p.get("time", "x"))
        except ValueError:
            problems.append("%s: time missing" % where)
        made.update(split(p.get("output")))

    for n, planned in items.items():
        if planned and n not in made and not n.startswith("feMold"):
            problems.append("planned item %s is made by no process" % n)

    for c in root.iter("chain"):
        steps = split(c.get("steps"))
        for s in steps:
            if s not in procs:
                problems.append("chain %s: unknown step %s" % (c.get("product"), s))
        if steps and steps[-1] in procs and c.get("product") not in split(procs[steps[-1]].get("output")):
            problems.append("chain %s: last step does not make it" % c.get("product"))

    active = sum(1 for p in procs.values() if p.get("planned") != "true")
    print("%d process(es) (%d active, %d planned), %d chain(s), %d problem(s)."
          % (len(procs), active, len(procs) - active, len(list(root.iter("chain"))), len(problems)))
    for pr in problems:
        print("  - " + pr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
