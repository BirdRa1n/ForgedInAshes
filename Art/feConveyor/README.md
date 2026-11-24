# feConveyor — Esteira baixa (reta, curvas, divisão, rampas)

Esteira na altura das portas das máquinas (padrão em `Art/CONVEYOR_PORTS.md`). Substitui o modelo alto
(mesa de 0,62 m) da D10 desde 2026-11-24, a pedido do usuário. A lógica é a mesma: `src/FerroEngrenagem/Belt.cs`.
Feita no Blender 5.3 por script.

| Peça (bloco) | O que é | FBX |
|---|---|---|
| `feConveyor` | Um modelo com todas as formas; o `BeltShape` mostra a que vale para o bloco | `Art/feConveyor/feConveyor.fbx` |
| `feConveyorRamp` | Sobe 1 bloco: atrás a 0,175 m, na frente a 1,175 m (45°) | `Art/feConveyorRamp/feConveyorRamp.fbx` |
| `feConveyorDown` | Desce 1 bloco: atrás a 1,175 m, na frente a 0,175 m | `Art/feConveyorDown/feConveyorDown.fbx` |
| `feConveyorStand` | Suporte de 1 bloco; a forma segue a esteira de cima (`ConveyorStand.cs`) | `Art/feConveyorStand/feConveyorStand.fbx` |

A Esteira com Filtro (`feConveyorFilter`) usa o modelo da `feConveyor`. O Duto (`feConveyorDuct`) continua com o modelo do Dário.

| Arquivo | O que faz |
|---|---|
| `build_feConveyor.py` | Gera as três peças (uma coleção cada). **Limpa a cena** antes |
| `export_feConveyor.py` | Salva `feConveyor.blend` e exporta os três FBX |
| `render_previews.py` | `preview_line.png` (linha montada), `preview_modes.png` (cada forma), `preview_front.png` |
| `render_icons.py` | Ícones 160×160 das quatro esteiras em `Mods/FerroEngrenagem/UIAtlases/ItemIconAtlas` |

Tudo em uma passada (sem interface):

```
blender --background --factory-startup --python build_feConveyor.py --python export_feConveyor.py --python render_previews.py
```

Depois `FeBuild.BuildAll` no Unity (bundle) e `tools/build.ps1` (DLL).

## Medidas

- Superfície da lona a **0,175 m** (`Belt.Top = 0.18`); a abertura das portas vai de 0,14 a 0,36 m, então a
  esteira encosta direto na máquina, sem calha.
- Lona com 0,32 m de largura; perfis em C a ±0,19 m (z 0,075 a 0,168) e guias até 0,235 m.
- Curva com raio de 0,5 m na linha de centro, em volta do canto de trás do lado da curva (o mesmo arco que os
  itens fazem).
- Suporte do eixo: mancal a 0,5 m (altura dos eixos) na face lateral, com uma corrente até a esteira.

## Peças que o `Belt.cs` liga e desliga (nomes obrigatórios)

Andar para a frente = −Y no Blender (+Z no Unity); `_L` = +X no Blender (esquerda no jogo). Todas as peças
ficam na raiz, sem pai (o FBX com bake estraga netos).

| Forma | Peças |
|---|---|
| Reta | `FeBeltBed`, `FeBeltSlats` (travessas que deslizam 0,125 m), `FeSpin_BeltRollerFront/Back`, `FeRail_L/R` (somem onde outra esteira encosta), `FeBeltEnd` (batente quando nada recebe na frente) |
| Curva | `FeCurveSet_L/R` + `FeCurveSlats_L/R` (giram em volta do canto) |
| Divisão (2 ou 3 saídas) | `FeJunction` (mesa de esferas), `FeJunctionPosts`, `FeJunctionWedge` (divisor em V, só quando divide para os dois lados) |
| Esteira larga | `FeBeltFill_L/R` + `FeBeltFillSlats_L/R`: lona até a face quando há uma esteira ao lado andando no mesmo sentido (o trilho daquele lado some) |
| Tração | `FeBeltDrive_L/R` + `FeSpin_BeltDrive_L/R`: aparecem só no lado onde encosta um bloco de torque (eixo, caixa, motor) |

As rampas têm só a base, as travessas, os roletes e a tração.

## Suporte (`feConveyorStand`)

`FeStand_Straight` (reta, rampa ou nada em cima), `FeStand_Curve_L/R`, `FeStand_Junction`, `FeStand_Duct`
(deck e berço do Duto). Feitas no referencial da esteira e giradas para a rotação da esteira de cima.

## Pré-visualização ao colocar

`BeltPreviewPatch` (Belt.cs): enquanto o jogador segura uma esteira ou um suporte, o fantasma mostra a forma
que ele terá naquela posição e rotação (curva, divisão, esteira larga, tração), em vez de todas as peças juntas.

## A fazer

- O bico do Funil (`feFunnel`, modelo HD do Dário) e a rampa do Duto (`FeDuctRamp`) ainda descem até 0,62 m;
  precisam ser baixados para 0,18 m.
- Testar no jogo: altura dos itens, animação das travessas e da curva, sentido de giro dos roletes, tração só
  ao lado do eixo.
