[← Início da documentação](README.md) · [English](../en/troubleshooting.md) · **Português (Brasil)** · [Español](../es/troubleshooting.md)

# 🩺 Solução de problemas

## O mod não carrega

| Sintoma | Causa e solução |
|---|---|
| ForgedInAshes não aparece na lista de *Mods* | A pasta está no lugar errado. Tem que ser `<jogo>/Mods/ForgedInAshes/ModInfo.xml` (sem pasta repetida). |
| O jogo diz que a DLL do mod foi bloqueada | O EasyAntiCheat está ligado. Abra o jogo **sem EAC**. |
| Tudo duplicado, erros de patch já aplicado | Ainda há uma cópia antiga instalada. Deixe só `Mods/ForgedInAshes`; apague `Mods/FerroEngrenagem` se existir. |
| Erros vermelhos sobre `0Harmony` | A pasta `Mods/0_TFP_Harmony` foi apagada. Verifique os arquivos do jogo na Steam para restaurá-la. |

## Máquinas

| Sintoma | Causa e solução |
|---|---|
| A máquina diz que precisa de torque | O **encaixe de motor** está vazio. Encoste um Motor Elétrico ou traga um eixo de uma rede de torque. |
| A rede mostra **SOBRECARGA** e para depois de 20 s | As máquinas gastam mais UT do que as fontes oferecem. Coloque mais fontes, baixe o RPM ou divida a rede com **Embreagem** ou **Regulador de Torque**. |
| A rede mostra **TRAVADO** | Fontes girando uma contra a outra ou em velocidades diferentes. Vire uma delas, coloque um **Inversor de Giro** ou iguale as velocidades com uma **Caixa de Velocidade**. |
| Giro errado numa máquina | Vire o motor ou coloque um **Inversor de Giro**. |
| O motor diz *Sem água* / *Sem Lubrificante* | Leve água por cano até o motor e coloque Lubrificante nos slots. |

## Fluidos

| Sintoma | Causa e solução |
|---|---|
| O cano mostra **BLOQUEADO** | Dois fluidos diferentes se encontraram na mesma rede. Separe-os ou use um **Separador de Fluido**. |
| O cano **vaza** | Pressão acima do limite: 4 bar no **Cano**, 12 bar no **Cano de Alta Pressão**. Use canos de alta pressão ou uma **Válvula de Alívio**. |
| O tambor diz *Nenhuma Fornalha de Caldeira acesa encostada* | Encoste uma fornalha acesa no tambor, de preferência **embaixo** dele. A fornalha só queima enquanto um tambor pede calor, então precisa de combustível. |
| O Sangrador diz que as costas devem encostar num tronco | Gire-o para que as **costas** fiquem no tronco; o látex sai pela frente. |

## Esteiras

| Sintoma | Causa e solução |
|---|---|
| Os itens param numa máquina (*não aceito, espera*) | A entrada da máquina está cheia ou ela não usa esse item na receita atual. |
| A esteira não anda | Sem torque: coloque um eixo do lado de qualquer esteira da linha (8 UT por esteira). |
| O funil não faz nada | Ele espera enquanto o baú está aberto ou a esteira da frente está cheia. |

## O texto ao olhar some

A leitura que aparece quando você olha para um bloco só aparece até **4 m** (**5 m** nas máquinas grandes).
Chegue mais perto. Se ela sumir mesmo colado na máquina, [relate o problema](#relatar-um-bug) com o seu log: o mod
grava diagnósticos detalhados desse caso (linhas que começam com `ui watchdog` e `look probe`).

## Logs

| Arquivo | Onde |
|---|---|
| Log do jogo (Windows) | `%APPDATA%\7DaysToDie\logs\output_log_client__<data>.txt` |
| Linhas do mod | Toda linha escrita pelo mod começa com **`[ForgedInAshes]`** |

Para um log bem mais detalhado, crie um arquivo vazio chamado **`debug.txt`** dentro de `Mods/ForgedInAshes/` e
reinicie o jogo. Apague-o depois: o log detalhado fica grande.

## Relatar um bug

Abra uma issue em **[github.com/BirdRa1n/ForgedInAshes/issues](https://github.com/BirdRa1n/ForgedInAshes/issues)**
com:

1. O que você fez, o que esperava e o que aconteceu.
2. Versão do jogo e do mod (veja `Mods/ForgedInAshes/ModInfo.xml`).
3. O arquivo `output_log_client__*.txt` **completo** da sessão em que aconteceu.
4. Uma captura de tela, se for algo visual.

---

[← Guia de jogo](gameplay.md) · Próximo: **[Desenvolvimento →](development.md)**
