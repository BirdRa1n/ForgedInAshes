# MODLOG — ForgedInAshes

Diário de trabalho (fatos, caminhos, o que falhou e por quê, próximo passo). O plano está em `PLANO_MOD.md`;
aqui fica só o que foi medido/verificado.

## Ambiente (verificado em 2026-11-22)

| Item | Valor | Como foi verificado |
|---|---|---|
| Jogo | 7 Days to Die **V 3.4.0 (b10)**, Steam app 251570, buildid 26309840 | log: `INF Version: V 3.4.0 (b10) Compatibility Version: V 3.4.0` |
| Instalação | `C:\Program Files (x86)\Steam\steamapps\common\7 Days To Die` | `um scan` |
| Engine | Unity 2022.3.62f2, **Mono** (`7DaysToDie_Data/Managed/Assembly-CSharp.dll`) | `um scan`, exe ProductVersion |
| Anti-cheat | EasyAntiCheat. Opção oficial sem EAC: `7DaysToDie.exe -noeac` (o launcher já usou isso em 2026-11-22 12:38) | log: `[EOS-ACC] Not started with EAC, anticheat disabled` |
| Saves | `%APPDATA%\7DaysToDie\Saves` (o `um scan` sugere LocalLow, mas lá está vazio) | listagem |
| Logs | `%APPDATA%\7DaysToDie\logs\output_log_client__<data>.txt` | listagem |
| Launcher | `%APPDATA%\7DaysToDie\launchersettings.json` (`UseEAC: true` por padrão) | leitura |
| Mods oficiais | Pasta `<jogo>\Mods\`; o jogo já traz `0_TFP_Harmony` (HarmonyX 1.1.0.4) | log `[MODS] Loaded Mod: TFP_Harmony (1.1.0.4)` |

## Rota escolhida

**Sistema de mods oficial do jogo**, não BepInEx (a rota 1 sugerida pelo `um scan`).
- Fases 0, 1 e 3: só XML (patches XPath em `Mods/ForgedInAshes/Config/`). Sem DLL.
- Fase 2+ (se a rota B de energia for necessária): DLL C# carregada pelo próprio jogo (o log mostra
  `Found ModAPI in assembly ... creating instance`) + Harmony do `0_TFP_Harmony`.
- Motivo: o jogo tem loader oficial com XML patching e Harmony embutidos; BepInEx seria uma segunda camada
  desnecessária e aumentaria conflito com outros mods.

## Oráculo (como verificar no jogo)

- Linhas do log por mod: `[MODS]   Trying to load from folder: '<pasta>'` e `[MODS]     Loaded Mod: <Name> (<Version>)`.
- Erros de XML/XPath: procurar `ERR`, `WRN`, `XPath` e `ForgedInAshes` no log mais recente.
- Antes de todo teste: `python tools/check_xpath.py` (deve terminar com 0 problemas).

## Backups / restauração

- `um backup create "%APPDATA%\7DaysToDie\Saves" --name 7dtd-saves` → `~\.universal-modder\backups\7dtd-saves\20261122-125555.zip` (2 arquivos; saves ainda vazios).
- Restaurar: `um backup restore 7dtd-saves`.
- Instalação do mod no jogo: só um junction (`tools/install.ps1`); desfazer com `tools/install.ps1 -Uninstall`.

## Ferramentas

- `um` (plugin universal-modder): no Windows usar `bin\um.cmd` pelo PowerShell; no Git Bash o `python3` cai no
  atalho da Microsoft Store. Dependências instaladas: pillow, numpy, pyyaml.
- MCP do fal: falhou ao conectar (variável `FAL_KEY` não definida). Só será necessário na fase 6 (assets).
- Base de conhecimento (`um kb search "7DTD"`): nenhuma nota sobre 7 Days to Die. Escrever uma ao fim da fase 1.

## Diário

### 2026-11-22
- F0-T01..T04 concluídas (ver `CHANGELOG.md`). Comandos de patch confirmados no `Assembly-CSharp.dll`.
- 633 receitas vanilla (workbench 306, inventário 195, forge 60, campfire 49, chemistryStation 18, cementMixer 5).
- F0-T05: fontes de MP, Spring e Engine levantadas (tabela em `PLANO_MOD.md` 12.1; nomes em 12.2).
  - A receita de MP "sem ingredientes" é de **sucata**: `tags="salvageScrap"` + `<wildcard_forge_category/>`.
    O jogo dá o recurso da `forge_category` do material do item desmanchado (`materials.xml`).
    `MsmallEngine` → `resourceMechanicalParts`, então desmanchar um Engine dá MP. Há 33 receitas desse tipo.
  - Salvage de blocos é sobretudo `event="Harvest"` **sem** `tool_category`; o `Disassemble` é minoria.
  - `RepairItems` dentro de blocos usa nomes de item como `name` de propriedade: é custo de reparo, não fonte.
  - "Wood Log" não existe; madeira é só `resourceWood`.

- F0-T06 **verificado no jogo** (13:04, `-noeac`, mundo criativo):
  - log: `[MODS] Trying to load from folder: 'ForgedInAshes'` → `Loaded Mod: ForgedInAshes (0.1.0)` →
    `[MODS] Loading localization from mod: ForgedInAshes`; nenhum ERR/WRN do mod.
  - tela: menu criativo, busca "test" → "Item de Teste ForgedInAshes (1435) feTestItem", ícone laranja.
  - Fatos confirmados: mod XML-only carrega por junction; `Config/Localization.csv` com o cabeçalho completo
    vanilla funciona; a coluna `brazilian` é usada quando o idioma da plataforma é brazilian; `CustomIcon` +
    `CustomIconTint` reaproveitam ícones vanilla.
  - Ruído vanilla do log (ignorado por `check_log.py`): notícias remotas, Xbox Live, Discord SDK 403, Twitch 404.
- Gotcha: no PowerShell 5.1, `Get-Content -Raw` lê UTF-8 sem BOM como ANSI e corrompe acentos ao regravar.
  Editar arquivos com acento só pelas ferramentas de edição ou por Python.
- **Fase 0 concluída.**

- F1-T01 testado (13:13): log limpo (`Loaded Mod: ForgedInAshes (0.1.0)`, 0 linhas marcadas). Visual dos
  3 itens confirmado pelo usuário (nomes PT-BR, ícones tingidos, descrições).

- F1-T02 (blocos M01/M02/M03 + receitas de construção). Fatos lidos no IL do `Assembly-CSharp.dll`
  (Mono.Cecil do `0_TFP_Harmony`, carregado no PowerShell com `Add-Type`):
  - `WorkstationData(string blockName, DynamicProperties props)` lê do bloco `WorkstationName`,
    `WorkstationIcon`, `CraftIcon`, `CraftActionName`, `WorkstationWindow`, sons.
  - `TileEntityWorkstation.OnLockResponseLocal`: janela = `WorkstationWindow` se não vazio, senão
    `string.Format("workstation_{0}", blockName)`; se o bloco se chama `forge` e `XUiM_Recipes.DisableSmelter`,
    acrescenta `_nosmelting`.
  - O `tableSaw` vanilla (CreativeMode Dev) já usa craft area própria + `WorkstationWindow="workstation_workbench"`.
  - A Bancada vanilla custa 20 MP e a Forja é `learnable`: as máquinas do mod são feitas no inventário com
    `always_unlocked="true"`.
  - Gotcha: buscar strings UTF-16 no DLL exige testar os dois alinhamentos (offset 0 e 1); com só um, metade
    das strings some.

- F1-T02 testado (13:22–13:25): log limpo (0 linhas marcadas; nenhuma exceção ao colocar/abrir as máquinas).
  Visual/janelas confirmados pelo usuário: as 3 aparecem no crafting do inventário, modelos corretos,
  Fundição abre a janela da Forja e Prensa/Torno a da Bancada, listas vazias. **`WorkstationWindow` funciona.**

- F1-T04 (receitas das máquinas):
  - A fundição da Forja depende de 6 receitas ocultas `craft_area="forge"`, `material_based="true"`,
    `tags="use_smelter"` (`resourceClayLump`, `resourceCrushedSand`, `resourceRockSmall`, `resourceScrapBrass`,
    `resourceScrapIron`, `resourceScrapLead` ← `unit_*`). Copiadas para `feFoundry`; **não confirmado** ainda se
    o código de fundição aceita craft area diferente de `forge` (é o principal ponto do teste).
  - Receitas de metal vêm em pares: `use_smelter` (unit_*) e `replace_smelter` (sucata direta, quando o
    servidor desliga a fundição). Ambas copiadas.
  - `tools/copy_recipes.py` gera cópias exatas de receitas vanilla trocando o craft_area.
  - `craft_time` explícito nas peças: o Forged Iron tem `CraftingIngredientTime=10`.
  - Totais: feFoundry 12, feLathe 4 (Eixo, Engrenagem, MP, Spring), fePress 1 (Chapa).

- F1-T04 testado (13:28–13:37): log limpo, sem exceções. **Atenção:** o mundo de teste tem
  `Option SmeltingType: 1/Receitas (default: 0/Fundidor)`, ou seja, fundição desligada; o jogo usa as receitas
  `replace_smelter` (sucata direta) e não o slot de entrada. O caminho `use_smelter` da Fundição **não foi
  exercitado** neste teste. Usuário confirmou: Fundição, Prensa e Torno fabricam a cadeia inteira
  (Ferro fundido → Chapa → Engrenagem/Eixo → MP e Mola). Testar o modo Fundidor no F1-T06 (mundo novo, padrão).

- F1-T04 correção: na Fundição apareciam 2× Ferro/Prego/Cano. Causa (IL): `XUiM_Recipes.FilterRecipesByWorkstation`
  e `FilterRecipesByName` só escondem as variantes `use_smelter`/`replace_smelter` quando
  `recipe.craftingArea == "forge"` (string fixa). `TileEntityWorkstation.HandleMaterialInput` funciona em qualquer
  estação. Decisão do usuário: Fundição só com as 3 receitas `replace_smelter` (sucata direta), `Modules`
  sem `material_input`, janela `workstation_forge_nosmelting`. Fundir em massa: Forja vanilla (D1).
  Alternativa futura: patch Harmony estendendo o filtro (fase 2+).
- Arte em paralelo: usuário vai rodar outra sessão em outro PC; regras e escopo em `ART_BRIEF.md`
  (só `Art/`, não tocar em `Config/`). Remoto: `origin` = GitHub `BirdRa1n/ForgedInAshes` (repositório
  renomeado de `ForgedInAshes` em 2026-11-22; URL local atualizada).

- F1-T05 (salvage e loot de MP/Spring), validado offline:
  - `blocks.xml`: `<set>` renomeia 48 drops `Destroy` de MP/Spring para `resourceScrapIron` (mesma contagem);
    `<remove>` tira 136 drops `Harvest`. Nenhum drop de MP/Spring sobra em blocos; cofres/ATM/válvula mantêm
    um drop `Destroy` (evita o "drop self" do XML.txt).
  - `loot.xml`: 18 `<set>` de contagem (metade, arredondando para cima, mínimo 1) gerados por
    `tools/loot_scale.py 0.5`. `groupToilet02` (count=1) ficou igual.
  - Fontes restantes de MP/Spring: receita do Torno, loot reduzido, trader `generalResources` (fase 3),
    sucata de `smallEngine` → MP (fase 3).

- F1-T06 (14:11–14:57, sobrevivência, mundos ModTester/ModTester2, `SmeltingType=Receitas`): log limpo.
  Usuário confirmou: Fundição mostra só 3 receitas; carro desmanchado com chave inglesa não dá MP/Mola;
  cadeia completa feita em sobrevivência; "foi bem legal e está de acordo". **Fase 1 concluída.**
  Não testado: desmontar cofre (Destroy → sucata).

- F2-T01 (pesquisa, sem teste no jogo): resumo completo em `PLANO_MOD.md` (F2-T01). Fatos-chave:
  - `XUiM_Recipes`/fuel: estações aceitam qualquer `FuelValue`; sem filtro por estação.
  - `BlockCollector`: `FuelTypes`/`OutputTypes` por XML; `CollectorTypes` enum = DewCollector, Apiary, ChickenCoop;
    `UsesFuel()` e tempos passam pelos multiplicadores de sandbox do tipo.
  - Generator: `XUiC_PowerSourceStats` usa tag `gasoline` (cctor) → `ItemClass.GetItemWithTag`.
  - 72 tipos `MinEventAction*`; nenhum dá item. `CallGameEvent` + `GameEvent.SequenceActions.ActionAddItems` sim.
  - Sino: `buffStatusCheck01` / `onSelfDamagedBlock` / `TriggerHasTags churchbell` (blocos `churchBell*`).
  - Nova ferramenta `tools/il_inspect.ps1` (`-Type`, `-Method`, `-Find`), lê a DLL da instalação.
  - Gotcha PowerShell 5.1: `foreach (...) { } | Select-Object` é erro de sintaxe; atribuir a uma variável antes.
- D6 decidido pelo usuário: **combustível com Harmony** (EAC não é restrição).
- Infra C# (F2, antes do patch de combustível):
  - P13 pelo IL: DLLs na raiz da pasta do mod; classe `IModApi.InitMod(Mod)`.
  - Visual Studio 2022 Community está **sem workloads** (nenhum Roslyn/MSBuild; `vswhere` vazio). Build com
    `%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe` (**C# 5**), `/nostdlib` + refs da instalação
    (`mscorlib`, `System`, `System.Core`, `System.Xml`, `netstandard`, `Assembly-CSharp`, `LogLibrary`,
    `UnityEngine*`, `0Harmony` 2.13 do `0_TFP_Harmony`). Sem `System.Xml` dá CS0012.
  - TfpHarmony mira .NET Framework 4.8; 0Harmony 2.13 mira 4.5.2.
  - `src/ForgedInAshes/ModApi.cs`: loga `[ForgedInAshes] InitMod` e aplica `PatchAll` (0 patches ainda).
  - DLL gerada fica fora do git (`.gitignore`).
  - **Verificado no jogo** (15:12, `-noeac`): `Loaded assembly ForgedInAshes` → `Found ModAPI ... creating instance`
    → `[ForgedInAshes] InitMod: code loaded (0.1.0.0)` → `Harmony: 0 method(s) patched` →
    `Initialized code in mod 'ForgedInAshes'`. Log sem erros. A DLL compilada com csc C# 5 contra o mscorlib
    do jogo roda no Mono do jogo.
- F2-T02 (XML, validado offline, falta teste no jogo):
  - `feCharge` (I19): `FuelValue=10` (= 10 s; `getFuelTime` devolve o FuelValue em segundos), material
    `MFuelBarrelMetal` (sem forge_category → não vira sucata de ferro).
  - `feResourceCharcoal` (I01): `FuelValue=100` como o carvão, material `MresourceCoal` (sem forge_category).
  - `feCharcoalKiln` (E02): `Class=Collector`, `CollectorType=DewCollector`, `FuelTypes={wood,resourceWood}`,
    `OutputTypes={charcoal,wood,5,5,5,feResourceCharcoal,...,250,350,...}`, 6 slots de saída, modelo da forja
    quebrada. Slots de mod travados em `feTestItem`. Construída no inventário (30 pedras, 10 argila, 20 madeira).
  - IL de `BlockCollector.Init`: `FuelTypes`/`OutputTypes` sem checagem de nulo (obrigatórios); `RequiredMods`
    opcional; `ModTransform*` padrão ",,"; `ModTypes` padrão "Count,Speed,Type". Todo coletor abre a janela
    `dewcollector`.
  - Incerto: semântica exata de `additionalCost`/`discountCost` e se o slot de saída acumula mais de 1 item.
  - Teste 15:20–15:28 (criativo): log limpo, nenhuma exceção de coletor. Usuário confirmou que funcionou
    (Carvoeira aceita Madeira e produz Carvão Vegetal). **Coletor como conversor em XML: funciona.**
- F2-T03 (XML + Harmony, compilado e validado offline, falta teste no jogo):
  - Coletor com **catalisador**: `TileEntityCollector.getCurrentConvertCount` = nº de catalisadores ×
    `CatalystMultiplier` quando `CatalystTypes` não está vazio; `CatalystRequirements` = mínimo para rodar;
    catalisadores não são consumidos. `feCoalGenerator`: Carvão Vegetal → Carga, `CatalystTypes=feFlywheel`,
    `charge=5` → 5 Cargas por Carvão por Volante (D2 resolvida: Volante = peça do gerador).
  - `feFlywheel` (I02) no Torno: 4 Engrenagem + 2 Chapa + 1 Eixo.
  - Prensa/Torno: `Modules=output,fuel`, janela `workstation_chemistryStation` (combustível + saída).
  - `ChargeFuelPatches.cs`: postfix em `TileEntityWorkstation.GetFuelTime/getFuelTime/getTotalFuelSeconds`
    (só Carga conta), prefix em `HandleFuel` (Carga vai para a frente do array; `HandleFuel` consome
    `fuel[0]`), postfix em `XUiC_WorkstationFuelGrid.hasAnyFuel/hasFuelStack/HasRequirement`.
    Só para `fePress`/`feLathe`. Campos lidos por reflexão: `XUiC_WorkstationGrid.workstationData`,
    `XUiC_ItemStackGrid.itemControllers`.
  - **Atenção:** sem a Manivela (F2-T04), a sobrevivência fica travada (Carga só sai do Gerador, que precisa
    de peças do Torno). Testar F2-T03 só no criativo.
  - Teste 15:35–15:44: log limpo; `Harmony: 7 method(s) patched` (os 7 listados), nenhuma exceção de Harmony,
    workstation ou coletor. Usuário confirmou: Prensa/Torno só queimam Carga (Madeira fica e não some),
    Forja vanilla normal, Gerador só aceita Carvão Vegetal, parado sem Volante, 5 Cargas por Carvão com 1 Volante.
    **D6 implementada e verificada.**
- F2-T04 (XML, validado offline, falta teste no jogo): Manivela `feCrank` = bloco com `Tags=feCrank`,
  `MaxDamage=50000`, `CanPickup`, modelo provisório da roda de carroça vanilla. `buffs.xml` acrescenta um
  `effect_group` próprio ao `buffStatusCheck01`: `onSelfDamagedBlock` + `TriggerHasTags feCrank` →
  `CallGameEvent fe_crank_charge` (`gameevents.xml`: `AddItems feCharge 1`). Feita no inventário (20 Ferro
  fundido, 20 Madeira, 10 Pregos). Destrava a sobrevivência (primeira fonte de Carga sem Torno).
  Balanceamento (P10, F2-T07) ainda não feito: 1 Carga (10 s) por golpe.
  - Teste 15:47–16:04: log limpo; `gameevents` carregou (`Loaded (local): gameevents`), nenhuma exceção.
    Usuário: "funcionou normalmente", mas 1 Carga por golpe é demais. Ajuste: `RandomRoll` 25% na sequência
    (`gameevents.xml`), ≈ 4 Cargas por 10 s de golpes com machado de pedra. Retestado: usuário aprovou o ritmo.
- Arte: a sessão do outro PC entregou `Art/feCrank/` (modelo da Manivela, 1 bloco, partes giratórias separadas).

- Usuário: **commits sem `Co-Authored-By: Claude`** a partir de 2026-11-22 (salvo também na memória).
- F2-T06 (servidor dedicado) adiada pelo usuário; fase 3 iniciada. D1/D3 aprovados: Forja/Bancada ocultas no
  fim da fase 3; máquinas da fase 3 sempre liberadas.
- F3-T01: `tools/remap_proposal.py` (600 receitas reais; seção 10.1 do plano).
- F3-T02 (validado offline, falta teste no jogo):
  - Patch de combustível agora é ligado por propriedade de bloco `FeChargeOnly` (cache por `blockID`), não
    por lista de nomes. Build passou a referenciar `MemoryPack.dll` (CS0012 ao usar `DynamicProperties`).
  - `tools/gen_phase3.py` gera região marcada em blocks/items/recipes.xml + linhas de localização:
    10 máquinas (M04–M07, M09–M12, M14, M16; todas `output,fuel` + janela da Estação Química + Carga),
    9 itens (I08, I09, I11, I13–I18), receitas deles e `resourceElectricParts` (I10) na Bancada Eletrônica.
    Modelos vanilla provisórios (bancada, bancada de combinar, estação química, fogueira, mesa de serra).
  - D4 adotada sem confirmação explícita: Carga em todas as máquinas da fase 3 (registrado no plano).
  - **Bug visto no jogo:** Cozinha (fogueira) e Serraria (mesa de serra) apareciam afundadas no chão.
    Causa (IL `BlockShapeModelEntity.Init`): `ModelOffset` padrão = `(0, 0.5, 0)`; o gerador escrevia `0,0,0`
    onde o bloco vanilla não escreve nada → modelo meio bloco para baixo (Refinaria/Laboratório também).
    Correção: o gerador só escreve `ModelOffset` quando o vanilla escreve (bancada `0,.5,0`, combinar `0,0,0`).
    **Regra:** ao reaproveitar um modelo vanilla, copiar exatamente o `ModelOffset` do bloco vanilla (ou omitir).
  - Teste 16:42–16:46 (após a correção): log limpo do lado do mod (7 patches, nenhuma exceção). O `check_log.py`
    marcava falsos positivos da EOS ("featured" casava com `fe[A-Z]` sob `re.I`); filtro corrigido.
    Comportamento no jogo: usuário confirmou modelos e máquinas novas OK, **mas Prensa e Torno antigos
    continuam funcionando com Madeira** (bug aberto). XML deles idêntico ao das novas (`FeChargeOnly` presente).
    Descartado pelo IL: módulos vêm do XML a cada carga (`OnSetLocalChunkPosition`), não do save; o save guarda
    itens, fila, `isBurning` e `currentBurnTimeLeft`. Sem fuel module, `HandleRecipeQueue` fabrica sem queimar.
    Diagnóstico temporário no DLL: loga a decisão "chargeOnly" por bloco e avisa se um bloco fe* queima sem ser
    tratado como charge-only.
  - Diagnóstico 16:53–16:58: `fePress` id 25033 e `feLathe` id 25034 → `hasProp=True raw='true' chargeOnly=True`
    (igual às 10 novas); `feFoundry` → False (correto). O aviso de "fe* queimando sem charge-only" não disparou.
    Ou seja, o patch reconhece Prensa/Torno. Falta o relato visual dos passos do teste para fechar a causa.
  - Relato do usuário: no teste de diagnóstico a Prensa/Torno **não** fabricaram com Madeira. Causa mais provável
    do relato anterior: tempo de queima restante de uma Carga (`currentBurnTimeLeft` é salvo no save e a estação
    continua fabricando até ele acabar). Log por bloco removido; mantido só o aviso de segurança (uma vez por
    sessão) para máquina fe* que queime sem `FeChargeOnly`. **F3-T02 verificada.**
- Trabalho do parceiro (Harrison, commit 9618344, integrado por rebase sem conflito):
  - **F2-T04b: Manivela "segurar E"** em C# (`src/ForgedInAshes/Crank.cs`, `Class=ForgedInAshes.FeCrank,
    ForgedInAshes`): rotor e polia giram, estamina 25/s (`FeCrankStaminaPerSecond`), 1 Carga a cada 2,5 s
    (`FeCrankChargeSeconds`), agachar + E recolhe. Substitui o gancho de `buffs.xml` + `gameevents.xml`
    (esvaziados). Testado por ele no jogo.
  - **Primeiro modelo próprio integrado:** `Resources/forgedinashes.unity3d` (projeto em `Art/UnityProject`,
    `FeBuild.cs`); `Model="#@modfolder:Resources/forgedinashes.unity3d?feCrankPrefab"` (sintaxe lida em
    `DataLoader.ParseDataPathIdentifier`). Responde em parte à integração pendente do `ART_BRIEF.md`.
  - `build.ps1` passou a referenciar `InControl.dll` (tecla Activate).
  - Fetch neste PC: o git do terminal não tem credencial; usar `git -c credential.helper= -c
    "credential.helper=!gh auth git-credential" fetch origin` (gh autenticado, nada gravado na config).
- F3-T03 (validado offline, falta teste no jogo): `tools/gen_remap.py` gera região em `recipes.xml` a partir de
  `remap_proposal.classify`: 328 `<set>` de `craft_area` + 27 `<remove>` (gêmeas `use_smelter` e as 3 receitas da
  Forja já copiadas na Fundição). 5 lotes, um commit cada. Resultado: Bancada 306 → 19 (2 estações vanilla +
  17 da fase 4), Forja 60 → 6 (só as receitas internas de fundição), Estação Química 18 → 0.
  - `craft_tool`: só a Fundição tem slot de ferramenta. A ponta de flecha de aço AP (exige Cadinho) foi
    redirecionada para a Fundição; `gen_remap.py` agora falha se uma receita com `craft_tool` cair numa estação
    sem `tools`.
  - Bug do gerador corrigido: a regra "gêmea use_smelter = remover" precisa vir antes das exceções manuais.
  - Cola (`resourceGlue`) tem 2 receitas legítimas na Refinaria (ossos e milho-da-graça), como no vanilla.
  - Fase 4 (Misturador, veículos, robôs) e Fogueira (comida, remédios): sem mudança nesta tarefa.
  - Teste 17:20 (usuário): Manivela segurar-E funciona, mas gasta pouca estamina; Forja e Bancada vanilla
    "ainda com uma cacetada de craft". Log sem erro de patch.
    - Bancada: `CraftingAreaRecipes="player,workbench"`; `FilterRecipesByWorkstation` inclui receitas com
      `craft_area` vazio para o token `player` → ~211 receitas de inventário. Patch: só `workbench`.
    - Manivela: `FeCrankStaminaPerSecond` 25 → 40 (a regeneração de estamina continua durante o giro).
    - Forja: pelo filtro, só restam as 6 receitas internas de fundição; pedir print ao usuário.
    - Prints do usuário (após o patch): Bancada só com as 19 da fase 4 (Betoneira, Estação Química, Drone/
      Marreta/Torreta robóticos, veículos e chassis); Forja só com as 6 de fundição (Areia triturada, Chumbo,
      Ferro, Latão, Pedra pequena, Solo argiloso). **Remapeamento confirmado no jogo.** Esconder as duas: F3-T07.
    - Manivela com `FeCrankStaminaPerSecond=40`: aprovada pelo usuário.
- F3-T04..T08 de uma vez (pedido do usuário), validados offline, falta teste no jogo:
  - T04 `tools/gen_parts.py`: Cano/Mecanismo/Coronha em 17 armas (escala por tier), Eixo/Chapa/Engrenagem/Bobina
    em 16 ferramentas e armas brancas. Região depois do remapeamento (procura `craft_area='feAssembler'`).
    Risco a ver no jogo: as peças entram depois de `resourceLegendaryParts x0`.
  - T05: MP e Mola fora de todo loot (`loot_scale.py 0`, nenhum grupo fica vazio) e do trader `generalResources`;
    `MsmallEngine` forge_category → `iron` (Engine desmanchado não dá mais MP).
  - T06: `craftingWorkstations` (listas paralelas icon/name_key/unlock_level) troca forge/workbench/chemistryStation
    por feFoundry/feAssembler/feRefinery na mesma posição. Gotcha: os `<set>` de `name_key` selecionam pelo item
    ORIGINAL, então precisam vir antes dos `<set>` que trocam o item.
  - T07: receitas das 3 estações removidas, `CreativeMode=Dev`, quests/loot/trader `workstations` dão as do mod.
  - T08: `tools/check_phase3.py` → 18/18.
- Teste F3-T04..T07 (usuário, prints): tudo certo, mas o crafting do inventário ainda tinha itens "de máquina"
  (Mina Terrestre de Lata, Bicicleta, Roda, equipamentos de bioma, Curativo de Primeiros Socorros).
  - Nova regra: inventário só faz o primitivo; o que usa Ferro fundido/Aço/Peça mecânica/Peça elétrica/Mola/
    Pólvora vai para máquina (`INVENTORY_MOVES` em `remap_proposal.py`, ~48 receitas). Bicicleta e Roda vão
    para a Montadora até a Garagem existir (fase 4).
  - Receitas de inventário não têm `craft_area`: o gerador usa `<setattribute ... name="craft_area">` (op
    confirmada no DLL) com xpath `[not(@craft_area) or @craft_area='']`.
  - Pólvora do inventário (2+2) era gêmea mais cara da da Estação Química (1+1, já na Refinaria): removida
    (`INVENTORY_REMOVE`), não movida.
  - Exceção mantida: Cano de ferro pequeno (1 Ferro fundido) segue no inventário para a Fundição ser construível.
  - `check_phase3.py` ganhou a regra "inventário sem materiais industriais" → 19/19. Inventário: 195 → 161.
  - Usuário testou o menu do inventário: "ficou certo". **Fase 3 concluída** (critério de pronto atingido).
    Extras opcionais ainda abertos: cópias melhoradas das receitas da Fogueira na Cozinha/Laboratório e peças
    novas nas demais receitas (armaduras, mods etc.).
- Push 4cd4c50 (remoto `ForgedInAshes`). Auditoria de arte: só `feCrank` está no bundle; 6 máquinas prontas
  em `Art/` esperam entrar no `FeBuild.cs` e ser empacotadas no Unity 2022.3.62f2 (não instalado neste PC).
  Pedido detalhado em `ART_BRIEF.md` ("Integração pendente").
- F4-T01 (validado offline): Misturadora, Garagem, Robótica (`gen_phase3.py`), Engine na Garagem, remapeamento
  da fase 4, Betoneira vanilla oculta. `check_phase3.py` 20/20 (Bancada e Betoneira vanilla vazias).
  Usuário testou no jogo: "tudo certo". **F4-T01 verificada.**
- F4-T02/T03 (validado offline, falta teste no jogo): P06 resolvida (painel/célula solar só loot/trader/quest).
  Gerador, banco de baterias e painel solar exigem peças do mod na Eletrônica (painel ganhou receita).
  `feGasGenerator`: coletor a Lata de gasolina com catalisador `smallEngine` (`charge=2`, 5 latas por ciclo).
  528 patches, `check_phase3.py` 20/20.
- Teste F4-T02/T03: funcionou; o galão se chama "Galão de combustível" em PT-BR (textos corrigidos).
- **D7 aprovada pelo usuário:** energia em watts pela rede elétrica vanilla (fios), sem o item Carga.
  - Pesquisa (IL): consumidores = `TileEntityPowered` (`RequiredPower`, `IsPowered`), blocos `Class="Powered"`
    (ex.: relé 1 W). Workstations não são consumidores. Fabricação avança em dois lugares:
    `TileEntityWorkstation.HandleRecipeQueue(float)` (janela fechada) e `XUiC_RecipeStack.Update` enquanto a fila
    "IsCrafting" (janela aberta); o vanilla pausa/retoma a fila em `XUiC_WorkstationWindowGroup.Update` (só com
    grade de combustível).
  - Etapa 1 (validada offline): `PowerGatePatches.cs` (prefix `HandleRecipeQueue`, postfix
    `XUiC_WorkstationWindowGroup.Update` com `HaltCrafting`/`ResumeCrafting`); máquina com `FeMinPower` (W) só
    fabrica se motores `FeMotor` energizados num raio de 3 blocos (dy -1..+2) somam ≥ FeMinPower. Máquinas sem
    slot de combustível, janela da bancada. `feElectricMotor` (Class Powered, 30 W). Bootstrap: Motor e Alicate
    de fios no inventário (o Alicate ia para a Montadora com Aço/MP/Bobina = ciclo sem saída).
  - Pendente: Manivela e Gerador a Carvão ainda produzem o item Carga (inútil até as etapas 2–4).
  - `check_phase3.py` 21/21.
  - **Bug achado no 1º teste:** `<removeattribute xpath="...recipe[...]" name="craft_area"/>` → jogo:
    "Can only remove Attributes (matched Element), use remove instead" e **o resto do recipes.xml não foi
    aplicado**. Forma certa: `<removeattribute xpath=".../@craft_area"/>`. `fe_common.py` agora aplica as regras
    de tipo do jogo (removeattribute só atributo; setattribute/append/insert* só elemento).
  - 2º teste (19:21–19:30), com diagnóstico: layout antigo → `fePress motors=1 powered=0` (motor achado, mas a
    energia não chegava pela ligação em série); motor ligado direto ao gerador → `watts=30/30 -> ON`; desligar o
    gerador → `OFF` e a fabricação pausa (confirmado pelo usuário). **Etapa 1 funciona no jogo.**
  - Furo achado no diagnóstico: um motor de 30 W ligava Prensa e Torno juntos. Correção: cada motor alimenta só a
    máquina com `FeMinPower` mais próxima (`OwnerOf`, cache 2 s). Compilado; DLL não gravada (jogo aberto).
  - Usuário: Manivela (segurar E) também funcionou nesse teste (ainda gera o item Carga).
- D7 etapa 2 (validada offline, falta teste no jogo): Manivela = gerador.
  - IL: `PowerManager` tick a cada 0,16 s; `PowerGenerator.TickPowerGeneration`: se `MaxPower-CurrentPower >=
    OutputPerFuel` e há combustível → -1 combustível, +`OutputPerFuel` energia; `PowerSource.HandleSendPower`
    entrega até `MaxOutput` aos filhos (cada consumidor gasta `RequiredPower` por tick); `ShouldAutoTurnOff` =
    sem combustível. `RefreshPowerStats`: `MaxOutput` = soma dos slots (`OutputPerStack`, interpolado pela
    qualidade). Propriedades lidas: `SlotItem`, `OutputPerStack`, `MaxPower`, `MaxFuel`, `OutputPerFuel`.
    Reabastecer (`XUiC_PowerSourceStats.BtnRefuel_OnPress`) usa o primeiro item com tag `gasoline`.
  - `BlockFeCrank : BlockGenerator`; girar soma `FeCrankFuelPerSecond`=12,5 combustível/s no `PowerGenerator` e
    o liga. 1 combustível = 60 de energia → 750/s de giro ≈ 4 s de motor de 30 W (mesmo ritmo aprovado).
    `MaxFuel` 400 (~1 min de 30 W). Saída: 30 W base (`FeCrankBaseOutput`, postfix em `RefreshPowerStats`) +
    30 W por Volante (`SlotItem=feFlywheel`). A base existe por bootstrap: o Volante sai do Torno, que precisa de
    energia. Botão Reabastecer bloqueado na Manivela (`PowerPatches.cs`).
  - Limite conhecido: só funciona no host/single-player (no cliente MP o `PowerItem` está no servidor).
  - Manivelas colocadas antes da mudança não têm tile entity de gerador: recolher e colocar de novo.

## 2026-11-22 — D7: encaixe fixo do motor (socket) + marcação

- Pedido do usuário: o motor continua ocupando um bloco, mas só "pluga" numa posição específica da máquina, e
  essa posição aparece destacada quando o motor está na mão.
- `PowerGate.SocketPos` (PowerGatePatches.cs): célula vizinha à pegada da máquina no lado `FeMotorSide`
  (back|front|left|right, padrão back = -Z local), na camada mais baixa, coluna do meio (à esquerda do meio em
  larguras pares). Células da multiblock vêm de `multiBlockPos.pos` (locais); rotação igual ao vanilla
  (`MultiBlockArray.Get`: `shape.GetRotation(bv) * local`, arredondado).
- Removidos a busca em caixa (SEARCH=3) e o `OwnerOf`: um encaixe pertence a uma máquina só.
- O motor no encaixe consome o `FeMinPower` da máquina (`PowerItem.RequiredPower` ajustado), então 30 W da
  manivela não tocam máquinas de 60/90 W.
- `MotorSocketMarker.cs`: segurando o motor, contorno pulsante (LineRenderer, shader Sprites/Default) no encaixe
  das máquinas num raio de 7 blocos: verde livre, ciano motor já plugado, vermelho ocupado.
- Diagnóstico no log: `power <máquina> at <pos> rot=<r> socket=<pos>: motor= watts= -> ON/OFF`.
- A confirmar no jogo: qual lado é a "traseira" visual de cada modelo (ajustável por `FeMotorSide` no XML).

## 2026-11-22 — Manivela nova mandava 0 W (causa do "motor nunca energiza")

- Teste: motor no encaixe (contorno ciano), fio da manivela ao motor, Prensa continua pausada; log só
  `motor=False/OFF` inicial.
- IL 3.4.0 b10: `PowerSource.SetValuesFromBlock` faz `MaxOutput = MaxPower = OutputPerStack * SlotCount`; o
  `RefreshPowerStats` (onde o postfix punha 30 W) só roda em `SetSlots`/`TryAddItemToSlot` (carregar mundo ou
  mexer nos slots). Manivela tem `OutputPerStack` 0 → manivela recém-colocada enviava 0 W até recarregar.
- Também: `PowerSource.HandleSendPower` só redistribui aos filhos quando `hasChangesLocal` (liga/desliga, fio);
  `PowerItem.HandlePowerReceived` liga o consumidor se recebeu `RequiredPower` inteiro.
- Correção: postfix também em `PowerSource.SetValuesFromBlock` (PowerPatches.cs).
- Diagnóstico ampliado: a linha `power ...` agora mostra a cadeia do motor até a fonte (`on=`, `maxOut=`).
- Encaixe: com rot=0 o `back` (-Z local) ficou na face da bancada de frente para o jogador (print do teste).

## 2026-11-22 — Manivela → motor → Prensa funcionando; gasolina ao recolher; Manivela de Torque

- Teste confirmado no log: `fePress ... motor=True watts=30/30 -> ON | ... <- feCrank(on=True maxOut=30)`, e
  OFF quando a carga da manivela acaba.
- Bug: ao recolher a manivela carregada caía uma bolsa de galões. Origem (IL 3.4.0 b10):
  `TileEntityPowerSource.ReplacedBy` junta os slots + `CurrentFuel` convertido no 1º item com tag `gasoline`
  e chama `GameManager.DropContentInLootContainerServer("DroppedLootContainer", ...)`. Correção: prefix zera o
  combustível só da manivela (`PowerPatches.cs`); módulo e bateria continuam caindo.
- Pedido do usuário: duas manivelas — a elétrica (gerador, já existente) e uma de TORQUE puro, que vai no mesmo
  encaixe do motor. `feTorqueCrank` (TorqueCrank.cs): bloco simples, segurar E gira (stamina 30/s), a máquina
  conta `FeTorqueOutput`=30 W enquanto gira + 1,5 s de inércia; nada armazenado. Estado em memória
  (`TorqueState`, SP/host). Receita no inventário (10 FI, 15 madeira, 6 pregos). Modelo: prefab da manivela.
- `PowerGate.IsDriver` = motor ou manivela de torque (marcação do encaixe também).
- Testado no jogo (usuário, 2026-11-22): sem bolsa de gasolina ao recolher a manivela; Manivela de Torque no
  encaixe move a Prensa enquanto gira.

## 2026-11-22 — D7 etapa 3: Gerador a Carvão elétrico

- `feCoalGenerator` deixou de ser Collector de Carga: agora `Class=Generator` (TileEntityPowerSource +
  PowerGenerator). `SlotItem=feFlywheel`, `OutputPerStack` 60 W, `MaxFuel` 200, `MaxPower` 40000,
  `OutputPerFuel` 30000 (1 Carvão ≈ 80 s de 60 W).
- Vanilla só sabe gasolina (IL 3.4.0 b10: `XUiC_PowerSourceStats.BtnRefuel_OnPress` pega até 250 itens com a
  tag do `XUiC_PowerSourceStats.tag`, cinto e depois mochila; `fueltitle` = "xuiGas"; `ReplacedBy` devolve
  combustível como galões). `FuelGenerator.cs`: propriedade `FeFuelItem`/`FeFuelPerItem` no bloco; prefix no
  Reabastecer usa o item, postfix troca o título, prefix no `ReplacedBy` devolve o carvão numa bolsa.
- Chaves de localização do coletor removidas (Fuel/Catalyst/Empty); `feCoalGeneratorHasCharge` fica até a
  etapa 4 (usada pelo `feGasGenerator`).
- Geradores a Carvão já colocados no mundo de teste são do tipo antigo (Collector): destruir/recolocar.
- Testado (usuário + log): 30 W não liga a Montadora (60 W); 60 W liga; desligar o gerador pausa.

## 2026-11-22 — D8 T1: núcleo da rede de torque

- Aprovada a proposta D8 (PLANO 5.4). `TorqueNetwork.cs`: `BlockFeKinetic` (`FeKinetic` shaft|gearbox,
  `FeShaftAxis` no espaço do modelo girado por `shape.GetRotation`), `Kinetic.Get` = flood fill face a face
  (máx. 1024 nós, cache 0,5 s por nó). Fontes: Motor Elétrico (`FeTorqueOutput` 128 UT se energizado; volta a
  consumir só os próprios 30 W) e Manivela de Torque (64 UT enquanto gira). Consumidor: máquina cujo encaixe
  (`PowerGate.SocketPos`) é um nó da rede com face para ela; custo `FeTorqueCost` ou FeMinPower×64/30
  (64/128/192 UT), sempre que conectada. Uso > capacidade = sobrecarga, todas as máquinas da rede param.
- `PowerGate.HasPower` agora consulta a rede; log `power ... cost= UT: net nodes= sources= machines= u/c UT`.
- Leitura ao olhar (`KineticLookController`): nome (+ eixo vertical/E-W/N-S) e "RPM - usado/disponível UT",
  "SOBRECARGA" ou "Parado". Manivela de Torque mostra o mesmo no próprio texto.
- Teste 1: motor direto na Montadora ON (128/128); eixo deitado no encaixe dava "does not face the machine" e a
  leitura dizia "vertical" → o `pipe_straight.fbx` é horizontal; `FeShaftAxis` trocado para Z (log `look shaft
  ... rot= axis=` ao olhar, para confirmar X/Z).
- Reteste: Motor → Eixo → Caixa → Eixo → encaixe da Montadora: `net nodes=4 sources=1 machines=1 128/128 UT -> ON`;
  eixos com rot=0 mostram N-S → eixo local Z confirmado.
- Sobrecarga testada: Prensa + Montadora numa rede de 6 nós: 1 fonte = `192/128 UT OVERLOAD` (as duas param);
  Motor + Manivela de Torque = `192/192 UT -> ON`, alternando ao girar/parar a manivela. T1 concluída.
- Blocos: `feShaft` (modelo `@:Shapes/pipe_straight.fbx`, eixo local assumido Y — confirmar no jogo) e
  `feGearbox` (`pipe_joint.fbx`). Receitas: Eixo ×2 no Torno, Caixa na Montadora.

## 2026-11-22 — D8 T2: Caixa de Velocidade e velocidade de fabricação

- `feSpeedBox` (FeKinetic=speedbox, modelo `pipe_flange.fbx`, mesmo eixo do Eixo): entrada em -eixo, saída em
  +eixo; razão no `meta` do bloco (0=x2, 1=x4, 2=x1/2), E alterna (`KineticLookController`, `WasPressed`,
  `SetBlockRPC` + `Kinetic.Invalidate`).
- Rede: cada nó tem um fator de velocidade relativo; atravessar a caixa pela saída multiplica, pela entrada ao
  contrário divide. Cada fonte fixa a RPM de referência (fonte = 32 RPM no nó dela); fontes que exigiriam RPMs
  diferentes, ou laços que discordam, = TRAVADO. RPM limitada a 4..256.
- Custo: máquina = custo base × (rpm/32)², arredondado para cima. Velocidade de fabricação = rpm/32.
- Fabricação acelerada (IL 3.4.0 b10): `TileEntityWorkstation.HandleRecipeQueue(float _timePassed)` (janela
  fechada) e `XUiC_RecipeStack.Update(float _dt)` (janela aberta; só a fila da máquina aberta, guardada no
  postfix do `XUiC_WorkstationWindowGroup.Update`) têm o tempo multiplicado.
- Log `power ...` agora inclui `rpm=` e `speed=x`.
- Testado (log 22:14): x4 → `1024/128 UT rpm=128 OVERLOAD`; x1/2 → `16/128 UT rpm=16 speed=x0.5 -> ON`;
  x2 → `256/128` OVERLOAD até 2 fontes (`256/256 UT rpm=64 speed=x2 -> ON`). Flange com o mesmo eixo do Eixo.
  E troca a razão de primeira. TRAVADO não testado; tempo real de fabricação confirmado só pelo usuário.

## 2026-11-22 — D8 T3: Embreagem, Regulador de Torque e Medidor

- `feClutch` (axial; meta 0 engatada / 1 solta: solta = nenhuma face, corta a rede). Modelo
  `pipeSmallValvePrefab` (eixo assumido Z — confirmar).
- `feTorqueRegulator` (axial, passa direto): `meta` 0..3 = 100/75/50/25 %. `ComputeUsage`: zona = nós alcançados
  pela saída sem cruzar outro regulador (esses viram zonas filhas); limite = % × capacidade da rede; a zona usa
  min(pedido, limite) e, se pede mais, as máquinas dela ficam a sqrt(limite/pedido) da velocidade (escala
  herdada por zonas internas). Zona que volta à entrada do próprio regulador = contornado (sem efeito).
  Modelo `pipe_valvePrefab` (eixo assumido Z).
- `feTorqueGauge` (6 faces, `pipe_cap.fbx`): leitura com fontes, máquinas, reguladores e carga %. O "painel fixo"
  da proposta ficou como leitura ao olhar (texto no mundo fica para a T5, com os modelos).
- E troca o ajuste de qualquer bloco com `Settings(kind) > 0` (velocidade, embreagem, regulador).
- Velocidade de fabricação = rpm/32 × escala do regulador (`TorqueNet.MachineSpeed`).

## 2026-11-22 — D8: sentido de giro, Inversor de Giro e contrato de animação

- T3 testada pelo usuário (embreagem, regulador 100/50 %, medidor).
- Pedido: a direção do giro importa; torque chegando ao contrário exige um item que inverta. E os modelos 3D
  precisam receber eventos de giro (com velocidade).
- Modelo: cada nó guarda a velocidade angular `Omega` (vetor unitário de eixo, regra da mão direita). Giro levado
  por uma face = +1/-1 ao longo da direção de viagem. Eixo/caixa de velocidade/embreagem/regulador mantêm;
  Caixa de Transmissão e Medidor: em linha mantém, curva de 90° inverte (engrenagens cônicas); Inversor inverte
  entre as pontas. Fontes (Motor, Manivela de Torque) agora só ligam pelas pontas do eixo (+Z local do modelo) e
  giram +Z. A primeira fonte fixa o sinal real; outra fonte contrária, ou laço que discorda = TRAVADO.
- Máquina: giro levado para dentro dela precisa ser +1; senão vai para `WrongSpin` (não roda, não consome).
  Log `power ...: wrong spin direction`; leitura do nó "X está girando ao contrário: use um Inversor de Giro";
  marcação do encaixe laranja quando algo está plugado mas não move a máquina.
- `feSpinInverter` (axial, `pipeSmallJointPrefab`), receita na Montadora.
- `KineticSpinner.cs`: em blocos ModelEntity da rede, no Motor (postfix `BlockPowered.OnBlockEntityTransformAfterActivated`)
  e nas máquinas (postfix `BlockWorkstation.OnBlockEntityTransformBeforeActivated`). Gira filhos `FeSpin*` no +Z
  local (tokens `In`/`Out`, `_Rev`, `_xN`), parâmetros de Animator opcionais; log `spin ...` quando o estado muda.
  Placeholders com `FeSpinWhole=true` giram o 1º filho. `build.ps1` passou a referenciar
  `UnityEngine.AnimationModule.dll`. Contrato documentado no ART_BRIEF.md.
- Testado (usuário, log 22:44): sentido, giro invertido (`wrongSpin`), travado com fontes opostas e eventos
  `spin` chegando a motores e máquinas; sem exceções. O log `spin` é verboso (260 linhas) — reduzir quando estável.

## 2026-11-22 — D8 T4: motores a combustível e melhorias do Motor Elétrico

- `TorqueEngine.cs`: motor a combustível = bloco vanilla `Class=Generator` com `FeTorqueEngine` (janela de
  combustível, Reabastecer, liga/desliga). Sem saída elétrica (`OutputPerStack` 0, `MaxPower`/`OutputPerFuel` 1);
  dá `FeTorqueOutput` UT pelo eixo (+Z local) enquanto ligado e com combustível. Queima 1 unidade a cada
  `FeFuelSecondsPerUnit` s (postfix em `PowerSource.HandleSendPower`, acumulando `Time.time`), desliga sozinho em
  0 (`ShouldAutoTurnOff`).
- Ligar exige `TileEntityPowerSource.MaxOutput > 0` (radial e botão On, "ttRequiresOneComponent", IL 3.4.0 b10):
  postfix no getter devolve 1 só para motores; o `PowerSource.MaxOutput` real fica 0 (fios não recebem nada).
- `feCoalEngine` (256 UT, 60 s/Carvão, `bigGeneratorPrefab`, Montadora) e `feGasEngine` (512 UT, 30 s/galão,
  `FeFuelItem=""` = gasolina vanilla, modelo do motor de carro, Garagem com 1 `smallEngine`).
- Bobinas: o Motor Elétrico é `Class=Powered` (sem slots), então viraram receitas de melhoria na Eletrônica:
  `feElectricMotor2` (256 UT, 60 W) e `feElectricMotor3` (512 UT, 120 W).
- Spinner também nos motores a combustível (postfix `BlockPowerSource.OnBlockEntityTransformAfterActivated`).

## 2026-11-22 — Indicador de conexão e recolher máquinas/peças

- Teste da T4: o usuário não achava onde ligar o eixo no Motor a Gasolina (o motor só liga pelas pontas do eixo
  dele) e pediu um indicador como o do encaixe; e que máquinas, motores e eixos se recolham como a manivela.
- `MotorSocketMarker.cs`: segurando qualquer peça de torque, além dos encaixes das máquinas, placas finas nas
  faces que levam torque de cada peça num raio de 7: verde = ponta livre, ciano = ligada (ou movendo a máquina do
  encaixe), laranja = peça vizinha desalinhada (ou máquina com giro ao contrário).
- `Pickup.cs`: o "take" vanilla de `BlockWorkstation`/`BlockPowerSource` só vale dentro do PRÓPRIO land claim
  (IL 3.4.0 b10). Para blocos "fe*": vale onde o jogador pode construir (`CanPlaceBlockAt`), mantendo as outras
  condições (colocado por jogador, `TakeDelay` > 0, entrada vazia nas bancadas). `TakeDelay` das máquinas e
  geradores 15 → 5 s (blocks.xml e `gen_phase3.py`).
- Peças da rede: `TakeDelay` 2 no `feShaft` (herdado); agachado + E abre um radial próprio com "pegar"
  (`BlockFeKinetic.GetBlockActivationCommands`/`OnBlockActivated` → `takeItemWithTimer`). O `CanPickup` vanilla
  foi tentado e removido: escreve "Aperte E para pegar" por cima da leitura e pega com E em pé.
- Bug no log (23:16): rede SEM fonte alternava entre "wrong spin" e "sem fonte" a cada 2 s (o sinal relativo
  depende do nó inicial). Sem bloco-fonte não há sentido real → não marca giro invertido.
- Motor a Carvão testado rodando (`spin feCoalEngine ... rpm=32 running=True`), mas numa rede só dele: eixo do
  motor N-S, Eixo do jogador L-O (posição; o indicador de pontas mostra).

## 2026-11-22 — Leitura e ajustes pelo menu vanilla (toque/segurar E)

- Depois do radial próprio, a leitura ao olhar e o E da Caixa de Velocidade sumiram: o MonoBehaviour que
  escrevia `XUiC_InteractionPrompt` a cada quadro perde para o prompt vanilla quando o bloco tem comandos.
- Caminho vanilla (IL 3.4.0 b10, `PlayerMoveController.TryHandleBlock`): com `HasBlockActivationCommands`, E abre o
  `XUiC_Radial` (toque = primeiro comando, segurar = menu) e o prompt é `string.Format(GetActivationText, tecla)`.
  Rótulos do radial: `blockcommand_<texto>`.
- `BlockFeKinetic`: comandos `fe_setting` (só caixa de velocidade/embreagem/regulador) e `take`;
  `GetActivationText` = leitura da rede (`KineticLookController.Describe`, chaves `{}` escapadas) + dica.
  Motor Elétrico e motores a combustível: postfix em `BlockPowered`/`BlockPowerSource.GetActivationText`.
  O antigo `KineticLookController` não roda mais por quadro.

## 2026-11-22 — Caixa de Transmissão: regra de giro consistente; motivo do TRAVADO

- Teste: leitura e menu (toque/segurar E) OK. Dois Motores a Carvão + Inversor travavam/alternavam mesmo
  "certos" (log 23:36: `locked` alternando, omegas trocando de sinal a cada recálculo).
- Causa: a regra da Caixa "em linha mantém, curva de 90° inverte" não é consistente — o giro de cada face
  dependia de por qual face o flood fill entrou primeiro (que muda com o nó inicial do recálculo).
- Correção: a Caixa (e o Medidor) gira todas as faces no mesmo sentido vistas de fora (k = giro da face de
  entrada); logo TODAS as saídas invertem em relação à entrada, em linha ou em curva (igual ao Create).
- TRAVADO agora diz o motivo: sentido ("fontes girando uma contra a outra") ou velocidade; no log `LOCKED(direction|speed)`.
- Testado (usuário, log 23:46): rede de 18 nós com 4 fontes → Prensa a 128 RPM (x4) com `1024/1024 UT -> ON`;
  travamentos só enquanto montava, já com motivo (`LOCKED(direction)`). T4 concluída.

## 2026-11-22 — Limpeza: fim da Carga (D7 etapa 4), slots dos motores, log enxuto

- Removidos: item `feCharge`, bloco + receita `feGasGenerator` (coletor de Carga a gasolina), chaves de
  localização deles e `ChargeFuelPatches.cs` (o "só queima Carga" da Prensa/Torno; nenhuma máquina tinha mais
  `FeChargeOnly`). Saves de teste com Carga no inventário perdem esses itens.
- Descrições: as 15 máquinas diziam "precisa de N W de Motores elétricos ao lado" → "precisa de N UT de torque
  no encaixe de motor (motor / manivela / motor a combustível / eixo)" (também no `gen_phase3.py`; sem vírgula
  para não quebrar o CSV). Manivela sem a frase dos Volantes.
- Motores a combustível: slots escondidos e shift-click recusado (`EngineSlots`, mesmo mecanismo do CrankSlots).
- Log: `ForgedInAshesMod.Verbose` só com `Mods/ForgedInAshes/debug.txt` (no .gitignore). Sem ele: a linha
  `power` só quando a máquina liga/desliga; sem `spin`, sem diagnóstico da manivela, sem a lista de patches.
- Manivela de Torque tinha `CanPickup`: E em pé pegava a manivela em vez de girar. Trocado por radial próprio
  (agachar + E → pegar), como as peças da rede.
- Testado (usuário, log 2026-11-23 00:01): sem erros; log enxuto (10 linhas do mod no teste inteiro); rede de 18
  nós segue ON a x4. Limpeza concluída.

## 2026-11-23 — Modelos 3D da rede de torque no jogo

- Blender 5.3 via MCP: `Art/feKinetic/build_feKinetic.py` gera Manivela de Torque, Eixo, Caixa de Velocidade,
  Caixa de Transmissão, Inversor de Giro e Regulador de Torque (peças `FeSpin*` com pivô no eixo), exporta um FBX
  por bloco (`export_feKinetic.py`) e prévias (`render_previews.py`).
- Unity CLI 1.0.1 instalado (com autorização do usuário; o instalador também instala skills de agente). Licença
  Personal já ativa na conta. Editor 2022.3.62f2 instalado sem elevação em `E:\UnityEditors` (`--no-elevate
  --download-directory`; o helper UAC falhou sem console).
- `FeBuild.BuildAll` em batch: 7 prefabs (inclui `feCrank`), bundle de 636 KB. O log novo confirma pivôs e +Z de
  cada peça. O Eixo precisou de raiz vazia (ver README do feKinetic).
- `blocks.xml`: os 6 blocos usam `#@modfolder:Resources/forgedinashes.unity3d?<bloco>Prefab`; `feShaft` virou
  `ModelEntity` (o Medidor ficou com `Shape=New` próprio); `FeSpinWhole` saiu do Inversor e do Regulador.
