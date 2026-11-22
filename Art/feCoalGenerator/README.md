# feCoalGenerator — Gerador a Carvão (E03)

Modelo do Gerador a Carvão (PLANO_MOD.md, seção 5.2, E03), feito no Blender 5.3 por script.
Queima Carvão Vegetal numa fornalha; o calor move um motor de ar quente que gira um dínamo (gera Carga).

| Arquivo | O que é |
|---|---|
| `build_feCoalGenerator.py` | Gera o modelo na cena aberta (rodar de novo recria os objetos `feCoalGen_*`) |
| `render_previews.py` | Gera `preview_front/back/side.png` |
| `export_feCoalGenerator.py` | Salva `feCoalGenerator.blend` e exporta `feCoalGenerator.fbx` |
| `feCoalGenerator.blend` / `.fbx` | Modelo atual |

## Medidas e orientação

- **2 × 1 × 2 blocos** (largura X × profundidade Y × altura Z; proposta: `MultiBlockDim="2,2,1"` no formato X,Y,Z
  do jogo = largura, altura, profundidade — confirmar). Caixa ocupada: X −1,0…0,99, Y −0,50…0,46, Z 0…1,96.
- Origem no centro do chão da área ocupada. A frente (porta da fornalha, mostrador) aponta para **−Y**.
- Triângulos: 5.128 sem bevel; ~13.100 no FBX (bevel de 1 segmento aplicado na exportação). É bastante para
  uma estação: tirar os `Bevel` antes de exportar corta para ~5.100.

## Peças

| Objeto | Gira? | Pivô | Conteúdo |
|---|---|---|---|
| `feCoalGen_Base` | não | chão (0,0,0) | esquis e chapa, fornalha (porta com frestas de brasa, gaveta de cinzas), chaminé, trocador aletado, cilindro do motor, carcaça do virabrequim, pedestal, dínamo, mostrador de Carga, caixote de carvão |
| `feCoalGen_Crank` | sim, eixo Y local | (0,12, 0, 0,95) | virabrequim, volante de inércia (5 raios, atrás), engrenagem de 16 dentes (frente) |
| `feCoalGen_DynamoRotor` | sim, eixo Y local | (0,42, 0, 0,95) | eixo do dínamo, pinhão de 8 dentes |

Os dois giram juntos: o pinhão gira **2× mais rápido e no sentido contrário** do virabrequim. Na fase 2, o
volante, as engrenagens e as frestas (material `Glow`) podem servir de indicação de "ligado".

## Portas de esteira

Seguem o padrão de `Art/CONVEYOR_PORTS.md`:

| Empty | Tipo | Posição | Onde |
|---|---|---|---|
| `feCoalGen_PortIn_1` | entrada (Carvão Vegetal) | (−1,0; 0; 0,25), para −X | lado esquerdo, na fornalha |
| `feCoalGen_PortOut_1` | saída (Carga) | (0,5; −0,5; 0,25), para −Y | frente da célula direita, duto até o pedestal do dínamo |

O caixote de carvão foi afastado (centro X = 0,85) para o duto de saída caber. 5.128 triângulos sem bevel.

## Materiais (provisórios)

`Iron`, `Rust`, `Copper`, `Soot`, `Dial`, `Wood` e `Glow` (emissivo laranja), todos com prefixo `feCoalGen_`:
só cores, sem textura. Falta UV + atlas (o ART_BRIEF pede 1 material por máquina; o `Glow` provavelmente
fica separado por ser emissivo).

## Não verificado

- Eixos do FBX no Unity 2022.3.62f2; pivô de blocos multibloco no 7DTD (centro da área ou bloco-pai).
- Caminho do `Model` no `blocks.xml` para asset bundle de mod.
