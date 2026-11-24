# feCoalGenerator — versão HD (teste do pipeline de IA local)

Gerado por `F:\IA\texturizar.bat F:\IA\fe_blender\configs\feCoalGenerator.json` (ver `F:\IA\LEIA-ME.md`).
O `feCoalGenerator.blend` e o `.fbx` originais não foram alterados.

| | Original | HD |
|---|---|---|
| Triângulos (export) | 13.152 (com Bevel) | 5.128 (Bevel na normal map) |
| Materiais | 9 cores lisas | 1 material, atlas 2048 PBR |
| Texturas | nenhuma | Albedo, Normal (OpenGL), MetallicSmoothness (R metal, A lisura), Emission |

Texturas base geradas localmente com SDXL (sem emenda), com desgaste nas quinas e sujeira nas cavidades
procedurais, e bake no Cycles. Os objetos, os pivôs (`feCoalGen_Crank`, `feCoalGen_DynamoRotor`) e os empties de
porta foram mantidos, com os mesmos nomes e eixos do export original.

`preview_antes.png` / `preview_depois.png` usam a mesma câmera.

**Não verificado no jogo**: falta o `FeBuild.cs` criar o material com essas texturas (ver "Ainda não feito" em
`F:\IA\LEIA-ME.md`).
