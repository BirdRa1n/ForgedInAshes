# feHD — modelos HD (estilo 7 Days to Die) e efeitos

Remake de vinte e cinco blocos (e dois blocos novos) com geometria nova, textura PBR gerada por IA local (`F:\IA`, ver `F:\IA\LEIA-ME.md`) e
efeitos ligados ao estado da máquina. Os modelos antigos (`Art/<bloco>/<bloco>.fbx`) continuam no repositório; o
`FeBuild.cs` usa o HD quando existe `Art/<bloco>/hd/<bloco>_HD.fbx`.

| Bloco | Pasta | O que mudou | Efeitos |
|---|---|---|---|
| Fundição `feFoundry` (modelo `feM_Foundry`) | `Art/feM_Foundry/hd` | fornalha de tijolo refratário sobre esqui de aço, cintas rebitadas, porta da fornalha, cadinho no garfo, chaminé de tijolo, soprador (`FeSpin_x3_Blower`), **canal de metal** em volta da camada de baixo com bica em cada face externa, **entradas de esteira** atrás (2) e nas pontas (2) | brilho da porta e fumaça na chaminé enquanto queima; faíscas no cadinho com metal; metal do canal/cadinho aceso conforme o metal; **jato** do cadinho para o canal enquanto sai metal |
| Calha de Metal `feMetalChute` | `Art/feMetalChute/hd` | calha em U de aço rebitado com revestimento de tijolo, pés, duto quadrado nos braços de cima/baixo | metal **corre** (textura rolando) e brilha enquanto passa; quando o fluxo para, **esfria** devagar (amarelo → vermelho → crosta escura) |
| Mesa de Moldagem `feCaster` | `Art/feCaster/hd` | mesa de ferro fundido com caixa de areia (molde), copo de vazamento atrás, tanque de têmpera, faixa de perigo | **jato** do bico para o molde enquanto enche; o metal no molde (`FeCastMetal`) **esfria** conforme o tempo de resfriamento real (`FluidState.Steam / Time`) e solta **vapor** enquanto esfria |
| Eixo `feShaft` | `Art/feShaft/hd` | acoplamentos com parafusos, cubo, colares de graxa, mancal fixo no meio | — (gira como antes) |
| Condensadora `feCondenser` | `Art/feCondenser/hd` | (rodada 5) **condensador a ar**: caixa com dois núcleos aletados (tubos de cobre + aletas) nas paredes, ventilador no topo puxando o ar, coletores de vapor em cima e de condensado embaixo, visor de fluxo, tambor recebedor com visor de nível, manômetro | ventoinha; **ponteiro** do manômetro (`FeNeedle_Steam`) com a entrada de vapor; **coluna d'água** no visor de nível (`FeLevelLiquid`); **gotas** no visor de fluxo (`FeFx_Drip`); vapor sobre a ventoinha |
| Cano `fePipe` | `Art/fePipe/hd` | conexão em cruz de ferro fundido com parafusos e **visor**; braços com flange parafusada e cordão de solda | o visor mostra a **cor do fluido** da rede (água, óleo, gasolina, lubrificante, vapor; vazio = vidro escuro) |
| Bomba Mecânica `feMechPump` | `Art/feMechPump/hd` | voluta de ferro fundido parafusada, pedestal, mancais, copo de escorva, base com chumbadores, faixa de perigo | visor com **água** enquanto bombeia |
| Lavadora `feWasher` | `Art/feWasher/hd` | **trommel**: tambor de grelha com levantadores e anéis, roletes, barra de spray com bicos, calha de água, tremonha | **tambor gira** trabalhando (`FeWorkSpin_x0.5_Trommel`); **spray** de água; gotas; água barrenta subindo com o nível |
| Misturador Químico `feChemMixer` | `Art/feChemMixer/hd` | tanque aberto de fundo cônico sobre pés, ponte com cabeçote cônico, corrente do eixo de torque, agitador âncora com pás inclinadas, tremonha de pó com comporta, válvula de fundo | agitador pelo torque; **calda sobe** com o nível e **gira** com espuma (`FeSurface_r0.22_Spin_Slurry`); bolhas |
| Secador a Vapor `feSteamDryer` | `Art/feSteamDryer/hd` | **secador rotativo**: tambor inclinado com levantadores, anéis de rolagem sobre roletes, coroa, serpentina de vapor (jaqueta), tremonha, coifa de descarga, chaminé, purgador | **tambor gira** trabalhando (`FeWorkSpin_x0.4_Drum`); vapor na chaminé; gotas no purgador; manômetro |
| Biodigestor Industrial `feBiodigesterBig` | `Art/feBiodigesterBig/hd` | tanque alto com cintas, domo, poço de inspeção aberto, caixas cônicas no eixo, proteção da corrente, cabeçote, escada, visor de nível alto, tocha | agitador pelo torque; mosto no poço com bolhas; **coluna no visor de nível** (`FeSurface_r0.95_Level`); tocha; manômetro |
| Biodigestor `feBiodigester` | `Art/feBiodigester/hd` | **biodigestor de campânula flutuante**: tanque com cintas, selo d'água, campânula de aço, câmara de visor na frente, linha de gás com manômetro, tocha | **campânula sobe** com o nível e **gira** devagar trabalhando (`FeSurface_r0.08_Spin_GasHolder`); mosto subindo no visor com espuma e **bolhas**; **chama** na tocha enquanto trabalha; ponteiro do gás |
| Motor a Vapor `feSteamEngine` | `Art/feSteamEngine/hd` | caldeira estilo locomotiva, fornalha com porta aberta, domo, válvula, apito, chaminé; **máquina vertical de dois cilindros sobre o virabrequim** (rodada 4): virabrequim = eixo de saída, com duas manivelas a 90°, contrapesos e volante na frente; mancais, colunas em A, guias, cruzetas, bielas, cilindros com caixa de vapor no andar de cima | biela-manivela de verdade (`KineticSpinner.Linkage`): cruzetas e bielas seguem o ângulo real do virabrequim; fogo, fumaça, purgas e pluma de escape como antes |
| Caixa de Transmissão `feGearbox` | `Art/feGearbox/hd` | cubo de ferro fundido com nervuras nos três eixos, flanges parafusadas nas 6 faces, bocal de óleo, placa | — |
| Caixa de Velocidade `feSpeedBox` | `Art/feSpeedBox/hd` | carcaça com nervuras e pés, grade no topo (engrenagens à mostra), seletor de relação com alavanca | — |
| Inversor de Giro `feSpinInverter` | `Art/feSpinInverter/hd` | tambor com carcaça cruzada, **engrenagens cônicas** de entrada/saída e uma intermediária que gira (`FeSpin_InverterIdler`), janela com grade, seta | — |
| Embreagem `feClutch` | `Art/feClutch/hd` | sino com fendas de ventilação, placa de pressão com molas, disco de fricção, marcas verde/vermelha no quadrante | **alavanca** (`FeLever_Clutch`) vai para um lado engatada e para o outro solta (`BlockFeKinetic.Engaged`), em ~0,5 s |
| Torno `feLathe` (modelo `feM_Lathe`) | `Art/feM_Lathe/hd` | gabinete com gavetas, bandeja de cavaco, barramento com guias, cabeçote com motor e capa da correia, contraponta com volante, luminária | **carro porta-ferramenta** anda no barramento enquanto trabalha (`FePiston_Carriage`); placa gira |
| Triturador `feCrusher` | `Art/feCrusher/hd` | laterais de ferro fundido com nervuras, mancais, funil rebitado com faixa de perigo, rolos dentados, par de engrenagens com proteção | **poeira** sobre o funil enquanto o progresso da receita anda |
| Esteira `feConveyor` | `Art/feConveyor/hd` | estrutura de cantoneira com diagonais e sapatas, lona de borracha escura com taliscas de aço, guardas rebitadas, fim com faixa de perigo; curva e mesa de esferas no mesmo estilo | — (todas as peças do `Belt.cs` mantidas) |
| Prensa de Munição `feAmmoPress` (modelo `feM_Ammo`) | `Art/feM_Ammo/hd` | (rodada 5) bancada de aço, painel, prensa progressiva com cabeçote de 5 matrizes, **alimentador de cápsulas e de projéteis** (tigelas que giram), tubo de espoletas, dosador de pólvora, **duas mini-esteiras**, rampa e calha, caixa de munição aberta | torre gira, aríete desce; **cápsulas vazias andam** do caixote pela esteira e sobem ao prato; **cartuchos prontos** descem pela calha e vão pela esteira até a caixa (`FeTrack_n_P*` / `FeTrackItem_n_*`); roletes e tigelas giram |
| Duto de Esteira `feConveyorDuct` (**novo**) | `Art/feConveyorDuct/hd` | caixa de aço com a esteira dentro, boca no padrão das entradas (0,36 × 0,22, centro 0,25), colarinhos com pés, caixas de engrenagem laterais nos cubos de eixo (0,5 m), setas na tampa | peças de encaixe trocadas pelo `BeltShape` (ver `Art/CONVEYOR_PORTS.md`); itens escondidos |
| Suporte de Esteira `feConveyorStand` (**novo**) | `Art/feConveyorStand/hd` | cavalete de cantoneira com X de travamento, tampo e berço que sobe 9 cm no bloco de cima (onde assentam os pés do duto) | — |
| Funil `feFunnel` | `Art/feFunnel/hd` | placa de fixação, tremonha rebitada em degraus, faixa de perigo; gira para qualquer lado | três bicos (`FunnelShape`): esteira, duto, reto |
| Esteira `feConveyor` | (rodada 2) | + calha de transferência `FeBeltChute` | aparece quando aponta para máquina ou duto |
| Motor Elétrico `feElectricMotor` / `feElectricMotor2` | `Art/feElectricMotor*/hd` | carcaça TEFC com aletas, tampas parafusadas, pés de ferro fundido, caixa de ligação com prensa-cabo, olhal | — |
| Motor Elétrico Industrial `feElectricMotor3` | `Art/feElectricMotor3/hd` | motor aletado sobre base de vigas, capa do ventilador com grade, redutor com visor de óleo, painel com manômetros, eletrocalha, escada | — |
| Dínamo `feDynamo` | `Art/feDynamo/hd` | carcaça octogonal com janelas mostrando as bobinas de cobre, comutador segmentado e porta-escovas, isoladores no topo | — |
| Dínamo Industrial `feDynamo2` | `Art/feDynamo2/hd` | gerador octogonal de 6 polos, excitatriz atrás, quadro com medidores e chaves-faca, barramentos de cobre até os isoladores, escada | — |

