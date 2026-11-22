# feCrank — Manivela (E01)

Modelo da Manivela (PLANO_MOD.md, seção 5.2, E01), feito no Blender 5.3 por script.

| Arquivo | O que é |
|---|---|
| `build_feCrank.py` | Gera o modelo na cena aberta (rodar de novo recria os objetos `feCrank_*`) |
| `render_previews.py` | Gera `preview_front/back/side.png` (câmera, sol e piso de preview) |
| `export_feCrank.py` | Salva `feCrank.blend` e exporta `feCrank.fbx` |
| `feCrank.blend` / `feCrank.fbx` | Modelo atual |

## Medidas e orientação

- 1 bloco (1×1×1 m). Caixa ocupada: X −0,47…0,50, Y −0,50…0,46, Z 0…0,905.
- Origem no centro do chão do bloco. A frente (onde o jogador gira a manivela) aponta para **−Y** no Blender.
- Triângulos: 3.120 sem bevel; ~8.000 no FBX (bevel de 1 segmento aplicado na exportação). Se ficar pesado,
  tirar os modificadores `Bevel` antes de exportar.

## Peças

| Objeto | Gira? | Pivô | Conteúdo |
|---|---|---|---|
| `feCrank_Base` | não | chão (0,0,0) | estrado, 2 cavaletes em A, mancais, dínamo, correia de couro |
| `feCrank_Rotor` | sim, eixo Y local | eixo (0, 0, 0,62) | eixo, volante de inércia (6 raios), polia, braço e empunhadura |
| `feCrank_DynamoPulley` | sim, eixo Y local | (0, 0,42, 0,17) | eixo e polia do dínamo |

Rotor e polia do dínamo são filhos da base. Relação das polias: 0,10 / 0,045 ⇒ a polia do dínamo gira
~2,2× mais rápido que o rotor.

## Porta de esteira

Segue o padrão de `Art/CONVEYOR_PORTS.md`. Uma **saída** (Carga) no lado direito (+X): caixa coletora de ferro
sobre o estrado, ligada ao dínamo por um cabo, com a porta na face do bloco. Empty `feCrank_PortOut_1` em
(0,5; 0; 0,25), +Z para fora. Com a caixa, o modelo vai até X = +0,5 e tem 3.120 triângulos sem bevel.

## Materiais (provisórios)

`feCrank_Wood`, `feCrank_Iron`, `feCrank_Rust`, `feCrank_Copper`, `feCrank_Leather`: só cores (Principled BSDF),
sem textura nem UV pensada. O ART_BRIEF pede 1 material por máquina: falta UV + atlas de textura 1024–2048.

## Não verificado

- Eixos do FBX dentro do Unity 2022.3.62f2 (exportado com Y up, −Z forward, transform aplicado).
- Se o pivô do prefab de bloco no 7DTD é o centro do chão ou o centro do bloco.
- Caminho do `Model` no `blocks.xml` para asset bundle de mod (ART_BRIEF, "Integração").
