# feFoundry — Fundição e Vidraria (M01)

Modelo da Fundição (PLANO_MOD.md 5.1, M01: Forged Iron, Forged Steel, latão, chumbo, vidro, Nails, Short Iron
Pipe; combustível como a Forja). Hoje o bloco `feFoundry` em `Config/blocks.xml` usa a forja vanilla (módulos
`tools,output,fuel`, janela `workstation_forge_nosmelting`); este é o modelo próprio pedido no ART_BRIEF
("fornalha de tijolo + cadinho, chaminé curta"). Feito no Blender 5.3 por script.

| Arquivo | O que é |
|---|---|
| `build_feFoundry.py` | Gera o modelo. **Limpa a cena** antes (salve o modelo anterior) |
| `render_previews.py` | Gera `preview_front/back/side.png` |
| `export_feFoundry.py` | Salva `feFoundry.blend` e exporta `feFoundry.fbx` |
| `feFoundry.blend` / `.fbx` | Modelo atual |

## Medidas e orientação

- **2 × 1 × 2 blocos**, igual ao `MultiBlockDim="2,2,1"` do `blocks.xml`. Caixa: X −1,0…1,0, Y −0,487…0,5,
  Z 0…1,77. Origem no centro do chão da área ocupada; a frente aponta para **−Y**.
- Célula esquerda: fornalha (até 1,08 m) com cadinho e chaminé curta (até 1,77 m). Célula direita: mesa de
  fundição (tampo a 0,74 m), fole e caixa de saída embaixo.
- Triângulos: **4.828** no FBX. A base **não tem bevel**: com ~300 tijolos ele triplicava a conta (~15k).

## Objetos

| Objeto | Movimento | Pivô | Conteúdo |
|---|---|---|---|
| `feFoundry_Base` | fixo (raiz) | chão (0,0,0) | fornalha de tijolos (fiadas desencontradas) com cantoneiras e cintas de ferro, porta com grelha em brasa, visor, cadinho de barro com metal derretido e tampa, chaminé de tijolo com chapéu, mesa com lingoteira (2 lingotes em brasa, 2 frios), lingotes prontos, concha, tenaz, corpo do fole com bico na fornalha, caixa de saída |
| `feFoundry_BellowsTop` | gira no **Y local** (dobradiça no lado do bico) | (0,10; −0,12; 0,17) | tábua de cima do fole + alavanca |
| `feFoundry_SmokePoint` | — | (−0,75; 0,24; 1,66) | empty na boca da chaminé (+Z para cima), para efeito de fumaça |

Para "ligado/desligado": materiais `feFoundry_Glow` (brasa) e `feFoundry_Molten` (metal derretido, mais forte)
são emissivos.

## Portas de esteira

Seguem `Art/CONVEYOR_PORTS.md`:

| Empty | Tipo | Posição | Onde |
|---|---|---|---|
| `feFoundry_PortIn_1` | entrada (minério/sucata) | (−0,5; 0,5; 0,25), para +Y | fundo da fornalha |
| `feFoundry_PortIn_2` | entrada (combustível) | (−1,0; 0; 0,25), para −X | lado esquerdo da fornalha |
| `feFoundry_PortOut_1` | saída (Forged Iron etc.) | (1,0; 0; 0,25), para +X | lado direito, caixa sob a mesa |

## Materiais (provisórios)

`Brick`, `BrickDark`, `Mortar`, `Clay`, `Iron`, `Rust`, `Steel`, `Soot`, `Wood`, `Leather`, `Glow`, `Molten`,
`PortIn`, `PortOut` (prefixo `feFoundry_`): só cores, sem textura. Falta UV + atlas.

## Não verificado

- Eixos do FBX no Unity; pivô de blocos multibloco; caminho do `Model` para asset bundle de mod.
- Se o 7DTD usa um ponto de partícula do modelo (a forja vanilla tem fogo/fumaça).
