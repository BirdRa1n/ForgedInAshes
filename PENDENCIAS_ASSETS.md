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

## Blocos (24)

| Bloco | Nome | Tipo / contrato | Modelo atual | Modelo próprio | Ícone próprio |
|---|---|---|---|---|---|
| `feItemVault` | Cofre Modular | - | `feBeltCratePrefab` | falta | falta |
| `fePistonHead` | Cabeça de Pistão | - | `fePipePrefab` | falta | falta |
| `feBeltTunnel` | Túnel de Esteira | belt | `feConveyorDuctPrefab` | falta | falta |
| `feFan` | Ventilador Industrial | fan | `feMechPumpPrefab` | falta | falta |
| `feDepot` | Depósito | holder | `feCasterPrefab` | falta | falta |
| `feItemChute` | Calha Vertical | holder | `fePipePrefab` | falta | falta |
| `feMechPiston` | Pistão Mecânico | piston | `feClutchPrefab` | falta | falta |
| `feItemDrain` | Dreno de Itens | processor | `feFluidFillerPrefab` | falta | falta |
| `feDisplayPanel` | Painel Numérico | signal | `feTorqueGaugePrefab` | falta | falta |
| `feSignalAnalog` | Alavanca Analógica | signal | `feClutchPrefab` | falta | falta |
| `feWirelessRx` | Receptor sem Fio | signal | `feTorqueGaugePrefab` | falta | falta |
| `feWirelessTx` | Transmissor de Sinal | signal | `feTorqueGaugePrefab` | falta | falta |
| `feCogwheel` | Engrenagem | torque | `feSpinInverterPrefab` | falta | falta |
| `feHosePulley` | Polia de Mangueira | torque | `feMechPumpPrefab` | falta | falta |
| `feWindmill` | Moinho de Vento | torque | `feWaterWheelPrefab` | falta | falta |
| `feTreeRubber08` | Seringueira | tree | `próprio` | ok | falta |
| `feTreeRubber16` | Seringueira | tree | `próprio` | ok | falta |
| `feTreeRubber27` | Seringueira | tree | `próprio` | ok | falta |
| `feTreeRubber41` | Seringueira | tree | `próprio` | ok | falta |
| `feTreeRubberSeed` | Seringueira (muda) | tree | `próprio` | ok | falta |
| `feDeployer` | Aplicador | world | `feTorqueRegulatorPrefab` | falta | falta |
| `feMechDrill` | Furadeira Mecânica | world | `feCrusherPrefab` | falta | falta |
| `feMechHarvester` | Colheitadeira Mecânica | world | `feSpeedBoxPrefab` | falta | falta |
| `feMechSaw` | Serra Mecânica | world | `feCrusherPrefab` | falta | falta |

## Itens sem ícone próprio (106)

Usam o ícone de um item do jogo com tinta. Um ícone 160x160 transparente em
`Mods/FerroEngrenagem/UIAtlases/ItemIconAtlas/<item>.png` + `python tools/apply_icons.py` resolve.