- Teste: modelos aparecem e a rede roda (1024/1024 UT). Um Inversor ficou "rolado" de lado (24 rotações do
  bloco): Caixa de Velocidade, Inversor e Regulador agora com `OnlySimpleRotations` (só as 4 de pé).
- Na verdade o Inversor girava INTEIRO: o FeBuild chama o modelo de `feSpinInverter` e o KineticSpinner
  comparava "FeSpin" sem diferenciar maiúsculas. Agora a comparação é exata (Ordinal). O `OnlySimpleRotations`
  fica (peças com pés não devem rolar).
- Testado (usuário): Inversor gira só os eixos internos. Modelos da rede de torque integrados e funcionando.
- Embreagem e Medidor modelados (Blender em background, `blender -b feKinetic.blend --python ...`, pois o
  Blender com MCP tinha fechado), bundle de 789 KB, XML apontando para os prefabs (Embreagem só de pé).
- Testado (usuário, 2026-11-23): Embreagem e Medidor certos no jogo. Os 8 blocos da rede de torque têm modelo.

## 2026-11-23 — F4-T04: Roda d'Água (fonte de torque)

- `feWaterWheel` (BlockFeKinetic, `FeKinetic=waterwheel`): fonte axial, 128 UT a `FeSourceRpm`=16 enquanto há água
  tocando as pás (`Kinetic.WaterTouching`: a célula dela, a de baixo e as laterais fora do eixo, via
  `World.IsWater`). Nova propriedade `FeSourceRpm` (padrão 32) — a referência de RPM da rede usa a RPM de cada
  fonte; misturar com motores de 32 RPM exige Caixa de Velocidade (senão TRAVADO por velocidade).
