# feFlywheel — Volante de Inércia (I02)

Modelo do item Volante de Inércia (PLANO_MOD.md, seção 6, I02: feito no Torno com 4 Engrenagem + 2 Chapa +
1 Eixo; ingrediente do Gerador a Carvão e do Motor a Vapor — D2). Feito no Blender 5.3 por script.

| Arquivo | O que é |
|---|---|
| `build_feFlywheel.py` | Gera o modelo. **Limpa a cena** antes (salve o modelo anterior) |
| `render_previews.py` | Gera `preview_front/side.png` (piso logo abaixo do aro) |
| `export_feFlywheel.py` | Salva `feFlywheel.blend` e exporta `feFlywheel.fbx` |
| `feFlywheel.blend` / `.fbx` | Modelo atual |

## O modelo

O visual segue a receita: aro pesado e liso com uma cinta usinada e uma **cremalheira** numa borda
(as engrenagens), **duas chapas** rebitadas formando o miolo (com furos de alívio), cubo com 6 parafusos e um
**eixo** usinado atravessando, com chaveta.

- Diâmetro ~0,42 m; caixa: X/Z ±0,208, Y ±0,15 (o eixo).
- Origem no centro; gira em torno do **Y local** (mesma convenção das peças que giram nas máquinas), então
  serve também como peça de máquina.
- Um objeto só (`feFlywheel`), **sem bevel** para ficar leve: 5.836 triângulos. Para um item no chão ainda é
  bastante; um LOD/versão simplificada pode ser feito depois.

## Materiais (provisórios)

`feFlywheel_Iron`, `_Rust`, `_Steel`, `_Soot` (só cores). Os furos de alívio são discos escuros, não furos reais.

## Não verificado

- Escala e pivô esperados para modelos de item no 7DTD (item no chão / na mão); ícone 160×160 ainda não feito.
