# feConveyor — Esteira (reta e curva)

Esteira para ligar as máquinas (PLANO_MOD.md 5.3, logística; padrão de encaixe em `Art/CONVEYOR_PORTS.md`).
Feita no Blender 5.3 por script. Duas peças, cada uma ocupa **1 bloco**:

| Peça | Fluxo | FBX |
|---|---|---|
| `feConveyor` (reta) | entra pela face −Y, sai pela +Y | `feConveyor.fbx` |
| `feConveyorCorner` (curva 90°) | entra pela −Y, vira à direita e sai pela +X (raio da linha de centro 0,5 m) | `feConveyorCorner.fbx` |

Curva para a esquerda = a mesma peça girada (entra pela face que era a saída). No jogo, o sentido vem da
rotação do bloco.

| Arquivo | O que é |
|---|---|
| `build_feConveyor.py` | Gera as duas peças. **Limpa a cena** antes (salve o modelo anterior) |
| `render_previews.py` | `preview_front/top.png` (reta em X = 0, curva em X = 1,6 só para exibição) |
| `render_line_preview.py` | `preview_line.png`: esteiras ligadas às portas do Gerador a Carvão (rodar em segundo plano; não salva) |
| `export_feConveyor.py` | Salva `feConveyor.blend` e exporta os dois FBX, cada peça com a raiz na origem |

## Medidas (casam com o padrão de portas)

- Lona: 0,32 m de largura, topo a **0,175 m** (a abertura das portas começa em 0,14 m e tem 0,36 m de largura).
- Perfis laterais em C a ±0,19 m (z 0,08–0,20), guias a 0,21–0,237 m, pernas com sapatas e travessa.
- Caixa: reta X ±0,228, Y ±0,5, Z 0…0,237; curva X −0,227…0,498, Y −0,498…0,227.
- Triângulos (sem bevel): reta 1.132, curva 2.236.

## Objetos (por peça, `<P>` = `feConveyor` ou `feConveyorCorner`)

| Objeto | Gira? | O que é |
|---|---|---|
| `<P>_Frame` | não (raiz) | perfis, guias, pernas, roletes de apoio, setas laranja do sentido |
| `<P>_Belt` | não | lona; **UV com V ao longo do fluxo** (1 repetição = 0,25 m): rolar a textura em V anima a esteira |
| `<P>_RollerIn`, `<P>_RollerOut` | sim, **X local** | tambores das pontas, pivô no eixo |
| `<P>_PortIn_1`, `<P>_PortOut_1` | — | empties nas faces do bloco a 0,25 m, +Z para fora (iguais aos das máquinas) |

Na curva a lona é plana (a borda de dentro é mais curta que a de fora); com a textura rolando isso não aparece.

## Materiais (provisórios)

`feConveyor_Iron`, `_Rust`, `_Steel`, `_Rubber` (lona), `_Paint` (setas). A lona precisa de uma textura com
nervuras repetindo em V para o movimento ficar visível.

## Não verificado

- Eixos do FBX no Unity; como o 7DTD anima UV ou gira partes de um bloco (Rota B / C#, fase 5).
- A lógica da esteira (mover itens entre blocos) não existe ainda: só o modelo.
