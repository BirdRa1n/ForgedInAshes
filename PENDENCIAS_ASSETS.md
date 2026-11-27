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
- **giant**: D14 giant machine, the WHOLE multi-block (MultiBlockDim: Mining Rig 7x9x7, Oil Extractor 5x11x5; origin = centre of the bottom layer, +Z = front). Products / oil leave by the middle of the FRONT face at ground level; the motor socket is on its side (PowerGate.SocketPos). Mining Rig: a drill tower over the centre, `FeSpin_*` (drill / gears), the shaft hole under the centre. Oil Extractor: a pumpjack / derrick, `FeSpin_*` crank, an outlet flange on the front (High Pressure Pipe size)
- **rail**: D14 track piece at rail height 0.15 m, two rails 1.435 m apart on sleepers; ends exactly on the cell edges: straight 1x1 (-Z edge to +Z edge), curve 5x5 (quarter circle radius 4.5: from x=-2 on the -Z edge to z=+2 on the +X edge), ramp 1x2x3 (rises 1 over 3), switches 5x5 = straight on the left (R) / right (L) column + the curve. Rails.cs LocalPaths is the source of truth
- **station**: D14 platform 9x4x3 (9 along the rails, the rails run along its +Z side, outside it): roof, benches, a sign board with a `TextMesh` child for the vanilla writable label (TEFeatureSignable), a fuel bunker, a small tank on the side
- **trainkit**: D14 kit block (a crate on a pallet with the car's silhouette painted): it turns into the train car when placed. The CARS themselves are separate prefabs (section below)

## Blocos (13)

| Bloco | Nome | Tipo / contrato | Modelo atual | Modelo próprio | Ícone próprio |
|---|---|---|---|---|---|
| `feMiningRig` | Mineradora | giant | `feCrusherPrefab` | falta | falta |
| `feOilExtractor` | Extratora de Petróleo | giant | `feRetortKilnPrefab` | falta | falta |
| `feRailCurve` | Curva de Trilho | rail | `feConveyorPrefab` | falta | falta |
| `feRailRamp` | Rampa de Trilho | rail | `feConveyorPrefab` | falta | falta |
| `feRailStraight` | Trilho | rail | `feConveyorPrefab` | falta | falta |
| `feRailSwitchL` | Desvio de Trilho (esquerda) | rail | `feConveyorPrefab` | falta | falta |
| `feRailSwitchR` | Desvio de Trilho (direita) | rail | `feConveyorPrefab` | falta | falta |
| `feTrainStation` | Estação de Trem | station | `feBeltCratePrefab` | falta | falta |
| `feStorageTank` | Tanque de Armazenamento | tank | `feWaterTankPrefab` | falta | falta |
| `feTrainLoco` | Locomotiva | trainkit | `feBeltCratePrefab` | falta | falta |
| `feWagonCargo` | Vagão de Carga | trainkit | `feBeltCratePrefab` | falta | falta |
| `feWagonPassenger` | Vagão de Passageiros | trainkit | `feBeltCratePrefab` | falta | falta |
| `feWagonTank` | Vagão-Tanque | trainkit | `feBeltCratePrefab` | falta | falta |

## Itens sem ícone próprio (0)

Usam o ícone de um item do jogo com tinta. Um ícone 160x160 transparente em
`Mods/ForgedInAshes/UIAtlases/ItemIconAtlas/<item>.png` + `python tools/apply_icons.py` resolve.

| Item | Nome | Ícone emprestado (tinta) |
|---|---|---|

## Vagões do trem (prefabs que não são blocos)

O trem (Trains.cs / TrainView.cs) desenha cada vagão com o prefab `<kit>Prefab` do pacote; sem ele usa uma caixa colorida.
Precisam entrar no `FeBuild.cs` como prefabs soltos (não são blocos). Origem no centro do vagão, no topo do trilho (y=0),
+Z = frente, sem colisores (o código desliga os que houver: trens não colidem).

| Prefab | Comprimento | O que é | Partes que ajudam |
|---|---|---|---|
| `feTrainLocoPrefab` | 8 m | locomotiva a vapor/fóssil (caldeira, cabine, chaminé) | `FeSpin_*` rodas, `FeFx_Smoke_*` chaminé |
| `feWagonCargoPrefab` | 7 m | vagão fechado de carga | `FeSpin_*` rodas |
| `feWagonTankPrefab` | 7 m | vagão-tanque (cilindro deitado) | `FeSpin_*` rodas, `FeLevelLiquid` |
| `feWagonPassengerPrefab` | 9 m | vagão de passageiros com bancos | `FeSpin_*` rodas, assento a 1 m de altura no centro |

Largura 2,6 m, altura até 3,6 m (o código usa essa caixa para a mira: olhar e apertar E).


## Outros assets

- **Sons**: nenhuma máquina nova tem som próprio (manivela, prensa, furadeira, serra, ventilador, compressor, pistão).
- **Partículas novas** que ajudariam: vento do Ventilador (`FeFx_Wind`), serragem da Serra, poeira da Furadeira,
  água do lavador do Ventilador. Hoje os blocos sem modelo não têm empties `FeFx_*`.
- **Seringueira**: usa os modelos do carvalho plantado.