- Leitura: "Na água" / "Sem água nas pás". Receita na Serraria (30 madeira, 4 chapas, 2 barras, 2 engrenagens).
- Modelo (Blender em background): roda de pás com aros de ferro e eixo de ponta a ponta, `FeSpin_WaterWheel`.
- Bundle NÃO gerado ainda: a licença Personal caiu (sessão OAuth "stale", `unity license activate` pede
  `unity auth login`, que exige o usuário no navegador). Até gerar, o bloco aponta para um prefab que não existe.
- Usuário renovou o login; `unity license activate` OK; bundle de 865 KB com `feWaterWheelPrefab` (roda no centro,
  +Z no eixo).
- Testado (usuário, log 2026-11-23 09:05): sucesso; sem erros. Rede de 86 nós e 16 fontes movendo a Prensa a
  256 RPM (x8) com `4096/4096 UT -> ON`. F4-T04 (Roda d'Água) concluída.

## 2026-11-23 — E08 Motor a Vapor (fonte de torque de fim de jogo)

- `feSteamEngine` (estende `feCoalEngine`): 1024 UT a 32 RPM; Carvão Vegetal 1/20 s; `FeNeedsWater` (água na
  célula, embaixo ou nas 4 laterais, `World.IsWater`); `FeLubeItem=feResourceLubricant` nos slots
  (`SlotItem` = Lubrificante), 1 a cada `FeLubeSecondsPerUnit`=300 s rodando. Faltando algo, não roda nem queima
  (`TorqueEngine.Missing` → leitura "Sem água" / "Sem Lubrificante"). Slots visíveis só nesse motor.
- Receita na Garagem: 2 `smallEngine`, 6 Volantes, 30 Chapas, 10 Engrenagens, 6 Lubrificantes, 6 canos.
- Modelo (Blender background): caldeira, chaminé, cilindro, volante `FeSpin_SteamFlywheel`; bundle 944 KB.

## 2026-11-23 — D9: rede de fluidos, bombas, Condensadora e Motor a Vapor grande (tudo de uma vez)

- Pedido do usuário (feito sem aprovação por etapas: "faça tudo de uma vez e eu testo no final").
- `FluidNetwork.cs`: `FeFluid` = pipe | tank | mechpump | elecpump | condenser | steamengine. Canos ligam os 6
  lados; portas por dispositivo (bombas: entrada atrás/local −Z puxando água do mundo, saída na frente; Condensadora:
  vapor atrás, água na frente; motor: água por baixo do bloco pai, vapor por cima da célula central de cima).
  Rede = canos + portas (ou duas portas encostadas). Um fluido por rede, dois = BLOQUEADO. `FluidTicker` (servidor,
  0,5 s): produção → ofertas para demandas, sobra enche tanques, falta esvazia tanques, vapor sem destino escapa.
- Persistência: `FluidStore` em `<save>/ForgedInAshes_fluids.txt` (registro dos dispositivos + níveis), salvo a cada
  30 s e no `SaveWorld`/`SaveAndCleanupWorld`. Registro: `BlockFeFluid`/`BlockFeKinetic` próprios, postfix em
  `BlockPowerSource.OnBlockAdded/Removed`, e em `Block.OnBlockAdded` + `BlockPowered.OnBlockRemoved` para os elétricos
  (BlockPowered não sobrescreve OnBlockAdded, IL 3.4.0 b10).
- Bomba Mecânica: `BlockFeKinetic` `FeKinetic=pump` (eixo lateral, local X), consumidora de torque como máquina
  (64 UT; vazão ∝ RPM). Bomba Elétrica (60 W, 150 L/min) e Condensadora (120 W, 120 L/min, 90 %): `Class=Powered`.
- Motor a Vapor agora multibloco 3×2×3 (`SteamEngine.cs`): até 1024 UT; nó de torque só na célula da frente da
  camada de baixo (`Kinetic.EnginePort/NodeOf/NodeHasFace`); tanque de água interno 2000 L; consumo de água e carvão
  ∝ carga (mín. 10 %); vapor para cima.
- Modelos (Blender background): Cano com 6 braços `FeArm_*` (eixos do Unity) ligados/desligados por `PipeArms`
  conforme as conexões; Caixa d'Água; Bomba Mecânica (`FeSpin_PumpShaft`); Bomba Elétrica; Condensadora; Motor a Vapor
  3×3×2. `FeBuild` aceita `WireOffset.001`. Bundle 1,1 MB.
- Não testado no jogo ainda.

## 2026-11-23 — D9 rodada 2: indicadores de portas, pistões, vapor visível, motores elétricos

- Teste do usuário: "não gera vapor". O arquivo de fluidos mostrou o motor com 980 L de água e 52 L de vapor: gerava,
  mas escapava invisível; o torque dele travava a rede (`LOCKED(direction/speed)` ao entrar como 17ª fonte).
  Cano em cima do motor caía: o motor tinha `StabilitySupport=false` → agora true (e no Motor Industrial).
- Portas de fluido no marcador (segurando peça de torque OU de fluido): azul = entrada de água, branco = saída de
  vapor, ciano = já ligada; amarelo = entrada de esteira (Motor a Vapor, laterais da camada de cima; só visual até a
  fase 5). Tanques não mostram (todos os lados).
- Motor a Vapor: entradas de água também nas laterais esquerda/direita/trás da camada de baixo. Modelo: dois
  pistões `FePiston_*` (KineticSpinner os desliza no Z local em fase com o giro, 90° entre eles), puffs de vapor
  `FeSteamPuff_*` (SteamVent.cs: sobem e crescem enquanto o motor roda sem cano no topo), portas de esteira.
- Item `feSteamPiston` (Metalúrgica); o Motor a Vapor usa 2 no lugar dos motores pequenos.
- Motores elétricos com modelo próprio; o Industrial (`feElectricMotor3`) virou multibloco 3×2×3 (eixo na frente da
  camada de baixo; `Kinetic.IsMultiEngine` agora vale para motores; Capacity lê o TE do pai). Bundle 1,5 MB.
- Não testado ainda: multibloco `Class=Powered` (fio no Motor Industrial) e os pistões/puffs no jogo.

## 2026-11-23 — Dínamo (torque → eletricidade)

- `feDynamo` (Dynamo.cs): `Class=Generator` + `FeDynamo`. Na rede de torque é consumidor (nó próprio, eixo local Z,
  `FeTorqueCost`=128 como máquina, custo ×(rpm/32)²); no lado elétrico, prefixo em `PowerSource.HandleSendPower`
  mantém combustível cheio e ligado enquanto a rede roda e define `MaxOutput` = `FeDynamoWatts`(60) × (rpm/32),
  chamando `SendHasLocalChangesToRoot` quando muda; sem torque zera o combustível (vanilla desliga).
- Reabastecer, linha de combustível e slots escondidos (como Manivela/motores). Receita na Eletrônica. Modelo com
  enrolamentos de cobre, comutador, isolador e `FeSpin_DynamoArmature`. Bundle 1,5 MB. Não testado ainda.

## 2026-11-23 — Dínamo Industrial e Barramento

- Usuário: ao ligar fio de um Dínamo em outro (ou no Motor a Vapor) o jogo diz "esta fonte de energia não pode ter
  uma conexão ao principal". Vanilla: `TileEntityPowerSource.CanHaveParent` só aceita pai se `PowerItemType == 7`
  (banco de baterias); `PowerSource.CanParent` devolve false. O Motor a Vapor não é elétrico (dá torque).
- `feDynamo2` (Dínamo Industrial, multibloco 3×2×3): 1024 UT → 500 W a 32 RPM; eixo na frente da camada de baixo
  (`Kinetic.IsMultiEngine` inclui dínamos; `Dynamo.Watts` usa `NodeOf`).
- `feBus` (Barramento): gerador com combustível interno. Puxa-se fio DO Barramento PARA cada Dínamo (ou outro
  Barramento): postfix em `CanHaveParent`/`CanParent` libera esse caso; um Dínamo com pai Barramento zera a própria
  saída e guarda os watts em `Dynamo.Contribution`; o Barramento soma as contribuições dos filhos e põe no próprio
  `MaxOutput` (PowerManager.Update atualiza todas as fontes, inclusive filhas). Leitura: "Juntando N fonte(s): W".
  Geradores vanilla, solar e baterias não entram. Modelos e bundle (1,6 MB). Não testado.
- Usuário testou Dínamo, Dínamo Industrial e Barramento: "deu certo".

## 2026-11-23 — Condensadora 2×2 com câmaras de vidro

- `feCondenser` agora é multibloco `MultiBlockDim 2,2,1` (células Unity x −1..0, y 0..1; o pai é a de baixo onde se
  mira). Portas (FluidNetwork.cs): vapor entra ATRÁS da célula de cima do pai (`pos+(0,1,0)`), água sai na FRENTE do
  pai.
- Modelo: câmara de gás em cima e de líquido embaixo, frente aberta com grade (janela), serpentina de cobre entre as
  duas, ventoinha no topo. Partes animadas (CondenserVisual.cs, postfix em
  `BlockPowered.OnBlockEntityTransformAfterActivated`): `FeFan*` gira no Z local (240°/s energizada, 900°/s
  condensando); `FeLevelGas` escala Y = vazão de vapor / `FeFluidRate`; `FeLevelLiquid` (azul, material novo
  `feKin_Water`) escala Y = água no buffer / `FeFluidBuffer`. Pivôs no fundo de cada câmara. Collider 1,90×1,95.
- Teste: modelo desalinhado meio bloco das portas. IL: `BlockShapeModelEntity.GetOffsetForMultiblock` já desloca
  −0,5 em X/Z quando a dimensão é PAR (y: −0,5+0,5 = 0). Logo um multibloco par deve ser modelado CENTRADO na origem;
  a coluna do pai fica em Blender x −0,5. Corrigido (collider centro 0).
- "Não gera vapor": o save mostrava a Condensadora com 200,6/200 L de água no buffer → entrada de vapor 0 (saída de
  água sem destino/afogada), Motor a Vapor com 240 L de vapor parado. Leitura da Condensadora agora mostra a água
  esperando e "CHEIA: a saída de água não tem para onde ir".
- Teste 2: Condensadora funcionando (34 L/min). Restou: cano da saída de água desalinhado, braço do cano não se junta
  à entrada de vapor, e o alicate mostrava o ícone de fonte elétrica sobre o Motor a Vapor.
  - Layout confirmado no IL (`Block.Init`): células x de −(n/2) a round(n/2+0,1)−1 → dim 2 = −1..0; o modelo é
    deslocado por `rot * (−0,5, 0, 0)` (`GetRotatedOffset`). Bocais agora na altura do cano (C = 0,5 e 1,5; antes
    0,55 e 1,45).
  - Log de diagnóstico sempre ligado (só quando muda): posição do modelo da Condensadora e cada braço de cano que
    liga/desliga contra um equipamento.
  - `ItemActionConnectPower.GetCrosshairType` devolve PowerSource para todo `BlockPowerSource`; postfix troca por
    Plus nos motores de torque (`FeTorqueEngine`).
- Teste 3: alinhado; alicate ok. PENDENTE (visual, adiado pelo usuário): o braço do cano não se junta à entrada de
  vapor atrás em cima (669,62,868 → célula filha 669,62,869), embora o vapor flua. Nenhum log de braço para esse cano.

## 2026-11-23 — D10 T1: Esteira

- Proposta D10 (PLANO_MOD 5.6) aprovada pelo usuário. T1 = `feConveyor` (Belt.cs, `BlockFeConveyor` : `BlockFeKinetic`,
  `FeKinetic=conveyor`, eixo dos roletes = X local).
- Torque: cada esteira é nó e máquina (`FeTorqueCost` 8). Faces: laterais (eixo do rolete; não liga em outra esteira
  ao lado) e frente/trás quando uma alimenta a outra (`Belt.Linked`). Entre esteiras a rotação segue W = cima × frente
  (o sentido da esteira não depende do giro), então a linha não trava sozinha.
- Itens lógicos (`BeltStore`, `<save>/ForgedInAshes_belts.txt`, ItemValue serializado pelo vanilla em base64),
  movidos no servidor a 10 Hz: 1 bloco/s × velocidade da máquina; 4 por esteira, espaço 0,25; passam para a esteira da
  frente (por trás entram no início, pelo lado no meio); no fim, param. Itens soltos (EntityItem) em cima entram na
  esteira. Pegar a esteira solta os itens.
- Visual no host: `BeltRenderer` (modelo de item largado via `ItemClass.CloneModel`, cubo para blocos, ~0,35 m),
  `BeltSurface` (filho `FeBeltSlats` desliza no Z local), roletes `FeSpin_*`.
- Aprendido: o eixo de giro (Unity +Z local) é o −Y LOCAL do objeto no Blender, levado pela rotação do objeto
  (log do FeBuild: bomba, caixa, roletes). Roletes feitos ao longo de Y e girados 90° em Z.
- build.ps1 passou a referenciar UnityEngine.PhysicsModule (Collider/Rigidbody). Receita: 4 esteiras na Montadora
  (2 Chapa, 1 Eixo, 4 Couro). Não testado.

## 2026-11-23 — D10: curvas, divisão em 2/3 e Esteira de Subida

- Pedido do usuário (desenho): esteira ao lado vira curva e compartilha o torque; 2 ou 3 saídas dividem os itens;
  o visual muda; esteira que sobe 1 bloco (escada de itens).
- `Belt.Outputs`: frente (por trás = início, pelo lado = meio/junção), laterais que apontam PARA FORA (curva/divisão),
  rampa = só a de cima à frente. `Belt.Links` = saídas + quem tem esta como saída (inclui a rampa embaixo-atrás); a
  BFS do torque usa `Links` (mapeamento W) e as faces normais só para eixos nas laterais.
- Divisão: cada item recebe a saída ao entrar, em rodízio por esteira (`ChooseExit`); se a dele está cheia, tenta as
  outras. Caminho no visual: reto, arco de 1/4 em volta do canto de trás do lado da curva, rampa a 45°.
- Modelo: `FeRail_L/R` somem onde outra esteira encosta, `FeBeltEnd` (batente) quando não há saída à frente,
  `FeCurve_L/R` no lado da curva; ripas 7 (não saem mais da esteira). `feConveyorRamp` (FeBeltRise 1) com ripas
  subindo a rampa. Receita: 2 Esteiras + 1 Chapa.
- Teste: ao fechar o jogo, "belts: could not write an item: Object reference" — no OnApplicationQuit as classes de
  item já foram descarregadas e o arquivo foi sobrescrito vazio. Agora salva no prefixo de
  `GameManager.SaveAndCleanupWorld` / `SaveWorld` e nunca grava lista parcial. Log extra das portas da Condensadora
  (o cano da entrada de vapor não apareceu no diagnóstico dos braços).
- Teste: itens subiram a rampa e o arquivo de esteiras agora salva. Usuário: a curva (e a subida pelo lado) parecia
  remendada. Novo modo CURVA (esteira com uma só saída, lateral): some a esteira reta (ripas, trilhos, batente,
  roletes) e aparece `FeCurveSet_L/R` (piso em 1/4 de anel em volta do canto de trás, trilho externo em arco, poste
  interno) e `FeCurveSlats_L/R` girando no eixo vertical em volta do canto (raio 0,5 = o arco dos itens; R: +ângulo,
  L: −ângulo em Unity). Divisões continuam no modo reto com laterais abertas.
- Condensadora: o log mostrou o cano 669,62,868 existindo e conectado, mas o PipeArms dele nunca rodou. Log novo
  no Attach dos canos vizinhos a equipamentos (ativo, componente, braços encontrados).
- Teste: funcionou, sem erros no log; curvas "horrorosas" (anel feito de caixas sobrepostas, base quadrada aparecendo).
  Modelo refeito com `arc_solid` (setor de anel sólido de verdade): piso, trilho externo em arco, filete interno e
  ripas em cunha. Divisões (2 ou 3 saídas) viram uma MESA DE TRANSFERÊNCIA (`FeJunction`: chapa com esferas,
  `FeJunctionPosts` nos cantos, `FeJunctionWedge` em V quando divide só para os lados). Cama da reta separada
  (`FeBeltBed`). BeltShape: 4 visuais (reta, curva E, curva D, junção); a mesa não anima.
- D10 T3 (parcial): esteira apontando para a entrada de itens do Motor a Vapor (laterais da camada de cima,
  `Fluids.ConveyorPorts`) entrega: Carvão → combustível (`FeFuelPerItem`), Lubrificante → slots. Outros itens esperam.
  `Belt.Exits` = saídas de esteira + a máquina; entra no rodízio das divisões.
- Condensadora: o cano 669,62,868 nem chegou a registrar vizinho → o mundo não devolve a Condensadora na célula de
  cima. `HasPortAt` agora cai para as portas dos aparelhos registrados; log do bloco na própria célula da porta.
- Teste: log sem erros. A célula de cima da Condensadora é AR (ela foi colocada quando ainda era de 1 bloco): pegar e
  recolocar; o fallback de portas já mostra o braço do cano. Carvão pela esteira: já entra no combustível do Motor a
  Vapor e recusa quando está cheio; agora loga (no máx. 1 linha por máquina a cada 15 s: "took", "fuel full", "not
  taken here").
- `feBeltCrate` (Armazém de Esteira): bloco completo (sem Extends, sem upgrade/downgrade) com TEFeatureStorage +
  Lockable e `FeBeltInput`. Esteira apontando para qualquer lado entrega (empilha, depois slots vazios via
  `UpdateSlot`); espera se cheio ou se um jogador está com ela aberta (`IsUserAccessing`). Receita na Montadora.

## 2026-11-23 — D10: Funil, entradas das máquinas e receita fixa

- Usuário: fazer tudo o que falta (multiplayer por último), testar no fim e depois conversar sobre balanceamento.
- Funil (`feFunnel`, `BlockFeFunnel`, Belt.cs `Funnel`): costas num baú (qualquer `TEFeatureStorage`, vanilla também) ou
  máquina (`TileEntityWorkstation`, só a SAÍDA), frente numa esteira; a cada 0,5 s põe até `FeFunnelAmount` (16) itens
  no início da esteira. Espera baú aberto (`IsUserAccessing`) e esteira cheia. Lista de funis salva no arquivo das
  esteiras (linhas "F;x;y;z").
- Entradas por qualquer lado (`BeltMachines.AnySide`): Armazém, as máquinas do mod (workstations "fe*") e geradores que
  queimam item (Gerador a Carvão, Motor a Carvão). Workstation: combustível (`ItemClass.GetFuelValue` > 0) → slots de
  combustível; material fundível (`MadeOfMaterial.ForgeCategory`) → entrada (Fundição); o resto → receita fixa.
- Receita fixa (AutoCraft.cs): comando radial "Receita fixa liga/desliga" nas máquinas fe* (postfix em
  `BlockWorkstation.GetBlockActivationCommands`, prefixo no `OnBlockActivated(string,...)`). Liga com a receita da fila;
  ingredientes que chegam pela esteira vão para um estoque interno (até 5 vezes a receita); com a fila vazia e tudo no
  estoque, põe 1 `RecipeQueueItem` na última posição. Desligar ou remover a máquina solta o estoque. Leitura mostra a
  receita e os ingredientes. Salvo em `ForgedInAshes_autocraft.txt`.
- Esteira de Descida (`feConveyorDown`, `FeBeltRise` -1): recebe da esteira um bloco ACIMA atrás (a de cima a vê como
  saída quando não há nada na frente no nível dela) e entrega na frente no nível dela; modelo = rampa espelhada.
  `Links` também procura entradas um nível acima.
- Esteira com Filtro (`feConveyorFilter`, `FeBeltFilter`): radial "Ajustar filtro" com o item na mão (mão vazia
  limpa); itens iguais ao filtro vão para as saídas laterais, os outros seguem em frente; cada tipo espera se o
  caminho dele não existe (`Belt.ExitsFor`). O item do filtro flutua girando sobre a esteira (host). Filtros salvos no
  arquivo das esteiras ("Q;x;y;z;item"). Licença do Unity expirou de novo: `unity license activate` resolveu.

## 2026-11-23 — D9: Óleo, Gasolina e Lubrificante nos canos

- Fluidos novos `oil`, `gasoline`, `lubricant` (FluidNetwork.cs, `Fluids.FluidOfItem/ItemOfFluid`): Óleo `resourceOil`
  10 L, Lata de Gasolina `ammoGasCan` 1 L, Lubrificante `feResourceLubricant` 10 L.
- Despejador (`feFluidFiller`, FluidKind.Filler): recebe itens por esteira (qualquer lado), funil ou mão (radial
  "Despejar o item da mão") e oferece o fluido pela porta da frente (1000 L).
- Envasadora (`feFluidBottler`, FluidKind.Bottler): demanda pela porta de trás qualquer fluido envasável (porta com
  fluido "" = coringa só para fluidos com item); a cada 0,5 s põe até 16 itens na esteira da frente; E dá os itens.
- Refinaria (`feRefinery` ganhou `FeFluid=refinery`): fluido por trás vira itens entregues à própria máquina
  (`BeltMachines.Insert` → estoque da receita fixa). Registro de aparelhos de fluido agora vale para qualquer bloco
  (postfix em `Block.OnBlockAdded`); refinarias já colocadas precisam ser recolocadas.

## 2026-11-23 — Fase 6: modelos próprios das máquinas de produção

- 17 modelos (`model_m_*` em build_feKinetic.py, prefabs `feM_*Prefab`): Fundição, Prensa, Torno, Carvoeira, Prensa de
  Munição, Montadora, Bancada de Mods, Tear, Refinaria, Laboratório, Cozinha, Bancada Eletrônica, Serralheria,
  Serraria, Misturadora, Garagem, Robótica. Mesma pegada do placeholder (MultiBlockDim mantido; largura par centrada).
- SEM `ModelOffset`: o padrão do motor (0, 0,5, 0) é o que o FeBuild espera (filho a −0,5). `gen_phase3.py` ganhou
  `OWN_MODELS` e `EXTRA` (o `FeFluid` da Refinaria agora sai do gerador); as 4 máquinas escritas à mão foram editadas.
  A regeneração tinha apagado a receita `feBatteryModule` do colega (estava dentro da região gerada): recolocada fora.
- MachineVisual.cs: `FeSpin_*` giram (token `x<mult>` na velocidade) e `FePiston_*` sobem/descem enquanto há receita
  na fila (ou a Fundição queima). Hook: postfix em `Block.OnBlockEntityTransformAfterActivated` (BlockWorkstation não
  o declara). Partes verticais: construídas ao longo de Y local e giradas (−90°, 0, 0) — mapa local (x,y,z)→(x,z,−y).

## Próximo passo (antigo, mantido para histórico)

Fase 1 — (feito) F1-T01: itens `feResourceIronPlate`, `feResourceIronShaft`, `feResourceGear` (+ localização,
ícones vanilla). Antes do F1-T03 resolver P14 (pasta XUi do mod).

## 2026-11-23: correções do teste geral (esteiras)
- Rampa (subida/descida) ao lado de uma esteira era vista como curva/divisão: `Belt.Outputs` não conta mais rampa como saída lateral.
- Tirar uma Esteira com Filtro deixava o item flutuando: o filtro é apagado ao remover o bloco, filtros órfãos são limpos (`PruneFilters`) e o desenho ignora posições sem filtro.
- Funil: funciona nos dois sentidos (`Funnel.Route`: baú/máquina de um lado, esteira do outro), registra-se de novo ao olhar para ele e loga `belt -> feFunnel at ...: took ...`.
- Salvar com itens nas esteiras: confirmado no jogo.

## 2026-11-23: F8.0 (craft em cadeia, D11 aprovado)
- `tools/craft_matrix.py`: as 600 receitas do jogo recebem um modelo de cadeia (0 sem modelo) → `tools/out/craft_matrix.csv`.
- `Mods/ForgedInAshes/Data/fe_processes.xml` (fora de Config/, para o jogo não tratar como patch): fluidos, máquinas, itens e processos. A linha da bala 9mm está toda como `planned`. `Processes.cs` lê o arquivo no InitMod; `tools/check_processes.py` valida.
- Painel de receita (N10): comandos "Próxima produção" / "Produção anterior" (`AutoCraft.Cycle`, receitas da craft_area = nome do bloco via `CraftingManager.GetAllRecipes()`).
- Site de tutoriais: `tools/gen_site.py` → `site/` (estático; Vercel com Root Directory = site). Gerado dos dados do mod: página por item fe*, por máquina e por `<chain>`.
- Nota: no pt-BR do jogo, `resourceBulletCasing` se chama "Revestimento de balas".

## 2026-11-23: F8.1 metalurgia
- Revestimento de argila retirado do plano (usuário): no pt-BR do jogo "Revestimento de balas" = cápsula.
- Metal fundido é fluido (`molten_brass/lead/iron/steel`), só passa por `feMetalChute` (FeFluid chute). `FluidPort.Metal`: a rede a partir de uma porta de metal só anda por calhas e só junta portas de metal; canos e calhas nunca se ligam (`NetFrom`, `HasPortAt(..., metal)`, PipeArms).
- Fundição (`feFoundry`, FeFluid smelter, FeMetalBuffer 200): derrete o que chega por esteira ou da mão (`fe_melt`) conforme os processos `melt` do fe_processes.xml, queimando o combustível dos slots (1 s de valor de combustível por s de derretimento). Saída de metal em qualquer lado de fora das 2 células de baixo que tenha calha.
- Mesa de Moldagem (`feCaster`, FeFluid caster): um molde (item), processos `cast` dizem metal/litros/saída/tempo; esfria (2x com água ao lado), solta na esteira da frente ou "Pegar as peças". FluidState ganhou Mold/Made/Count (salvos no ForgedInAshes_fluids.txt).
- Modelos feMetalChute (braços FeArm_*.001: PipeArms procura também por prefixo) e feCaster (FeCastMetal, FeCastReady; CasterVisual).
- Moldes: Cápsula, Ponta, Lingote, Chapa, Tubo, Engrenagem (Torno). Cápsula Bruta → Revestimento de Bala na Prensa de Munição (a Prensa já tinha a receita vanilla da cápsula: regra de duplicata).

## 2026-11-23: teste da F8.1 (log 21-32-13)
- Funcionou: Funil (baú) → Fundição derrete latão → Calha → Mesa de Moldagem (24x "cast 5x feCasingRaw") → esteira → Prensa de Munição → Funil tirou 16 Revestimentos. Molde de Lingote: 12 lingotes de ferro. Trocar molde ok.
- Bug: itens sumiam nas máquinas do mod. O ramo "material de forja vai para a entrada" (`InsertWorkstation`) colocava itens com ForgeCategory (Cápsula Bruta, argila...) nos slots de entrada escondidos (as janelas das máquinas do mod não têm entrada): 90 Cápsulas Brutas e 16 argilas perdidas. Corrigido: esse ramo não vale para máquinas fe*; `RescueHidden` devolve o que estiver escondido (cai no chão ao lado da máquina, quando uma esteira entrega ou quando o jogador olha para ela).
- "Próxima produção" com um item na mão pula direto para a receita dele (a Prensa de Munição tem 49 receitas).

## 2026-11-23: F8.2 química
- `ProcessMachine.cs`: máquina genérica (FeFluid processor). O que faz = processos não planejados do fe_processes.xml com machine = nome do bloco. Itens por esteira (qualquer lado) ou "Colocar o item da mão", estoque de 8 receitas por ingrediente; fluido pela porta de trás (o fluid_in dos processos); torque quando o processo pede (bloco FeKinetic pump, eixo na lateral); produtos na esteira da frente ou "Pegar os produtos". FluidState.Stock salvo (coluna 10).
- Blocos: feCrusher (torque 128), feChemMixer (torque 64 + água), feWasher (água), feSteamDryer (vapor). Itens: feCoalDust, feNitratePure, feGunPowderWet. Processos crush_coal, crush_stone, wash_nitrate, mix_powder, dry_powder; linha "Pólvora" no site.
- Modelos com FeSpin (rolos do Triturador ao contrário um do outro, agitador vertical no Misturador).

## 2026-11-24: versões industriais e Biodigestor
- `Industrial.cs`: patches no BlockPowered (comandos colocar/pegar/molde/derreter e visual da Mesa) para máquinas F8 elétricas; `ProcessMachine.Speed` e a Mesa respeitam energia (FeProcSpeed, FeCoolFactor); Fundição elétrica (`te == null` em `Melt`) aquece enquanto ligada (`TickElectricSmelter`, FeMeltSpeed, FeHeatMax).
- Blocos: feInductionFurnace (2x2, 250 W), feCasterElectric (60 W), feRetortKiln (100 W), feBiodigester (água). Itens: feNitreEarth, feBioMash, feBiofuel. Processos: ind_melt_*, retort_wood, nitre_flesh/crops, rot_meat, mash_*, wash_nitre_earth, distill_biofuel (receita da Refinaria).
- Combustível alternativo nos motores: FeAltFuel/FeAltFuelPer (Motor a Gasolina: 3 Biocombustíveis = 1 unidade), só por esteira.
- Exportação do Blender: o disco F: deu "Invalid argument"/"cannot save" intermitente ao gravar FBX/PNG; repetir a exportação até "EXPORTED".

## 2026-11-24: crash ao carregar (log 09-01-31)
- `blocks.xml` falhou: "Could not find Extends block feElecPump". feInductionFurnace/feCasterElectric/feRetortKiln estendiam feElecPump mas estavam antes dele no arquivo; o jogo resolve Extends na ordem do arquivo. Os erros seguintes (items/recipes/loot) eram cascata.
- Corrigido movendo os três para depois do feCondenser. Nova regra no `check_phase3.py`: Extends (blocos e itens) deve apontar para algo definido antes (23 regras).

## 2026-11-24: texto legível, livro de receitas e ícones
- Texto de foco minúsculo: o rótulo `interactionPrompt/lblText` do jogo tem 70 px e usa ShrinkContent (padrão do XUiV_Label). Patch `Config/XUi/windows.xml`: `overflow="resizeheight"` (cresce em altura, fonte normal). A lista "Faz:" saiu do texto das máquinas de processo (agora "N receitas (segure E: Receitas)").
- `RecipeBook.cs`: comando "Receitas" (fe_recipes, ícone book) em toda máquina fe* com processos (fe_processes.xml) ou receitas de bancada (craft_area). Abre a janela XUi `feRecipes` (controller `ForgedInAshes.FeRecipes, ForgedInAshes` -> `XUiC_FeRecipes`, 20 linhas por página, << >> OK). Se a janela não abrir, mostra as primeiras linhas num tooltip. Ganchos: BlockWorkstation (AutoCraft), BlockPowered (Industrial), BlockFeFluid, BlockFeKinetic.
- Ícones: `Art/feKinetic/render_icons.py` (rodar depois do build_feKinetic no mesmo namespace) renderiza 160x160 transparente em `Mods/ForgedInAshes/UIAtlases/ItemIconAtlas/`: 55 blocos (do modelo 3D) e 29 itens (modelos de item simples; moldes mostram a cavidade em metal incandescente). `tools/apply_icons.py` aponta CustomIcon de cada um para o próprio ícone, sem tint. Sem ícone próprio ainda: feCrank (outro .blend), feCoalGenerator, feBeltCrate, feCoalEngine, feGasEngine (usam prefab do jogo), feTestItem.

## 2026-11-24: XUi na pasta certa, escolha de receita, Biodigestor Industrial
- Log 10-41-58: `GUIWindowManager.Open: Window "feRecipes" unknown!` e o texto continuou pequeno. Nenhum patch de XUi tinha sido aplicado: o jogo procura `XUi_InGame/windows` e `XUi_InGame/xui` (XUi::SetXmlsForUi), então a pasta do mod é `Config/XUi_InGame/`. Uma pasta `Config/XUi/` é ignorada sem erro. Pasta movida; comentário corrigido em fe_common.py.
- Escolha de receita (máquinas de processo): comando "Escolher receita" (fe_proc_pick) cicla automática -> receita 1 -> ... -> automática. Novo campo `FluidState.Pick` (coluna 11 do fluids.txt). Com uma receita escolhida, a máquina só roda essa receita e só aceita os ingredientes dela (esteira e mão). O texto de foco mostra a receita atual.
- Biodigestor no teste: carne crua + osso -> carne podre estava certo pelo projeto (rot_meat). A Terra Nitrosa pede carne PODRE + ossos; agora dá para escolher a receita.
- feBiodigesterBig (Biodigestor Industrial): 1x2x1, torque 64 (FeKinetic pump, eixo x), água por trás, esteira em qualquer lado, calha na frente. Lotes dobrados; só nele, carne crua vai direto para Terra Nitrosa (nitre_meat_big) ou Mosto (mash_meat_big). Receita no Montador: 2 Biodigestores + 6 engrenagens + 16 chapas + 2 eixos. Comandos em multiblocos usam o bloco pai (ParentOf).

## 2026-11-24: modelos HD com IA local e efeitos (Art/feHD)

- IA local em `F:\IA` (ComfyUI 0.46 + SDXL + Hunyuan3D-2, scripts do Blender headless; ver `F:\IA\LEIA-ME.md`).
- Sete blocos refeitos em estilo 7DTD (`Art/feHD/build_feHD.py`): Fundição (`feM_Foundry`), Calha de Metal, Mesa de
  Moldagem, Eixo, Condensadora, Cano, Bomba Mecânica. Textura PBR em atlas (1 material por bloco), contratos de nome
  antigos mantidos. Gerador a Carvão ganhou versão HD de teste (`Art/feCoalGenerator/hd`, ainda fora do bundle).
- `FeBuild.cs`: usa `Art/<bloco>/hd/<bloco>_HD.fbx` quando existe; cria o material Standard do atlas, os materiais de
  efeito (`FeMolten`, `FeLiquid`, `FeGas`, `FeGlow`, `FeSmoke`, `FeSpark`) e `ParticleSystem` nos empties `FeFx_*`;
  esconde `FePour_*`; texturas com crunch (bundle 14 MB).
- `FxVisual.cs` (novo): metal fundido com cor por metal, fluxo rolando e resfriamento; cor do fluido nos visores;
  brilho da fornalha; jatos de metal; vapor/fumaça/faíscas pelo estado (FluidStore, FluidTicker, workstation).
  Patches em `Block`, `BlockPowered` e `BlockPowerSource.OnBlockEntityTransformAfterActivated`.
- `tools/build.ps1`: referência `UnityEngine.ParticleSystemModule.dll`.
- Verificado: DLL compila; bundle gera com os sete HD (pivôs das peças que giram conferidos no log); jogo carrega o mod
  sem erro (`Harmony: 34 method(s) patched`). **Não verificado no mundo**: roteiro em `TESTE_GERAL.md` seção 13.

## 2026-11-24: HD rodada 2 (fogo, despejo, nove modelos)

- Teste do usuário: fogo da forja vanilla atravessando a Fundição → `ParticleName`/`ParticleOffset` removidos do
  `feFoundry`; fornalha aberta com chama própria (`FeFx_Fire`).
- Despejo natural: jatos em arco afinando (helper `stream()` no `build_feHD.py`, UV ao longo do jato), respingo
  (`FeFx_Splash`); Mesa de Moldagem rebaixada para o metal descer por gravidade (molde a 0,22 m).
- Novos HD: Motor a Vapor, Caixa de Transmissão, Embreagem (alavanca `FeLever_Clutch` animada pelo estado), Caixa de
  Velocidade, Inversor de Giro (engrenagem cônica intermediária `FeSpin_InverterIdler`), Torno (`FePiston_Carriage`),
  Triturador (poeira `FeFx_Dust`), Esteira, Prensa de Munição (`FePiston_Ram`).
- FeBuild: tabela de partículas `FxLooks` (Fire, Splash, Sparks, Smoke, Dust, SteamVent, Steam), `flame.png`.
- `FxVisual`: motor a vapor (fogo/brasa/fumaça/purgas via `TorqueEngine.IsRunning`), poeira das máquinas de processo,
  alavanca da embreagem; `SteamVent` também liga `FeFx_SteamVent_*`.
- Bundle 27,5 MB (16 modelos HD, crunch). Jogo carrega sem erro (Player.log 13:21). **Não verificado no mundo**:
  `TESTE_GERAL.md` 13b.

## 2026-11-24: Duto de Esteira, Suporte, funil girando, encaixes reais, motores e dínamos HD

- `feConveyorDuct` (Duto de Esteira): variante fechada da esteira (`FeBeltClosed`, `Belt.IsClosed`): o `BeltRenderer`
  não desenha os itens, o `Absorb` não pega itens do chão, nada anima. Boca no padrão das entradas de máquina.
  Receita: 2 esteiras + 3 chapas → 2 dutos (Montador).
- `feConveyorStand` (Suporte de Esteira): cavalete decorativo com berço para o duto. Receita: 1 chapa + 6 sucata → 2.
- Funil: `AllowedRotations=No45` (qualquer lado, inclusive para baixo); `FunnelShape` escolhe o bico.
- Encaixes: `FeBeltChute` (esteira → máquina/duto), `FeDuctBoot`, `FeDuctRamp`, `FeDuctCapF/B`, `FeDuctSide_L/R`,
  `FeDuctHatch` (`Belt.FedFrom` = quem alimenta pelo lado/trás/cima). Ver `Art/CONVEYOR_PORTS.md`.
- HD: Funil, Esteira (com calha), Motores Elétricos 1/2/3, Dínamos 1/2. Ícones dos 25 blocos HD refeitos.
- Colliders sem as peças de encaixe (`FeBuild.OptionalParts`). Bundle 39,8 MB.
- Verificado: DLL compila, XPath 534/0, regras 23/23, bundle gera, jogo carrega o mod (14:12). **Não verificado no
  mundo**: `TESTE_GERAL.md` seção 14.

## 2026-11-24: Motor a Vapor com virabrequim (biela-manivela)

- Pistão atravessando a fornalha (teste do usuário) → motor refeito: vertical, dois cilindros sobre o virabrequim
  (o eixo de saída), manivelas a 90°, volante, mancais, colunas, guias, cruzetas e bielas.
- `KineticSpinner.Linkage`: `FeCrankPin_n` / `FeCrosshead_n` / `FeConrod_n` resolvidos a partir do ângulo real do
  virabrequim (captura uma vez no modelo intacto; contas no espaço da raiz do modelo). Os antigos `FePiston_*`
  senoidais saíram do motor (o contrato `FePiston` continua para as outras máquinas).
- Cinemática validada no Blender (erro 0 nos 4 ângulos). DLL compila, bundle gera. **Não verificado no jogo**: seção 15.

## 2026-11-24: Condensadora realista, máquinas de processo e Prensa de Munição HD

- Condensadora refeita como condensador a ar (núcleos aletados, ventilador, coletores, tambor com visor de nível,
  visor de fluxo, manômetro). `CondenserVisual`: ponteiro `FeNeedle` (vapor); o nível é uma coluna num visor.
- Biodigestor (campânula flutuante), Biodigestor Industrial, Secador a Vapor (tambor rotativo), Misturador Químico
  (tanque aberto com agitador âncora), Lavadora (trommel com spray) e Prensa de Munição (alimentadores, mini-esteiras).
- `FxVisual`: `FeWorkSpin_*`, `FeSurface_r*_[Spin]`, ponteiros `FeNeedle_*`, gotas/spray/bolhas, tocha do biogás,
  cores do mosto / calda / água de lavagem; `MachineVisual`: mini-esteiras `FeTrack_n_P*` + `FeTrackItem_n_*`.
- FeBuild: presets Drip/Spray/Bubbles; `FeSurface`/`FeTrackItem` fora do collider. Bundle 45 MB. Jogo carrega (15:03).
  **Não verificado no mundo**: `TESTE_GERAL.md` seção 16.

## 2026-11-24: barra de atalhos travada depois do livro de receitas

- Relato: depois de mexer na Lavadora e abrir "Receitas", a barra não trocava mais de slot (nem pelo número).
  Log da sessão 15:04: janela aberta normalmente (`recipe book feWasher ... window=True`), sem exceção.
- Causa provável (IL 3.4.0): o comando roda dentro do callback do menu radial; abrir uma janela modal ali fecha o
  radial à força no meio do fechamento dele, e a transição do item na mão (`Hand.isSwitching`) pode ficar presa.
  `PlayerMoveController.Update` só troca de slot com `canSwapHeldItem()` = mão sem transição.
- Correção (`RecipeBook.cs`): a janela abre alguns quadros depois, quando não há janela modal aberta (como o jogo faz
  com baús/bancadas); ao fechar, um vigia conclui uma transição da mão ainda presa depois de 1 s
  (`Hand.CompleteTransition`, com aviso no log). **Não verificado no jogo.**

## 2026-11-24: rede de torque parada ao carregar, pendências de arte e desempenho

- **Bug (usuário):** ao iniciar o mundo a rede ficava parada até isolar com a embreagem o Motor Elétrico Industrial
  e o Dínamo Industrial. Log 15:20: `sources=2 ... 4018/2048 UT OVERLOAD`. Impasse: o dínamo só gera com a rede
  rodando, a rede só roda sem sobrecarga, e o motor elétrico (alimentado por esse dínamo) só soma capacidade com
  energia. Correção: **inércia de partida** (`TorqueNet.Grace`, `Kinetic.GraceSeconds` = 20 s): uma rede que entra em
  sobrecarga continua girando 20 s antes de parar (tempo do dínamo ligar o motor); sobrecarga real para depois disso e
  só tenta de novo quando a carga cai. Texto de foco "PARTINDO (inércia)"; log no início e no fim do episódio.
- Modelos próprios (HD) e ícones: Motor a Carvão (cilindro vertical + virabrequim, fornalha, chaminé), Motor a
  Gasolina (monocilíndrico horizontal, dois volantes), Baú de Esteira (caixote de ferro com 4 entradas de esteira),
  Manivela (texturizada), Gerador a Carvão (HD no bundle, `MultiBlockDim 2,2,1`, ponto de fio pelo `FeBuild.WireFallback`,
  virabrequim e dínamo giram enquanto queima). O ícone do Gerador a Carvão estava quebrado (PNG apagado, propriedade
  ficou) — corrigido.
- Braço do cano na entrada de vapor da Condensadora: já resolvido (log 15:20 `port=True arm=shown` na célula filha).
- Desempenho: `HasPortAt` sai cedo em célula de ar (antes varria todos os equipamentos de fluido por braço de cano a
  cada 0,5 s); `FxVisual` dorme a mais de 45 m da câmera e só reenvia cor/emissão quando muda; diagnóstico dos canos
  só com `Verbose`.
- Bundle 52 MB; jogo carrega (15:59). **Não verificado no mundo**: `TESTE_GERAL.md` seção 18.
- **Pegue e coloque de novo** os Geradores a Carvão já colocados (agora ocupam 2×2).

## 2026-11-24: peças piscando, cadinho da Fundição, molde piscando

- Relato com prints: peças piscando com o movimento (Caixa de Transmissão, Torno, Motor a Vapor...), cadinho "sem
  nada" com faíscas, metal piscando ao encher o molde.
- Piscar = z-fighting: primitivas montadas rentes tinham faces no mesmo plano (nervuras cruzadas, chapas sobre
  chapas). `build_feHD.py`: cada box/cyl/ring cresce uma folga determinística diferente (0..4,8 mm, no máx. ¼ da menor
  medida). Os 32 modelos HD reconstruídos e rebakeados; ícones refeitos.
- Cadinho: era um cilindro tampado escondendo o metal. Agora panela aberta com revestimento refratário, metal
  incandescente com escória e a tampa levantada num braço giratório; faíscas no lado descoberto.
- Molde: `FeCastMetal` 4 mm acima da areia (não coincide no começo do enchimento) e o jato fica visível 0,8 s depois
  do último fluxo (a rede de fluidos move o metal em passos; antes o jato piscava).
- Bundle 52 MB; jogo carrega. **Não verificado no mundo.** (O Gerador a Carvão e a Manivela vêm de scripts antigos e
  não ganharam a folga.)

## 2026-11-24: proposta D12, cadeia completa (PLANO_CADEIA.md)

- Pedido do usuário: todos os itens do jogo pelo mod, borracha da seiva até o pneu, refinaria de petróleo, tanques,
  gases com pressão, válvulas, menus próprios, comida numa máquina simples.
- `PLANO_CADEIA.md`: cobertura das 600 receitas (`craft_matrix.py`: 448 ganham cadeia, 152 ficam), 17 itens que o
  jogo só dá por loot/desmanche com rota nova, fluidos 2.0 (líquido/gás, bar, tanques que se juntam, 6 válvulas),
  passagem nas esteiras, 5 janelas XUi, cadeias por grupo, 49 blocos novos, fases F9.0–F9.11, decisões D12-1..11.
- Só proposta: nada aplicado. Esperando o usuário.

## 2026-11-24: esteira baixa (modelo nosso no lugar do modelo alto da D10)
- Usuário prefere a nossa esteira (`Art/feConveyor`). `build_feConveyor.py` refeito: um modelo `feConveyor` com
  todas as formas que o `BeltShape` usa (reta, curva L/R, divisão, batente, trilhos) + `feConveyorRamp` e
  `feConveyorDown`, todos com a lona a 0,175 m (altura das portas das máquinas, sem calha).
- `Belt.Top` 0,62 → 0,18. Tração nova: `FeBeltDrive_L/R` + `FeSpin_BeltDrive_L/R` (mancal na altura do eixo e
  corrente), mostrados só no lado onde encosta um bloco de torque (`BeltShape.ApplyDrive`).
- Removidos: `Art/feConveyor/hd` (HD do modelo antigo), `feConveyor_HD.mat`, `feConveyorCorner.fbx`.
  `export_feKinetic.py` e `render_icons.py` (feKinetic) não exportam nem desenham mais as três esteiras e o ícone
  da Esteira com Filtro; os ícones vêm de `Art/feConveyor/render_icons.py`. Colisor ignora a tração (FeBuild).
- Pendente: bico do Funil e rampa do Duto ainda a 0,62 m; teste no jogo.
- Teste do usuário: esteira não entrava em cima do Suporte (o colisor do berço invadia 9 cm a célula de cima;
  `GameUtils.IsColliderWithinBlock` recusa). FeBuild corta colisores na face da célula quando passam < 0,15 m.
- Pedidos seguintes: esteiras lado a lado viram uma esteira larga (`FeBeltFill_L/R`); Suporte de Esteira nosso
  (`ConveyorStand.cs`, classe `FeConveyorStand`) com forma reta, curva L/R, divisão e berço de Duto, seguindo a esteira
  de cima; pré-visualização real ao colocar (`BeltPreviewPatch`, Harmony em `RenderDisplacedCube.update0`, com
  `Belt.SetVirtual` para a vizinhança enxergar a esteira que ainda não existe). `BeltShape` dividido em `BeltLook`
  (cálculo) e `BeltParts` (peças). HD antigo do Suporte removido; `build_feHD.py` não gera mais o Suporte.
## 2026-11-24: D12 aplicada (cadeia completa, sem modelos novos)

- Pedido: "faça tudo de uma vez, mas não precisa fazer os modelos 3D". Fases F9.0-F9.11 do PLANO_CADEIA.md em código e
  dados; os blocos novos reusam modelos do mod (ícone = ícone do modelo com tinta). Tamanhos 1x1.
- C#: `Processes.cs` (2 fluidos de entrada, 3 de saída, subproduto com chance, pressão mínima, calor, registro de
  fluidos `<fluid class item per>`); `ProcessMachine.cs` reescrito (entradas atrás/embaixo, saídas em cima/direita/
  esquerda, torre de destilação com seções, liga/desliga, produtos em `FluidState.Out`, colunas novas no
  fluids.txt: Tanks, Out, Off); `FluidNetwork.cs` (gás com bar: tanques de gás, pressão das fontes, cano FeMaxBar
  4/12, vazamento; tanques encostados dividem o conteúdo); `FluidControl.cs` (Registro, Retenção, Reguladora,
  Separador, Alívio, Compressor, Manômetro, Queimador a Gás, Sangrador de Seiva); `Signals.cs` (alavanca, receptor,
  manômetro, contador -> registro, comporta, embreagem; `ForgedInAshes_logic.txt`); `Logistics.cs` (divisor,
  comporta, contador, Braço Mecânico); `Inline.cs` (estações sobre a esteira); `AutoCraft.cs` (baús ligados até 16,
  escolher receita); `FeUi.cs` + `tools/gen_ui.py` (Painel da Máquina, Seletor de Receita, Configurações, Painel de
  Rede, Guia de Produção, Manual e Chave de Engenheiro); `Settings.cs` (`Data/fe_settings.xml`, fallback x3).
- Dados: `tools/gen_chain.py` -> 97 itens, 55 blocos (incl. Seringueira em 5 estágios), 164 processos (Cozinha
  Industrial gerada das receitas da fogueira x4), 85 receitas, 222 receitas do jogo com peças da cadeia, 10 remoções
  de atalho. `tools/check_coverage.py`: 559/559 itens do jogo ainda fabricáveis, 16/16 itens só-loot com rota.
- Validadores: check_xpath 773/0, check_processes 205/0, check_phase3 23/23, check_coverage 0 faltando. DLL compila.
- Teste do usuário (log 19:16): spam de `NullReferenceException` no binding `fetitle` do fePicker (o jogo pede os
  bindings ao carregar, sem mundo) e `XUiV_TextList.Cleanup` ao sair (o `<textfield>` numa janela do mod).
  Corrigido: bindings protegidos (vazios sem mundo / em erro) e busca por texto trocada por filtro de letra.
  **Não verificado de novo no jogo.** Roteiro: `TESTE_GERAL.md` seção 19.
- Limites conhecidos: sem modelos (tudo 1x1); Queimador não aquece a Fundição (ela segue com combustível); moldes da
  vulcanização viraram escolha de receita; números são proposta para o balanceamento; multiplayer depois.

## 2026-11-24: bug do texto de mira sumindo (e E pegando o bloco)

- Relato: depois de um tempo o texto de mira e o "(E)" somem em todos os blocos e o E pega o item.
- Log 19:29 sem exceção. Leitura do jogo (IL 3.4.0 b10): `PlayerMoveController.Update` só mostra o texto quando
  nenhuma janela modal está aberta (`guiOpenThisUpdate = IsModalWindowOpen`); a roda do E (`radial`) é modal. As
  janelas do mod abrem logo depois de um comando da roda e, depois de 1,5 s (90 quadros), abriam à força com a roda
  ainda fechando: a roda podia ficar registrada como aberta e escondida, o que esconde todo texto de mira e faz o
  toque no E executar o primeiro comando (Pegar).
- Correção: as janelas esperam até 5 s a roda fechar e desistem em vez de forçar; `UiWatchdog.cs` fecha uma roda
  escondida que ficou aberta sem o E apertado por 1,5 s e registra no log (`ui watchdog: ...`); também registra
  quando o jogador mira um bloco fe* e a janela do texto está fechada (diagnóstico de outra causa).
- **Não verificado no jogo.** Se voltar a acontecer, o log dirá qual janela segurou o texto.

## 2026-11-24: esteira do Harrison texturizada + modelos próprios para os 50 blocos do D12

- Pull do colega (esteira reimaginada, baixa: lona a 0,175). `Art/feConveyor/split_for_hd.py` separa o
  `feConveyor.blend` dele em um `_src.blend` por bloco (feConveyor, feConveyorRamp, feConveyorDown,
  feConveyorStand), nomes mantidos (Belt.cs e ConveyorStand.cs acham as peças pelo nome). Texturizados no tema
  7DTD (`F:\IA\fe_blender\configs\feConveyor*.json`: ferro pintado, ferrugem, aço, borracha nova (textura
  `borracha`), pintura laranja gasta).
- Os 50 blocos do D12 deixaram de reusar modelos de outras máquinas. `Art/feHD/build_feHD.py` (`D12_MODELS`) faz um
  modelo para cada um seguindo o contrato da função dele:
  - Válvulas / Compressor: entrada atrás (verde), saída na frente (laranja), Registro com volante e fio
    (`WireOffset`), Alívio com chaminé de alívio (`FeFx_Steam_1`), Reguladora e Compressor com manômetro
    (`FeNeedle_*`), Manômetro com mostrador grande e lâmpada de sinal (`feHD_Glow`).
  - Tanques: Líquido (bocais nas 4 faces, coluna de nível `FeSurface_r0.70_Level`), Gás (cilindro deitado, faixas,
    manômetro `FeNeedle_Bar`).
  - Queimador (chama `FeFx_Fire_1`, brilho), Sangrador (costas na árvore, gotejar `FeFx_Drip_1`, látex no balde,
    saída na frente), Torre (base com fornalha + seção empilhável com saídas nos 4 lados e escada).
  - 20 processadores: entrada atrás a 0,5, calha baixa na frente para a esteira nova (0,24), eixo de torque de lado
    (`FeSpin_DriveShaft`) nos que usam torque, fio nos elétricos; partes animadas: rolos da Calandra, mó do
    Moinho, fusos da Fiadeira, carretel e mandril da Enroladeira, rotor da Centrífuga, pá do Tanque de Coagulação,
    prato da Prensa de Suco e da Vulcanização (`FePiston`), superfícies de líquido (tanino, óleo de têmpera,
    panelas), Injetora com `FeCastMetal` / `FeCastReady` como a Mesa de Moldagem.
  - Estações em linha (ficam no bloco de cima da esteira): pórtico com pernas até o chão da esteira
    (`FeReach_*`), ferramenta que desce (`FePiston_Inline*`), rebolo da Esmerilhadeira (`FeSpin_x6_InlineWheel`,
    faíscas), tocha da Soldadora, capô aquecido do Forno de Refusão. FeBuild deixa `FeReach`, `FePiston_Inline`,
    `FeSpin_x6_Inline` fora do colisor (não invadem o bloco da esteira).
  - Divisor / Comporta / Contadora: a esteira do Harrison + peças nossas (`FeBeltExtra_*`, fora do colisor). A
    aba da Comporta (`FeLever_BeltGate`) desce quando segura os itens.
  - Braço Mecânico (torre `FeArmYaw` que gira de trás para a frente), Alavanca de Sinal (`FeLever_Signal`),
    Receptor (lâmpada), Motor a Gás (o motor a gás com dois cilindros de gás).
  - Materiais novos: `feHD_Red` (volantes, cilindros) e `feHD_Leather` (couros).
- `blocks.xml`: os 50 apontam para `<bloco>Prefab`; ícones próprios (`render_icons_hd.py`, `apply_icons.py`).
- Seringueira (5 estágios) continua com as árvores do jogo (é planta, não máquina).

## 2026-11-24: fita da esteira que anda, barramento HD, fio no Dínamo Industrial

- Relato (print): a animação da esteira era só traços (as travessas `FeBeltSlats` deslizando 0,125 m) sobre uma
  lona parada. Agora a lona inteira anda: `Art/feConveyor/split_for_hd.py` dá às faces de borracha (FeBeltBed,
  FeCurveSet_*, FeBeltFill_*, base das rampas) o material `feBelt_Band` e um UV próprio (`BandUV`: u = largura,
  v = ao longo do percurso, 1 repetição = 0,25 m; em volta dos tambores e pelo arco da curva). As travessas soltas
  saíram (as nervuras em V estão na textura). `Art/feFx/make_belt_band.py` gera a textura repetível (borracha gasta,
  nervuras em V, poeira, riscos) e o normal map. Texturizador: `materiais_uv_proprio` mantém esse UV.
  FeBuild: material `FeBeltBand`. `BeltShape` rola `_MainTex_ST` só nesse submesh, na velocidade da esteira
  (rampa x1,41 ao longo da inclinação).
- Barramento (`feBus`): modelo HD novo (`model_bus`): armário de manobra rebitado, 3 barras de cobre em isoladores,
  isoladores de entrada atrás, isolador grande de saída na frente (WireOffset), disjuntor, amperímetro, placa de perigo.
- Dínamo Industrial não ligava no barramento. Causa (IL 3.4.0 b10): `ItemActionConnectPower.OnHoldingUpdate` usa
  a célula mirada como está; numa célula filha de um bloco grande (o dínamo é 3x2x3) `GetPoweredBlock` CRIA um
  tile entity de energia novo ali, e o fio ia para esse fantasma. `WireMultiblock.cs`: com o alicate na mão, a mira
  numa célula filha de um bloco fe* elétrico vai para a célula pai; fantasmas de tentativas antigas são removidos
  quando o alicate mira a célula (log `wire tool: removed a stray power tile entity`). Vale também para o Gerador a
  Carvão (2x2x1).
- Jogo abriu o mundo com a DLL nova (Player.log 21:17: `Harmony: 38 method(s) patched`, sem erro do mod).
  **Não verificado no jogo:** a fita andando e o fio no dínamo.

## 2026-11-24: curva e esteiras lado a lado (print do usuário)

- Montagem: linha para leste terminando numa curva para o sul; ao lado da saída da curva, outra esteira para o sul
  (até uma máquina). Causa: `Belt.Outputs` conta como saída a esteira ao lado que aponta para fora, então a célula
  antes da curva virou divisão (leste + sul) e era desenhada como mesa de junção; e as duas faixas para o sul foram
  fundidas numa esteira larga (`FillL/R`), embora uma saia da curva e a outra da divisão.
- `BeltLook`: divisão com frente + um lado = esteira reta + a curva daquele lado (`SplitL/R`), sem a mesa; a curva
  fica 3 mm acima da reta (sem piscar). O guarda-corpo externo da curva virou peça própria (`FeCurveRail_L/R`,
  `split_for_hd.py`) e só aparece na curva normal, para não atravessar a reta.
- Esteira larga só junta faixas que são linhas próprias (`OwnLane`: atrás não há esteira, ou a de trás corre no
  mesmo sentido). Faixa que nasce de curva ou divisão fica separada, com o guarda-corpo dela.
- **Não verificado no jogo.**

## 2026-11-24: junções viram curvas, sem esteira larga (segundo print)

- Pedido: "quando duas esteiras estão juntas elas têm a animação de uma única esteira: remova" e as junções devem
  ser suaves (curvas). A esteira larga (`FillL/R`) saiu: duas esteiras lado a lado são duas esteiras, cada uma com
  sua lona e guarda-corpo.
- Divisões sem mesa de junção: frente + um lado = reta + curva daquele lado; os dois lados (T) = duas curvas em Y;
  frente + os dois lados = reta + duas curvas. As lonas que se sobrepõem ficam 3/6 mm acima uma da outra; o
  guarda-corpo externo da curva só aparece na curva simples. Saída para rampa de descida conta como frente.
- **Não verificado no jogo** (render de conferência do Y no Blender).

## 2026-11-24: rampa de descida longe do bloco; diagnóstico das junções

- Rampa de descida aparecia a 3 blocos do lugar (print). Causa: `build_feConveyor.py` põe as peças lado a lado em X
  para exibição (rampa 1,6; descida 3,2; suporte 4,8) e o `export_feConveyor.py` dele as devolve ao centro; o
  `split_for_hd.py` não devolvia. Corrigido (tabela `OFFSET`); FeBuild agora mostra os colisores centrados.
  O suporte (feConveyorStand) tinha o mesmo erro (4,8 m).
- Junções marcadas em azul ainda sem curva no jogo (DLL nova carregada às 21:55, mas a esteira larga já tinha
  sumido). No save, as faixas curtas (-232/-236, 61, 842..843 → fundições em z 844) têm na célula de trás um registro
  de funil (`F;-232;61;841`, `F;-236;61;841`). Para não chutar: `BeltShape` registra uma linha por mudança de visual
  (`belt look <bloco> at <pos> front .. left .. exits[..] -> mode .. split ..`, até 600 por sessão).
- Log das 84 esteiras (22:11) mostrou o contrário do suposto: as linhas ENTRAM pelos lados da esteira central
  (-232, 61, 856, indo para +z até a máquina) e as faixas curtas entram de lado na linha. Não eram divisões, eram
  uniões. Novo: `BeltLook.MergeL/R` (um vizinho de lado entrega nesta esteira) e `BackFed`. O modelo ganhou
  `FeMerge_L/R` (a curva do outro lado girada 180°, lona com v invertido: corre do lado para a frente) e
  `FeMergeRail_L/R`. Reta + união(ões) quando há entrada por trás; só a(s) curva(s) de entrada quando não há.
  Render de conferência ok. **Não verificado no jogo.**

## 2026-11-25: ferramenta única (fe.bat / tools/fe.ps1)

- Pedido: um script para recompilar os modelos alterados no Blender, gerar os ícones e compilar/instalar o mod.
- `fe.bat` (duplo clique = menu) chama `tools/fe.ps1 [estado|modelos|icones|mod|tudo] [-Modelos a,b] [-Forcar]
  [-Copiar] [-Simular]`:
  - modelos: `_HD.blend` mais novo que o `_HD.fbx` -> reexporta o FBX (`tools/blender_export_hd.py`, mesmas opções
    do texturizador); `_src.blend` mais novo -> `F:\IA	exturizar.bat <config>` (os dois mudaram: vale o `_HD.blend`,
    com aviso); `feKinetic.blend` mais novo que os FBX da lista do `export_feKinetic.py` -> reexporta; FBX/texturas
    mais novos que o bundle -> Unity `FeBuild.BuildAll` (mostra os erros do febuild.log se falhar).
  - icones: ícone mais velho que o `_HD.blend` -> `render_icons_hd.py` + `apply_icons.py`.
  - mod: os 4 validadores, `build.ps1`, `install.ps1` (link; `-Copiar` = cópia); avisa se o jogo/Unity estão abertos.
- Testado: `tudo` de verdade (3 esteiras retexturizadas, Unity, 3 ícones, mod) em 105 s; antes: estado, simulação,
  ícone do Funil, passo do mod, reexportação do
  feCrusher para uma pasta temporária (FBX igual ao original). Correção: o `texturizar.bat` via `cmd /c` quebrava as
  aspas; agora o Blender roda `texturizar_pbr.py` direto. Bundle 98,3 MB (perto do limite de 100 MB do GitHub).

## 2026-11-25: D13 - "um Create com pé no chão" (sem modelos)

- Pedido: terminar código e lógica (sem lava, sem caldeira modular, motor a vapor simples mas montado peça por peça,
  trens e multiplayer depois, modelos em outra sessão).
- C#: `WorldMachines.cs` (Furadeira, Serra, Colheitadeira, Aplicador, Pistão Mecânico + `fePistonHead`, Ventilador
  com lavar / aquecer / empurrar), `ItemTransport.cs` (Calha Vertical com subida por ventilador, Depósito com estação
  em cima, Cofre Modular em conjunto, Túnel de Esteira), `MachineItems.cs` (item visível nas máquinas, `FeHead_*`
  descendo), `Display.cs` (Painel Numérico com TextMesh), engrenagens (`KineticKind.Cog`, encaixe lado a lado inverte
  o giro), moinho (`FeWind` na roda d'água: altura livre e ar na frente), Polia de Mangueira (`FeIntakeDepth`),
  sinais analógicos (0-15, reguladora) e sem fio (frequência = item), guia "Como ligar". `build.ps1 -Out` compila em
  outro lugar (o jogo aberto trava a DLL).
- Dados (`gen_chain.py`): 19 blocos novos, processos do Ventilador e do Dreno de Itens, receitas das 16 "Peças"
  (armas, ferramentas, armadura, robótica) que só vinham de loot, motor a vapor com 9 peças novas.
  `check_coverage.py` agora cobra todo ingrediente `*Parts`. Validadores: xpath 774/0, processos 223/0, regras 23/23,
  cobertura 0 faltando.
- **Bug evitado:** o `gen_chain.py` reescrevia os blocos D12 com os modelos emprestados e desfazia os 50 modelos
  próprios feitos em outra sessão (que editou o `blocks.xml` direto). Agora o gerador usa `<bloco>Prefab` quando
  existe `Art/<bloco>/hd/<bloco>_HD.fbx` e o ícone próprio quando existe o png.
- `PENDENCIAS_ASSETS.md` (gerado por `tools/list_assets.py`): 15 blocos novos sem modelo, 106 itens sem ícone
  próprio, contratos de nomes por tipo de bloco, sons e partículas que faltam.
- Compilado (fora da pasta do jogo, que estava aberto). **Não instalado nem testado no jogo:** `TESTE_GERAL.md` 20.

## 2026-11-25: pendências de assets (PENDENCIAS_ASSETS.md) com a IA local

- **Ícones dos itens (106) e das Seringueiras (5):** feitos pelo SDXL local (F:\IA, ComfyUI), sem modelar no Blender
  e sem gastar tokens. `Art/feIcons/prompts.txt` (item | descrição em inglês | seed) + `tools/gen_item_icons.py`:
  o SDXL desenha o objeto sobre fundo "chroma" (verde; magenta para itens verdes), a cor do fundo é medida na
  borda da imagem e a região parecida ligada à borda (sombras incluídas) é cortada, mais o fundo preso em furos;
  recorta, centraliza e reduz para 160×160 transparente. As imagens grandes ficam em `F:\IA\saida\icones` (para
  refazer só o recorte: `--recut`; refazer um item: `--only feTire` e outra seed no prompts.txt).
  (rembg/U²-Net foi tentado, mas instalar pacote foi bloqueado: ficou o recorte por cor.)
- **19 blocos do D13** com modelo próprio (`build_feHD.py`, `D13_MODELS`), cada um no contrato da função:
  Furadeira (broca `FeSpin_x2_Bit` na frente, poeira), Serra (disco `FeSpin_x3_Blade`), Colheitadeira (molinete
  `FeSpin_x0.5_Reel` + barra de corte), Aplicador (`FeHead_Ram`, `FeItemAnchor`), Ventilador (pás `FeSpin_x4_Blades`
  num anel com grade), Pistão Mecânico + Cabeça de Pistão (placa + haste), Engrenagem (`FeSpin_Cog`, dentes até as
  faces), Moinho de Vento (nacele, eixo atrás, pás `FeSpin_WindSails` fora do colisor), Polia de Mangueira (carretel
  `FeSpin_x0.3_Reel`, mangueira `FeReach_Hose` descendo), Depósito (tampo a 0,82, `FeItemAnchor`), Calha Vertical
  (tubo fechado empilhável), Cofre Modular, Dreno de Itens (bacia `FeSurface`, cano em cima, calha baixa),
  Painel Numérico (face escura na frente, onde o DisplayVisual escreve), Alavanca Analógica (quadrante 0..15,
  `FeLever_Analog`), Transmissor (antena) e Receptor (antena parabólica) sem fio, Túnel de Esteira (a esteira nova
  com cobertura e janelas de filtro). Eixos de lado (`FeSpin_DriveShaft`) nos de torque com eixo X.
- Ícones: 111 gerados; 28 refeitos com outra seed / descrição mais firme (placas de circuito viravam textura, a sola
  virou botas, sobrava "chão" atrás de alguns), 6 com o recorte tolerante (`--loose`). Ícones dos 19 blocos
  renderizados dos modelos (`render_icons_hd.py`).
- `gen_chain.py` passou os 19 blocos para `<bloco>Prefab` sozinho (existe o `_HD.fbx`); `list_assets.py`:
  **0 blocos e 0 itens pendentes**. Validadores ok (check_xpath 774/0, phase3 23/23, coverage 0).
- Pacote: 120 MB passava do limite de 100 MiB por arquivo do GitHub. FeBuild agora importa os mapas
  `_MetallicSmoothness` a 512 px (os outros seguem até 2048): 91,7 MB.
- **Não verificado no jogo.** Sons e partículas novas (vento, serragem) seguem em "Outros assets".

## 2026-11-25: usina termelétrica modular; Motor a Vapor restaurado

- Correção de entendimento: o Motor a Vapor continua o motor simples e barato (quebra-galho); a receita original
  voltou (Garagem: 2 pistões, 6 volantes, 30 chapas, 10 engrenagens, 6 lubrificantes, 6 canos).
- Nova **usina** (`SteamPlant.cs`), montada do tamanho que o jogador quiser: **Fornalha de Caldeira** (queimador
  grande: itens ou gás) encostada em **Tambores de Caldeira** (água nos lados, vapor a 4 bar em cima; cada fornalha
  acesa encostada ferve 90 L/min, até 180 por tambor; tambores encostados são uma caldeira só) -> canos de vapor ->
  **Turbinas a Vapor** (fonte de torque: até 1024 UT com 240 L/min, gasta vapor conforme a carga, vapor usado sai na
  frente para a Condensadora) -> **Dínamos** no mesmo eixo para eletricidade. As peças feitas na D13 (corpo de
  caldeira, fornalha, válvula de segurança, manômetro, carcaça, regulador, rotor novo) montam esses blocos.
- `gen_chain.py` também usa o ícone próprio dos itens quando o png existe. **Não testado no jogo.**

## 2026-11-25: modelos da usina termelétrica (commit 422298f, outra sessão)

- `build_feHD.py` (`PLANT_MODELS`), no contrato do `SteamPlant.cs`:
  - Fornalha de Caldeira: fornalha de tijolo com cintas de ferro, porta com grelha e brasa (`feHD_Glow`, fogo e
    fumaça pelo caso Burner do FxVisual), cinzeiro, gás entrando atrás, tampo de ferro onde o tambor assenta.
  - Tambor de Caldeira: tambor rebitado deitado em X com flanges nas pontas (tambores encostados emendam num
    corpo só), bocais de água na frente / atrás, domo e saída de vapor em cima, válvula de segurança
    (`FeFx_Steam_1`), visor de nível (`FeSurface_r0.50_Level`) e manômetro (`FeNeedle_Steam`).
  - Turbina a Vapor: carcaça bipartida no eixo X (acoplamentos dos dois lados: várias turbinas num eixo), vapor
    entra atrás pela válvula do regulador, sai pelo escape da frente, regulador de esferas (`FeSpin_x2_Governor`),
    manômetro e vapor de gaxeta.
- FxVisual: casos Boiler (nível = água, ponteiro = vapor, válvula sopra com o vapor acima de 90 %) e Turbine
  (ponteiro = vapor de entrada, vapor de gaxeta enquanto gira).
- Pacote 94 MB. Pendente: ícone do item `feTurbineRotor`. **Não verificado no jogo.**

## 2026-11-25: modelos D13 e da usina integrados; limpeza de assets

- Commit dos modelos HD dos 19 blocos D13 e dos 3 da usina, dos ícones dos itens (SDXL local) e do bundle (89,7 MB).
- Removidas as pastas de modelos antigos sem uso (nem no FeBuild nem em blocks.xml): `Art/feCharcoalKiln`,
  `Art/feFoundry`, `Art/feLathe`, `Art/fePress`, `Art/feSawmill` (protótipos da fase 1, substituídos pelos
  `feM_*` do feKinetic) e `Art/feFlywheel` (modelo do item, não usado). Ícones, materiais e prefabs: todos em uso.
- Pendente de arte: só os ícones da Seringueira (5 estágios) e 1 item (`PENDENCIAS_ASSETS.md`).

## 2026-11-25: últimos assets pendentes (Seringueira e Rotor de Turbina)

- Seringueira (5 estágios): os PNGs existiam, mas `gen_chain.py` (`tree_xml`) recriava os blocos sem `CustomIcon`
  a cada execução, e a pendência voltava. Agora ele usa o ícone próprio quando o PNG existe (como `block_xml`).
  O ícone do estágio 08 tinha uma faixa de fundo: novo recorte, guardando só as formas grandes (as folhas).
- Rotor de Turbina (`feTurbineRotor`): modelo só para o ícone (`ITEM_MODELS` em `build_feHD.py`: eixo, três rodas
  de palhetas crescentes com aro, mancais e flange de acoplamento), texturizado e renderizado como os blocos.
- `list_assets.py`: **0 blocos e 0 itens pendentes**. check_xpath 773/0, phase3 23/23.

## 2026-11-25: site de tutoriais refeito (React + 3D, páginas geradas dos dados)

- `site/` agora é um app Vite + React 19 + react-router + three/@react-three/fiber (Vercel: raiz `site`,
  `npm run build`, saída `dist`, rewrite SPA em `vercel.json`). O site estático antigo (`itens/`, `maquinas/`,
  `linhas/`, `app.js`) saiu.
- Nenhuma página por item: `tools/gen_site.py` gera `site/public/data/mod.json` (itens, receitas, processos,
  fluidos, linhas em destaque, indicadores) e copia os ícones do mod; o front monta sozinho, para qualquer item,
  a árvore de produção, o passo a passo em ordem, as máquinas e a matéria-prima (`plan()` em `src/data.js`).
  Só os guias de conceito (`src/guides.js`, sintaxe `[[id]]` vira chip com link) são escritos à mão.
- Modelos 3D: `tools/blender_export_glb.py` exporta os `_HD.blend` como GLB (texturas 512 px JPEG, partes de
  estado ocultas), 110 modelos, 26 MB. Só modelos e ícones do próprio mod (nada do jogo).
- Páginas: início (vitrine 3D), linhas (quantidade ajustável), máquinas, catálogo com filtros, item (3D + como
  ligar + como fazer + linha completa + usado em), guias, indicadores (gráficos) e busca Ctrl+K.
- `fe.bat site` (`tools/fe.ps1`, opção 5): GLB dos modelos alterados + `gen_site.py` + `npm run build`.
- Corrigido: o spinner `Html` do drei dentro do Canvas causava `removeChild` ao trocar de página (removido).

## 2026-11-26: texto ao olhar sumia sem janela aberta (Motor a Vapor)

- Log 00:06-00:08: `ui watchdog: looking at feSteamEngine ... but the look-text window is closed`, sem janela modal.
- Causa (IL 3.4.0 b10, `PlayerMoveController.HandleInteraction`): o jogo só chama `XUiC_InteractionPrompt.SetText`
  quando o texto difere do cache `strTextLabelPointingTo`. Se a janela é fechada por fora com o mesmo texto em cache
  (motor parado, leitura que não muda), ela nunca reabre até olhar algo com outro texto.
- Correção (`UiWatchdog`): sem modal, sem HUD oculto, janela fechada e cache não vazio → limpa o cache; no quadro
  seguinte o jogo reabre a janela sozinho (no máximo 0,25 s). Loga "reopened it" a cada 30 s no máximo.
- **Não verificado no jogo.**

## 2026-11-26: Motor a Vapor torto; diagnóstico do texto que some

- Teste 00:14: o motor apareceu torto. A edição de 00:04 do `feSteamEngine_HD.blend` deixou `feSteamEngine_Base` com
  rotação X -6° (-0,105 rad) e x +1 cm. Zerados (cópia do arquivo torto no TEMP), FBX e bundle refeitos e ícone
  re-renderizado. A cópia final do bundle pelo Unity falhou (arquivo preso pelo jogo fechando); copiado à mão.
- O texto sumiu de novo, mas o log não teve nenhuma mensagem do vigia (nem "reopened", nem "window is closed"):
  a mira provavelmente não acertava o bloco (colisor torto?). Novo diagnóstico em `UiWatchdog`: se o texto de um
  bloco "fe" sumir menos de 2 s depois de aparecer, loga o que o jogo vê (acerto, tag, bloco, distância, cache).
- **Não verificado no jogo.**

## 2026-11-26: causa do texto ao olhar que some: distância de ativação de 2 m

- Diagnóstico novo (log 00:22): `look text gone right after feGasEngine (hit ... terrAsphalt ..., dist 5.35)`.
- IL 3.4.0 b10: `TryHandleBlock` só gera o texto (e o E) se `hit.distanceSq < Block.GetActivationDistanceSq()`, e um
  bloco sem `ActivationDistance` usa `Constants.cCollectItemDistance` = **2 m**. Nenhum bloco do mod definia: bastava
  dar um passo para trás de uma máquina (o Motor a Vapor tem 3x2x3) para o texto sumir.
- Correção (fim de `blocks.xml`, depois da região do gen_chain): todos os blocos `fe*` com `ActivationDistance` 4
  (o alcance de construir); os com `MultiBlockDim` (20) com 5. check_xpath 775/0.
- **Não verificado no jogo.**

## 2026-11-26: texto ainda some no Motor a Vapor: diagnóstico detalhado

- Log 00:27:52: `looking at feSteamEngine at -231, 61, 813 but the look-text window is closed`, sem modal, dentro do
  alcance, com o texto em cache vazio: o jogo calculou texto vazio para o motor.
- IL 3.4.0 b10 (`TryHandleBlock`): o texto só existe se `HasBlockActivationCommands(parentBV, parentPos)` for
  verdadeiro; em `BlockPowerSource` isso é "há `TileEntityPowerSource` na célula pai". Senão cai em `DisplayInfo`
  (nada).
- `UiWatchdog.WhyNoText`: nesse caso agora loga célula, filho/offset, célula pai e bloco, tile entity, distância /
  alcance, `HasBlockActivationCommands` e o tamanho do texto (ou a exceção).
- Próximo teste decide a correção.

## 2026-11-26: sonda no HandleInteraction (texto ao olhar que some)

- Usuário: "acho que os itens do mod em si estejam causando isso". IL 3.4.0 b10 (`PlayerMoveController.Update`):
  antes do bloco, um raio de itens (máscara 73728 = camadas 13 e 16) com tag "Item" vence o bloco se estiver até
  1,2 m atrás dele; com `TPCameraCheckResult == 2` os blocos são ignorados. O vigia antigo só olhava acertos em bloco.
- `LookTextProbe.cs`: postfix em `HandleInteraction`; quando o texto passa de mostrado a vazio com um bloco "fe" na
  mira (ou um item), loga tudo: acerto, tag, bloco e distância, célula interna, acerto de item (nome, raiz, tag,
  camada, distância), checagem de câmera, item na mão e o texto anterior. No máximo 1 linha a cada 10 s.

## 2026-11-26: texto existe mas não aparece (Prensa de Munição)

- Log 00:38:34: olhando `feAmmoPress` a 1,31 m (alcance 5), tile entity ok, `HasBlockActivationCommands` true,
  texto de 158 caracteres, sem modal, janela fechada e cache vazio. Outras linhas da sonda: só fora do alcance.
- IL 3.4.0 b10 (`PlayerMoveController.Update`, início): todo quadro, se `IsCursorWindowOpen()` (janela aberta e
  mostrada com `alwaysUsesMouseCursor`) ou modal ou `playerInput.Enabled` falso (e veículo também) ou
  `bCanControlOverride` falso, o jogo faz `SetText(null)` e zera o cache. Algo deixa uma dessas condições ligada.
- `UiWatchdog.Controls`: o diagnóstico agora loga essas condições e a lista de janelas abertas (mostrada/oculta,
  modal, cursor, actions).

## 2026-11-26: rótulo do texto ao olhar com tamanho fixo

- Log 00:42: com blocos "fe" na mira e dentro do alcance, a janela do texto estava ABERTA (nenhum "window is closed")
  e mesmo assim o usuário não via o texto. Usuário: "será que o texto está subindo até sair da visão?".
- Desde 2026-11-24 o `lblText` do `interactionPrompt` usava `overflow=resizeheight` (pivot center): altura variando
  em tempo de execução. Agora: caixa fixa de 260 px (cerca de 7 linhas na fonte normal, `shrinkcontent` só além
  disso), `pivot=bottom`, `pos=0,-35` (base 20 px acima da mira, a mesma base do original), crescendo para cima.
- `UiWatchdog.LabelGeometry`: a cada 30 s com texto de bloco "fe" aberto loga altura, posição local e na tela,
  visível/alfa/ativo e linhas. `build.ps1` passa a referenciar `NGUI.dll`.
- **Não verificado no jogo.**

## 2026-11-26: projeto renomeado para ForgedInAshes; documentação EN / PT-BR / ES; AGENTS.md

- Nome: "Ferro & Engrenagem" / `FerroEngrenagem` → **ForgedInAshes** (repositório BirdRa1n/ForgedInAshes). Pastas
  `src/ForgedInAshes`, `Mods/ForgedInAshes`, DLL `ForgedInAshes.dll`, namespace e classes XML
  `ForgedInAshes.<Classe>, ForgedInAshes`, Harmony `com.forgedinashes.mod`, prefixo de log `[ForgedInAshes]`,
  pacote `Resources/forgedinashes.unity3d` (`FeBuild.BundleName` também), ferramentas, site e textos.
- **IDs `fe*` de blocos e itens mantidos** (estão nos saves).
- Saves: `ForgedInAshesMod.SaveFile(nome)` usa `ForgedInAshes_<nome>.txt` e renomeia uma vez o
  `FerroEngrenagem_<nome>.txt` antigo (esteiras, fluidos, sinais, autocraft).
- `install.ps1` remove o link/cópia antigo `Mods/FerroEngrenagem` do jogo (senão o mod carregaria duas vezes).
  Reinstalado: junction `Mods/ForgedInAshes`. A DLL antiga `FerroEngrenagem.dll` foi apagada da pasta do mod.
- `ModInfo.xml`: descrição nova e Website = GitHub.
- Documentação: `README.md` (EN, principal), `README.pt-BR.md`, `README.es.md`, `CONTRIBUTING.md`,
  `docs/{en,pt-BR,es}/` (índice, instalação, guia de jogo, solução de problemas, desenvolvimento), arte em
  `docs/assets` gerada por `tools/gen_docs_art.py` só com ícones do mod. Links e âncoras conferidos (0 problemas).
- `AGENTS.md` na raiz e em `src/ForgedInAshes`, `tools`, `Art`, `site`, `docs`.
- Validadores: check_xpath 778/0, processes 223/0, phase3 23/23, coverage 0 sobrando; DLL compila; site compila.
- **Não verificado no jogo** (carregar o mod com o nome novo e um save antigo).

## 2026-11-26: revisão de alimentos e nova verificação dos itens e receitas do jogo

- Alimentos: as 87 comidas/bebidas do jogo conferidas. Toda receita de comida da fogueira continua na fogueira e
  tem lote de 4 na Cozinha Industrial (43 processos); fubá (Moinho), suco de mandioca, gordura (Prensa de Suco),
  água fervida (Cozinha, Ventilador), carne tostada (Ventilador), frascos (Mesa de Moldagem), cerveja (Cozinha).
  Ovos, penas e frango doméstico vêm do galinheiro do jogo (`cntChickenCoop`, fabricado na Cozinha do mod), mel
  do apiário, água dos coletores.
- Lacuna: só 4 dos 14 enlatados eram fabricados. Enlatadora ganhou 6: frango (2 latas + frango doméstico → 2),
  cordeiro (3 carnes cruas), caldo (4 ossos + água fervida), missô (2 cogumelos + água fervida), ração de cão
  (2 carnes podres) e de gato (carne podre + osso), todos com vapor. Ervilha, pera, salmão e atum continuam só
  saque: o jogo não tem ervilha, pera nem peixe.
- `tools/check_reach.py` (novo): fecha o conjunto do que o jogador consegue a partir do mundo (saque, drops,
  colheita de animais, comerciantes, encher recipientes, produção de galinheiro/apiário/coletor) repetindo
  receitas (com estação e ferramenta alcançáveis) e processos (máquina, itens e fluidos alcançáveis). Resultado:
  0 itens fabricados inalcançáveis, 0 ingredientes/estações sem origem, 0 fluidos sem fonte (os `unit_*` da forja
  são internos e ficam de fora). `check_coverage`: 559/559 e 22/22 itens só de saque agora fabricados.
- `gen_chain.py` chama `apply_icons.py` no fim: rodar o gerador não reordena mais as propriedades de ícone.
- **Não verificado no jogo.**

## 2026-11-26: análise de desempenho do código e otimizações seguras

Feito (mesmo comportamento, só menos trabalho; compila, **não medido no jogo**):
- `Dynamo.Is` em cache por id de bloco: `Kinetic.Kind` cai nela para todo vizinho que não é do mod (terra, ar) a cada
  reconstrução de rede de torque.
- `Fluids.Prop` em cache por (id do bloco, nome): `DynamicProperties.GetFloat` reinterpretava o texto a cada chamada,
  e o tick de fluidos chama por dispositivo e por porta 2 vezes por segundo.
- `PortKey` (struct) no lugar da chave em texto `Owner|Cell|Dir|Out` montada para cada porta em cada inundação de
  rede (lixo de memória a cada tick).
- Tick de fluidos: casar as portas de cada rede era `todas as portas × portas da rede` (quadrático); agora dicionário
  por `PortKey`, mantendo a mesma ordem de antes na partilha (`Flow`).

Encontrado e ainda não feito (por prioridade; precisam de teste no jogo):
1. Fluidos: toda rede de canos é refeita do zero a cada 0,5 s (inundação + `Ports()` alocando listas para cada
   vizinho). Guardar a topologia e refazer só quando um cano/dispositivo é colocado, removido ou girado.
2. Torque: o cache de rede expira por tempo (0,5 s) e os `KineticSpinner` perguntam 4×/s, então cada rede é
   reconstruída (BFS com 6 `GetBlock` por nó) cerca de 2×/s mesmo sem mudança. Invalidar por evento
   (colocar/remover/girar bloco de torque; `Invalidate()` já existe para caixa/embreagem).
3. Esteiras (`BeltRenderer.LateUpdate`): todo quadro percorre todas as esteiras do mundo, mede distância e faz
   `GetBlock` nas que têm itens. Manter a lista das esteiras perto do jogador, renovada a cada 0,5 s.
4. Visual dos canos: cada cano refaz 6 consultas de porta + `GetBlock` a cada 0,5 s; pode ser por evento ou a 2 s.
5. Alocações por tick (listas/dicionários novos no tick de fluidos, cópia das chaves no `Belt.Move`, `Ports()`):
   reutilizar coleções para evitar pausas do coletor de lixo.
6. Diagnósticos do texto ao olhar (`LookTextProbe` a cada quadro, `UiWatchdog` a cada 0,25 s): baratos, mas sair
   quando o problema for fechado.

## 2026-11-27: pacote fora do git, pacote em alta qualidade, usina termelétrica refeita

- **Pacote compilado fora do repositório:** `Mods/ForgedInAshes/Resources/forgedinashes.unity3d` saiu do índice
  (`git rm --cached`) e entrou no `.gitignore`, para as texturas poderem ter a qualidade que quisermos. Os jogadores
  baixam o pacote separado (Assets da release no GitHub): `Resources/README.md` explica, e a instalação
  (docs en / pt-BR / es) ganhou o passo. As texturas-fonte em `Art/*/hd` continuam versionadas.
- **Qualidade do pacote (FeBuild):** sem crunch, compressão BC7 de alta qualidade (`CompressedHQ`, qualidade 100),
  até 4096 px (o limite de 512 nos mapas de metal saiu). Pacote: 94 MB → 458 MB (só local).
- **Usina refeita** (`build_feHD.py`, mais detalhe, visual 7DTD, atlas 2048, 64 amostras):
  - Turbina a Vapor: base de vigas I, mancais com tampa, prisioneiros e copo de óleo, carcaça bipartida com
    junta parafusada e **janela de inspeção gradeada** (o rotor de 3 rodas de palhetas aparece girando,
    `FeSpin_x8_Rotor`), engrenagem de giro lento + pinhão engrenado (`FeSpin_BarringGear`,
    `FeSpin_x3.7_Rev_BarringPinion`) com motor, regulador de esferas no mancal (`FeSpin_x2_Governor`),
    **bomba de óleo de êmbolo** (manivela `FeSpin_PumpCrank` + biela + êmbolo pelo solver biela-manivela do
    KineticSpinner), linhas de óleo de cobre, válvula de bloqueio com volante, caixa de vapor com válvula do
    regulador e manômetro, escape com nervuras, vapor nas duas gaxetas.
  - Fornalha de Caldeira: corpo de tijolo em quadro de aço com cintas e rebites, frente de ferro fundido com
    portas duplas, dobradiças, respiros, visor e brasa, gaveta de cinzas, alavanca da grelha, **alimentador
    mecânico** (caçamba com carvão, rosca `FeWorkSpin_x0.6_Stoker` numa calha aberta) e **soprador de tiragem
    forçada** atrás (`FeWorkSpin_x6_Blower` atrás da grade); gás no centro da face de trás.
  - Tambor de Caldeira: revestimento de ripas de madeira com cintas de aço, tampos com rebites e flanges (emendam
    no vizinho), boca de visita com travessa, visor de nível com torneiras e grades, manômetro com sifão, duas
    válvulas de segurança, apito, válvulas de retenção na alimentação, descarga de fundo e **bomba de alimentação
    a vapor** com volante (`FeWorkSpin_x1.5_FeedPump`).
- FxVisual: a fornalha acesa liga `working` (soprador e alimentador giram); a caldeira produzindo vapor liga a
  bomba de alimentação.
- DLL, validadores ok (check_xpath 778/0, processes 229/0, phase3 23/23, coverage 0). **Não verificado no jogo.**

## 2026-11-27: sons das máquinas

- **14 loops originais**, sintetizados por código (`Art/feSounds/make_sounds.py`; sem áudio de terceiros, loops
  sem emenda: ruído montado no domínio da frequência, tons com ciclos inteiros no loop, batidas com ataque de 2 ms
  e fora da emenda): turbina (assobio do rotor + tom das palhetas + vapor + ronco), motor a vapor / a carvão (dois
  bufos e uma batida de biela por volta), vapor escapando, motor elétrico / dínamo (zumbido de rede + harmônicos),
  caixa de engrenagens, britador / moinho, ventilador, bomba, esteira, borbulhas (biodigestor, fermentador),
  furadeira, serra, prensa, zumbido elétrico (forno de indução, soldadora...).
- **Integração pelo sistema de som do jogo** (`MachineSound.cs`): `Audio.Manager.Play(blockPos, grupo)` /
  `Stop(...)`, como a armadilha de lâminas (`BlockBladeTrap.OnBlockUnloaded`, IL 3.4.0 b10). `KineticSpinner`
  (eixo girando) e `FxVisual` (fogo, trabalho, vapor) avisam o estado; o som fica ligado enquanto houve aviso
  "ligado" no último 1,2 s e toca só a até 24 m do jogador (o jogo corta loops distantes sozinho:
  `Audio.Manager.StopDistantLoopingPositionalSounds`). Som por bloco: propriedade `FeLoopSound` ou a tabela por
  prefixo de nome; fogo usa os grupos do próprio jogo (`FireMediumLoop`, `FireSmallLoop`) e o motor a gás o
  `generator_run`, pelo nome (nada do jogo é copiado).
- `Config/sounds.xml`: 14 `SoundDataNode` (fonte `AudioSource_Generators` do jogo: volume das opções, distância,
  mixer), clipes em `forgedinashes.unity3d?<nome>`. `FeBuild.SyncSounds` põe os `.wav` no pacote (mono, Vorbis).
- Jogo abriu até o menu sem erro (Player.log: `Harmony: 39 method(s) patched`, sem ERR/WRN do mod). Validadores ok.
  **Não verificado no jogo** (ouvir os sons num mundo).

## 2026-11-27: plantação por máquina (Torre Hidropônica + Adubo) e Roda d'Água 3x3

- **Torre Hidropônica** (`feHydroTower`, elétrica 60 W, 1x2 blocos): a semente entra por mão, esteira ou braço e
  **fica plantada**; com água por cano (atrás) e energia ela planta, colhe e replanta sozinha, e a colheita sai na
  frente. 13 processos `hydro_*` (milho, batata, mirtilo, cogumelo, abóbora, iúca, algodão, café, solidago, aloe,
  crisântemo, lúpulo, milho da graça; sementes `planted<Planta>1` do jogo), 10 L de água por ciclo, 7 a 12 min.
- **Adubo** (`feFertilizer`): com adubo no estoque o ciclo anda 2,5x mais rápido e gasta 1 por colheita. Feito no
  Biodigestor (`compost`: 4 carne podre + 2 osso + 10 L de água → 4) ou na mão (3 carne podre + 1 osso).
- Processos ganharam `keep` (ingrediente que não é gasto) e `boost` / `boost_speed` (item que acelera e é gasto 1 por
  ciclo): `Processes.cs`, `ProcessMachine.cs` (estoque aceita o reforço, velocidade, consumo); `gen_chain.proc`,
  `check_processes.py` e o site conhecem o tipo `grow`.
- Modelo da torre: bacia, coluna com copos em 4 níveis, gaiola, tubos de luz de cultivo (acesos enquanto cresce,
  `FeGrowLight`), caixa de controle; as plantas (`FeGrow_*`) **crescem com o progresso** e voltam pequenas na colheita
  (FxVisual). Som: borbulhas. Ícones de torre, roda e adubo renderizados dos modelos (sem IA de imagem).
- **Roda d'Água 3x3** (`MultiBlockDim 3,3,1`, origem = célula do meio embaixo): modelo novo (roda de madeira com aros
  cintados, raios, 16 pás, cubo de ferro, cavaletes com mancais). Na rede de torque (`TorqueNetwork.IsMultiWheel`):
  o eixo é a célula do **centro** (1,5 m) e liga nos dois sentidos do eixo; a água conta sob a fileira de baixo e em
  volta dela. Turbina e Moinho de Vento herdam da roda: `Extends param1="MultiBlockDim"` (gerado por `gen_chain`,
  `NO_INHERIT`) para continuarem 1x1. Torque da roda segue 128 UT.
