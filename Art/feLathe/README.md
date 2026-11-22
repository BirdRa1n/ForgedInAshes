# feLathe — Torno e Usinagem (M03)

Modelo do Torno (PLANO_MOD.md 5.1, M03: faz Eixo, Engrenagem, Mechanical Parts, Spring e Volante de Inércia;
F1 sem energia, F2+ com Carga). Hoje o bloco `feLathe` em `Config/blocks.xml` usa a mesa de serra vanilla;
este é o modelo próprio pedido no ART_BRIEF ("torno mecânico pequeno, polia/correia, manivela lateral").
Feito no Blender 5.3 por script.

| Arquivo | O que é |
|---|---|
| `build_feLathe.py` | Gera o modelo. **Limpa a cena** antes (salve o modelo anterior) |
| `render_previews.py` | Gera `preview_front/back/side.png` |
| `export_feLathe.py` | Salva `feLathe.blend` e exporta `feLathe.fbx` |
| `feLathe.blend` / `.fbx` | Modelo atual |

## Medidas e orientação

- **1 × 1 × 1 bloco** (como no `blocks.xml`). Caixa: X −0,5…0,5, Y −0,365…0,5, Z 0…0,99.
- Origem no centro do chão do bloco; a frente aponta para **−Y**. Linha de centro do torno: Y −0,01, Z 0,90.
- Triângulos: 3.656 sem bevel; ~8.800 no FBX (bevel aplicado na exportação).

## Peças

Todas são filhas **diretas** da base (hierarquia plana: o export FBX com `bake_space_transform` desloca
"netos" — foi o que aconteceu com a manivela do carro antes da correção).

| Objeto | Movimento | Pivô | Conteúdo |
|---|---|---|---|
| `feLathe_Base` | fixo (raiz) | chão (0,0,0) | armário pintado (portas, gaveta, mostrador de Carga, chave), bandeja de cavacos, barramento com guias e fuso de avanço, cabeçote, contraponto, motor a Carga e correia |
| `feLathe_Spindle` | gira no **X local** | (−0,18; −0,01; 0,90) | eixo-árvore, placa de 3 castanhas, peça sendo torneada (um eixo escalonado), polia |
| `feLathe_MotorPulley` | gira no **X local** (mesmo sentido) | (−0,445; 0,19; 0,80) | polia do motor |
| `feLathe_Carriage` | desliza no **X local** | (0,02; 0; 0,80) | carro, carro transversal, porta-ferramenta com bit, avental |
| `feLathe_CarriageWheel` | gira no **Y local** e **acompanha o carro** | (−0,01; −0,195; 0,77) | manivela lateral do avental |
| `feLathe_TailWheel` | gira no **X local** | (0,40; −0,01; 0,90) | volante do contraponto |

## Portas de esteira

Seguem `Art/CONVEYOR_PORTS.md`:

| Empty | Tipo | Posição | Onde |
|---|---|---|---|
| `feLathe_PortIn_1` | entrada (matéria-prima: Forged Iron, Chapa, Eixo…) | (−0,5; 0; 0,25), para −X | lado esquerdo |
| `feLathe_PortIn_2` | entrada (Carga) | (0; 0,5; 0,25), para +Y | fundo |
| `feLathe_PortOut_1` | saída (peças prontas) | (0,5; 0; 0,25), para +X | lado direito |

## Materiais (provisórios)

`Wood`, `Iron`, `Rust`, `Steel`, `Brass`, `Copper`, `Soot`, `Dial`, `Rubber`, `Paint` (verde do armário),
`PortIn`, `PortOut` (prefixo `feLathe_`): só cores, sem textura. Falta UV + atlas.

## Não verificado

- Eixos do FBX no Unity; caminho do `Model` no `blocks.xml` para asset bundle de mod.