Todos os contratos antigos foram mantidos: nomes `FeArm_*`, `FeSpin_*`, `FeCastMetal`, `FeCastReady`, `FeLevelGas`,
`FeLevelLiquid`, `FeFan_*`, `WireOffset`; pivôs e eixos (conferidos no log do FeBuild: eixo +Z, bomba +X), altura
das flanges (0,5 m) e da calha.

## Contrato de efeitos (novo)

| No Blender | No Unity (FeBuild) | No jogo (`src/ForgedInAshes/FxVisual.cs`) |
|---|---|---|
| material `feHD_Molten` | `FeMolten.mat` (Standard; albedo `molten_crust`, emissão `molten_heat`) | `_EmissionColor` = cor do metal × calor; `_MainTex_ST` rola enquanto corre |
| material `feHD_Liquid` | `FeLiquid.mat` (Standard transparente, liso) | `_Color` = cor do fluido |
| material `feHD_Gas` | `FeGas.mat` (Standard fade) | — |
| material `feHD_Glow` | `FeGlow.mat` (emissão) | aceso e piscando enquanto a fundição queima |
| objeto `FePour_*` | escondido no prefab | aparece enquanto o metal escorre ali |
| empty `FeFx_<tipo>_*` | `ParticleSystem` para cima, aparência pela tabela `FxLooks` do FeBuild: `Fire` (chama, `FeFlame.mat`), `Splash` (respingo de metal), `Sparks`, `Smoke`, `Dust` (poeira), `SteamVent` (pluma forte), `Steam` | `Play`/`Stop` conforme o estado (`SteamVent` pelo `SteamVent.cs`) |
| objeto `FeWorkSpin_[x<m>]_*` | — | gira no +Z local enquanto a máquina de processo trabalha (sem eixo de torque) |
| objeto `FeSurface_r<faixa>[_Spin]_*` (pivô no nível VAZIO) | — | sobe até `<faixa>` m com o buffer de fluido; `_Spin` gira devagar trabalhando; cor do líquido por máquina (mosto, calda, água de lavagem) |
| objeto `FeNeedle_*` | — | ponteiro de manômetro (270°): condensadora = entrada de vapor (`CondenserVisual`); outras = pressão trabalhando |
| empties `FeTrack_<n>_P<i>` + objetos `FeTrackItem_<n>_<k>` | — | mini-esteira (`MachineVisual`): as peças andam pelo caminho enquanto a oficina trabalha, nascendo e sumindo nas pontas |
| `FeFx_Drip_*`, `FeFx_Spray_*`, `FeFx_Bubbles_*` | presets na `FxLooks` | gotas, spray d'água (para baixo), bolhas |
| objeto `FeLever_*` | — | gira ±35° no X local conforme o estado (embreagem) |
| `FeCrankPin_<n>` (empty no pino da manivela, pose de construção), `FeCrosshead_<n>` (pivô no pino da cruzeta), `FeConrod_<n>` (pivô no pino da cruzeta, apontando para o pino da manivela) | — | `KineticSpinner` resolve a biela-manivela a partir do ângulo do `FeSpin_*` com "Flywheel"/"Crank" no nome: a cruzeta corre na reta eixo→cruzeta, a biela gira até o pino |

