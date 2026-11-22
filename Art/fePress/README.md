# fePress — Prensa de Peças (M02)

Modelo da Prensa de Peças (PLANO_MOD.md 5.1, M02: faz Chapa de Ferro e outras peças; F1 sem energia, F2+ com
Carga). Hoje o bloco `fePress` em `Config/blocks.xml` usa o modelo emprestado da bancada de combinar vanilla;
este é o modelo próprio pedido no ART_BRIEF ("prensa de bancada com volante e fuso, matriz de chapa").
Feito no Blender 5.3 por script.

| Arquivo | O que é |
|---|---|
| `build_fePress.py` | Gera o modelo. **Limpa a cena** antes (salve o modelo anterior) |
| `render_previews.py` | Gera `preview_front/back/side.png` |
| `export_fePress.py` | Salva `fePress.blend` e exporta `fePress.fbx` |
| `fePress.blend` / `.fbx` | Modelo atual |

## Medidas e orientação

- **2 × 1 × 2 blocos**, igual ao `MultiBlockDim="2,2,1"` do `blocks.xml`. Caixa: X −1,0…1,0, Y −0,43…0,5,
  Z 0…1,985. Origem no centro do chão da área ocupada; a frente aponta para **−Y**.
- Bancada com tampo a 0,88 m.
- Triângulos: 4.640 sem bevel; ~11.900 no FBX (bevel aplicado na exportação; o fuso rosqueado é a parte
  mais pesada: ~4.000).

## Peças

| Objeto | Movimento | Pivô | Conteúdo |
|---|---|---|---|
| `fePress_Base` | fixo (raiz) | chão (0,0,0) | bancada, armários de entrada/saída, pedestal de ferro fundido com mostrador de Carga, mesa da prensa, matriz de chapa, colunas, travessa com porca de latão, motor a Carga, alavanca de embreagem, lingotes (esq.) e chapas (dir.) |
| `fePress_Screw` | gira no **Z local** | (0, 0, 1,60) | fuso rosqueado + volante horizontal (4 raios, pino de mão) |
| `fePress_Ram` | sobe/desce no **Z local** | (0, 0, 1,26) | martelo com buchas nas colunas e punção; ~0,10 m de curso até a matriz |
| `fePress_DriveWheel` | gira no **Z local**, sentido contrário ao volante | (0,415, 0, 1,90) | roda de fricção do motor, encostada no aro do volante |

Ciclo sugerido para animar: motor e volante giram; o fuso desce o martelo, que prensa a chapa e volta.

## Portas de esteira

Seguem `Art/CONVEYOR_PORTS.md`:

| Empty | Tipo | Posição | Onde |
|---|---|---|---|
| `fePress_PortIn_1` | entrada (Forged Iron) | (−1,0; 0; 0,25), para −X | lado esquerdo, armário de entrada |
| `fePress_PortIn_2` | entrada (Carga) | (0,5; 0,5; 0,25), para +Y | fundo da célula direita |
| `fePress_PortOut_1` | saída (Chapa) | (1,0; 0; 0,25), para +X | lado direito, armário de saída |

## Materiais (provisórios)

`Wood`, `Iron`, `Rust`, `Steel`, `Brass`, `Copper`, `Soot`, `Dial`, `Rubber`, `PortIn`, `PortOut`
(prefixo `fePress_`): só cores, sem textura. Falta UV + atlas.

## Não verificado

- Eixos do FBX no Unity; pivô de blocos multibloco (o XML atual usa `ModelOffset="0,0,0"` com o prefab vanilla).
- Caminho do `Model` no `blocks.xml` para asset bundle de mod.