- Validadores ok (check_xpath 779/0, processes 243/0, phase3 23/23, coverage 0, assets 0 pendentes). Pacote ok.
  **Não verificado no jogo.**

## 2026-11-27: D14 máquinas gigantes (Mineradora, Extratora de Petróleo, Tanque de Armazenamento) e trens

Pedido: duas máquinas gigantes que trabalham uma área do tamanho de um chunk, e a lógica de trens (curvas, estações
com nome, cargas de itens e líquidos, passageiros, painel com mapa e rota automática, sem colisão, combustível fóssil,
estação que é armazém e carrega/descarrega). Modelos ficam para a sessão de modelos.

Referência: o mod Ashen Rails (Downloads, 3.3.3.2, Red_Torch_TV) foi só estudado (estrutura: trilho = bloco com
geometria em arco, trem = veículo que segue a geometria). Nada do código nem dos modelos dele foi copiado (código
sem licença declarada; modelos CC BY de terceiros). Tudo aqui é código próprio.

- **Mineradora** (`feMiningRig`, 7x9x7, `FeWorld=miner`, 2048 UT no encaixe): `GiantMachines.TickMiner` percorre o
  disco de raio 16 (do centro para fora) camada por camada até a rocha-mãe (y<3); cada célula de terreno (pedra,
  minério, areia, cascalho, terra) dá os drops de Harvest (`WorldMachines.Drops`, agora público) e, se não é terra,
  vira `terrDirt` com a mesma densidade (`SetBlocksRPC` em lote). A coluna do centro vira ar (poço da broca).
  Cursor em LogicStore (`y`, `i`), cada célula uma vez; buffer de saída (`buf`, 40 pilhas) empurrado para a frente
  (esteira/baú/máquina); 8 células/s x velocidade; para quando o buffer enche.
