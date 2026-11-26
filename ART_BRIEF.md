# Briefing de arte — modelos 3D e ícones (trabalho em paralelo)

Este arquivo é para o agente/sessão que vai fazer a **arte** do mod em **outro PC**, em paralelo à Fase 1
(XML). Leia também `PLANO_MOD.md` (seções 5, 6 e "Fase 6") e `MODLOG.md`.

## Regras para não conflitar com o trabalho de XML

- Trabalhe **só** na pasta `Art/` (criar) e, quando chegar a hora de integrar, em `Mods/ForgedInAshes/Resources/`
  e `Mods/ForgedInAshes/UIAtlases/` (ou o que for confirmado; ver "Integração").
- **Não edite** `Mods/ForgedInAshes/Config/*`, `tools/*`, `PLANO_MOD.md` nem `MODLOG.md`: são da sessão de XML.
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

## Animação de giro da rede de torque (contrato, D8 — src/ForgedInAshes/KineticSpinner.cs)

Vale para os modelos (prefab no `forgedinashes.unity3d`, bloco com `Shape=ModelEntity`) de: Eixo, Caixa de
Transmissão, Caixa de Velocidade, Embreagem, Regulador, Medidor, Inversor de Giro, Motor Elétrico, Manivela de
Torque e as máquinas com encaixe de motor. O mod lê a rede a cada 0,25 s e anima sozinho; o asset só precisa
seguir os nomes abaixo (nenhum script dentro do bundle).

**Peças que giram (por nome do objeto no prefab)**
- Qualquer objeto cujo nome começa com `FeSpin` (exatamente assim, com F e S maiúsculos) gira em torno do **+Z local dele** (Unity; no Blender é o +Y
  antes de exportar, como o rotor da Manivela), na RPM da peça, no sentido real da rede (1 RPM = 6°/s; a rede vai
  de 4 a 256 RPM). Gire o pivô do objeto para o centro do eixo.
- `FeSpinIn` / `FeSpinOut`: lados de entrada e saída (Caixa de Velocidade: a saída usa a relação ×2/×4/×½;
  Inversor: a saída gira ao contrário). Nos outros blocos, os dois usam a RPM da peça.
- Sufixos separados por `_`: `_Rev` (gira ao contrário — a segunda engrenagem de um par) e `_x2`, `_x0.5`...
  (multiplicador, para engrenagens internas de tamanhos diferentes). Ex.: `FeSpinOut_x0.5_Rev`.
- Aceleração e desaceleração são suavizadas pelo mod (volante).

**Eixos dos blocos (orientação do modelo)**
- Eixo, Caixa de Velocidade, Embreagem, Regulador e Inversor: o eixo do bloco é o **+Z local** do modelo (como o
  cano de placeholder). Caixa de Velocidade e Regulador: entrada em −Z, saída em +Z.
- Motor Elétrico e Manivela de Torque: o eixo de saída é o **+Z local**, e eles giram no sentido +Z (regra da
  mão direita). As duas pontas (±Z) entregam torque.
- Caixa de Transmissão e Medidor: ligam as 6 faces; todas as saídas giram ao contrário da entrada (vistas de
  fora da caixa, todas as faces giram no mesmo sentido).

**Parâmetros de Animator (opcionais; só são usados se existirem no Animator do prefab)**
- `float FeRpm` (com sinal, em relação ao +Z do bloco), `float FeSpeed` (|RPM|/32; 1 = velocidade base, bom para
  multiplicar a velocidade de um estado), `bool FeRunning`, `bool FeOverloaded`, `bool FeLocked`,
  `bool FeWrongSpin` (máquina recebendo giro ao contrário).

**Modelos feitos (2026-11-23, `Art/feKinetic`)**: Manivela de Torque, Eixo, Caixa de Velocidade, Caixa de
Transmissão, Inversor de Giro e Regulador de Torque — FBX, bundle e `blocks.xml` integrados (2026-11-23; ver `Art/feKinetic/README.md`).

**Placeholders**: enquanto não há modelo, os blocos com `FeSpinWhole=true` giram o primeiro filho do prefab
vanilla, só para ver que os eventos chegam (os canos `Shape=New` não têm objeto para animar).

## Integração pendente (auditoria de 2026-11-22, sessão de XML)

Já no jogo: **feCrank** (Manivela), via `Resources/forgedinashes.unity3d` + `FeBuild.cs`.

Prontos em `Art/` mas **fora do bundle** (o `FeBuild.cs` só tem `Blocks = { "feCrank" }`):

| Bloco | Ocupa (`MultiBlockDim`) | Modelo usado hoje no jogo |
|---|---|---|
| `feFoundry` | 2×2×1 | forja vanilla |
| `fePress` | 2×2×1 | bancada de combinar vanilla |
| `feLathe` | 1×1×1 | mesa de serra vanilla |
| `feSawmill` | 1×1×1 | mesa de serra vanilla |
| `feCharcoalKiln` | 2×2×1 | forja quebrada vanilla |
| `feCoalGenerator` | 1×1×1 | gerador vanilla |

Pedido para quem tem o Unity 2022.3.62f2:
1. Acrescentar esses nomes ao array `Blocks` do `Art/UnityProject/Assets/Editor/FeBuild.cs` e rodar **ForgedInAshes > Build All**.
2. Commitar o `Mods/ForgedInAshes/Resources/forgedinashes.unity3d` novo.
3. Avisar a sessão de XML, que troca em `blocks.xml`, para cada bloco:
   `<property name="Model" value="#@modfolder:Resources/forgedinashes.unity3d?<bloco>Prefab"/>`
   **e** ajusta o `ModelOffset` ao pivô do prefab novo. O padrão do jogo é `(0, 0.5, 0)` quando a propriedade
   não existe; os blocos que hoje copiam um modelo vanilla podem ter `0,0,0` ou nada (ver MODLOG, bug da
   Cozinha/Serraria afundadas). Dizer qual pivô o prefab usa (base no chão ou centro).

Outros: `feFlywheel` é **item** (precisa de `Meshfile`, não de `Model`; formato ainda não verificado);
`feConveyor` é da logística (fase 5), sem bloco no XML ainda. As 10 máquinas da fase 3 ainda não têm modelo.

## Integração no jogo (ainda NÃO verificada — fazer junto com a sessão de XML)

- Modelos de mod entram como **asset bundle** do Unity 2022.3.62f2 e o bloco aponta `Model` para o bundle.
  A sintaxe exata do caminho (`#@modfolder:Resources/<bundle>.unity3d?<Prefab>` ou outra) **precisa ser confirmada**
  nos arquivos/código do jogo 3.4.0 antes de usar — não chutar.
- Ícones de mod: confirmar se a pasta `Mods/ForgedInAshes/UIAtlases/ItemIconAtlas/` é o caminho lido pela 3.4.0.
- Entregável mínimo antes da integração: `Art/<maquina>/<maquina>.blend` + `.fbx` exportado + PNGs de preview,
  e os ícones em `Art/icons/`.