Cores do metal: ferro laranja, aço amarelo-claro (mais quente), latão amarelo, chumbo quase sem brilho (prateado).
O estado vem do `FluidStore`/`FluidTicker`/workstation, como os outros visuais: em servidor dedicado os clientes
não veem os efeitos (mesma limitação do `CasterVisual` e do `CondenserVisual`).

## Refazer

```powershell
# 1. geometria (um .blend por bloco em Art/<bloco>/hd/<bloco>_src.blend)
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b --factory-startup --python Art\feHD\build_feHD.py -- feCaster
# 2. textura + bake + FBX HD (config em F:\IA\fe_blender\configs\<bloco>.json)
F:\IA\texturizar.bat F:\IA\fe_blender\configs\feCaster.json
# 3. bundle
& "E:\UnityEditors\2022.3.62f2\Editor\Unity.exe" -batchmode -quit -projectPath Art\UnityProject -executeMethod FeBuild.BuildAll -logFile Art\UnityProject\Logs\febuild.log
```

Texturas de efeito compartilhadas em `Art/feFx/` (`molten_heat.png`, `molten_crust.png` da IA; `smoke_puff.png` e
`spark.png` gerados por código). As texturas HD vão para o bundle com compressão crunch (bundle de 2,5 MB → 14 MB
com estes sete).