- **Extratora de Petróleo** (`feOilExtractor`, 5x11x5, `FeWorld=oilwell`, `FeFluid=oilwell`, 512 UT): mede o disco
  de raio 24 até a rocha-mãe sem quebrar nada (3000 células por tick) contando `terrOreOilDeposit`; reserva = xisto x
  300 L; bombeia 120 L/min x velocidade para o próprio tanque (2000 L), oferecido na porta da frente
  (`FluidKind.OilWell`). `FeNeedPipeBar=12`: na rede com cano comum (4 bar) **vaza** (regra nova no `Flow`, vale
  também para líquido).
- **Tanque de Armazenamento** (`feStorageTank`, 5x6x5, 100.000 L): tanque multibloco; `Ports()` de tanques multibloco
  agora põe portas em todas as faces de fora da camada de baixo (`MultiCells.BottomFaces`).
- **Trilhos** (`Rails.cs`): `BlockFeRail` guarda cada peça (`RailStore`, `ForgedInAshes_rails.txt`); geometria local
  por tipo (reto 1x1, curva 5x5 raio 4,5, rampa 1x2x3, desvio D/E 5x5); grafo por pontas (grade de 0,1 m);
  Dijkstra com continuidade de direção (>60 graus não passa: nada de voltar pelo outro ramo do desvio).
