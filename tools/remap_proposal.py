"""F3-T01/T03: propose a target machine for every vanilla recipe (except scrap recipes).

Rules follow PLANO_MOD.md section 10, keyed on (vanilla craft_area, recipe-name prefix / name).
Output: tools/out/remap_proposal.csv + a summary. Rows the rules cannot place get target "?" (review).

Targets:  KEEP = stays where it is (vanilla station or inventory)
          KEEP+COPY:<m> = stays, and a better copy goes to machine <m> (campfire food etc.)
          <machine id> = move (craft_area -> that machine), phase in column "phase"

Usage: python tools/remap_proposal.py [--unmatched]
"""
import collections
import csv
import re
import sys

import fe_common as fe

M = {  # machine id -> craft_area (PLANO_MOD.md section 5.1)
    "M01": "feFoundry", "M02": "fePress", "M03": "feLathe", "M04": "feAmmoPress", "M05": "feAssembler",
    "M06": "feModBench", "M07": "feLoom", "M08": "feMixer", "M09": "feRefinery", "M10": "feLab",
    "M11": "feKitchen", "M12": "feElectronics", "M13": "feGarage", "M14": "feMetalShop", "M15": "feRobotics",
    "M16": "feSawmill",
}
PHASE = {k: 3 for k in M}
PHASE.update({"M08": 4, "M13": 4, "M15": 4, "M01": 1, "M02": 1, "M03": 1})

WORKSTATIONS = {"forge", "workbench", "chemistryStation", "cementMixer", "campfire"}

ELECTRIC = re.compile(r"^(ceiling|industrial|lantern|pressureplate|batterybank|generatorbank|solarbank|auto|"
                      r"spotlight|switch|speaker|motionsensor|electric|wire|timer|tripwire|light|blade|dart|"
                      r"shotgunTurret|trap|electricFence|lightBulb|poweredLight|sledge)", re.I)
METALSHOP = re.compile(r"^(cnt|vault|roll|steel|iron|metal|wooden|cellar|drawbridge|garage|hatch|door|"
                       r"shutters|bars|commercial|bulletproof|secure|bunker|scrap)", re.I)


OVERRIDES = {  # exact recipe name -> (target, note); checked before the prefix rules
    "burningBarrelPlayer": ("M14", "metal decor"),
    "endTableLamp": ("M12", "light"),
    "ladderSteel": ("M14", "metal building"),
    "resourceLockPick": ("M05", "tool"),
    "resourceLockPickBundle": ("M05", "tool"),
    "m60Turret": ("M12", "turret"),
    "tvBlockVariantHelper": ("M12", "electrical decor"),
    "toolForgeCrucible": ("M01", "forge tool"),
    # needs craft_tool=toolForgeCrucible: only the Foundry has tool slots (F3-T03 check)
    "resourceArrowHeadSteelAP": ("M01", "needs the crucible (craft_tool)"),
    "cntApiary": ("M11", "section 10: apiary/dew collector -> Kitchen"),
    "cntDewCollector": ("M11", "section 10: apiary/dew collector -> Kitchen"),
}


def classify(area: str, name: str, tags: str):
    n = name or ""
    low = n.lower()
    if n in WORKSTATIONS:
        return "KEEP", "vanilla workstation (D1)"
    # must come before OVERRIDES: a use_smelter twin is always dropped, whatever its recipe's destination
    if area == "forge" and "use_smelter" in (tags or ""):
        return "DROP-VARIANT", "use_smelter twin: drop when the recipe leaves 'forge' (filter only for forge)"
    if area != "inventory" and n in OVERRIDES:
        return OVERRIDES[n]
    if area == "workbench" and low.startswith("gunbot"):
        return "M15", "robots (phase 4)"
    if area == "workbench" and low.startswith(("tooldew", "toolapiary", "toolchickencoop")):
        return "M11", "collector mods (section 10: apiary/coop/water -> Kitchen)"
    if area == "workbench" and low.startswith("mine"):
        return "M12", "land mines = traps"
    if area == "inventory":
        return "KEEP", "inventory recipe: review (P1, no early locks)"
    if area == "campfire":
        if low.startswith(("food", "drink")):
            return "KEEP+COPY:M11", "campfire stays early; better copy in Kitchen"
        if low.startswith(("drug", "medical")):
            return "KEEP+COPY:M10", "campfire stays early; copy in Lab"
        return "KEEP", "campfire resource (glue/paint/paper) stays early"
    if area == "cementMixer":
        return "M08", "phase 4"
    if area == "chemistryStation":
        if low.startswith(("drug", "medical")):
            return "M10", ""
        if low.startswith("drink"):
            return "M11", "beer"
        return "M09", "chemical resource / fuel"
    if area == "forge":
        if "use_smelter" in (tags or ""):
            return "DROP-VARIANT", "use_smelter twin: drop when the recipe leaves 'forge' (filter only for forge)"
        if low.startswith(("ammo", "resourcebullet", "resourcearrowhead", "resourcebuckshot", "resourcerocket")):
            return "M02", "ammo parts"
        if low.startswith(("ironbars", "metaltrussing", "metalfence")):
            return "M02", "bars/beams"
        if low.startswith(("glass", "drinkjar", "trapglass", "resourcescopelens", "resourcecrushedsand")):
            return "M01", "glass"
        if low.startswith(("resourcenail", "resourcemetalpipe")):
            return "M01", "stays in Foundry (already copied) + cheaper copy in Press"
        return "M01", "metals / tools / cement"
    if area == "workbench":
        if low.startswith("mod"):
            return "M06", ""
        if low.startswith(("armor", "apparel", "backpack")):
            return "M07", ""
        if low.startswith("ammo"):
            return "M04", ""
        if low.startswith(("gun", "thrown", "mine", "melee", "tool")):
            return "M05", ""
        if low.startswith("vehicle"):
            return "M13", "phase 4"
        if ELECTRIC.match(n):
            return "M12", ""
        if METALSHOP.match(n):
            return "M14", ""
        return "?", ""
    return "?", "unknown area"


def main() -> int:
    root = fe.load_vanilla("recipes.xml").getroot()
    rows = []
    for rec in root.iter("recipe"):
        tags = rec.get("tags") or ""
        if "salvageScrap" in tags:
            continue
        area = rec.get("craft_area") or "inventory"
        target, note = classify(area, rec.get("name"), tags)
        mid = target.split(":")[-1]
        rows.append({
            "name": rec.get("name"), "area": area, "tags": tags, "target": target,
            "craft_area_new": M.get(mid, ""), "phase": PHASE.get(mid, ""), "note": note,
        })
    out = fe.REPO / "tools" / "out" / "remap_proposal.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    by = collections.Counter((r["area"], r["target"]) for r in rows)
    print(f"{'from':<18}{'to':<16}{'n':>4}")
    for (a, t), n in sorted(by.items()):
        print(f"{a:<18}{t:<16}{n:>4}")
    tot = collections.Counter(r["target"] for r in rows)
    print("\nby target:", dict(sorted(tot.items())))
    print(f"total {len(rows)} -> {out}")
    if "--unmatched" in sys.argv:
        for r in rows:
            if r["target"] == "?":
                print("  ?", r["area"], r["name"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
