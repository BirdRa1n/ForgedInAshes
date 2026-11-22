# feSawmill — Serraria (M16)

Modelo da Serraria (PLANO_MOD.md 5.1, M16, fase 3: faz Tábua `feResourcePlank` e Viga `feResourceBeam`;
energia Carga ou elétrica; custo 30 Forged Iron, 40 Nails, 10 Engrenagem). O bloco `feSawmill` **ainda não
existe** no `blocks.xml`. Feito no Blender 5.3 por script.

| Arquivo | O que é |
|---|---|
| `build_feSawmill.py` | Gera o modelo. **Limpa a cena** antes (salve o modelo anterior) |
| `render_previews.py` | Gera `preview_front/back/side.png` |
| `export_feSawmill.py` | Salva `feSawmill.blend` e exporta `feSawmill.fbx` |
| `feSawmill.blend` / `.fbx` | Modelo atual |

## Medidas e orientação (proposta)

- Ocupa **2 × 1** blocos no chão e vai até **1,125 m** de altura. Proposta para o bloco:
  `MultiBlockDim="2,2,1"` (como as outras estações grandes). Se preferirem **2,1,1**, basta baixar a mesa
  ~0,13 m (`TOP` e `BLADE` no script) para tudo caber em 1 m.
- Caixa: X −1,0…1,0, Y −0,42…0,5, Z 0…1,125. Origem no centro do chão; a frente aponta para **−Y**.
- Mesa a 0,80 m. Triângulos: 4.300 sem bevel; ~10.500 no FBX.

## Peças

Todas filhas **diretas** da base (ver a regra em `Art/CONVEYOR_PORTS.md`).

| Objeto | Movimento | Pivô | Conteúdo |
|---|---|---|---|
| `feSawmill_Base` | fixo (raiz) | chão (0,0,0) | bancada de madeira com fenda da serra, trilhos, proteção em arco (borda amarela) no braço, faca divisora, mancais e correia, motor a Carga, serragem, mostrador de Carga e alavanca, troncos à espera (esq.), tábuas e vigas (dir.), caixas de entrada/saída e caixa de ligação da Carga |
| `feSawmill_Blade` | gira no **Y local** | (0,10; 0; 0,70) | disco de 0,68 m com 36 dentes, flanges, eixo e polia |
| `feSawmill_MotorPulley` | gira no **Y local** (mesmo sentido) | (0,10; 0,24; 0,22) | polia do motor |
| `feSawmill_Carriage` | desliza no **X local** (para +X ao cortar) | (−0,15; 0,19; 0,82) | carro com rodas, montantes, garras, catraca e o tronco (com a face já serrada) |

O tronco fica atrás da serra e passa 1 cm na frente do disco: ao andar para +X, o disco "corta" uma tábua.

## Portas de esteira

Seguem `Art/CONVEYOR_PORTS.md`:

| Empty | Tipo | Posição | Onde |
|---|---|---|---|
| `feSawmill_PortIn_1` | entrada (madeira/troncos) | (−1,0; 0; 0,25), para −X | lado esquerdo, caixa de entrada |
| `feSawmill_PortIn_2` | entrada (Carga) | (−0,5; 0,5; 0,25), para +Y | fundo da célula esquerda, caixa de ligação (cabo até o motor) |
| `feSawmill_PortOut_1` | saída (Tábua/Viga) | (1,0; 0; 0,25), para +X | lado direito, caixa de saída |

## Materiais (provisórios)

`Wood`, `Bark`, `WoodCut`, `Sawdust`, `Iron`, `Rust`, `Steel`, `Copper`, `Rubber`, `Paint`, `Soot`, `Dial`,
`PortIn`, `PortOut` (prefixo `feSawmill_`): só cores, sem textura. Falta UV + atlas.

## Não verificado

- Tamanho final do bloco (fase 3); eixos do FBX no Unity; caminho do `Model` para asset bundle de mod.
