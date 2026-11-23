# feKinetic — modelos da rede de torque (D8)

Seis modelos feitos no Blender 5.3 por script, no mesmo estilo da Manivela (`Art/feCrank`):

| Bloco | Pasta | Peças que giram (contrato `FeSpin`, ver ART_BRIEF.md) | Triângulos* |
|---|---|---|---|
| Manivela de Torque | `Art/feTorqueCrank` | `feCrank_Rotor` (volante, eixo de saída e manivela; girado pelo CrankSpinner enquanto o jogador gira) | 1.732 |
| Eixo | `Art/feShaft` | `FeSpin_Shaft` | 576 |
| Caixa de Velocidade | `Art/feSpeedBox` | `FeSpinIn_SpeedBox` (engrenagem grande), `FeSpinOut_SpeedBox` (pinhão) | 2.020 |
| Caixa de Transmissão | `Art/feGearbox` | `FeSpin_Gearbox1..6` (um cubo/flange por face, cada um girado para o seu eixo) | 1.908 |
| Inversor de Giro | `Art/feSpinInverter` | `FeSpinIn_Inverter`, `FeSpinOut_Inverter` (o mod gira a saída ao contrário) | 2.504 |
| Regulador de Torque | `Art/feTorqueRegulator` | `FeSpinIn_Regulator`, `FeSpinOut_Regulator`, `FeSpin_x0.5_Governor` (regulador centrífugo vertical, meia velocidade) | 2.092 |

\* sem o bevel de 1 segmento aplicado na exportação.

| Arquivo | O que é |
|---|---|
| `build_feKinetic.py` | Gera os seis modelos (uma coleção por bloco); rodar de novo recria |
| `render_previews.py` | `preview_front/back.png` em cada pasta + `preview_lineup.png` aqui |
| `export_feKinetic.py` | Salva `feKinetic.blend` e exporta `Art/<bloco>/<bloco>.fbx` |

## Medidas e eixos

- 1 bloco (1×1×1 m), origem no centro do chão. O **eixo de torque** é o Y do Blender, na altura 0,5 (centro do
  bloco), com eixo de 0,06 m de raio e flange de 0,10 m rente à face do bloco: peças vizinhas se alinham.
- Exportação igual à da Manivela (−Z forward, Y up, transform aplicado): Blender +Y = Unity −Z, Blender −Y =
  Unity +Z. Logo o eixo do bloco é o **Z local** do prefab (o mod usa `FeShaftAxis = z`), a **entrada** (anel
  verde) fica em Unity −Z e a **saída** (anel laranja) em Unity +Z — como o mod espera.
- Manivela de Torque: o volante fica no centro, a manivela na frente (Blender −Y) e o eixo de saída passa pelo
  cavalete de trás até o flange da face traseira (Blender +Y).

## Integração (feita em 2026-11-23)

Bundle gerado nesta máquina com o Unity 2022.3.62f2 (instalado pelo Unity CLI em `E:\UnityEditors\2022.3.62f2`):

```
E:\UnityEditors\2022.3.62f2\Editor\Unity.exe -batchmode -quit -projectPath Art\UnityProject -executeMethod FeBuild.BuildAll -logFile Art\UnityProject\Logs\febuild.log
```

O `FeBuild` agora registra cada peça que gira (`[FE] <bloco>: spin part ... +Z -> (...)`): todas no centro do
bloco e com o +Z no eixo do bloco (os 6 flanges da Caixa de Transmissão cada um no seu eixo; o regulador
centrífugo na vertical). O Eixo ganhou uma raiz vazia (`feShaft_Base`): com um objeto só, o Unity fazia da peça
que gira a raiz do modelo e o deslocamento de −0,5 m do FeBuild a derrubava no chão.

Passos aplicados no `blocks.xml`:

- `feTorqueCrank`: `Model` → `#@modfolder:Resources/ferroengrenagem.unity3d?feTorqueCrankPrefab`.
- `feShaft`: `Shape` → `ModelEntity`, `Model` → `...?feShaftPrefab` (tirar `Texture`). Os blocos que estendem o
  Eixo herdam o Shape: `feSpeedBox`, `feGearbox`, `feSpinInverter`, `feTorqueRegulator` ganham cada um o seu
  `Model` `...?<bloco>Prefab`; o `feTorqueGauge` (ainda o cano `pipe_cap.fbx`) precisa de `Shape=New` próprio.
- Tirar `FeSpinWhole` do Inversor e do Regulador (agora têm peças `FeSpin`). A Embreagem e o Medidor continuam
  placeholders.

## Não verificado

- Eixos e pivôs dentro do Unity/jogo (mesma premissa da Manivela, que já funciona: rotor girando no Z local).
- Peças giradas (cubos da Caixa de Transmissão, regulador centrífugo): premissa de que o Y local do objeto
  rotacionado vira o Z local no Unity.
- Materiais só com cor (sem UV/atlas), como os outros modelos do mod.
