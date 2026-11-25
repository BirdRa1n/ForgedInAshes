# Modelos e assets pendentes

Gerado por `python tools/list_assets.py` (rode de novo depois de fazer modelos: a lista encolhe sozinha).
Para outra sessão de modelagem: cada bloco abaixo usa hoje o modelo de **outro** bloco (coluna "modelo atual")
e/ou um ícone emprestado com tinta. O código já funciona; só falta a arte. Fluxo: geometria em
`Art/<bloco>/hd/<bloco>_src.blend` (estilo e contratos em `Art/feHD/README.md` e `Art/feHD/build_feHD.py`),
config da IA em `F:\IA\fe_blender\configs\<bloco>.json`, depois `fe.bat tudo` (modelos -> bundle, ícones, mod).
Ao ganhar modelo próprio, o `blocks.xml` deve apontar `Model` para `...unity3d?<bloco>Prefab` (o gerador
`tools/gen_chain.py` monta os blocos D12/D13: troque o 8º campo de `block(...)` / `machine(...)`).

## Contratos (nomes de objetos que o código procura no modelo)

- **processor**: `FeItemAnchor` (empty: where the item it works on floats; default = on top), `FeHead_*` (parts that press down while working, MachineItems.cs), `FeWorkSpin_*` / `FeSurface_r*` / `FeFx_*` (FxVisual.cs, see Art/feHD/README.md)
- **inline**: sits ON TOP of a belt: open underneath (the belt item passes 0.62 m up); `FeHead_*` goes down onto the item (MachineItems.cs)
- **torque**: `FeSpin_*` (turns with the shaft, KineticSpinner.cs); shaft ends on its local X (left / right), port height 0.5 m
- **pipe**: `FeArm_PX/NX/PY/NY/PZ/NZ` (pipe arms shown where a pipe or port connects, FluidNetwork.cs PipeArms); fluid IN at the back (local -Z), OUT at the front (+Z)
- **tank**: `FeLevelLiquid` / `FeSurface_r*` (level), arms on every side
- **belt**: same object names as feConveyor (Belt.cs BeltShape, Art/CONVEYOR_PORTS.md)
- **world**: front (+Z) is the working face: drill bit / saw blade / fan blades as `FeSpin_*`; shaft on its local X
- **fan**: `FeSpin_*` blades facing +Z
- **piston**: the body; the head is the block `fePistonHead` (needs its own small model: plate + rod)
- **holder**: flat top at 0.82 m (the depot's item sits there); the chute is a closed vertical tube
- **signal**: a lever / box; the Display Panel writes its digits on the +Z face 0.52 m from the centre (DisplayVisual)
- **tree**: uses the planted oak models (a Rubber Tree look: lighter bark, the sap cup)

## Blocos (0)

| Bloco | Nome | Tipo / contrato | Modelo atual | Modelo próprio | Ícone próprio |
|---|---|---|---|---|---|

## Itens sem ícone próprio (0)

Usam o ícone de um item do jogo com tinta. Um ícone 160x160 transparente em
`Mods/FerroEngrenagem/UIAtlases/ItemIconAtlas/<item>.png` + `python tools/apply_icons.py` resolve.

| Item | Nome | Ícone emprestado (tinta) |
|---|---|---|

## Outros assets

- **Sons**: nenhuma máquina nova tem som próprio (manivela, prensa, furadeira, serra, ventilador, compressor, pistão).
- **Partículas novas** que ajudariam: vento do Ventilador (`FeFx_Wind`), serragem da Serra, poeira da Furadeira,
  água do lavador do Ventilador. Hoje os blocos sem modelo não têm empties `FeFx_*`.
- **Seringueira**: usa os modelos do carvalho plantado.
