# Padrão de portas de esteira (proposta)

Toda máquina poderá ser ligada a uma esteira. Este é o padrão que os modelos em `Art/` seguem, para que a
esteira (ainda não projetada; ver PLANO_MOD.md 5.3, L01/L02) encaixe em qualquer máquina do mesmo jeito.
É uma **proposta de arte**: a lógica (C#, fase 5) e a esteira em si podem pedir ajustes.

## Geometria

| Item | Valor |
|---|---|
| Abertura | 0,36 m (largura) × 0,22 m (altura) |
| Altura do centro | **0,25 m** acima do chão do bloco |
| Posição | na face externa de **uma célula** de bloco, centrada nela (ex.: máquina 2×1, célula da esquerda: X = −0,5) |
| Moldura | ferro, 0,045 m, rente à face do bloco (não passa do limite do bloco) |
| Cor | barra de cima **verde** = entrada (`*_PortIn`), **laranja** = saída (`*_PortOut`) |
| Entrada | rampa interna descendo para dentro da máquina |
| Saída | aba articulada sobre a parte de cima da abertura |
| Duto | liga a face do bloco ao corpo da máquina; fundo escuro |

## Pontos para a programação

Cada porta tem um **empty** filho da base da máquina, no centro da abertura, sobre a face do bloco:

- Nome: `<prefixo>_PortIn_<n>` ou `<prefixo>_PortOut_<n>` (n começa em 1, por tipo).
- Orientação: o **+Z local aponta para fora** da máquina (no Blender; conferir como chega no Unity).

## Portas atuais

| Máquina | Entrada | Saída |
|---|---|---|
| Manivela `feCrank` (1×1×1) | — | Carga: lado direito (+X), caixa coletora ligada ao dínamo |
| Gerador a Carvão `feCoalGenerator` (2×1×2) | Carvão Vegetal: lado esquerdo (−X), na fornalha | Carga: frente (−Y) da célula direita |
| Carvoeira `feCharcoalKiln` (2×1×2) | Wood: fundo (+Y) da célula do forno | Carvão Vegetal: lado esquerdo (−X) |

O Volante de Inércia (`feFlywheel`) é um item, não tem portas.

## A esteira

`Art/feConveyor`: reta (`feConveyor`) e curva de 90° (`feConveyorCorner`), 1 bloco cada, lona com topo a
0,175 m e 0,32 m de largura, entrando na abertura das portas. As pontas da esteira têm os mesmos empties
`*_PortIn_1` / `*_PortOut_1`: uma esteira encaixa numa máquina (ou em outra esteira) quando um `PortOut`
fica na mesma face que um `PortIn`, apontando em sentidos opostos. Ver `feConveyor/preview_line.png`.

## Ao modelar uma máquina nova

O código das portas está em cada `build_*.py` (função `port()` e lista `PORTS`); copie o bloco
"conveyor ports" e declare `PORTS = [(tipo, ponto_na_face, normal_para_fora, profundidade_do_duto), ...]`.
Evite colocar outras peças na faixa de 0,095 a 0,405 m de altura na frente de uma porta.
