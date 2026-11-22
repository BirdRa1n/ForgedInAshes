# feCharcoalKiln — Carvoeira (E02)

Modelo da Carvoeira (PLANO_MOD.md, seção 5.2, E02: 10 Wood → 2 Carvão Vegetal, lento), feito no Blender 5.3
por script. Forno de alvenaria em abóbada (pedra + argila, como o custo: Cobblestone Rocks, Clay Soil, Wood).

| Arquivo | O que é |
|---|---|
| `build_feCharcoalKiln.py` | Gera o modelo. **Limpa a cena** antes (salve o modelo anterior) |
| `render_previews.py` | Gera `preview_front/back/side.png` |
| `export_feCharcoalKiln.py` | Salva `feCharcoalKiln.blend` e exporta `feCharcoalKiln.fbx` |
| `feCharcoalKiln.blend` / `.fbx` | Modelo atual |

## Medidas e orientação

- **2 × 1 × 2 blocos** (largura X × profundidade Y × altura Z), como o Gerador a Carvão. Caixa ocupada:
  X −1,0…0,97, Y −0,48…0,50, Z 0…1,945.
- Origem no centro do chão da área ocupada. A frente (porta) aponta para **−Y**.
- Triângulos: 3.348 sem bevel; ~11.400 no FBX (bevel de 1 segmento aplicado na exportação).

## Objetos

| Objeto | O que é |
|---|---|
| `feKiln_Base` | tudo (nada se move): base de pedra, paredes e abóbada de pedra em fiadas desencontradas, paredes das pontas rebocadas com argila, porta de ferro em arco com visor, brasa sob a porta e nos 2 respiros, tirantes de ferro, chaminé de tijolo com chapéu, pilha de lenha |
| `feKiln_SmokePoint` | empty (filho da base) na boca da chaminé, em (−0,35; 0,24; 1,805), seta para +Z: ponto para um efeito de fumaça |

Para "ligado/desligado": as partes com o material `feKiln_Glow` (emissivo) podem ser trocadas ou apagadas.

## Portas de esteira

Seguem o padrão de `Art/CONVEYOR_PORTS.md`:

| Empty | Tipo | Posição | Onde |
|---|---|---|---|
| `feKiln_PortIn_1` | entrada (Wood) | (−0,5; 0,5; 0,25), para +Y | fundo da célula do forno |
| `feKiln_PortOut_1` | saída (Carvão Vegetal) | (−1,0; 0; 0,25), para −X | lado esquerdo |

Os tirantes de ferro subiram para 0,45 m para não cruzar a moldura da saída. 3.348 triângulos sem bevel.

## Materiais (provisórios)

`Stone`, `StoneDark`, `Clay`, `Iron`, `Soot`, `Glow`, `Bark`, `WoodCut` (prefixo `feKiln_`): só cores, sem
textura. Falta UV + atlas.

## Não verificado

- Eixos do FBX no Unity 2022.3.62f2; pivô de blocos multibloco no 7DTD.
- Se o 7DTD aceita um ponto de partícula vindo do modelo (a Forja vanilla tem fumaça/fogo: ver como é feita).
- Caminho do `Model` no `blocks.xml` para asset bundle de mod.
