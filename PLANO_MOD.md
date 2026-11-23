# Plano do mod: Ferro & Engrenagem (7 Days to Die)

> Documento de trabalho para o Claude Code. Coloque este arquivo na raiz do repositório do mod (por exemplo `PLANO_MOD.md`) e peça para o Claude Code lê-lo antes de começar. O nome do mod e o prefixo de IDs são provisórios; troque à vontade, mas de forma consistente.

**Ambiente confirmado (2026-11-22):**

| Item | Valor |
|---|---|
| Versão do jogo | 3.4.0 (B10), build Steam `26309840` |
| Instalação | `C:\Program Files (x86)\Steam\steamapps\common\7 Days To Die` (também em `tools/game_path.txt`, fora do git) |
| Unity do jogo | 2022.3.62f2 (versão do `7DaysToDie.exe`), backend Mono |
| Log do jogo | `%APPDATA%\7DaysToDie\logs\output_log_client__<data>.txt` |
| Saves | `%APPDATA%\7DaysToDie\Saves` (backup: `um backup create ... --name 7dtd-saves`) |
| Sem EAC | Opção oficial `-noeac` (o launcher já usa); ver `MODLOG.md` |
| Harmony | `Mods/0_TFP_Harmony` v1.1.0.4 (traz `0Harmony.dll`, `TfpHarmony.dll`) |
| Localização vanilla | `Data/Config/Localization.csv` (CSV, não `.txt`). Colunas: `Key,File,Type,UsedInMainMenu,NoTranslate,KeepLoaded,english,Context / Alternate Text,german,spanish,french,italian,japanese,koreana,polish,brazilian,...`. PT-BR = coluna `brazilian` |
| XUi vanilla | `Data/Config/XUi_InGame/` (`windows.xml`, `xui.xml`, `styles.xml`, `templates.xml`), `XUi_Menu/`, `XUi_Common/` |
| Comandos de patch | Confirmados no `Assembly-CSharp.dll`: `set`, `setattribute`, `append`, `prepend`, `insertAfter`, `insertBefore`, `remove`, `removeattribute`, `csv`, `conditional` |
| Salvage | Drops com `tool_category="Disassemble"` em `blocks.xml` (eventos `Harvest` e `Destroy`) |
| Receitas vanilla | 633 no total: workbench 306, inventário 195, forge 60, campfire 49, chemistryStation 18, cementMixer 5 (`recipe_report.py`) |

---

## 0. Instruções para o Claude Code (leia primeiro)

1. **Nunca invente nomes do jogo.** Todo nome de item, bloco, receita, janela XUi, propriedade ou classe vanilla precisa ser confirmado com busca (`grep`/`rg`) nos arquivos da instalação do jogo antes de ser usado em XML ou C#. Se não encontrar, pare e registre na seção 12 (Pendências), não chute.
2. **Fonte da verdade:** a pasta `Data/Config` da instalação do jogo do usuário. Peça o caminho ao usuário na primeira sessão e grave-o em `tools/game_path.txt` (não versionar se tiver caminho pessoal). Caminho típico no Windows: `C:\Program Files (x86)\Steam\steamapps\common\7 Days To Die`.
3. **Não edite nada dentro da instalação do jogo.** Todo o trabalho fica no repositório do mod. A instalação para teste é uma cópia/link de `Mods/FerroEngrenagem` para a pasta `Mods` do jogo.
4. **Patches, não cópias.** Altere o vanilla com `<set>`, `<append>`, `<insertAfter>`, `<remove>` etc. via XPath. Para mudar a estação de uma receita vanilla, use `<set>` no atributo `craft_area`, nunca reescreva a receita inteira. Isso reduz conflito com outros mods e quebra menos em updates.
5. **Uma fase por vez.** Não comece a fase N+1 sem o critério de pronto da fase N cumprido e confirmado pelo usuário no jogo. O Claude Code não consegue rodar o jogo: ao fim de cada tarefa, escreva um **roteiro de teste manual** curto (o que o usuário faz no jogo e o que deve ver) e pare.
6. **Ler o log.** Depois de cada teste, peça ao usuário o log do jogo (`output_log*.txt` / `Player.log`, confirme o local) e procure por `ERR`, `WRN`, `XPath` e o nome do mod.
7. **Commits pequenos**, um por tarefa, com mensagem dizendo a fase e o ID (ex.: `F1-T03: receitas da Prensa`).
8. **Números são propostas.** Custos, tempos e quantidades deste plano são valores iniciais de balanceamento. Centralize-os (seção 9) para ajustar depois.
9. **Idioma:** código e IDs em inglês/ASCII; textos para o jogador em português e inglês no arquivo de localização.

---

## 1. Visão

Fazer a fabricação depender de uma **cadeia de máquinas, energia e peças intermediárias**, no espírito de Create e Satisfactory, em vez de achar peças-chave em loot.

Princípios:

- **P1 – Sem travas no começo.** Máquinas dos estágios iniciais custam só itens que o jogador já consegue obter sem elas.
- **P2 – Energia em camadas.** Manivela (estamina) → carvão vegetal → gasolina/solar/baterias → geradores mecânicos simulados.
- **P3 – XML primeiro, C# depois, assets por último.** Cada fase termina jogável.
- **P4 – Provar diversão cedo.** Uma fatia vertical pequena é testada antes do trabalho em volume (reescrever ~410 receitas).

Protótipo visual de referência (só para sentir o fluxo, não é o jogo): https://claude.ai/artifact/8pqiEFTeY18UjXV9eooNxo

---

## 2. Ambiente e ferramentas

| ID | Ferramenta | Uso | A partir da fase |
|---|---|---|---|
| T01 | 7 Days to Die (PC, Steam) — **confirmar a versão instalada** | Testar e ler `Data/Config` | 0 |
| T02 | Servidor dedicado (SteamCMD) | Testar multiplayer/sincronização | 2 |
| T03 | VS Code + extensão XML | Editar XML | 0 |
| T04 | Git | Versionamento | 0 |
| T05 | ILSpy ou dnSpyEx | Ler `Assembly-CSharp.dll` (só estudo, não redistribuir) | 0 (estudo), 2 |
| T06 | Visual Studio Community ou Rider | Compilar a DLL | 2 |
| T07 | .NET SDK com framework-alvo compatível | Compilar contra as DLLs do jogo (confirmar o alvo num mod que funcione na versão atual) | 2 |
| T08 | Harmony | Patches em C#. **O jogo já traz `Mods/0_TFP_Harmony`**; referencie essa DLL, não baixe outra | 2 |
| T09 | Console do jogo (F1), modo criativo/debug | Testes rápidos | 0 |
| T10 | Logs do jogo | Erros de XPath e exceções | 0 |
| T11 | `xmllint` ou validador de XPath | Garantir que cada patch acha o nó | 1 |
| T12 | Mods de referência compatíveis com a versão atual | Ver como definem workstations, XUi e receitas | 0 |
| T13 | Unity Editor (**mesma versão do jogo**) | Asset bundles | 6 |
| T14–T17 | AssetRipper/UABEA, Blender, GIMP/Krita, Audacity | Modelos, ícones, sons | 6 |

---

## 3. Estrutura do repositório

