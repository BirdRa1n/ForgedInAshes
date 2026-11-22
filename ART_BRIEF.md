# Briefing de arte — modelos 3D e ícones (trabalho em paralelo)

Este arquivo é para o agente/sessão que vai fazer a **arte** do mod em **outro PC**, em paralelo à Fase 1
(XML). Leia também `PLANO_MOD.md` (seções 5, 6 e "Fase 6") e `MODLOG.md`.

## Regras para não conflitar com o trabalho de XML

- Trabalhe **só** na pasta `Art/` (criar) e, quando chegar a hora de integrar, em `Mods/FerroEngrenagem/Resources/`
  e `Mods/FerroEngrenagem/UIAtlases/` (ou o que for confirmado; ver "Integração").
- **Não edite** `Mods/FerroEngrenagem/Config/*`, `tools/*`, `PLANO_MOD.md` nem `MODLOG.md`: são da sessão de XML.
  Se a arte precisar de mudança em XML (trocar `Model`, `CustomIcon`), escreva o pedido em `Art/PEDIDOS_XML.md`.
- Commits pequenos com prefixo `F6-ART:`; faça `git pull --rebase` antes de cada push.
- **Não redistribuir assets do jogo**: nada de exportar modelos/texturas vanilla (AssetRipper etc.) para dentro do
  repositório. Referência visual pode ser olhada no jogo/prints; o que vai no repo é arte própria.
- Arquivos grandes (`.blend`, `.fbx`, `.png` > alguns MB): considerar Git LFS antes do primeiro commit de binários.

## Versões que importam

| Item | Valor |
|---|---|
| Jogo | 7 Days to Die **V 3.4.0 (b10)** |
| Unity do jogo | **2022.3.62f2** (asset bundles precisam ser feitos nesta versão exata) |
| Blender | qualquer recente (no PC principal: 5.3) |
| Ícones vanilla | **160×160 px, PNG RGBA**, fundo transparente |

## O que fazer (por prioridade)

### 1. Máquinas da Fase 1 (já existem no jogo com modelos vanilla emprestados)

| ID do bloco | Nome (EN / PT-BR) | Ocupa (`MultiBlockDim` X,Y,Z) | Modelo provisório hoje | Ideia |
|---|---|---|---|---|
| `feFoundry` | Foundry / Fundição | 2×2×1 | forja vanilla | fornalha de tijolo + cadinho, chaminé curta |
| `fePress` | Parts Press / Prensa de Peças | 2×2×1 | bancada de combinar vanilla | prensa de bancada com volante e fuso, matriz de chapa |
| `feLathe` | Lathe / Torno | 1×1×1 | mesa de serra vanilla | torno mecânico pequeno, polia/correia, manivela lateral |

- Unidade: **1 bloco = 1 m**. Um 2×2×1 tem 2 m de largura × 2 m de altura × 1 m de profundidade
  (confirmar eixo no Unity; X,Y,Z do jogo = largura, altura, profundidade).
- Orientação de colocação: `TowardsPlacerInverted` (a frente aponta para o jogador que coloca).
- Estilo: sucata industrial pós-apocalíptica, metal gasto, parafusos, um pouco de ferrugem — combinar com o vanilla.
- Fase 2 vai precisar de **peças que giram** (volante, polia, engrenagem) quando a máquina estiver ligada: modele
  essas partes como **objetos separados** com pivô no eixo de rotação.
- Poucos polígonos (referência: estações vanilla), 1 material por máquina se possível, texturas 1024–2048.

### 2. Ícones dos itens (hoje são ícones vanilla tingidos)

`feResourceIronPlate` (Chapa de Ferro), `feResourceIronShaft` (Eixo de Ferro), `feResourceGear` (Engrenagem),
e das máquinas acima. 160×160 RGBA, nome do arquivo = nome do item (`feResourceGear.png`).

### 3. Depois (fases 2–4): `E01` Manivela, `E02` Carvoeira, `E03` Gerador a Carvão, `I01` Carvão Vegetal,
`I02` Volante de Inércia — ver tabelas em `PLANO_MOD.md`.

## Integração no jogo (ainda NÃO verificada — fazer junto com a sessão de XML)

- Modelos de mod entram como **asset bundle** do Unity 2022.3.62f2 e o bloco aponta `Model` para o bundle.
  A sintaxe exata do caminho (`#@modfolder:Resources/<bundle>.unity3d?<Prefab>` ou outra) **precisa ser confirmada**
  nos arquivos/código do jogo 3.4.0 antes de usar — não chutar.
- Ícones de mod: confirmar se a pasta `Mods/FerroEngrenagem/UIAtlases/ItemIconAtlas/` é o caminho lido pela 3.4.0.
- Entregável mínimo antes da integração: `Art/<maquina>/<maquina>.blend` + `.fbx` exportado + PNGs de preview,
  e os ícones em `Art/icons/`.
