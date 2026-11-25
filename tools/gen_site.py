"""Data of the tutorial site (site/, a React + Vite app): everything the pages show comes from the mod's own files, so
the site grows with the mod and no page is written by hand.

Writes:
  site/public/data/mod.json   items and blocks (names / descriptions in pt-BR, category, energy, ports, how to connect,
                              3D model and icon when the mod has one), every recipe, every chain process, fluids,
                              machines, featured production lines and the indicators of the dashboard
  site/public/icons/<id>.png  the mod's own inventory icons (no game files are copied)
The 3D models (site/public/models/<model>.glb) come from tools/blender_export_glb.py (fe.bat site does both).

Usage: python tools/gen_site.py
"""
import csv
import datetime
import json
import re
import shutil
from collections import Counter, defaultdict

from lxml import etree

import fe_common as fe

SITE = fe.REPO / "site"
PUB = SITE / "public"
PROC = fe.MOD_DIR / "Data" / "fe_processes.xml"
ATLAS = fe.MOD_DIR / "UIAtlases" / "ItemIconAtlas"

AREA_PT = {"workbench": "Bancada", "forge": "Forja", "chemistryStation": "Estação Química", "campfire": "Fogueira",
           "cementMixer": "Betoneira", "": "Inventário"}
KIND_PT = {"melt": "Fundir", "cast": "Moldar", "press": "Prensar", "turn": "Tornear", "crush": "Triturar",
           "wash": "Lavar", "mix": "Misturar", "dry": "Secar / aquecer", "distill": "Destilar", "spin": "Fiar / centrifugar",
           "assemble": "Encaixar", "sequence": "Fechar (sequência)", "boil": "Cozinhar / ferver"}
BASE_FLUIDS = {"water": ("Água", "liquid"), "steam": ("Vapor", "gas"), "oil": ("Óleo", "liquid"),
               "gasoline": ("Gasolina", "liquid"), "lubricant": ("Lubrificante", "liquid"),
               "molten_brass": ("Latão Fundido", "molten"), "molten_lead": ("Chumbo Fundido", "molten"),
               "molten_iron": ("Ferro Fundido", "molten"), "molten_steel": ("Aço Fundido", "molten")}

# featured production lines (auto tutorials: the site builds the whole tree from the data)
FEATURED = [
    ("ammo9mmBulletBall", "Munição 9mm em linha", "Cápsula moldada, pólvora química e montagem em sequência sobre a esteira."),
    ("gunHandgunT1Pistol", "Pistola", "Cano usinado, mecanismo, peças e montagem final na Montadora."),
    ("vehicleWheels", "Roda de veículo", "Da seiva da árvore ao pneu vulcanizado, com aro e cubo."),
    ("ammoGasCan", "Gasolina", "Xisto, retorta, torre de destilação e envasadora."),
    ("resourceForgedSteel", "Aço", "Fundição, conversor de aço e molde de lingote."),
    ("feCircuitBoard", "Placa de circuito", "Polímero injetado, trilhas de latão e forno de refusão em linha."),
    ("smallEngine", "Motor pequeno", "Bloco fundido, pistões, virabrequim e velas encaixados em sequência."),
    ("drugAntibiotics", "Antibiótico", "Fermentação, centrífuga e secagem: a penicilina do apocalipse."),
    ("feSteamTurbine", "Turbina a vapor", "O coração da usina termelétrica modular."),
    ("resourcePaper", "Papel", "Polpa de madeira, calandra e secador a vapor."),
]


def load_loc():
    loc = {}
    for path in (fe.vanilla_config() / "Localization.csv", fe.MOD_CONFIG / "Localization.csv"):
        if not path.exists():
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = csv.reader(f)
            head = next(rows)
            ki, ei = head.index("Key"), head.index("english")
            ci = head.index("brazilian") if "brazilian" in head else None
            for r in rows:
                if len(r) <= ei or not r[ki]:
                    continue
                v = r[ci] if ci is not None and len(r) > ci and r[ci] else r[ei]
                loc[r[ki]] = v.replace("\\n", "\n")
    return loc


def resolve(props_by, n, depth=0):
    d = dict(props_by.get(n, {}))
    base = d.get("Extends")
    if base and base in props_by and depth < 10:
        r = resolve(props_by, base, depth + 1)
        r.update(d)
        return r
    return d


