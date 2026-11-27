"""Writes PENDENCIAS_ASSETS.md: every block / item of the mod that still lacks its own model or icon, with the object
names the code looks for in each model (the "contracts"), so a modelling session knows exactly what to make.

A block has its own model when blocks.xml points it to "<block>Prefab" (or its HD folder Art/<block>/hd exists and
FeBuild.cs builds it); otherwise it borrows another block's model. An icon is its own when CustomIcon = its own name
and the png exists in UIAtlases/ItemIconAtlas.

Usage: python tools/list_assets.py
"""
import os
import re

import fe_common as fe

OUT = fe.REPO / "PENDENCIAS_ASSETS.md"
ATLAS = fe.MOD_DIR / "UIAtlases" / "ItemIconAtlas"

# what the code looks for inside a model, by kind of block (see the .cs files named)
CONTRACTS = {
    "processor": "`FeItemAnchor` (empty: where the item it works on floats; default = on top), `FeHead_*` (parts that press down "
                 "while working, MachineItems.cs), `FeWorkSpin_*` / `FeSurface_r*` / `FeFx_*` (FxVisual.cs, see Art/feHD/README.md)",
    "inline": "sits ON TOP of a belt: open underneath (the belt item passes 0.62 m up); `FeHead_*` goes down onto the item (MachineItems.cs)",
    "torque": "`FeSpin_*` (turns with the shaft, KineticSpinner.cs); shaft ends on its local X (left / right), port height 0.5 m",
    "pipe": "`FeArm_PX/NX/PY/NY/PZ/NZ` (pipe arms shown where a pipe or port connects, FluidNetwork.cs PipeArms); fluid IN at the back "
            "(local -Z), OUT at the front (+Z)",
    "tank": "`FeLevelLiquid` / `FeSurface_r*` (level), arms on every side",
    "belt": "same object names as feConveyor (Belt.cs BeltShape, Art/CONVEYOR_PORTS.md)",
    "world": "front (+Z) is the working face: drill bit / saw blade / fan blades as `FeSpin_*`; shaft on its local X",
    "fan": "`FeSpin_*` blades facing +Z",
    "piston": "the body; the head is the block `fePistonHead` (needs its own small model: plate + rod)",
    "holder": "flat top at 0.82 m (the depot's item sits there); the chute is a closed vertical tube",
    "signal": "a lever / box; the Display Panel writes its digits on the +Z face 0.52 m from the centre (DisplayVisual)",
    "tree": "uses the planted oak models (a Rubber Tree look: lighter bark, the sap cup)",
    "giant": "D14 giant machine, the WHOLE multi-block (MultiBlockDim: Mining Rig 7x9x7, Oil Extractor 5x11x5; origin = centre of the "
             "bottom layer, +Z = front). Products / oil leave by the middle of the FRONT face at ground level; the motor socket is behind "
             "the middle of the back (PowerGate.SocketPos). Moving parts turn with the socket torque (KineticSpinner; walking beam "
             "`FeRock_*`)." " Mining Rig: a drill tower over the centre, `FeSpin_*` (drill / gears), the shaft hole under the "
             "centre. Oil Extractor: a pumpjack / derrick, `FeSpin_*` crank, an outlet flange on the front (High Pressure Pipe size)",
    "rail": "D14 track piece at rail height 0.15 m, two rails 1.435 m apart on sleepers; ends exactly on the cell edges: straight 1x1 "
            "(-Z edge to +Z edge), curve 5x5 (quarter circle radius 4.5: from x=-2 on the -Z edge to z=+2 on the +X edge), ramp 1x2x3 "
            "(rises 1 over 3), switches 5x5 = straight on the left (R) / right (L) column + the curve. Rails.cs LocalPaths is the source of truth",
    "station": "D14 platform 9x4x3 (9 along the rails, the rails run along its +Z side, outside it): roof, benches, a sign board with "
               "`FeSignText_F/_B` empties (FeBuild adds the TextMesh for the vanilla label), `FeCol_*` collider boxes (walkable deck), a fuel bunker, a small tank on the side",
    "trainkit": "D14 kit block (a crate on a pallet with the car's silhouette painted): it turns into the train car when placed. The CARS "
                "themselves are separate prefabs (section below)",
}