- **Trens** (`Trains.cs`): `TrainStore` (`ForgedInAshes_trains.txt`: vagões, carga, rota, combustível, trilho);
  `TrainSim` move a cabeça ao longo do trilho (14 m/s, aceleração 0,8, frenagem 1,2), consome combustível por metro,
  espera 12 s na estação, planeja a próxima perna e **inverte** a composição se voltar for mais curto. Kits
  (`BlockFeTrainKit`): locomotiva a até 4 m de um trilho vira trem; vagão a até 10 m de um trem é engatado.
  Combustível: Carvão 25, Galão 4, Botijão de Gás 60 unidades (nada vegetal).
- **Estação** (`feTrainStation`, 9x4x3, `BlockFeStation : BlockCompositeTileEntity`): armazenamento de 100
  espaços (`feStationStorage` em loot.xml), tranca e **etiqueta gravável do jogo = nome** (sem campo de texto nosso:
  um textfield em janela do mod já quebrou o XUi). Esteiras/funis/braços como num baú; combustível de trem chegando
  por esteira vai primeiro para o depósito de combustível (2000); comandos E: pôr combustível da mão, modo
  Carregar/Descarregar. Tanque de 20.000 L (`FluidKind.Station`, portas em todas as faces de fora, cada uma com a sua
  fração). Na chegada: abastece, carrega ou descarrega vagões de carga e tanque.