| Item | Nome | Ícone emprestado (tinta) |
|---|---|---|
| `feAntibioticPowder` | Pó Antibiótico | `drugAntibiotics` (ffffff) |
| `feArmorPlate` | Placa de Armadura Temperada | `feResourceIronPlate` (6080a0) |
| `feArrowHeaded` | Haste com Ponta | `ammoArrowIron` (a0a0a0) |
| `feArrowShaft` | Haste de Flecha | `resourceWood` (c0a080) |
| `feBarkDust` | Casca Moída | `resourceWood` (806040) |
| `feBatteryCase` | Caixa de Bateria | `carBattery` (a0a0a0) |
| `feBoilerShell` | Corpo de Caldeira | `feResourceIronPlate` (806040) |
| `feBrassDust` | Pó de Latão | `resourceScrapBrass` (e0c060) |
| `feBuckle` | Fivela | `resourceDoorKnob` (c0c0c0) |
| `feBulb` | Bulbo de Vidro | `resourceBrokenGlass` (ffffc0) |
| `feCarbonBlack` | Negro de Fumo | `resourceCoal` (303030) |
| `feChassisFrame` | Quadro Soldado | `resourceMetalPipe` (707070) |
| `feCircuitBase` | Base de Placa | `resourceElectricParts` (40a040) |
| `feCircuitBoard` | Placa de Circuito | `resourceElectricParts` (40ff40) |
| `feCircuitPopulated` | Placa Montada | `resourceElectricParts` (80e080) |
| `feCircuitTraced` | Placa com Trilhas | `resourceElectricParts` (60c060) |
| `feCrankshaft` | Virabrequim | `feResourceIronShaft` (e0e0e0) |
| `feCultureBroth` | Caldo de Cultura | `foodCropMushrooms` (c0c080) |
| `feCultureExtract` | Extrato de Cultura | `drugAntibiotics` (e0e0a0) |
| `feElectricMotorSmall` | Motor Elétrico Pequeno | `feResourceCoil` (80a0ff) |
| `feEngineBlock` | Bloco de Motor Fundido | `smallEngine` (808080) |
| `feEngineBlockBored` | Bloco de Motor Furado | `smallEngine` (a0a0a0) |
| `feEngineStage1` | Motor (pistões) | `smallEngine` (b0b0b0) |
| `feEngineStage2` | Motor (virabrequim) | `smallEngine` (c0c0c0) |
| `feEngineStage3` | Motor (velas) | `smallEngine` (d0d0d0) |
| `feEngineStage4` | Motor (lubrificado) | `smallEngine` (e0e0e0) |
| `feEngineerManual` | Manual do Engenheiro | `resourcePaper` (e0a030) |
| `feEngineerWrench` | Chave de Engenheiro | `meleeToolSalvageT1Wrench` (e0a030) |
| `feEthanol` | Álcool | `drinkJarGrandpasMoonshine` (e0f0ff) |
| `feFirebox` | Fornalha | `feResourceIronPlate` (a04020) |
| `feFruitConcentrate` | Concentrado de Fruta | `foodCropBlueberries` (c040c0) |
| `feGasCanister` | Botijão de Gás | `ammoGasCan` (60a0ff) |
| `feGasket` | Junta de Vedação | `resourceDuctTape` (303030) |
| `feGlassPane` | Placa de Vidro | `resourceBrokenGlass` (c0f0ff) |
| `feGrenadeFilled` | Carcaça Carregada | `thrownGrenade` (a07050) |
| `feGrenadeShell` | Carcaça de Granada | `thrownGrenade` (707070) |
| `feHerbExtract` | Extrato de Ervas | `drinkJarGoldenRodTea` (80c040) |
| `feHinge` | Dobradiça | `resourceDoorKnob` (a0a0a0) |
| `feHose` | Mangueira | `resourceMetalPipe` (303030) |
| `feHub` | Cubo de Roda | `feResourceGear` (c0c0c0) |
| `feInsulator` | Isolador de Cerâmica | `resourceClayLump` (f0f0f0) |
| `feLeadPlate` | Placa de Chumbo | `feResourceIronPlate` (707080) |
| `feLeatherTanned` | Couro Curtido | `resourceLeather` (a06030) |
| `feLensRaw` | Lente Bruta | `resourceScopeLens` (a0c0c0) |
| `feLightBulb` | Lâmpada | `resourceElectricParts` (ffff80) |
| `feLock` | Fechadura | `resourceDoorKnob` (e0c060) |
| `feMoldArrowHead` | Molde de Ponta de Flecha | `feMoldPlate` (a0a0a0) |
| `feMoldBatteryCase` | Molde de Caixa de Bateria | `feMoldPlate` (a0a0a0) |
| `feMoldBeaker` | Molde de Béquer | `feMoldPlate` (c0f0ff) |
| `feMoldBoard` | Molde de Placa | `feMoldPlate` (40a040) |
| `feMoldBuckshot` | Molde de Chumbo Grosso | `feMoldPlate` (707080) |
| `feMoldBulb` | Molde de Bulbo | `feMoldPlate` (ffffc0) |
| `feMoldCrank` | Molde de Virabrequim | `feMoldPlate` (e0e0e0) |
| `feMoldCylinder` | Molde de Cilindro | `feMoldPlate` (707070) |
| `feMoldEngineBlock` | Molde de Bloco de Motor | `feMoldPlate` (808080) |
| `feMoldGlassPane` | Molde de Placa de Vidro | `feMoldPlate` (c0f0ff) |
| `feMoldJar` | Molde de Pote | `feMoldPlate` (c0f0ff) |
| `feMoldLens` | Molde de Lente | `feMoldPlate` (a0c0c0) |
| `feMoldPellet` | Molde de Pellet | `feMoldPlate` (c0c0ff) |
| `feMoldPiston` | Molde de Pistão | `feMoldPlate` (c0c0c0) |
| `feMoldRocket` | Molde de Corpo de Foguete | `feMoldPlate` (707070) |
| `feMoldRod` | Molde de Vareta | `feMoldPlate` (c0c0c0) |
| `feMoldShell` | Molde de Carcaça | `feMoldPlate` (707070) |
| `feMoldStock` | Molde de Coronha Sintética | `feMoldPlate` (604020) |
| `feMoldToolHead` | Molde de Cabeça de Ferramenta | `feMoldPlate` (808080) |
| `feNeedle` | Agulha | `resourceNail` (e0e0e0) |
| `fePigment` | Pigmento | `resourcePaint` (ff6040) |
| `fePiston` | Pistão | `feSteamPiston` (c0c0c0) |
| `fePlaster` | Gesso em Pó | `resourceCement` (ffffff) |
| `fePolymerDust` | Grânulos de Polímero | `resourceScrapPolymers` (c0c0ff) |
| `fePressureGaugeItem` | Manômetro de Caldeira | `resourceScopeLens` (ffffff) |
| `feProfile` | Perfil de Aço | `resourceMetalPipe` (909090) |
| `fePulp` | Polpa de Madeira | `resourceWood` (e0d0b0) |
| `feRim` | Aro | `vehicleWheels` (c0c0c0) |
| `feRocketFilled` | Corpo de Foguete Carregado | `resourceRocketCasing` (a07050) |
| `feRod` | Vareta de Aço | `resourceMetalPipe` (c0c0c0) |
| `feRodBrass` | Vareta de Latão | `resourceMetalPipe` (e0c060) |
| `feRoundPrimed` | Cápsula com Pólvora | `resourceBulletCasing` (c08040) |
| `feRoundTipped` | Munição Aberta | `resourceBulletTip` (c0a060) |
| `feRubberBelt` | Correia de Borracha | `resourceDuctTape` (505050) |
| `feRubberCoagulum` | Coágulo de Borracha | `resourceClayLump` (f0f0e0) |
| `feRubberCompound` | Composto de Borracha | `resourceClayLump` (404040) |
| `feRubberRaw` | Borracha Crua | `resourcePaper` (b09060) |
| `feRubberSheetRaw` | Folha de Borracha Úmida | `resourcePaper` (e0d8b0) |
| `feRubberSole` | Sola de Borracha | `resourceLeather` (303030) |
| `feSafetyValve` | Válvula de Segurança | `feResourceGear` (ff4040) |
| `feServo` | Servo | `feResourceGear` (80a0ff) |
| `feShaleAsh` | Cinza de Xisto | `resourceCrushedSand` (707070) |
| `feShaleCrushed` | Xisto Moído | `resourceOilShale` (a0a0a0) |
| `feSparkPlug` | Vela de Ignição | `resourceElectricParts` (e0e0ff) |
| `feSparkPlugCeramic` | Corpo de Vela | `resourceClayLump` (e0e0ff) |
| `feSteamCylinder` | Cilindro a Vapor | `feSteamPiston` (c0c0c0) |
| `feSteamCylinderRaw` | Cilindro a Vapor Bruto | `feSteamPiston` (707070) |
| `feSteelPlate` | Chapa de Aço | `feResourceIronPlate` (a0b0c0) |
| `feSteelWire` | Fio de Aço | `feResourceBrassWire` (d0d0d0) |
| `feSulfur` | Enxofre | `resourcePotassiumNitratePowder` (f0e040) |
| `feTestItem` | Item de Teste Ferro & Engrenagem | `resourceMechanicalParts` (ff8000) |
| `feThread` | Linha | `resourceCloth` (f0f0f0) |
| `feTinCan` | Lata Vazia | `foodCanSoup` (c0c0c0) |
| `feTire` | Pneu | `vehicleWheels` (303030) |
| `feToolHead` | Cabeça de Ferramenta | `meleeToolPickT1IronPickaxe` (d0d0d0) |
| `feToolHeadRaw` | Cabeça de Ferramenta Bruta | `meleeToolPickT1IronPickaxe` (808080) |
| `feValveGear` | Distribuidor | `feResourceGear` (c0c0c0) |
| `feWetPaper` | Papel Úmido | `resourcePaper` (d0d0c0) |
| `feWireThick` | Fio de Aço Grosso | `feResourceBrassWire` (b0b0b0) |
| `feZipper` | Zíper | `resourceNail` (c0c0c0) |

## Outros assets

- **Sons**: nenhuma máquina nova tem som próprio (manivela, prensa, furadeira, serra, ventilador, compressor, pistão).
- **Partículas novas** que ajudariam: vento do Ventilador (`FeFx_Wind`), serragem da Serra, poeira da Furadeira,
  água do lavador do Ventilador. Hoje os blocos sem modelo não têm empties `FeFx_*`.
- **Seringueira**: usa os modelos do carvalho plantado.