def kind_of(props):
    if props.get("FeWorld") in ("miner", "oilwell"):
        return "giant"
    if props.get("FeRail"):
        return "rail"
    if props.get("FeTrainStation") == "true":
        return "station"
    if "FeTrainKit" in props.get("Class", ""):
        return "trainkit"
    if props.get("FeInline") == "true":
        return "inline"
    if props.get("FeWorld"):
        return {"fan": "fan", "piston": "piston"}.get(props["FeWorld"], "world")
    f = props.get("FeFluid", "")
    if f == "processor":
        return "processor"
    if f in ("valve", "gauge", "burner", "tapper", "pipe") or props.get("FeMaxBar"):
        return "pipe"
    if f in ("tank", "gastank", "towersection"):
        return "tank"
    if props.get("FeKinetic") in ("conveyor",) or props.get("FeBeltSplit") or props.get("FeBeltGate") or props.get("FeBeltCounter") or props.get("FeBeltTunnel"):
        return "belt"
    if props.get("FeChute") or props.get("FeDepot"):
        return "holder"
    if props.get("FeSignal") or "FeDisplay" in props.get("Class", ""):
        return "signal"
    if props.get("FeKinetic"):
        return "torque"
    return ""


def main():
    blocks, _ = fe.patched("blocks.xml")
    items, _ = fe.patched("items.xml")
    rows_b, rows_i = [], []
    own_props = {}
    for b in blocks.getroot().iter("block"):
        own_props[b.get("name")] = {p.get("name"): p.get("value") for p in b.findall("property") if p.get("name")}

    def resolved(n, depth=0):
        d = dict(own_props.get(n, {}))
        base = d.get("Extends")
        if base and depth < 8:
            r = resolved(base, depth + 1)
            r.update(d)
            return r
        return d

    for b in blocks.getroot().iter("block"):
        n = b.get("name") or ""
        if not n.startswith("fe"):
            continue
        props = resolved(n)
        # inherited props (Extends) matter for the kind
        model = props.get("Model", "")
        icon = props.get("CustomIcon", "")
        own_model = model.endswith("?" + n + "Prefab") or "?feM_" in model or (fe.REPO / "Art" / n / "hd" / f"{n}_HD.fbx").exists()
        # variants of a block (Extends it and keeps its model on purpose: filter belt, ramps...) are not pending
        if not own_model and "Model" not in own_props.get(n, {}):
            own_model = True
        own_icon = icon == n and (ATLAS / f"{n}.png").exists()
        if own_model and own_icon:
            continue
        k = kind_of(props)
        if n.startswith("feTreeRubber"):
            k = "tree"
        borrowed = re.sub(r".*\?", "", model) if model else "(herdado)"
        rows_b.append((n, k, borrowed if not own_model else "próprio", "falta" if not own_model else "ok", "falta" if not own_icon else "ok"))
    for it in items.getroot().iter("item"):
        n = it.get("name") or ""
        if not n.startswith("fe"):
            continue
        props = {p.get("name"): p.get("value") for p in it.findall("property") if p.get("name")}
        icon = props.get("CustomIcon", "")
        if icon == n and (ATLAS / f"{n}.png").exists():
            continue
        rows_i.append((n, icon, props.get("CustomIconTint", "")))
    loc = {}
    import csv
    with (fe.MOD_CONFIG / "Localization.csv").open(encoding="utf-8", newline="") as fh:
        r = list(csv.reader(fh))
    ib = r[0].index("brazilian")
    for row in r[1:]:
        if row:
            loc[row[0]] = row[ib]
    out = ["# Modelos e assets pendentes",
           "",
           "Gerado por `python tools/list_assets.py` (rode de novo depois de fazer modelos: a lista encolhe sozinha).",
           "Para outra sessão de modelagem: cada bloco abaixo usa hoje o modelo de **outro** bloco (coluna \"modelo atual\")",
           "e/ou um ícone emprestado com tinta. O código já funciona; só falta a arte. Fluxo: geometria em",
           "`Art/<bloco>/hd/<bloco>_src.blend` (estilo e contratos em `Art/feHD/README.md` e `Art/feHD/build_feHD.py`),",
           "config da IA em `F:\\IA\\fe_blender\\configs\\<bloco>.json`, depois `fe.bat tudo` (modelos -> bundle, ícones, mod).",
           "Ao ganhar modelo próprio, o `blocks.xml` deve apontar `Model` para `...unity3d?<bloco>Prefab` (o gerador",
           "`tools/gen_chain.py` monta os blocos D12/D13: troque o 8º campo de `block(...)` / `machine(...)`).",
           "",
           "## Contratos (nomes de objetos que o código procura no modelo)",
           ""]
    for k, v in CONTRACTS.items():
        out.append(f"- **{k}**: {v}")
    out += ["", f"## Blocos ({len(rows_b)})", "", "| Bloco | Nome | Tipo / contrato | Modelo atual | Modelo próprio | Ícone próprio |", "|---|---|---|---|---|---|"]
    for n, k, borrowed, m, i in sorted(rows_b, key=lambda r: (r[1], r[0])):
        out.append(f"| `{n}` | {loc.get(n, '')} | {k or '-'} | `{borrowed}` | {m} | {i} |")
    out += ["", f"## Itens sem ícone próprio ({len(rows_i)})", "",
            "Usam o ícone de um item do jogo com tinta. Um ícone 160x160 transparente em",
            "`Mods/ForgedInAshes/UIAtlases/ItemIconAtlas/<item>.png` + `python tools/apply_icons.py` resolve.", "",
            "| Item | Nome | Ícone emprestado (tinta) |", "|---|---|---|"]
    for n, icon, tint in sorted(rows_i):
        out.append(f"| `{n}` | {loc.get(n, '')} | `{icon}` ({tint}) |")
    cars = [("feTrainLocoCar", "8 m", "locomotiva a vapor (caldeira, cabine, chaminé)"),
            ("feWagonCargoCar", "7 m", "vagão fechado de carga"),
            ("feWagonTankCar", "7 m", "vagão-tanque (cilindro deitado)"),
            ("feWagonPassengerCar", "9 m", "vagão de passageiros com bancos, piso a 1 m")]
    missing = [c for c in cars if not (fe.REPO / "Art" / c[0] / "hd" / f"{c[0]}_HD.fbx").exists()]
    out += ["", f"## Vagões do trem (prefabs que não são blocos) ({len(missing)})", "",
            "O trem (TrainView.cs) desenha cada vagão com o prefab `<kit>CarPrefab` do pacote (feito por `Art/feHD/build_feHD.py`,",
            "lista `Loose` do `FeBuild.cs`); sem ele usa uma caixa colorida. Origem no centro do vagão, no topo do trilho (y=0),",
            "+Z = frente, sem colisores. Rodas `FeSpin_r<raio>_*`; locomotiva: `FeTrainPin_n`, `FeTrainCouple_n`, `FeTrainCross_n`,",
            "`FeTrainMain_n`, `FeFx_Smoke_*` / `FeFx_Steam_*` (TrainCarVisual). Largura 2,6 m, altura até 3,6 m.", ""]
    if missing:
        out += ["| Prefab | Comprimento | O que é |", "|---|---|---|"]
        for n, length, what in missing:
            out.append(f"| `{n}Prefab` | {length} | {what} |")
    else:
        out.append("Todos os vagões têm modelo próprio.")
    out.append("")
    out += ["", "## Outros assets", "",
            "- **Sons**: nenhuma máquina nova tem som próprio (manivela, prensa, furadeira, serra, ventilador, compressor, pistão).",
            "- **Partículas novas** que ajudariam: vento do Ventilador (`FeFx_Wind`), serragem da Serra, poeira da Furadeira,",
            "  água do lavador do Ventilador. Hoje os blocos sem modelo não têm empties `FeFx_*`.",
            "- **Seringueira**: usa os modelos do carvalho plantado.",
            ""]
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"{OUT.name}: {len(rows_b)} blocks, {len(rows_i)} items pending")


if __name__ == "__main__":
    main()