## Não verificado

- **No jogo**: a DLL carrega e os patches aplicam (Player.log 2026-11-24 12:45), mas os modelos e efeitos ainda não
  foram vistos num mundo. Roteiro em `TESTE_GERAL.md`, seção 13.
- Direção das partículas com o bloco girado (o emissor é girado para cima no prefab sem rotação).
- Sentido da alavanca da embreagem (engatada para um lado é só convenção: conferir se faz sentido visualmente).
- Visual do shader Standard com a iluminação do jogo (brilho do metal pode precisar de ajuste em `FxVisual.MetalGlow`).

## Rodada 2 (2026-11-24, depois do primeiro teste no jogo)

- **Fogo atravessando a fornalha** (print do usuário): era a partícula vanilla `forgeWorkstation` (`ParticleName` +
  `ParticleOffset` no `blocks.xml` do `feFoundry`), posicionada para o modelo antigo. Saiu do XML; a Fundição ganhou
  uma **boca de fornalha aberta** (lintel, grelha, brasa, porta aberta encostada no tijolo) na célula esquerda, com
  chama própria (`FeFx_Fire_1`) que fica dentro da boca.
- **Despejo pouco natural**: além do jato reto, a mesa estava fisicamente errada (molde a 0,60 m, acima da calha
  a ~0,45 m). Agora é uma bancada baixa de fundição: copo atrás na altura da calha, canal inclinado revestido de
  tijolo, e o metal cai **em arco** do bico até o molde (fundo a 0,22 m), afinando na queda, com a textura correndo para
  baixo e faíscas de respingo no ponto de impacto (`FeFx_Splash_1`). A peça pronta sai numa prateleira à altura da
  esteira. Mesmo jato em arco do cadinho da Fundição até o canal.

## Rodada 3 (2026-11-24): duto fechado, suporte, funil girando, encaixes reais, motores e dínamos

- `feConveyorDuct` = `feConveyor` + `FeBeltClosed=true` (mesma lógica; sem desenhar itens, sem animação, não pega
  itens do chão). `feConveyorStand` sem lógica. Funil: `AllowedRotations=No45`.
- Ícones de todos os blocos HD refeitos a partir dos modelos novos: `Art/feHD/render_icons_hd.py` e depois
  `python tools/apply_icons.py`.
- Peças de encaixe ficam fora do collider (`FeBuild.OptionalParts`).

## Rodada 4 (2026-11-24): motor a vapor com virabrequim

- Teste do usuário: o pistão 1 atravessava a fornalha (cilindros paralelos ao eixo, pistões oscilando numa senoide
  sem ligação com nada). O motor virou uma máquina vertical de dois cilindros sobre o virabrequim.
- Cinemática conferida no Blender com o mesmo algoritmo (`render` de 0/90/180/270°: erro biela↔pino 0,0000;
  cruzetas entre 0,81 e 1,03 m, dentro das guias).

## Rodada 5 (2026-11-24): condensadora, máquinas de processo, prensa de munição

- Condensadora: as caixas `FeLevelGas`/`FeLevelLiquid` esticando ("massinha pulando") saíram; agora ponteiro,
  coluna d'água num visor de vidro, gotas e ventoinha num condensador a ar de verdade.
- Biodigestores, secador, misturador, lavadora e prensa refeitos (ver tabela). Movimento real: tambores rotativos,
  campânula flutuante, agitadores, spray, gotas, bolhas, chama, mini-esteiras.
- `FeSurface`/`FeTrackItem` fora do collider. Bundle 45 MB.