```
FerroEngrenagem/                 ← raiz do repo
├─ PLANO_MOD.md                  ← este arquivo
├─ CHANGELOG.md
├─ tools/
│  ├─ game_path.txt              ← caminho da instalação (fora do git se pessoal)
│  ├─ install.ps1 / install.sh   ← copia/linka Mods/FerroEngrenagem para o jogo
│  ├─ check_xpath.py             ← valida cada xpath dos patches contra Data/Config vanilla
│  └─ recipe_report.py           ← lista receitas vanilla por craft_area e confere o remapeamento
├─ Mods/FerroEngrenagem/         ← o mod em si
│  ├─ ModInfo.xml
│  ├─ Config/
│  │  ├─ items.xml
│  │  ├─ blocks.xml
│  │  ├─ recipes.xml
│  │  ├─ loot.xml
│  │  ├─ traders.xml             ← se necessário (confirmar nome)
│  │  ├─ progression.xml
│  │  ├─ buffs.xml               ← se a manivela precisar
│  │  ├─ Localization.csv        ← vanilla usa .csv; confirmar cabeçalho na versão atual
│  │  └─ XUi/
│  │     ├─ windows.xml
│  │     └─ xui.xml
│  ├─ Harmony/  (ou a DLL na raiz do mod — confirmar o padrão atual)
│  │  └─ FerroEngrenagem.dll
│  └─ Resources/                 ← asset bundles (fase 6)
└─ src/                          ← projeto C# (fase 2+)
   └─ FerroEngrenagem.csproj
```

Convenções:

- **Prefixo de IDs:** `fe` (ex.: `feResourceIronPlate`, `feWorkstationPress`, `fePress` como `craft_area`). Itens seguem o padrão de nome do vanilla (`resource…`, `workstation…`), com o prefixo na frente.
- Toda chave nova tem entrada em `Localization.txt` (português e inglês) na mesma tarefa em que é criada.
- Ícones: reutilizar ícones vanilla (propriedade de ícone/tint — confirmar nomes) até a fase 6.

---

## 4. Ferramentas de apoio que o Claude Code deve escrever (fase 0)

1. **`tools/check_xpath.py`** — lê cada arquivo em `Mods/FerroEngrenagem/Config/*.xml`, extrai os `xpath` de cada comando de patch e testa contra o XML vanilla correspondente (usando `lxml`). Para `<set>`/`<remove>`, o xpath precisa achar pelo menos 1 nó; reporte os que acham 0. Rodar antes de todo teste no jogo.
2. **`tools/recipe_report.py`** — lê `recipes.xml` vanilla e gera um CSV: nome da receita, `craft_area` atual (vazio = inventário do jogador), item de saída, ingredientes. Depois aplica os patches do mod e mostra o `craft_area` final. Serve para conferir a fase 3 e detectar receitas esquecidas.
3. **`tools/find_sources.py <item>`** — procura um item em `recipes.xml`, `loot.xml`, `blocks.xml` (drops de salvage/harvest/destroy), `traders.xml` e quests. Resolve as pendências P05, P06 e P11.
4. **`tools/install`** — copia ou cria link simbólico do mod para a pasta `Mods` do jogo.

---

## 5. Máquinas

Legenda de energia: **Comb.** = combustível na própria máquina (como a Forja); **Carga** = energia da fase 2 (ver seção 7); **Elét.** = rede elétrica vanilla ou equivalente (fase 3+).

### 5.1 Produção

| ID | Máquina | `craft_area` | Fase | Faz | Energia | Custo de construção (proposta) | Base vanilla a copiar |
|---|---|---|---|---|---|---|---|
| M01 | Fundição e Vidraria | `feFoundry` | 1 | Forged Iron, Forged Steel (upgrade), latão, chumbo, vidro, **e também Nails e Short Iron Pipe** (para não travar) | Comb. | Igual à Forja vanilla | Forja |
| M02 | Prensa de Peças | `fePress` | 1 | Chapa de Ferro, Fio de Latão, barras/vigas, cápsulas e pontas de bala; versões mais baratas de Nails e Pipe | F1: nenhuma · F2+: Carga | 30 Forged Iron, 60 Nails, 40 Wood, 4 Short Iron Pipe | Bancada (workstation) |
| M03 | Torno e Usinagem | `feLathe` | 1 | Eixo, Engrenagem, Mechanical Parts, Spring, Volante de Inércia | F1: nenhuma · F2+: Carga | 40 Forged Iron, 80 Nails, 30 Wood, 6 Short Iron Pipe | Bancada |
| M04 | Prensa de Munição | `feAmmoPress` | 3 | Munições, flechas, foguetes | Elét. | 20 Chapa, 10 Mech. Parts, 8 Engrenagem, 4 Spring | Bancada |
| M05 | Montadora de Armas e Ferramentas | `feAssembler` | 3 | Armas, ferramentas, componentes de arma | Elét. | 25 Chapa, 15 Mech. Parts, 10 Engrenagem, 6 Spring, 10 Forged Steel | Bancada |
| M06 | Bancada de Mods | `feModBench` | 3 | Mods de arma/armadura/veículo | Elét. | 15 Chapa, 10 Mech. Parts, 4 Fio de Latão | Bancada |
| M07 | Tear e Curtume | `feLoom` | 3 | Tecido, couro, roupas, armaduras | Elét. | 20 Chapa, 10 Engrenagem, 6 Mech. Parts | Bancada |
| M09 | Refinaria | `feRefinery` | 3 | Gasolina, óleo, pólvora, cola, tinta, papel, Lubrificante, bateria | Elét. + Comb. | Custo da Estação Química vanilla | Estação Química |
| M10 | Laboratório | `feLab` | 3 | Remédios | Elét. | 10 Chapa, 5 Beaker, 3 Fio de Latão | Estação Química |
| M11 | Cozinha e Destilaria | `feKitchen` | 3 | Comida/bebida em lote (a Fogueira continua no início) | Comb. / Elét. | Custo da Fogueira + 10 Chapa | Fogueira |
| M12 | Bancada Eletrônica | `feElectronics` | 3 | Bobina, Placa de Circuito, itens elétricos, armadilhas, torretas | Elét. | 20 Chapa, 10 Mech. Parts, 6 Fio de Latão | Bancada |
| M14 | Serralheria | `feMetalShop` | 3 | Portas, escotilhas, garagens, cofres | Elét. | 20 Chapa, 10 Mech. Parts, 6 Engrenagem | Bancada |
| M16 | Serraria | `feSawmill` | 3 | Tábua e Viga de Madeira | Carga ou Elét. | 30 Forged Iron, 40 Nails, 10 Engrenagem | Bancada |
| M08 | Misturadora de Concreto | `feMixer` | **4** (movida da 3: depende do Engine) | Cimento, concreto | Elét. | 25 Forged Iron, 4 Spring, 1 Engine, 10 Mech. Parts | Cement Mixer |
| M13 | Garagem | `feGarage` | 4 | Veículos, chassis, **Engine** | Elét. | 40 Chapa, 20 Mech. Parts, 10 Engrenagem, 4 Spring | Bancada |
| M15 | Oficina de Robótica | `feRobotics` | 4 | Drone, Sledge, torretas robóticas | Elét. | 30 Chapa, 10 Placa de Circuito, 5 Bobina | Bancada |

> **Correção de ciclo (fase 1):** a Prensa e a Fundição custam Nails e Short Iron Pipe. Se essas receitas saíssem da Forja e fossem só para a Prensa, ninguém conseguiria construir a Prensa. Por isso Nails e Pipe **continuam disponíveis na M01 (e na Forja vanilla enquanto ela existir)**; a Prensa só oferece versões mais eficientes.
>
> **Decisão em aberto (D1):** substituir a Forja vanilla pela M01 ou manter as duas? Recomendação: na fase 1, **manter a Forja vanilla** e adicionar a M01 ao lado. Só remover/ocultar a Forja na fase 3, depois de tudo testado.

### 5.2 Energia

