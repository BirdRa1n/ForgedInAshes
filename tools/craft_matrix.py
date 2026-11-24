"""F8.0: coverage sheet of the chain craft ("modo Create", PLANO_CRAFT.md section 5).

Reads tools/out/remap_proposal.csv (one row per vanilla recipe, from remap_proposal.py) and gives every recipe the
chain template of its group, the intermediate parts it will need and the F8 phase that covers it.
Output: tools/out/craft_matrix.csv + a summary per template. Rows no rule places get template "?" (review).

Usage: python tools/craft_matrix.py [--unmatched]
"""
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "remap_proposal.csv")
OUT = os.path.join(HERE, "out", "craft_matrix.csv")

# template id -> (description, intermediates, F8 phase)
T = {
    "AMMO": ("Fundir + Moldar (capsula/ponta) + Quimica (polvora) + Montar",
             "resourceBulletCasing resourceBulletTip resourceGunPowder", "F8.4"),
    "ARROW": ("Serraria (haste) + Moldar (ponta) + Tear (pena) + Montar", "haste, resourceArrowHeadIron", "F8.4"),
    "ROCKET": ("Moldar (carcaca) + Quimica (polvora) + Montar", "resourceRocketCasing resourceRocketTip", "F8.4"),
    "WEAPON": ("Fundir + Moldar + Torno (cano) + Montar", "feGunBarrel feGunMechanism feGunStock", "F8.5"),
    "TOOL": ("Fundir + Moldar cabeca + Prensa + Esmeril + cabo (Serraria) + Montar", "cabeca bruta, cabo", "F8.5"),
    "EXPLOSIVE": ("Quimica (polvora, acido) + Moldar (carcaca) + Montar", "carcaca, detonador", "F8.5"),
    "MOD": ("Prensa (chapa) + Torno + Eletronica + Montar", "feResourceIronPlate resourceSpring", "F8.5"),
    "ARMOR": ("Tear (fio, tecido) + Curtume (couro) + Prensa (placas) + Montar",
              "feResourceClothRoll couro curtido", "F8.7"),
    "METALSHOP": ("Fundir + Moldar chapas + Prensa + Serralheria", "feResourceIronPlate dobradica fechadura", "F8.8"),
    "BUILDMAT": ("Triturar + Forno + Misturar + Moldar", "resourceCrushedSand cascalho resourceCement", "F8.8"),
    "ELECTRIC": ("Trefila + Bobina + Placa + Montar", "feResourceBrassWire feResourceCoil placa", "F8.9"),
    "VEHICLE": ("Moldar bloco de motor + Torno + montagem em sequencia", "bloco de motor, pistao, roda", "F8.9"),
    "ROBOT": ("Eletronica + motor eletrico + Montar", "servo, placa", "F8.9"),
    "MEDICINE": ("Triturar + Destilar + Misturar + Secar", "extrato, pasta", "F8.10"),
    "CHEM": ("Refinaria com fluidos (destilar)", "oleo cru, acido", "F8.10"),
    "FOOD": ("Sem dificultar: Fogueira igual, Cozinha em lote", "", "-"),
    "METAL": ("Fundir (metal fundido) + Moldar lingote", "metal fundido", "F8.1"),
    "KEEP": ("Sem mudanca (tier primitivo / inventario / estacao vanilla)", "", "-"),
    "DROP": ("Variante use_smelter removida", "", "-"),
}

RULES = [  # (template, regex on recipe name) checked in order; first match wins
    ("ROCKET", r"^ammoRocket|^resourceRocket"),
    ("ARROW", r"^ammo(Arrow|Crossbow)|^resourceArrowHead"),
    ("AMMO", r"^ammo|^resourceBullet|^resourceBuckshot|^resourceGunPowder$"),
    ("EXPLOSIVE", r"^thrown|^mine|Explosive|Dynamite|Molotov|Grenade|PipeBomb", ),
    ("MOD", r"^mod"),
    ("ROBOT", r"^gunBot|^drone|Sledge|JunkTurret|JunkDrone"),
    ("VEHICLE", r"^vehicle|Chassis|Handlebars|smallEngine|Wheels"),
    ("WEAPON", r"^gun"),
    ("TOOL", r"^(melee|tool)"),
    ("ARMOR", r"^(armor|apparel|backpack)"),
    ("MEDICINE", r"^(medical|drug)"),
    ("CHEM", r"^resource(GasCan|Oil|Glue|Paint|Paper|Acid|Battery)|^ammoGasCan|^cntGas"),
    ("FOOD", r"^(food|drink)"),
    ("BUILDMAT", r"^(resourceCement|resourceConcrete|resourceCrushedSand|resourceCobblestone|resourceClay|"
                 r"concrete|glass|resourceBrokenGlass)"),
    ("METAL", r"^resource(ForgedIron|ForgedSteel|Scrap|Lead|Brass|MetalPipe|Nail)|^unit_"),
]

BY_MACHINE = {  # fallback on the remap target
    "M04": "AMMO", "M05": "WEAPON", "M06": "MOD", "M07": "ARMOR", "M08": "BUILDMAT", "M09": "CHEM",
    "M10": "MEDICINE", "M11": "FOOD", "M12": "ELECTRIC", "M13": "VEHICLE", "M14": "METALSHOP", "M15": "ROBOT",
    "M01": "METAL", "M02": "METAL", "M16": "BUILDMAT",
}


def template(row):
    target = row["target"]
    if target == "DROP-VARIANT":
        return "DROP"
    if target == "KEEP":
        return "KEEP"
    if target.startswith("KEEP+COPY"):
        return "MEDICINE" if target.endswith("M10") else "FOOD"
    for t, rx in RULES:
        if re.search(rx, row["name"]):
            return t
    return BY_MACHINE.get(target, "?")


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    out = []
    for r in rows:
        t = template(r)
        desc, parts, phase = T.get(t, ("?", "", "?"))
        out.append({"name": r["name"], "vanilla_area": r["area"], "remap_target": r["target"],
                    "template": t, "chain": desc, "intermediates": parts, "phase": phase})
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    c = collections.Counter(o["template"] for o in out)
    print("%d recipes -> %s" % (len(out), os.path.relpath(OUT, os.path.dirname(HERE))))
    for t, n in sorted(c.items(), key=lambda kv: -kv[1]):
        print("  %-10s %4d  %s" % (t, n, T.get(t, ("?",))[0]))
    if "--unmatched" in sys.argv:
        for o in out:
            if o["template"] == "?":
                print("  ? %s (%s -> %s)" % (o["name"], o["vanilla_area"], o["remap_target"]))
    return 0 if c.get("?", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