- **Visual e interação** (`TrainView.cs`): cada vagão usa `<kit>Prefab` do pacote ou uma caixa colorida; colisores
  desligados; mira por raio contra a caixa do vagão; E na locomotiva = Painel do Trem, E no vagão de passageiros
  (ou agachado na locomotiva) = sentar (posição presa ao assento a cada quadro, sem dano de queda), E ou pulo desce.
- **Painel do Trem** (`feTrain`, gen_ui.py, `XUiC_FeTrain`): mapa 512x512 desenhado em textura (trilhos, estações
  numeradas, rota, trens), lista de estações (clique = pôr na rota), rota (clique = tirar), Ligar/Parar, Abastecer
  (mão), Limpar rota, Recolher trem.
- gen_chain: blocos, receitas (Montadora), traduções EN/PT e comandos; `block_xml` aceita `__xml` (propriedades
  aninhadas). `build.ps1` referencia `Unity.Addressables` e `Unity.ResourceManager` (`DataLoader.LoadAsset`).
  `list_assets.py`: contratos giant/rail/station/trainkit e a seção dos prefabs de vagão. Docs EN/PT/ES seções 10 e 11.
- Validadores: check_xpath 780/0, processes 243/0, phase3 23/23, coverage 0, check_reach 0/0/0. DLL compilada e no
  mod (link). PENDENCIAS_ASSETS: 13 blocos + 4 prefabs de vagão.