def category(n, p, is_block, machines):
    if not is_block:
        if n.startswith("feMold"):
            return "Moldes"
        if not n.startswith("fe"):
            return "Jogo"
        return "Peças e materiais"
    if p.get("FeSteamTurbine") or p.get("FeFluid") == "boiler" or n == "feBoilerFirebox":
        return "Usina termelétrica"
    if p.get("FeWorld"):
        return "Máquinas no mundo"
    if p.get("FeInline") == "true":
        return "Estações em linha"
    if p.get("FeSignal") or "FeDisplay" in p.get("Class", ""):
        return "Sinais"
    if p.get("FeTorqueOutput") or p.get("FeKinetic") in ("waterwheel",) or "Motor" in n or "Engine" in n or "Dynamo" in n \
            or "Crank" in n or "Generator" in n or n == "feBus":
        return "Energia"
    k = p.get("FeKinetic", "")
    if k == "conveyor" or p.get("FeChute") or p.get("FeDepot") or p.get("FeVault") or p.get("FeBeltInput") or "Funnel" in p.get("Class", "") \
            or "FeArm" in p.get("Class", "") or n in ("feFunnel", "feConveyorStand"):
        return "Logística"
    if k in ("shaft", "gearbox", "speedbox", "clutch", "regulator", "gauge", "inverter", "cog"):
        return "Transmissão"
    f = p.get("FeFluid", "")
    if f in ("processor", "caster", "smelter") or n in machines:
        return "Processamento" if f else "Bancadas"
    if f:
        return "Fluidos"
    return "Outros"


def how_to(n, p):
    """Where the ports are (the same rules as GuideData.HowToConnect in FeUi.cs)."""
    h = []
    k, f, w = p.get("FeKinetic", ""), p.get("FeFluid", ""), p.get("FeWorld", "")
    if k in ("pump", "conveyor"):
        h.append("Um eixo à esquerda ou à direita dá o torque" + (f" ({p['FeTorqueCost']} UT)" if p.get("FeTorqueCost") else "") + ".")
    if k == "cog":
        h.append("Engrenagens lado a lado (eixos paralelos) giram uma à outra ao contrário, sem eixo entre elas.")
    if p.get("FeWind"):
        h.append("No alto, com ar livre na frente das pás; o eixo sai por trás. Mais altura livre embaixo = mais vento.")
    if p.get("Class") == "Powered" or p.get("RequiredPower"):
        h.append(f"Ligue com fio na energia ({p.get('RequiredPower', '?')} W).")
    if p.get("FeMinPower"):
        h.append(f"Bancada: precisa de {p['FeMinPower']} W de motores elétricos encostados (ou torque no encaixe de motor).")
    if f == "processor":
        if p.get("FeInline") == "true":
            h.append("Coloque EM CIMA de uma esteira (ou de um Depósito): trabalha nos itens que passam embaixo; os outros ingredientes chegam por esteira, braço ou mão.")
        else:
            h.append("Itens entram por esteira, funil ou braço em qualquer lado; os produtos saem na esteira da frente.")
        h.append("Fluidos entram atrás (e embaixo) e saem em cima (e à direita, à esquerda).")
        if p.get("FeHeat") == "true":
            h.append("Precisa de calor: um Queimador a Gás aceso encostado.")
        if p.get("FeTower") == "true":
            h.append("Empilhe Seções de Torre em cima: cada seção dá uma fração nos seus lados.")
    if f == "valve":
        h.append("O fluido entra atrás e sai na frente; ajuste nas configurações (toque E).")
    if f == "burner":
        h.append("Gás combustível entra atrás, ou carvão / madeira / biocombustível pela esteira; aquece o que encosta.")
    if f == "tapper":
        h.append("As costas num tronco vivo (Seringueira rende muito; carvalho e bordo, pouco); cano na frente.")
    if f == "boiler":
        h.append("Fornalhas de Caldeira embaixo ou ao lado; água por cano nos lados; vapor sai em cima. Tambores encostados viram uma caldeira só.")
    if f == "turbine":
        h.append("Vapor entra atrás, vapor usado sai na frente (para a Condensadora); eixo nos lados. Dínamos no mesmo eixo geram eletricidade.")
    if f in ("tank", "gastank"):
        h.append("Canos em qualquer lado; tanques iguais encostados dividem o conteúdo.")
    if w in ("drill", "saw"):
        h.append("Trabalha no bloco da frente; o que cai vai para o baú, esteira ou calha atrás dela.")
    if w == "harvester":
        h.append("Virada para a plantação (na frente, ou na frente e um bloco abaixo); colhe e replanta.")
    if w == "deployer":
        h.append("Dê blocos ou sementes (esteira, braço, mão); ele coloca na frente.")
    if w == "piston":
        h.append("Um sinal (alavanca, receptor) faz estender; sem sinal, recolhe.")
    if w == "fan":
        h.append("Água logo na frente = lava; Queimador aceso na frente = aquece; nada = empurra itens. Para cima embaixo de uma Calha Vertical: sobe os itens.")
    if p.get("FeChute"):
        h.append("Empilhe em coluna: os itens caem até o que está embaixo; um ventilador embaixo, para cima, sobe.")
    if p.get("FeDepot"):
        h.append("Guarda uma pilha à vista; uma estação em cima trabalha nela; braços pegam.")
    if p.get("FeSignal"):
        h.append("Encoste no bloco que controla (registro, comporta, embreagem, pistão).")
    return h