| ID | Bloco | Fase | Função | Custo (proposta) | Implementação |
|---|---|---|---|---|---|
| E01 | Manivela | 2 | Converte estamina em **Carga** | 20 Forged Iron, 20 Wood, 10 Nails | Ver seção 7 (rota A: XML; rota B: C#) |
| E02 | Carvoeira | 2 | 10 Wood → 2 Carvão Vegetal (lento) | 30 Cobblestone Rocks, 10 Clay Soil, 20 Wood | XML (cópia da Forja) |
| E03 | Gerador a Carvão | 2 | Queima Carvão Vegetal e gera Carga/energia | 15 Mech. Parts, 10 Chapa, 8 Engrenagem, 5 Short Iron Pipe | Rota A: workstation que "fabrica" Carga; rota B: C# |
| E04 | Gerador a Gasolina | 4 | Generator Bank vanilla com gasolina da Refinaria | Custo vanilla | XML |
| E05 | Painel Solar | 4 | Energia diurna (exige baterias) | Custo vanilla (confirmar origem — P06) | XML |
| E06 | Banco de Baterias | 4 | Armazena energia | Custo vanilla | XML |
| E07 | Roda d'Água / Moinho de Vento | 4 | Gerador simulado com visual mecânico | 30 Chapa, 15 Engrenagem, 10 Eixo, 20 Tábua | C# leve |
| E08 | Motor a Vapor | 4 | Gerador de fim de jogo (combustível + água + Lubrificante) | 20 Engine, 20 Volante, 40 Chapa, 10 Lubrificante | C# leve/médio |

### 5.4 Rede mecânica de torque (proposta D8, pedido do usuário 2026-11-22)

Ideia: o espírito do Create (eixos, caixas, velocidade e "estresse") com um toque de Satisfactory (fontes que
queimam combustível, sobrecarga que para tudo). A eletricidade (D7) continua existindo: o **Motor Elétrico**
passa a ser o conversor watts → torque.

**Duas grandezas**
- **RPM** (velocidade do giro): 16, 32, 64, 128 ou 256. Fontes giram a 32 RPM.
- **UT** (unidades de torque): cada fonte dá uma capacidade em UT; cada consumidor gasta UT.

**Regras da rede**
- Uma rede = blocos de torque ligados face a face (eixo, caixa, fonte, máquina). Calculada no servidor quando
  um bloco entra ou sai, e a cada 0,5 s para as fontes a combustível.
- Capacidade da rede = soma das fontes (vários motores no mesmo eixo **somam** torque).
- Consumo da rede = soma dos consumidores. Se consumo > capacidade → **sobrecarga**: a rede inteira para até
  tirar carga ou somar fontes (como o "overstress" do Create).
- Fontes na mesma rede precisam girar na mesma velocidade; senão a rede fica **travada**.
- Olhar para qualquer bloco da rede mostra: RPM, UT usada / UT disponível, e "Sobrecarga"/"Travada".

**Fontes de torque**

| Bloco | Como gira | RPM | UT | Observação |
|---|---|---|---|---|
| Manivela de Torque (existe) | segurar E (estamina) | 32 | 64 | só enquanto gira |
| Motor Elétrico (existe) | watts pelo fio | 32 | 128 | consome 30 W; **melhoria**: até 3 Bobinas no slot, cada uma +128 UT e +30 W |
| Motor a Carvão (novo) | queima Carvão Vegetal | 32 | 256 | slot de combustível; 1 carvão ≈ 60 s |
| Motor a Gasolina (novo) | queima Galão de combustível | 32 | 512 | fim de jogo (gasolina da Refinaria) |
| Roda d'Água (E07, F4-T04) | água/vento | 16 | 128 | já previsto na fase 4 |

**Transmissão**

| Bloco | Função |
|---|---|
| Eixo | liga as duas pontas (frente/trás); encadeia em linha reta |
| Caixa de Transmissão | liga as 6 faces: junta torque de várias entradas e divide para várias saídas (curvas e derivações) |
| Caixa de Velocidade | entrada numa face, saída na oposta; E alterna ×½ / ×2 / ×4 da RPM. O lado rápido custa mais (ver abaixo) |
| Embreagem | E liga/desliga a passagem do torque (desligar uma linha sem quebrar nada) |
| Regulador de Torque | E ajusta o limite que passa: 25 / 50 / 75 / 100 % da UT da entrada. O que está atrás dele nunca gasta mais que isso; se precisar de mais, trabalha mais devagar |
| Medidor (tacômetro) | mostra RPM e UT de forma fixa num painel; útil para montar fábricas |

**Consumidores**
- **Máquinas**: o encaixe que já existe (D7) vira a entrada de torque. Qualquer bloco da rede no encaixe (eixo
  apontando para a máquina, caixa, motor, manivela de torque) move a máquina. Motor colado na máquina continua
  funcionando (é uma rede de 2 blocos).
- Custo base da máquina em UT (substitui o FeMinPower em W): 64 (as de 30 W), 128 (60 W), 192 (90 W).
- **Velocidade de fabricação** = RPM / 32: 16 RPM = 0,5×, 64 RPM = 2×, 128 RPM = 4×, 256 RPM = 8×.
- **Custo cresce ao quadrado** da velocidade: UT = custo base × (RPM/32)². Exemplo da Prensa (64 UT): 2× mais
  rápida gasta 256 UT, 4× gasta 1024 UT, 8× gasta 4096 UT. Acelerar muito exige muitos motores/geradores.
- **Esteiras** (fase 5) entram na mesma rede, com custo por bloco.

**Etapas (cada uma testada no jogo antes da próxima)**
1. T1 [feita e testada] — Núcleo: Eixo, Caixa de Transmissão, rede (BFS), Motor Elétrico e Manivela de Torque como fontes,
   máquina no encaixe como consumidor em UT, sobrecarga, leitura ao olhar.
2. T2 [feita e testada] — Caixa de Velocidade + velocidade de fabricação com custo ao quadrado.
3. T3 [feita e testada] — Embreagem, Regulador de Torque e Medidor.
3b. T3b [feita e testada] — **Sentido de giro** (pedido do usuário): fontes e peças axiais só ligam pelas
   pontas do eixo; a Caixa de Transmissão inverte o giro em todas as saídas (como no Create; a regra antiga
   "reto mantém, curva inverte" era inconsistente e travava redes); máquina recebendo giro ao contrário não
   roda nem consome → **Inversor de Giro**; fontes girando uma contra a outra = travado. **Contrato de animação**
   (`KineticSpinner.cs`, ART_BRIEF): peças `FeSpin*` giram no +Z local na RPM/sentido reais; parâmetros de
   Animator `FeRpm`, `FeSpeed`, `FeRunning`, `FeOverloaded`, `FeLocked`, `FeWrongSpin`.
4. T4 [feita e testada] — Motor a Carvão, Motor a Gasolina e melhorias do Motor Elétrico (as Bobinas viraram
   receitas de Motor Reforçado 256 UT/60 W e Industrial 512 UT/120 W: o motor vanilla `Powered` não tem slots).
5. T5 — Modelos 3D com peças que giram (colega/arte) e sincronização visual em multiplayer.

**Limites conhecidos**: cálculo no servidor/host; o giro visual em clientes multiplayer precisa de pacote de
rede (fica com o F2-T06). Modelos começam com placeholders vanilla.

### 5.3 Logística (opcional — "versão 2.0")

| ID | Bloco | Função | Implementação |
|---|---|---|---|
| L01 | Funil | Move itens de um contêiner para o adjacente | C# difícil + sincronização multiplayer |
| L02 | Duto de Itens | Rede de dutos ligando máquinas e contêineres | C# muito difícil |

Só iniciar depois da versão 1.0 lançada e estável.

---

## 6. Itens

| ID | Item (ID proposto) | Vanilla? | Feito em | Receita proposta | Fase |
|---|---|---|---|---|---|
| I01 | Carvão Vegetal (`feResourceCharcoal`) | Não | E02 | 10 Wood → 2 | 2 |
| I02 | Volante de Inércia (`feFlywheel`) | Não | M03 | 4 Engrenagem + 2 Chapa + 1 Eixo → 1 | 2 |
| I03 | Chapa de Ferro (`feResourceIronPlate`) | Não | M02 | 2 Forged Iron → 1 | 1 |
| I04 | Eixo de Ferro (`feResourceIronShaft`) | Não | M03 | 2 Forged Iron → 1 | 1 |
| I05 | Engrenagem (`feResourceGear`) | Não | M03 | 1 Chapa → 2 | 1 |
| I06 | Mechanical Parts | **Sim** (confirmar que não tem receita — P05) | M03 | 2 Engrenagem + 1 Eixo → 1 | 1 |
| I07 | Spring | **Sim** (P05) | M03 | 1 Eixo + 1 Forged Iron → 2 | 1 |
| I08 | Fio de Latão (`feResourceBrassWire`) | Não | M02 | 1 Brass → 3 | 3 |
| I09 | Bobina Elétrica (`feResourceCoil`) | Não | M12 | 3 Fio de Latão + 1 Eixo → 1 | 3 |
| I10 | Placa de Circuito | Verificar se usar Electrical Parts vanilla (P06) | M12 | 2 Fio de Latão + 1 Chapa + 1 Glue → 1 | 3 |
| I11 | Lubrificante (`feResourceLubricant`) | Não | M09 | 2 Oil → 1 | 3 |
| I12 | Engine (motor pequeno) | **Sim** (P05) | M13 | 10 Mech. Parts + 4 Spring + 6 Chapa + 2 Lubrificante | 4 |
| I13 | Tábua de Madeira (`feResourcePlank`) | Não | M16 | Não há item "Wood Log"; existe o **bloco** `woodLogPillar100` ("Tronco de madeira", ingrediente da Forja). Opções: 1 `woodLogPillar100` → 4 Tábuas, ou 4 `resourceWood` → 1 Tábua (decidir na fase 3) | 3 |
| I14 | Viga de Madeira (`feResourceBeam`) | Não | M16 | 3 Tábua → 1 | 3 |
| I15 | Rolo de Tecido (`feResourceClothRoll`) | Não | M07 | 10 Cloth Fragment → 1 | 3 |
| I16 | Cano de Arma (`feGunBarrel`) | Não | M05 | 1 Short Iron Pipe + 1 Forged Steel → 1 | 3 |
| I17 | Mecanismo de Disparo (`feGunMechanism`) | Não | M05 | 4 Mech. Parts + 2 Spring + 1 Chapa → 1 | 3 |
| I18 | Coronha (`feGunStock`) | Não | M05 | 4 Tábua + 1 Leather → 1 | 3 |
| I19 | Carga (`feCharge`) — só na rota A de energia | Não | E01 / E03 | ver seção 7 | 2 |

> **Ajuste de balanceamento:** na planilha original, 1 Forged Iron virava 4 Springs e 1 Mechanical Part custava ~1,25 Forged Iron — barato demais para um gargalo. Os valores acima já estão mais caros (Eixo 2 FI → 1; MP ≈ 3 FI; Spring ≈ 1,5 FI). Comparar com o que o jogador ganha desmontando sucata na versão atual e ajustar.

---

## 7. Energia na fase 2: duas rotas

Até onde se sabe, nenhuma workstation vanilla usa a rede elétrica (P02). Ligar uma workstation à rede elétrica de verdade exige C# e sincronização com o servidor. Por isso há duas rotas; **comece pela A** e só vá para a B se a A não for boa o bastante no teste.

### Rota A — "Carga" como combustível (só XML, dificuldade ~2)

- Workstations vanilla como a Forja já têm slot de combustível. Prensa e Torno (fase 2+) passam a aceitar **apenas** `feCharge` como combustível (confirmar as propriedades de combustível no bloco da Forja e se dá para restringir o item aceito — P03).
- **Manivela (E01):** precisa transformar estamina em `feCharge`. Opções a investigar, nesta ordem:
  1. Um item-ferramenta "Manivela Portátil" cuja ação de uso gasta estamina (como golpes corpo a corpo) e dá `feCharge` (ver `items.xml`/`buffs.xml` por ações com custo de estamina e por triggers que dão item).
  2. Uma workstation "Manivela" com receita `0 itens → 1 feCharge` e um buff que drena estamina enquanto a janela está aberta e fabricando (provavelmente precisa de C# para detectar isso).
- **Gerador a Carvão (E03):** workstation com receita `1 Carvão Vegetal → N feCharge`. Simples e totalmente XML.
- Desvantagem: a "energia" vira um item que o jogador carrega na mão. Aceitável para o protótipo.

### Rota B — energia real (C# + Harmony, dificuldade 4)

- Estudar no `Assembly-CSharp.dll` as classes de workstation (tile entity de workstation, update de fabricação) e de energia (tile entity powered, power items).
- Patch Harmony no update de fabricação: se a workstation é `fePress`/`feLathe` e não há energia disponível, pausar o progresso.
- Gerador a Carvão: estender ou copiar a lógica do Generator Bank para aceitar Carvão Vegetal como combustível.
- Manivela: bloco interativo que, enquanto o jogador segura a interação, drena estamina e injeta energia. É a parte mais difícil.
- Testar sempre em **servidor dedicado com 2 jogadores** (estado precisa sincronizar).
- Mods com DLL exigem EAC desligado e instalação no cliente (P08); documentar para os jogadores.

---

## 8. Fases e tarefas

Cada tarefa tem ID `F<fase>-T<n>`. Ao terminar uma tarefa: rodar `check_xpath.py`, commitar, escrever o roteiro de teste manual e parar se a tarefa precisar de teste no jogo.

### Fase 0 — Preparação (dificuldade 1)

- **F0-T01** Perguntar ao usuário o caminho do jogo e a versão instalada (menu principal ou propriedades do Steam). Registrar em `tools/game_path.txt` e no topo deste arquivo.
- **F0-T02** Criar a estrutura da seção 3, `.gitignore`, `CHANGELOG.md`.
- **F0-T03** Escrever `ModInfo.xml` copiando o formato de um mod vanilla/oficial ou de um mod que funcione na versão instalada (P01). Não usar formato de memória.
- **F0-T04** Escrever as ferramentas da seção 4.
- **F0-T05** Rodar `find_sources.py` para `resourceMechanicalParts`, `resourceSpring` e o nome real do Engine (confirmar os nomes primeiro). Registrar o resultado em P05 e P11: receitas, loot, **salvage em `blocks.xml`**, traders, quests.
- **F0-T06** Item de teste `feTestItem` com localização. Usuário confirma que aparece no jogo e que o log está limpo.

**Pronto quando:** o mod carrega sem erros e o item de teste aparece; P01 e P05 resolvidas.

**Status: CONCLUÍDA em 2026-11-22.** Log: `Loaded Mod: FerroEngrenagem (0.1.0)` e `Loading localization from mod: FerroEngrenagem`, sem erros do mod. No jogo (criativo, idioma brazilian), `feTestItem` aparece como "Item de Teste Ferro & Engrenagem" (ID 1435), com o ícone do Mechanical Parts tingido de laranja.

### Fase 1 — Fatia vertical em XML, sem energia (dificuldade 2)

Objetivo: provar que a cadeia de peças funciona e é divertida, com o mínimo de conteúdo.

- **F1-T01** Itens I03, I04, I05 em `items.xml` (+ localização, ícones vanilla).
- **F1-T02** Blocos M01, M02, M03 em `blocks.xml`, copiando a definição da Forja (M01) e da Bancada (M02, M03): `craft_area` próprio, custos da seção 5.1. Receitas para fabricar as três máquinas no inventário do jogador ou na Bancada vanilla.
- **F1-T03** Janelas XUi das três workstations, copiando as da Forja/Bancada e renomeando (confirmar nomes das janelas vanilla).
  **Atualização (F1-T02):** desnecessária na fase 1. O código do jogo abre a janela indicada pela propriedade de bloco `WorkstationWindow` (senão `workstation_<nomeDoBloco>`); M01 usa `workstation_forge` e M02/M03 usam `workstation_workbench`, como o `tableSaw` vanilla. XUi própria só quando a máquina precisar de slots diferentes (ex.: combustível `feCharge` na fase 2).
- **F1-T04** Receitas novas: I03 na M02; I04, I05, I06, I07 na M03; Forged Iron, Nails e Short Iron Pipe na M01 (com os mesmos ingredientes da Forja vanilla).
- **F1-T05** Desligar as fontes de Mechanical Parts e Spring **só no salvage** (drops dos blocos desmontáveis em `blocks.xml`) e reduzir pela metade no loot. Traders e quests ficam para a fase 3.
- **F1-T06** Roteiro de teste para o usuário: mundo novo, sem loot de peças, Iron + Clay + Wood → construir M01 → M02 → M03 → fabricar 10 Mechanical Parts. Medir quanto tempo levou e se foi divertido.

**Pronto quando:** do zero e sem loot, o jogador fabrica Mechanical Parts e Spring; nenhum erro no log; o usuário aprovou a sensação. **Se não for divertido, rebalancear antes de seguir.**

**Status: CONCLUÍDA em 2026-11-22.** Teste em sobrevivência (14:11–14:57, log limpo): Fundição → Prensa → Torno → Mechanical Parts e Spring, sem peças de loot/desmanche; usuário aprovou ("foi bem legal e está de acordo"; tempo exato não medido, sessão ≤ 45 min). Desvios do plano: F1-T03 dispensada (`WorkstationWindow`); Fundição sem fundição/slot de entrada (filtro de variantes do jogo só vale para `forge`).

### Fase 2 — Energia inicial (dificuldade 2 na rota A, 4 na rota B)

- **F2-T01** Resolver P02, P03, P04 lendo `blocks.xml`, `items.xml`, `buffs.xml` e (se preciso) o código decompilado. Escrever um resumo curto das descobertas aqui.
  **Concluída (2026-11-22). Resumo** (fonte: XMLs vanilla + IL via `tools/il_inspect.ps1`):
  1. **P02:** nenhuma estação (`Workstation`/`Forge`/`Campfire`) tem propriedade de energia. A rede elétrica só existe em classes próprias (`Generator`, `BatteryBank`, `SolarPanel`, `Powered*`). Ligar máquina à rede = C#.
  2. **P03 — combustível de estação:** qualquer item/bloco com `FuelValue` serve (`ItemClass.GetFuelValue`, `XUiC_WorkstationFuelGrid`, `TileEntityWorkstation.GetFuelTime`); **não há filtro por estação em XML**. Restringir a `feCharge` exige Harmony.
  3. **P03 — alternativa em XML:** `feCharge` como **ingrediente** das receitas da Prensa/Torno (ex.: Chapa = 2 Ferro fundido + 1 Carga). Força o uso de energia sem filtro de combustível.
  4. **P03 — conversores por XML:** a classe `Collector` (coletor de orvalho, galinheiro) aceita **só** os itens de `FuelTypes="{nome,item,…}"` e converte em `OutputTypes` ao longo do tempo (1000 ticks = 1 h de jogo). Serve para **E02 Carvoeira** (Madeira → Carvão Vegetal) e **E03 Gerador a Carvão** (Carvão → Carga). Limite: `CollectorType` é enum (`DewCollector`, `Apiary`, `ChickenCoop`), então a máquina herda os multiplicadores de sandbox desse tipo.
  5. **P03 — Generator Bank:** reabastece com o primeiro item de tag `gasoline` (`XUiC_PowerSourceStats`, `ItemClass.GetItemWithTag`). Não queima Carvão Vegetal sem C#.
  6. **P04 — estamina:** golpe corpo a corpo gasta estamina via `passive_effect name="StaminaLoss" tags="primary"` (machado de pedra: 8).
  7. **P04 — dar item:** não existe `MinEventAction` de item, mas `triggered_effect action="CallGameEvent"` chama uma `action_sequence` do `gameevents.xml` com `<action class="AddItems">` (vanilla: `action_give_silver`).
  8. **P04 — Manivela como bloco:** o vanilla faz o sino da igreja reagir a golpes: buff sempre ativo `buffStatusCheck01` + `trigger="onSelfDamagedBlock"` + `requirement name="TriggerHasTags" tags="churchbell"`. Mesmo padrão: bloco `feCrank` com tag própria; cada golpe gasta estamina e chama um GameEvent que dá `feCharge`. Cuidado: o golpe também causa dano ao bloco (usar `MaxDamage` alto). Multiplayer não verificado (F2-T06).
  **Proposta de Rota A 100% XML:** `feCharge`; E01 = bloco Manivela (golpe → Carga); E02 e E03 = `Collector`; Prensa/Torno exigem Carga como ingrediente. Decisão D6 com o usuário.
- **F2-T02** E02 Carvoeira + I01 Carvão Vegetal.
- **F2-T03** Rota A: item `feCharge`; E03 como workstation `Carvão → Carga`; M02 e M03 passam a exigir `feCharge` como combustível.
- **F2-T04** E01 Manivela pela opção de rota A mais viável (seção 7). Se nenhuma for viável em XML, parar e discutir a rota B com o usuário.
- **F2-T05** I02 Volante de Inércia (upgrade da manivela, ou ingrediente do gerador, a decidir — D2).
  **Feita junto com a F2-T03:** Volante = catalisador do Gerador a Carvão (5 Cargas por Carvão por Volante). D2 resolvida.
- **F2-T06** Teste em servidor dedicado com 2 jogadores (P08).
- **F2-T07** Balancear P10: girar a manivela não pode virar tarefa chata. Meta inicial: 10 s de manivela ≈ 30–60 s de máquina rodando.
  **Feita (2026-11-22):** 25% de chance de 1 Carga por golpe (≈ 40 s de máquina por 10 s de golpes); usuário aprovou.

**Status da fase 2 (2026-11-22):** F2-T01 a F2-T05 e F2-T07 concluídas e verificadas no jogo em single-player. Falta **F2-T06** (servidor dedicado + 2 jogadores). **Decisão do usuário: F2-T06 adiada** para antes do lançamento (fase 7); seguir para a fase 3. Riscos em aberto: Manivela (GameEvent `AddItems`) e patch de combustível em multiplayer.

**Pronto quando:** M02 e M03 só funcionam com Carga vinda da manivela ou do gerador, também em servidor dedicado.

### Fase 3 — Cadeia completa (dificuldade 3, volume alto)

- **F3-T01** Gerar com `recipe_report.py` a lista completa de receitas vanilla por `craft_area`, **incluindo as do inventário do jogador** (sem `craft_area`) e do Cement Mixer. A planilha original contava ~410 (Bancada 306, Forja 33, Estação Química 17, Fogueira 49, Misturador 5); conferir na versão instalada.
- **F3-T02** Criar M04, M05, M06, M07, M09, M10, M11, M12, M14, M16 e os itens I08–I11, I13–I18.
- **F3-T03** Remapear receitas com `<set>` em `craft_area`, seguindo a tabela da seção 10. Fazer em lotes por máquina; um commit por lote.
- **F3-T04** Inserir as peças novas nos ingredientes das receitas remapeadas (ex.: armas passam a exigir Cano, Mecanismo, Coronha). Começar só pelas armas e ferramentas; o resto depois do teste.
- **F3-T05** Loot, traders e quests: reduzir as peças-chave (P11). Desmanche: decidir se dá 0 peças ou só sucata.
- **F3-T06** `progression.xml`: decidir se as máquinas dependem de perks/livros (D3).
  **Feita:** D3 = máquinas sempre liberadas. A habilidade `craftingWorkstations` passa a exibir Fundição, Montadora e Refinaria no lugar de Forja, Bancada e Estação Química (mesma posição; desbloqueio só visual).
- **F3-T07** Decidir D1 (ocultar a Forja vanilla ou não).
  **Feita (D1 = ocultar):** receitas da Forja, Bancada e Estação Química removidas; `CreativeMode=Dev`; quests (`groupQuestForge/Workbench/ChemistryStation`), loot `workstations` e trader `workstations` dão Fundição/Montadora/Refinaria. Blocos já existentes em POIs continuam funcionando (só com as receitas restantes).
- **F3-T08** `recipe_report.py` sem nenhuma receita esquecida numa estação vanilla que não deveria mais ser usada.
  **Feita:** `python tools/check_phase3.py` → 18/18 regras (estações vanilla, duplicatas, `craft_tool`, ingredientes, máquinas fabricáveis, Carga, localização, e MP/Mola só no Torno). Rodar antes de cada teste.

**Status da fase 3 (2026-11-22): CONCLUÍDA.** F3-T01 a F3-T08 feitas e testadas no jogo pelo usuário; inventário restrito ao primitivo (F3-T03b); `check_phase3.py` 19/19. Pendências conhecidas: Fogueira sem cópias melhoradas na Cozinha/Laboratório (seção 10.1, KEEP+COPY) e peças novas só em armas/ferramentas (o resto depois do teste).

**Pronto quando:** todas as receitas estão realocadas e nenhum caminho dispensa as máquinas (receita, loot, salvage, trader, quest).

### Fase 4 — Energia avançada (dificuldade 4)

- **F4-T01** M08 Misturadora, M13 Garagem, M15 Robótica, I12 Engine com receita.
  **Feita e testada no jogo (2026-11-22):** 3 máquinas no `gen_phase3.py` (a Carga, janela da Estação Química); Engine na Garagem (10 MP + 4 Mola + 6 Chapa + 2 Lubrificante); receitas da fase 4 remapeadas (Garagem 17, Robótica 3, Misturadora 5); Bicicleta e Roda da Montadora para a Garagem; Betoneira vanilla oculta como as outras estações (quest/loot/trader/progressão → feMixer). Bancada e Betoneira vanilla vazias; `check_phase3.py` 20/20. Engine continua no loot (decidir se corta).
- **F4-T02** E04, E05, E06 (vanilla, ajustando receitas/estação). Resolver P06.
  **Feita (offline):** Gerador (+4 Bobina, +6 Chapa) e Banco de baterias (+2 Bobina, +4 Chapa) na Bancada Eletrônica; Painel solar ganhou receita (10 Chapa, 4 Bobina, 10 Peça Elétrica, 10 Polímero). Células solares seguem loot/trader.
- **F4-T03** Decidir se na fase 3+ "Elét." usa a rede vanilla (rota B obrigatória) ou continua com Carga (rota A). Se rota A, adicionar receitas de Carga nos geradores novos.
  **Feita (offline):** D4 = Carga (rota A). Novo `feGasGenerator` (coletor): 5 Latas de gasolina → 2 Cargas por Motor instalado (catalisador `smallEngine`, mínimo 1). Solar/água/vapor gerando Carga: F4-T04 (C#).
- **F4-T04** E07 e E08 (C#). **E07 Roda d'Água feita e testada (2026-11-23)** como fonte de torque (D8). E08 pendente.

**Pronto quando:** cada fonte de energia exige peças e combustíveis da cadeia anterior.

### Fase 5 — Logística (opcional, dificuldade 5)

Só depois do lançamento da 1.0. L01 Funil primeiro; L02 Duto só se o Funil for estável em multiplayer.

### Fase 6 — Visual e assets (dificuldade 5, pode correr em paralelo a partir da fase 3)

- Resolver P07 (versão da Unity).
- Modelos próprios das máquinas, engrenagens que giram quando ligadas, ícones próprios para os itens novos, sons da manivela e das máquinas.

### Fase 7 — Balanceamento e lançamento (dificuldade 3)

- Campanha completa em multiplayer.
- Testar ao lado de outros mods populares (P09).
- README para jogadores (instalação, EAC, cliente e servidor), página do mod, versão do jogo suportada.

---

## 9. Tabela de balanceamento

Manter todos os números ajustáveis num lugar só, por exemplo comentados no topo de cada XML ou num `balance.md`:

| Grandeza | Valor inicial | Onde aparece |
|---|---|---|
| Custo das máquinas | seção 5.1 | `recipes.xml` |
| Receitas das peças | seção 6 | `recipes.xml` |
| Tempo de fabricação das peças | 2–4 s (comparar com o tempo do Forged Iron vanilla) | `recipes.xml` |
| Carga por Carvão Vegetal | 5 `feCharge` **por Volante instalado** (catalisador) | E03 (`blocks.xml`, `CatalystMultiplier`) |
| Manivela (segurar E, F2-T04b) | **1 `feCharge` a cada 2,5 s** de giro (≈ 4 por 10 s ≈ 40 s de máquina); **40 de estamina/s** (era 25; aprovado). A regeneração natural continua durante o giro | E01 (`blocks.xml`: `FeCrankChargeSeconds`, `FeCrankStaminaPerSecond`) |
| Duração de 1 `feCharge` como combustível | ~10 s | M02, M03 |
| Corte de loot das peças | -50% (fase 1); **0 na fase 3 (F3-T05, aplicado)**: MP e Mola fora do loot, do trader e do desmanche do Engine | `loot.xml`, `traders.xml`, `materials.xml` |

---

## 10. Remapeamento das receitas vanilla (fase 3)

Contagem da planilha original (fonte: pindrop.gg); reconferir com `recipe_report.py`.

| Estação vanilla | Grupo | Nº | Destino | Ação |
|---|---|---|---|---|
| Bancada | Munição e armas | 72 | M04 / M05 | Munição → M04; armas e granadas → M05 |
| Bancada | Básico (Apiary, Dew Collector) | 2 | M11 | Mover |
| Bancada | Construção (portas, garagens, cofres, Cement Mixer, Chemistry Station) | 28 | M14 | Mover; estações vanilla passam a exigir peças novas |
| Bancada | Roupas e armaduras | 63 | M07 | Mover; exigir Rolo de Tecido |
| Bancada | Decoração e diversos | 5 | M14 | Mover |
| Bancada | Mods | 74 | M06 | Mover; exigir peças novas |
| Bancada | Ciência (veículos, eletricidade, torretas, armadilhas) | 40 | M12 / M13 | Veículos → M13 (fase 4); resto → M12 |
| Bancada | Ferramentas e armadilhas | 22 | M05 / M11 | Ferramentas → M05; apiário, galinheiro, água → M11 |
| Forja | Munição (cápsulas, pontas, flechas) | 8 | M02 | Mover |
| Forja | Construção (vidro, barras, grades, vigas) | 9 | M01 / M02 | Vidro → M01; barras e vigas → M02 |
| Forja | Recursos (Forged Iron, latão, chumbo, cimento, pregos, canos) | 13 | M01 / M02 | Metais → M01; **pregos e canos ficam na M01 e ganham cópia na M02** |
| Forja | Anvil, Cooking Grill, Cooking Pot | 3 | M01 | Manter |
| Estação Química | Cerveja | 1 | M11 | Mover |
| Estação Química | Recursos (gasolina, cola, pólvora, óleo, tinta, papel, bateria) | 9 | M09 | Mover |
| Estação Química | Remédios | 7 | M10 | Mover |
| Fogueira | Comida | 41 | M11 | Manter na Fogueira; cópias melhoradas na M11 |
| Fogueira | Cola, tinta, papel | 3 | M09 | Manter na Fogueira no início |
| Fogueira | Remédios | 5 | M10 | Manter na Fogueira no início |
| Misturador | Todas | 5 | M08 (fase 4) | Mover na fase 4 |
| Inventário do jogador | **não contado** | ? | — | Listar no F3-T01 e decidir |

### 10.1 Proposta automática (F3-T01, jogo 3.4.0 B10)

Gerada por `python tools/remap_proposal.py` → `tools/out/remap_proposal.csv` (uma linha por receita, com destino e motivo). Contagem real: **600 receitas** (633 menos 33 de sucata): inventário 162, Bancada 306, Forja 60, Fogueira 49, Estação Química 18, Misturador 5.

| Destino | Nº | Origem |
|---|---|---|
| KEEP (fica onde está) | 167 | 162 do inventário (tier primitivo/T0-T1: P1) + 5 estações vanilla (D1) |
| KEEP + cópia na M11 Cozinha | 41 | comida e bebida da Fogueira |
| KEEP + cópia na M10 Laboratório | 5 | remédios da Fogueira |
| M01 Fundição | 15 | Forja: metais, vidro, cimento, ferramentas de forja |
| M02 Prensa | 13 | Forja: peças de munição, barras, vigas |
| M04 Prensa de Munição | 41 | Bancada: munição |
| M05 Montadora | 40 | Bancada: armas, ferramentas, explosivos, lockpick |
| M06 Bancada de Mods | 74 | Bancada: mods |
| M07 Tear | 63 | Bancada: armaduras, roupas, mochilas |
| M08 Misturadora (fase 4) | 5 | Misturador |
| M09 Refinaria | 10 | Estação Química: gasolina, óleo, pólvora, cola, tinta, papel, bateria |
| M10 Laboratório | 7 | Estação Química: remédios |
| M11 Cozinha | 12 | cerveja, apiário, coletor de orvalho, galinheiro e seus mods |
| M12 Eletrônica | 28 | Bancada: luzes, energia, armadilhas, minas, torretas |
| M13 Garagem (fase 4) | 14 | Bancada: veículos |
| M14 Serralheria | 29 | Bancada: portas, garagens, cofres, escotilhas |
| M15 Robótica (fase 4) | 3 | Bancada: Junk Sledge/Turret/Drone |
| DROP-VARIANT | 33 | Forja: gêmeas `use_smelter` (ver abaixo) |

**Armadilha técnica (descoberta no F1-T04):** o jogo só esconde a variante `use_smelter`/`replace_smelter` errada quando `craft_area == "forge"`. Receitas da Forja que mudarem de estação precisam **perder a gêmea `use_smelter`** (`<remove>`), senão aparecem duplicadas, como aconteceu na Fundição.

---

## 11. Decisões em aberto (perguntar ao usuário)

| ID | Decisão | Recomendação |
|---|---|---|
| D1 | Substituir ou manter a Forja vanilla? | Manter na fase 1; decidir na fase 3 |
| D2 | Volante de Inércia é upgrade da manivela ou ingrediente? | Ingrediente do gerador e do Motor a Vapor; upgrade só se a rota B for usada |
| D3 | Máquinas novas dependem de perks/livros? | Sim, as da fase 3+ atrás de livros existentes; M01–M03 livres |
| D4 | Energia "Elét." da fase 3: Carga (rota A) ou rede vanilla (rota B)? | **Adotado no F3-T02 (a confirmar com o usuário): Carga como combustível** em todas as máquinas da fase 3, pelo mesmo patch Harmony, ligado pela propriedade de bloco `FeChargeOnly="true"`. Trocar depois é local (bloco + patch) |
| D5 | O desmanche deve dar 0 peças ou um pouco? | Um pouco de sucata de ferro, 0 peças prontas |
| D7 | (Pedido do usuário após a F4-T03) Energia como **watts pela rede elétrica vanilla** (fios ligando Manivela/geradores às máquinas e esteiras), em vez do item Carga? | **Proposta:** bloco "Motor elétrico" encostado na máquina = consumidor vanilla (`RequiredPower` em W); patch Harmony: máquina `fe*` só fabrica com o motor vizinho energizado. Manivela vira gerador (giro soma `CurrentFuel`), Gerador a Carvão vira `PowerGenerator` a Carvão Vegetal, gerador/bateria/solar vanilla ligam direto. Remove item Carga, slot de combustível e `ChargeFuelPatches`. **Aprovado (2026-11-22).** Etapas: (1) Motor elétrico + bloqueio por energia [feita e testada; depois: motor só no **encaixe** da máquina, com contorno ao segurar, e consome o `FeMinPower` dela — testado]; (2) Manivela como gerador [feita e testada: 30 W fixos, slot de Módulo de Banco de Baterias do colega; não solta gasolina ao recolher]; (2b) **Manivela de Torque** no encaixe do motor, torque puro 30 W enquanto gira [feita e testada]; (3) Gerador a Carvão elétrico [feito e testado: `Class Generator`, queima Carvão Vegetal pelo Reabastecer, 60 W por Volante]; (4) remover Carga e geradores de Carga [feito] |
| D8 | (Pedido do usuário após D7 etapa 3) Rede mecânica de **torque** estilo Create + Satisfactory: eixos, caixas de transmissão, caixa de velocidade, regulador, fontes de torque a carvão/gasolina, motores que somam torque e melhorias, velocidade de fabricação maior com custo muito maior? | **Proposta:** seção 5.4 (RPM + UT, sobrecarga para a rede, custo ao quadrado da velocidade, etapas T1–T5). **Aprovado (2026-11-22).** T1–T4 feitas e testadas (falta T5: modelos/arte e giro visual em multiplayer). |
| D6 | Na fase 2, a Carga entra como **ingrediente** das receitas (XML) ou como **combustível** só-Carga (exige Harmony)? | **Decidido (2026-11-22): combustível com Harmony.** EAC não é restrição para o mod (usuário). Prensa/Torno ganham slot de combustível; patch C# faz aceitarem só `feCharge`. Manivela, Carvoeira e Gerador a Carvão continuam em XML |

---

## 12. Pendências (verificar nos arquivos do jogo)

| ID | Pergunta | Como verificar | Fase | Status |
|---|---|---|---|---|
| P01 | Formato exato do `ModInfo.xml` na versão instalada | Copiar de um mod que funcione nessa versão | 0 | **Resolvida:** copiado de `Mods/0_TFP_Harmony/ModInfo.xml` (raiz `<xml>`, campos `Name`, `DisplayName`, `Description`, `Author`, `Version`, `Website`). Confirmado no jogo no F0-T06 |
| P02 | Alguma workstation vanilla exige energia? | Buscar em `blocks.xml` e no código (workstation × powered) | 2 | **Resolvida:** não (F2-T01, item 1) |
| P03 | Dá para criar combustível novo e restringir o combustível aceito por uma workstation? E pelo Generator Bank? | Propriedades de combustível da Forja e do gerador em `blocks.xml` + código | 2 | **Resolvida:** estação não restringe em XML; `Collector` restringe; gerador só aceita tag `gasoline` (F2-T01, itens 2–5) |
| P04 | Como fazer uma ação contínua que gasta estamina? | Ações de item com custo de estamina em `items.xml`, `buffs.xml`; mods de referência | 2 | **Resolvida no papel:** golpe gasta estamina + `onSelfDamagedBlock`/`TriggerHasTags` + `CallGameEvent` → `AddItems` (F2-T01, itens 6–8); falta teste no jogo |
| P05 | Mechanical Parts, Spring e Engine têm receita? De onde vêm? | `find_sources.py` (receitas, loot, **salvage em `blocks.xml`**, traders, quests) | 0 | **Resolvida** (detalhes em 12.1) |
| P06 | De onde vêm o painel solar e as Electrical Parts? | `find_sources.py` | 4 | **Resolvida:** painel solar e célula solar sem receita (loot `groupRareElectrical`, trader `traderElectrical`/`traderSolarCells`, quest); Peças Elétricas de loot, desmanche e (mod) Bancada Eletrônica. Painel ganhou receita no F4-T02 |
| P07 | Versão da Unity do jogo | Propriedades do executável / documentação de modding | 6 | **Resolvida:** 2022.3.62f2 |
| P08 | EAC e servidores com DLL | Testar em servidor dedicado com EAC desligado; documentar | 2 | Aberta |
| P09 | Conflito com overhauls grandes | Testar em pares; documentar incompatibilidades | 7 | Aberta |
| P10 | Equilíbrio de estamina × carga da manivela | Teste no jogo (F2-T07) | 2 | Aberta |
| P11 | Cortar peças de loot/salvage/traders sem quebrar quests | `find_sources.py` + teste | 1, 3 | Parcial: lista de fontes em 12.1; falta testar no jogo |
| P12 | Nome real dos itens vanilla usados no plano (Short Iron Pipe, Nails, Wood Log, Engine, Cloth Fragment etc.) | `find_sources.py --search` + `Localization.csv` | 0 | **Resolvida** (tabela em 12.2) |
| P13 | Onde a DLL do mod deve ficar e como o jogo a carrega na versão atual | Comparar com um mod de código que funcione nessa versão | 2 | **Resolvida no código:** `Mod.LoadAssemblies` carrega todo `*.dll` da **raiz** da pasta do mod; `Mod.InitModCode` instancia a classe que implementa `IModApi` e chama `InitMod(Mod)`. Com EAC ligado: aviso "AntiCheat needs to be disabled", ou mod pulado se `SkipWithAntiCheat=true`. Build: `tools/build.ps1` (csc .NET 4 / C# 5, refs da instalação). **Confirmado no jogo** (2026-11-22 15:12): `Loaded assembly FerroEngrenagem` → `Found ModAPI` → `[FerroEngrenagem] InitMod` → `Initialized code in mod` |
| P14 | Nome da subpasta XUi dentro do mod: `Config/XUi/` aplica sobre `XUi_InGame`? | `tools/fe_common.py` assume que sim (`SUBDIR_MAP`); confirmar com mod de referência ou ILSpy antes de criar a primeira XUi própria | 2 | Adiada (F1 não precisa de XUi; ver F1-T03) |
| P15 | Mod só de XML precisa de `SkipWithAntiCheat` ou EAC desligado? | O Harmony vanilla usa `SkipWithAntiCheat=true`; o nosso `ModInfo.xml` não usa. Testar com EAC ligado | 0 | Parcial: funciona com `-noeac` (F0-T06); com EAC ligado ainda não testado |

### 12.1 Fontes de Mechanical Parts, Spring e Engine (F0-T05, jogo 3.4.0 B10)

Saída completa: `python tools/find_sources.py <item> --uses` (as cópias em `tools/out/` ficam fora do git).

| Fonte | `resourceMechanicalParts` | `resourceSpring` | `smallEngine` (Engine) |
|---|---|---|---|
| Receita normal | **nenhuma** | **nenhuma** | **nenhuma** |
| Sucata (desmanchar no inventário) | Sim: receita `salvageScrap` com `<wildcard_forge_category/>`. Os materiais `MmechanicalParts` e `MsmallEngine` têm `forge_category=resourceMechanicalParts`, então **desmanchar um Engine dá MP** | não | não |
| Loot | 14 lootgroups (ex.: `groupCraftingUncommon`, `groupWorkbenchLoot02`, `groupRollingToolbox02`, `groupMoPower01`, zumbis `groupZpack*`, `groupQuestResourcesT1`, `twitch_craftresources2`) | 6 lootgroups (`groupCraftingUncommon`, `groupWorkbenchLoot02`, `groupToilet02`, `groupZpackLab01`, `groupZpackUtility01`, `twitch_craftresources2`) | 9 lootgroups (`groupRareAutomotive`, `minibikeParts`, `motorcycleParts`, `4x4Parts`, `gyroCopterParts`, `groupGenBank`, 3 `twitch_*`) |
| Salvage em `blocks.xml` | ~150 blocos. Maioria `event="Harvest"` **sem** `tool_category` (carros, eletrodomésticos, canos, a própria `workbench` dá 8); alguns `event="Destroy" tool_category="Disassemble"` (cofres, portas de garagem) | ~60 blocos (carros, portas de garagem, camas, cofres) | ~20 blocos (carros, caminhões, empilhadeiras, `decoCarMotorFlat`) |
| Traders | `generalResources` (15–80, prob 0.8) | `generalResources` (5–30) | `rareTools`, `groupVehicles` |
| Quests | Via loot `groupQuestResourcesT1`; objetivo de desafio em `challenges.xml` | — | Pacotes `questRewardGeneratorBankBundle`, `questRewardVehiclePartsBundle`; desafio em `challenges.xml` |
| Não é fonte | `RepairItems` em blocos (custo de reparo, ex.: `workbench` 20 MP) e `passive_effect tags` em receitas (bônus de perk) | idem | `generatorbank` usa Engine como propriedade (combustível/peça) |

Consequências para o F1-T05:
- "Desligar o salvage" precisa cobrir **`Harvest` sem `tool_category`**, não só `Disassemble`. Um único patch
  `<remove xpath="/blocks/block/drop[@name='resourceMechanicalParts']"/>` pega todos; conferir os blocos com
  `dropextendsoff` e herança `Extends`.
- A receita de sucata do MP faz um Engine de loot virar MP. Na fase 1 pode ficar; na fase 3, decidir.
- A `workbench` vanilla custa e dá MP ao ser desmontada: se M02/M03 copiarem a workbench, revisar drops e `RepairItems`.

### 12.2 Nomes vanilla confirmados (P12)

| No plano | Nome real | | No plano | Nome real |
|---|---|---|---|---|
| Mechanical Parts | `resourceMechanicalParts` | | Forge | bloco `forge` (`craft_area="forge"`) |
| Spring | `resourceSpring` | | Workbench | bloco `workbench` |
| Engine | `smallEngine` | | Chemistry Station | bloco `chemistryStation` |
| Nails | `resourceNail` | | Cement Mixer | bloco `cementMixer` |
| Short Iron Pipe | `resourceMetalPipe` | | Campfire | bloco `campfire` |
| Forged Iron | `resourceForgedIron` | | Generator Bank | bloco `generatorbank` |
| Forged Steel | `resourceForgedSteel` | | Battery Bank | bloco `batterybank` |
| Wood | `resourceWood` (não existe "Wood Log") | | Solar Bank / Solar Cell | bloco `solarbank` / item `solarCell` |
| Cloth Fragment | `resourceCloth` | | Electrical Parts | `resourceElectricParts` (também tem receita de sucata) |
| Leather | `resourceLeather` | | Beaker | `toolBeaker` |
| Iron (sucata) | `resourceScrapIron` | | Anvil / Crucible | `toolAnvil` / `toolForgeCrucible` |
| Brass | `resourceScrapBrass` | | Duct Tape | `resourceDuctTape` |
| Lead | `resourceScrapLead` | | Glue | `resourceGlue` |
| Clay Soil | `resourceClayLump` | | Oil | `resourceOil` |
| Cobblestone Rocks | `resourceCobblestones` | | Gunpowder / Coal | `resourceGunPowder` / `resourceCoal` |
| Plant Fibers | `resourceYuccaFibers` | | Cement / Concrete Mix | `resourceCement` / `resourceConcreteMix` |

---

## 13. Primeira mensagem sugerida para o Claude Code

> Leia `PLANO_MOD.md` inteiro. Vamos começar pela Fase 0. Antes de escrever qualquer arquivo, me pergunte o caminho da minha instalação do 7 Days to Die e confirme a versão. Siga a seção 0 à risca: nada de nomes inventados, tudo conferido em `Data/Config`. Ao fim de cada tarefa que precise de teste no jogo, me dê um roteiro curto e pare.