- **Não verificado no jogo.** Riscos conhecidos: andar sentado no vagão (o controle do jogador pode brigar com a
  posição presa), modelos provisórios (caixas), desempenho do Painel com muitas estações, a Mineradora gera muitos
  itens (só anda na velocidade em que a saída escoa).

## 2026-11-27 — Modelos D14: trilhos, máquinas gigantes, tanque, estação, kits e vagões do trem

Pedido: "Analise o PENDENCIAS_ASSETS.md e crie os modelos pendentes com cuidado com qualidade animações e posições
corretas." Os 13 blocos e os 4 vagões da lista ganharam modelo próprio (`Art/feHD/build_feHD.py`, `D14_MODELS`),
textura PBR (F:\IA, atlas 4096 nos grandes) e ícone.

- **Eixos conferidos no código**: Blender (x, y, z) = jogo local (-x, -z, y); origem = chão da célula-pai (célula do
  meio da camada de baixo). Trilhos batem com `Rails.LocalPaths` (topo do trilho a 0,15; bitola 1,435 entre as faces
  internas; curva com centro (-2,5; 2,5) no Blender = (2,5; -2,5) no jogo); vagões com origem no topo do trilho, +Z
  = frente (`Train.CarPose`).
- **Trilhos** (reto, curva 5x5, rampa 1x2x3, desvio D/E): lastro de brita, dormentes a cada 0,5 m (a emenda entre
  peças mantém o passo), placas e grampos, trilho de perfil real varrido no caminho, talas de junção; desvio com
  agulhas (o trilho da curva começa onde se afasta do reto), dormentes longos sob os dois ramos, coração (jacaré) e
  aparelho de manobra; rampa sobre aterro com escoramento de madeira.
- **Mineradora** (7x9x7): base de vigas I, subestrutura, piso gradeado a 2,4 m com guarda-corpo e escada, torre
  treliçada até 9 m, catarina, cabine do sondador, BOP; peças que giram com o torque do encaixe: haste/mesa rotativa,
  roldanas do topo, tambor do guincho, eixo de entrada, roda dentada, peneira rotativa (trommel) e roletes da esteira
  de saída (frente, no meio, no chão).
- **Extratora de Petróleo** (5x11x5): cavalo-de-pau sob uma torre de workover; **balancim de verdade**: manivela com
  contrapesos (`FeSpin_x0.25_Crank`), bielas (`FeRockRod_1`), balancim (`FeRock_1`) e haste polida (`FeRockSlide_1`)
  resolvidos a partir do ângulo real da manivela (comprimento da biela constante); árvore de natal, separador, flange
  de alta pressão na frente.
- **Tanque de Armazenamento** (5x6x5): costado soldado, teto cônico com guarda-corpo, escada em espiral, bocais com
  válvula no meio de cada lado, boca de visita, **indicador de boia** subindo numa régua (`FeSurface_r4.60_Float`) e
  manômetro de nível (`FeNeedle_Level`).
- **Estação** (9x4x3): plataforma de concreto com face de tijolo, faixa amarela, degraus nas pontas, cobertura em
  colunas de ferro com lambrequim, escritório (armazém), caixotes, carvoeira (combustível), tanque de 20.000 L com
  cano de enchimento no fundo, bancos, lampiões, relógio; **placa de nome** com `TextMesh` dos dois lados para a
  etiqueta do jogo. Colisores por caixa (`FeCol_*`): dá para andar na plataforma sob o teto.
- **Kits** (1x1): caixote em palete com a silhueta do vagão pintada (cor por tipo); o ícone mostra o vagão.
- **Vagões** (`<kit>CarPrefab`, prefabs soltos): locomotiva-tanque (caixa de fumaça, chaminé, domos, tanques laterais,
  cabine, carvoeira, cilindros, 3 eixos acoplados + truque + eixo traseiro), vagão fechado, vagão-tanque, vagão de
  passageiros (piso a 1 m, bancos frente a frente, corredor livre, plataformas nas pontas).
- **Código**:
  - `KineticSpinner`: balancim `FeRock_*` (busca do ângulo + bisseção); máquina gigante desligada fica parada.
  - `BlockFeGiant` liga o animador de giro no modelo. `MachineSound`: Mineradora = broca, Extratora = bomba.
  - `TrainView`: carrega `<kit>CarPrefab` (antes `<kit>Prefab`, que agora é o caixote do kit); `TrainCarVisual` gira
    as rodas pela distância andada, move bielas de acoplamento, cruzetas e bielas motrizes a partir dos pinos (90° de
    defasagem entre os lados) e solta fumaça/vapor andando.
  - `FeBuild`: lista `Loose` (vagões: sem camada de bloco, sem deslocamento de -0,5, sem colisor), colisores
    `FeCol_<n>_<x>x<y>x<z>` (cm), `FeSignText_F/_B` vira `TextMesh`.
  - `build_feHD.build()`: atualiza a cena antes de parentear (raiz com transformação deslocava as peças).
  - Materiais novos `feHD_Concrete` e `feHD_Ballast`.
- Verificação: validadores check_xpath 780/0, processes 243/0, phase3 23/23, coverage 0; `list_assets.py`: 0 blocos,
  0 itens, 0 vagões pendentes. DLL compilada. FeBuild: colisores e eixos conferidos no log (estação 11 caixas,
  trilhos dentro das células, rodas no eixo X a 0,40/0,42/0,70 m, manivela da Extratora atrás). Pacote 898 MB.
- Corrigido no caminho: raiz do `_HD` precisa estar na origem (a texturização exporta relativo a ela): `build()` põe
  como raiz o primeiro objeto sem transformação.
- **Não verificado no jogo** (roteiro: TESTE_GERAL seção 26). Riscos: tamanho da letra da placa da estação
  (`TextMesh` escala 2,5), sentido do giro das rodas, o concreto ficou com textura de pedra.
- **Teste 17:05** ("não consegui entrar na cabine do trem para controlar ele, nem no vagão de passageiros"): o log
  mostra a locomotiva colocada (`train 1 placed`) e nenhum registro de mira/E. Mudanças: E na locomotiva = **entrar
  na cabine** (assento no piso da cabine do modelo, 1,47 m, 2,2 m atrás do meio); na cabine, E = Painel do Trem e
  pulo = descer; agachado + E = painel de fora. Vagão de passageiros: assento no piso (1,02 m) girando com o vagão.
  Mira até 6 m e um bloco dentro da caixa do vagão (trilho, chão) não esconde mais o vagão. Log novo: `train use:`
  (cada E perto de trem: mirou?, distância, bloco, janela livre) e `wagon coupled` (distância, trilho atrás da
  cabeça). Traduções `feTrainCab` / `feTrainDriving`. **Não verificado no jogo.**
- **Vagões sólidos para o jogador** ("analise o motivo pelo qual o jogador está atravessando a locomotiva" → "Sim,
  sólidos"): o atravessar era de propósito (pedido do D14 "sem colisão": colisores desligados no `TrainView`, prefabs
  `Loose` sem colisor). Agora `TrainView.Solid()` tira o jogador de dentro da forma de cada vagão a cada quadro
  (caixas por tipo; locomotiva baixa na caldeira e alta na cabine), pela lateral ou ponta mais perto; até 0,55 m
  abaixo do teto ele sobe e fica em pé no teto, levado junto quando o trem anda e faz curva. Sem colisores físicos:
  trens continuam sem bater em blocos nem entre si e a mira de blocos não muda. **Não verificado no jogo** (riscos:
  tremida em pé no teto com o trem andando; o trem empurra quem estiver na frente).
- **Teste 17:25** ("fiquei preso na cabine"; "talvez precise alterar uma lógica grande para o jogo entender como um
  automóvel"; "o vagão de passageiros: só quando apertam E, com visão externa do vagão"). Logs 17:13 e 17:24: nenhuma
  linha `train use`/`boards`: o E nunca chegava ao trem. Causa: o jogo entrega Activate pelo `PlayerActionsPermanent`;
  o `TrainView` lia só `PlayerActionsLocal.Activate.WasPressed`. Agora lê os dois com detecção de borda (como
  `Crank.IsActivateHeld`). Decisões do usuário: direção **manual + rota**; passageiro **só viaja**.
  - **Locomotiva como veículo** (sem `EntityVehicle`, cujas rodas físicas brigariam com o trilho): E entra na cabine e
    a câmera vai para **terceira pessoa** afastada (`SetFirstPersonView(false)` + `vp_FPCamera.Position3rdPersonOffset`,
    o mesmo campo que os veículos usam em `RefreshDrivingCameraPositions`, IL 3.4.0 b10). W acelera, S freia e dá ré
    (até 18 km/h), espaço freia, A/D escolhe o ramo nos próximos desvios (fica marcado), agachar abre o Painel, E desce.
    Apertar W/S assume o trem (`Manual`, desliga a rota); "Ligar" no Painel volta ao piloto automático.
  - `TrainSim.StepManual`: velocidade pela manete, trilho à frente refeito (60 m) quando o desvio escolhido muda ou o
    fim chega perto, trilho atrás estendido na ré, fim de linha para o trem; sem maquinista o trem manual freia.
    `Rails.WalkFrom/Walk(prefer)`: ramo mais à esquerda/direita pelo lado para onde a curva abre.
  - Passageiro: E senta com a mesma visão externa; E ou pulo desce. Traduções novas EN/PT.
  - **Não verificado no jogo** (riscos: a animação de andar do jogador na cabine; a câmera de terceira pessoa pode
    bater em blocos; A/D só valem para desvios ainda a mais de ~2 m).
