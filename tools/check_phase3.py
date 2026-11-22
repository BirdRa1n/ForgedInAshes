"""F3-T08: phase-3 done check -- "no path skips the machines" (PLANO_MOD.md, phase 3 done criteria).

Runs on the patched XML (vanilla + mod patches, simulated by fe_common) and prints PASS/FAIL per rule.
Exit code 1 if any rule fails.

Usage: python tools/check_phase3.py
"""
import collections
import csv
import sys

import fe_common as fe

KEY_PARTS = {"resourceMechanicalParts", "resourceSpring"}
VANILLA_STATIONS = {"forge", "workbench", "chemistryStation", "cementMixer"}  # cementMixer since F4-T01
FORGE_ALLOWED = {"resourceClayLump", "resourceCrushedSand", "resourceRockSmall", "resourceScrapBrass",
                 "resourceScrapIron", "resourceScrapLead"}
LEGIT_DUPLICATES = {("resourceGlue", "feRefinery")}  # two different vanilla glue recipes (bones / grace corn)


def phase4_workbench(name):
    return name.startswith(("vehicle", "gunBot")) or name in ("cementMixer",)


def main() -> int:
    recipes = fe.patched("recipes.xml")[0].getroot()
    blocks = fe.patched("blocks.xml")[0].getroot()
    items = fe.patched("items.xml")[0].getroot()
    loot = fe.patched("loot.xml")[0].getroot()
    traders = fe.patched("traders.xml")[0].getroot()
    materials = fe.patched("materials.xml")[0].getroot()
    names = {e.get("name") for e in items} | {e.get("name") for e in blocks}
    results = []

    def rule(title, problems):
        results.append((title, problems))

    by_area = collections.defaultdict(list)
    for r in recipes.iter("recipe"):
        by_area[r.get("craft_area") or ""].append(r)

    # 1. vanilla stations keep only what is allowed
    # since F4-T01 the phase-4 machines exist: the vanilla workbench and cement mixer must be empty
    rule("workbench is empty", sorted({r.get("name") for r in by_area["workbench"]}))
    rule("cement mixer is empty", sorted({r.get("name") for r in by_area["cementMixer"]}))
    rule("forge keeps only its 6 smelting helpers",
         sorted({r.get("name") for r in by_area["forge"] if r.get("name") not in FORGE_ALLOWED}))
    rule("chemistry station is empty", sorted({r.get("name") for r in by_area["chemistryStation"]}))
    rule("vanilla stations cannot be crafted",
         sorted({r.get("name") for r in recipes.iter("recipe") if r.get("name") in VANILLA_STATIONS}))
    hidden = []
    for b in blocks:
        if b.get("name") in VANILLA_STATIONS:
            cm = [p.get("value") for p in b.findall("property") if p.get("name") == "CreativeMode"]
            if cm != ["Dev"]:
                hidden.append(f"{b.get('name')} CreativeMode={cm}")
    rule("vanilla stations hidden from the creative menu", hidden)

    # 2. mod stations: no smelter twins, no duplicates, craft_tool only where tools exist
    fe_recipes = [r for r in recipes.iter("recipe") if (r.get("craft_area") or "").startswith("fe")]
    rule("no use_smelter recipe in mod stations",
         [r.get("name") for r in fe_recipes if "use_smelter" in (r.get("tags") or "")])
    c = collections.Counter((r.get("name"), r.get("craft_area")) for r in fe_recipes)
    rule("no duplicate recipe in mod stations",
         [f"{k} x{v}" for k, v in c.items() if v > 1 and k not in LEGIT_DUPLICATES])
    modules, areas_with_block, charge_only = {}, set(), {}
    for b in blocks:
        props = {p.get("name"): p.get("value") for p in b.findall("property")}
        for cls in b.findall("property"):
            if cls.get("class") == "Workstation":
                m = {p.get("name"): p.get("value") for p in cls.findall("property")}
                for a in (m.get("CraftingAreaRecipes") or "").split(","):
                    a = a.strip()
                    modules[a] = m.get("Modules", "")
                    areas_with_block.add(a)
                    if (b.get("name") or "").startswith("fe"):
                        charge_only[b.get("name")] = (m.get("Modules", ""), props.get("FeChargeOnly"))
    rule("recipes with craft_tool are in stations with tool slots",
         [f"{r.get('name')}@{r.get('craft_area')}" for r in fe_recipes
          if r.get("craft_tool") and "tools" not in modules.get(r.get("craft_area"), "")])
    rule("every mod craft_area has a station block",
         sorted({r.get("craft_area") for r in fe_recipes if r.get("craft_area") not in areas_with_block}))
    rule("every fueled mod machine burns only Charge (except the Foundry)",
         [n for n, (mods, co) in charge_only.items() if "fuel" in mods and n != "feFoundry" and co != "true"])

    # 3. ingredients and outputs exist
    unknown = sorted({(r.get("name"), g.get("name")) for r in recipes.iter("recipe") for g in r.iter("ingredient")
                      if g.get("name") not in names and not g.get("name", "").startswith("unit_")})
    rule("every ingredient exists", [f"{a} <- {b}" for a, b in unknown][:30])
    mod_blocks = [b.get("name") for b in blocks if (b.get("name") or "").startswith("fe")]
    mod_items = [i.get("name") for i in items if (i.get("name") or "").startswith("fe") and i.get("name") != "feTestItem"]
    crafted = {r.get("name") for r in recipes.iter("recipe")}
    rule("every mod machine can be crafted", [n for n in mod_blocks if n not in crafted])

    # 4. key parts only from the Lathe
    rule("no key part in loot", sorted({f"{i.getparent().get('name')}:{i.get('name')}" for i in loot.iter("item")
                                        if i.get("name") in KEY_PARTS}))
    rule("no key part sold by traders", sorted({f"{i.getparent().get('name')}:{i.get('name')}" for i in traders.iter("item")
                                               if i.get("name") in KEY_PARTS}))
    rule("no key part from block drops", sorted({f"{d.getparent().get('name')}:{d.get('name')}" for d in blocks.iter("drop")
                                                 if d.get("name") in KEY_PARTS}))
    scrap_to_parts = []
    for m in materials.iter("material"):
        for p in m.findall("property"):
            if p.get("name") == "forge_category" and p.get("value") in KEY_PARTS and m.get("id") != "MmechanicalParts":
                scrap_to_parts.append(f"{m.get('id')} -> {p.get('value')}")
    rule("no other material scraps into a key part", scrap_to_parts)
    producers = sorted({(r.get("craft_area") or "inventory", r.get("name")) for r in recipes.iter("recipe")
                        if r.get("name") in KEY_PARTS and "salvageScrap" not in (r.get("tags") or "")})
    rule("key parts are crafted only in the Lathe", [f"{n}@{a}" for a, n in producers if a != "feLathe"])

    # 4b. the inventory only makes primitive things (user feedback after the F3 test)
    industrial = {"resourceForgedIron", "resourceForgedSteel", "resourceMechanicalParts", "resourceElectricParts",
                  "resourceSpring", "resourceGunPowder"}
    inv_ok = {"resourceMetalPipe"}  # needed to build the Foundry (bootstrap)
    inv_bad = sorted({r.get("name") for r in by_area[""]
                      if "salvageScrap" not in (r.get("tags") or "")
                      and not r.get("name", "").startswith("fe") and r.get("name") not in inv_ok
                      and any(g.get("name") in industrial for g in r.iter("ingredient"))})
    rule("inventory recipes use no industrial materials (except bootstrap)", inv_bad)

    # 5. localization for every mod block/item
    with (fe.MOD_CONFIG / "Localization.csv").open(encoding="utf-8", newline="") as fh:
        keys = {row["Key"] for row in csv.DictReader(fh)}
    rule("every mod block/item has a localized name", [n for n in mod_blocks + mod_items if n not in keys])

    failed = 0
    for title, problems in results:
        ok = not problems
        failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {title}" + ("" if ok else f": {problems}"))
    print(f"\n{len(results) - failed}/{len(results)} rules pass.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
