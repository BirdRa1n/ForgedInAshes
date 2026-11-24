"""D12 (PLANO_CADEIA.md 1, 3): no item of the game is left without a way to make it.

Checks, after the mod's patches:
  1. every item the game has a recipe for (vanilla recipes.xml, salvage-scrap recipes aside) still has at least one
     recipe or one chain process (Data/fe_processes.xml) that makes it;
  2. the items the game only gives by loot / salvage (PLANO_CADEIA.md section 3) now have a route in the mod;
  3. no advanced item is made at a vanilla workstation that the mod hides (forge, workbench, chemistryStation,
     cementMixer).

Usage: python tools/check_coverage.py [--list]   (--list prints the route count per item)
"""
import sys

from lxml import etree

import fe_common as fe

LOOT_ONLY = ["resourceSpring", "resourceMechanicalParts", "resourceElectricParts", "resourceScrapPolymers", "resourceAcid",
             "resourceSewingKit", "resourceHeadlight", "smallEngine", "resourceRadiator", "toolBeaker", "drugVitamins",
             "foodCanBeef", "foodCanSoup", "foodCanChili", "foodCanPasta", "resourceAnimalFat"]
HIDDEN = {"forge", "workbench", "chemistryStation", "cementMixer"}
# the vanilla stations themselves are hidden on purpose (D1); the forge still "smelts back" raw materials
EXEMPT = {"forge", "workbench", "chemistryStation", "cementMixer"}
RAW_BACK = ("resourceScrap", "resourceClayLump", "resourceCrushedSand", "resourceRockSmall")
# filled by the Bottler from fluids (FluidNetwork.cs ItemFluids)
BOTTLED = {"resourceOil", "ammoGasCan", "feResourceLubricant"}


def main():
    vanilla = fe.load_vanilla("recipes.xml").getroot()
    patched, _ = fe.patched("recipes.xml")
    procs = etree.parse(str(fe.MOD_DIR / "Data" / "fe_processes.xml")).getroot()
    made_by_proc = {}
    for p in procs.iter("process"):
        if p.get("planned") == "true":
            continue
        for n in (p.get("output"), p.get("extra")):
            if n:
                made_by_proc[n] = made_by_proc.get(n, 0) + 1
    recipes = {}
    hidden = []
    for r in patched.getroot().iter("recipe"):
        if "salvageScrap" in (r.get("tags") or ""):
            continue
        recipes[r.get("name")] = recipes.get(r.get("name"), 0) + 1
        if (r.get("craft_area") or "") in HIDDEN and not r.get("name", "").startswith(RAW_BACK):
            hidden.append(f"{r.get('name')}@{r.get('craft_area')}")
    wanted = sorted({r.get("name") for r in vanilla.iter("recipe") if "salvageScrap" not in (r.get("tags") or "")})
    for f in procs.iter("fluid"):
        if f.get("item"):
            BOTTLED.add(f.get("item"))
    for n in BOTTLED:
        made_by_proc[n] = made_by_proc.get(n, 0) + 1
    missing = [n for n in wanted if recipes.get(n, 0) + made_by_proc.get(n, 0) == 0 and n not in EXEMPT]
    loot = [n for n in LOOT_ONLY if recipes.get(n, 0) + made_by_proc.get(n, 0) == 0]
    if "--list" in sys.argv:
        for n in wanted:
            print(f"{n}: {recipes.get(n, 0)} recipe(s), {made_by_proc.get(n, 0)} process(es)")
    print(f"{len(wanted)} game items with a recipe: {len(wanted) - len(missing)} still made, {len(missing)} missing")
    print(f"{len(LOOT_ONLY)} loot-only items: {len(LOOT_ONLY) - len(loot)} now made by the mod, {len(loot)} not")
    print(f"recipes left on hidden vanilla stations: {len(hidden)}")
    for n in missing:
        print("  MISSING: " + n)
    for n in loot:
        print("  LOOT ONLY: " + n)
    for n in hidden:
        print("  HIDDEN STATION: " + n)
    return 1 if missing or loot or hidden else 0


if __name__ == "__main__":
    sys.exit(main())