def energy(p):
    e = {}
    for k, label in (("FeTorqueOutput", "torqueOut"), ("FeTorqueCost", "torqueCost"), ("RequiredPower", "watts"),
                     ("FeMinPower", "minWatts"), ("FeSourceRpm", "rpm"), ("FeFluidCapacity", "capacity"),
                     ("FeFluidBuffer", "buffer"), ("FeMaxBar", "maxBar"), ("FeOutBar", "outBar"), ("FeRange", "range")):
        if p.get(k):
            try:
                e[label] = float(p[k])
            except ValueError:
                pass
    return e


def main():
    loc = load_loc()
    recipes, _ = fe.patched("recipes.xml")
    blocks, _ = fe.patched("blocks.xml")
    items, _ = fe.patched("items.xml")
    props_by = {}
    block_names = set()
    for e in blocks.getroot().iter("block"):
        props_by[e.get("name")] = {p.get("name"): p.get("value") for p in e.findall("property") if p.get("name")}
        block_names.add(e.get("name"))
    for e in items.getroot().iter("item"):
        props_by.setdefault(e.get("name"), {}).update({p.get("name"): p.get("value") for p in e.findall("property") if p.get("name")})

    # ------------------------------------------------------------ recipes and processes
    recs = []
    for r in recipes.getroot().iter("recipe"):
        if "salvageScrap" in (r.get("tags") or "") or not r.get("name"):
            continue
        ing = [[i.get("name"), int(i.get("count", "1"))] for i in r.iter("ingredient")
               if not i.get("name", "").startswith("unit_") and int(i.get("count", "1")) > 0]
        if not ing:
            continue
        recs.append({"out": r.get("name"), "n": int(r.get("count", "1")), "area": r.get("craft_area") or "",
                     "t": float(r.get("craft_time") or 0), "ing": ing})
    procs, fluids, machine_text = [], {}, {}
    root = etree.parse(str(PROC)).getroot()
    for k, (pt, cl) in BASE_FLUIDS.items():
        fluids[k] = {"name": pt, "class": cl}
    for e in root.iter("fluid"):
        fluids[e.get("name")] = {"name": e.get("text") or e.get("name"),
                                 "class": e.get("class") or ("molten" if e.get("name", "").startswith("molten_") else "liquid")}
    for e in root.iter("machine"):
        machine_text[e.get("name")] = e.get("text")

    def split(v):
        return [x for x in (v or "").split(",") if x]

    for p in root.iter("process"):
        if p.get("planned") == "true":
            continue
        ins, cnt = split(p.get("input")), split(p.get("count"))
        fin, lit = split(p.get("fluid_in")), split(p.get("liters"))
        fout, olit = split(p.get("fluid_out")), split(p.get("out_liters"))
        procs.append({
            "id": p.get("id"), "kind": p.get("kind"), "machine": p.get("machine"),
            "in": [[i, int(cnt[k]) if k < len(cnt) else 1] for k, i in enumerate(ins)],
            "fin": [[f, float(lit[k]) if k < len(lit) else 0] for k, f in enumerate(fin)],
            "out": [p.get("output"), int(p.get("out_count") or 1)] if p.get("output") else None,
            "fout": [[f, float(olit[k]) if k < len(olit) else 0] for k, f in enumerate(fout)],
            "extra": [p.get("extra"), int(p.get("extra_count") or 1), float(p.get("chance") or 1)] if p.get("extra") else None,
            "t": float(p.get("time") or 0), "torque": float(p.get("torque") or 0), "bar": float(p.get("pressure") or 0),
            "heat": p.get("heat") == "true", "mold": p.get("mold"), "text": p.get("text") or "",
        })
    for f in fluids:   # bottled items
        pass

    # ------------------------------------------------------------ items
    machines = {r["area"] for r in recs if r["area"].startswith("fe")} | {p["machine"] for p in procs}
    referenced = set()
    for r in recs:
        referenced.add(r["out"])
        referenced.update(i for i, _ in r["ing"])
        if r["area"]:
            referenced.add(r["area"])
    for p in procs:
        referenced.add(p["machine"])
        referenced.update(i for i, _ in p["in"])
        for x in (p["out"], p["extra"]):
            if x:
                referenced.add(x[0])
        if p["mold"]:
            referenced.add(p["mold"])
    mod_names = {n for n in props_by if n and n.startswith("fe")}
    models_dir = PUB / "models"
    (PUB / "icons").mkdir(parents=True, exist_ok=True)
    out_items = {}
    for n in sorted(mod_names | referenced):
        if not n:
            continue
        is_block = n in block_names
        p = resolve(props_by, n) if n in props_by else {}
        is_mod = n.startswith("fe")
        model = None
        if is_block and is_mod:
            m = re.search(r"\?(\w+)Prefab", p.get("Model", ""))
            if m and (models_dir / f"{m.group(1)}.glb").exists():
                model = m.group(1)
        icon = None
        if is_mod:
            src = ATLAS / f"{p.get('CustomIcon', n)}.png"
            if not src.exists():
                src = ATLAS / f"{n}.png"
            if src.exists():
                shutil.copy(src, PUB / "icons" / f"{n}.png")
                icon = True
        desc = loc.get(p.get("DescriptionKey") or n + "Desc", "") if is_mod else ""
        out_items[n] = {
            "name": loc.get(n) or machine_text.get(n) or n,
            "desc": desc,
            "mod": is_mod,
            "block": is_block,
            "cat": category(n, p, is_block, machines) if is_mod else ("Estação do jogo" if n in AREA_PT else "Jogo"),
            "icon": bool(icon),
            "model": model,
            "energy": energy(p) if is_mod else {},
            "how": how_to(n, p) if is_mod and is_block else [],
            "machine": n in machines,
        }
    for a, pt in AREA_PT.items():
        if a:
            out_items.setdefault(a, {"name": pt, "desc": "", "mod": False, "block": True, "cat": "Estação do jogo",
                                     "icon": False, "model": None, "energy": {}, "how": [], "machine": True})

    # ------------------------------------------------------------ indicators
    proc_by_machine = Counter(p["machine"] for p in procs)
    rec_by_area = Counter(r["area"] for r in recs if r["area"].startswith("fe"))
    vanilla = fe.load_vanilla("recipes.xml").getroot()
    vanilla_made = {r.get("name") for r in vanilla.iter("recipe") if "salvageScrap" not in (r.get("tags") or "")}
    made_now = {r["out"] for r in recs} | {p["out"][0] for p in procs if p["out"]} | {p["extra"][0] for p in procs if p["extra"]}
    covered = len([n for n in vanilla_made if n in made_now or n in ("forge", "workbench", "chemistryStation", "cementMixer")])
    sources = sorted(([n, d["energy"].get("torqueOut", 0)] for n, d in out_items.items() if d["energy"].get("torqueOut")),
                     key=lambda x: -x[1])
    cats = Counter(d["cat"] for n, d in out_items.items() if d["mod"] and d["block"])
    stats = {
        "blocks": sum(1 for d in out_items.values() if d["mod"] and d["block"]),
        "items": sum(1 for d in out_items.values() if d["mod"] and not d["block"]),
        "machines": len([m for m in machines if m.startswith("fe")]),
        "processes": len(procs),
        "recipes": len(recs),
        "fluids": len(fluids),
        "models": sum(1 for d in out_items.values() if d["model"]),
        "icons": sum(1 for d in out_items.values() if d["icon"]),
        "coverage": [covered, len(vanilla_made)],
        "procByMachine": proc_by_machine.most_common(14),
        "recByArea": rec_by_area.most_common(14),
        "sources": sources[:12],
        "blockCats": cats.most_common(),
        "kinds": Counter(p["kind"] for p in procs).most_common(),
    }
    data = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": out_items, "recipes": recs, "processes": procs, "fluids": fluids,
        "areas": AREA_PT, "kinds": KIND_PT,
        "featured": [{"id": a, "title": b, "text": c} for a, b, c in FEATURED if a in out_items],
        "stats": stats,
    }
    (PUB / "data").mkdir(parents=True, exist_ok=True)
    (PUB / "data" / "mod.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"site data: {stats['blocks']} blocks, {stats['items']} items, {stats['processes']} processes, "
          f"{stats['recipes']} recipes, {stats['models']} 3D models, {stats['icons']} icons")


if __name__ == "__main__":
    main()
