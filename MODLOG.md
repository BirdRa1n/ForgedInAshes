# MODLOG — Ferro & Engrenagem

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
- Fases 0, 1 e 3: só XML (patches XPath em `Mods/FerroEngrenagem/Config/`). Sem DLL.
- Fase 2+ (se a rota B de energia for necessária): DLL C# carregada pelo próprio jogo (o log mostra
  `Found ModAPI in assembly ... creating instance`) + Harmony do `0_TFP_Harmony`.
- Motivo: o jogo tem loader oficial com XML patching e Harmony embutidos; BepInEx seria uma segunda camada
  desnecessária e aumentaria conflito com outros mods.

## Oráculo (como verificar no jogo)

- Linhas do log por mod: `[MODS]   Trying to load from folder: '<pasta>'` e `[MODS]     Loaded Mod: <Name> (<Version>)`.
- Erros de XML/XPath: procurar `ERR`, `WRN`, `XPath` e `FerroEngrenagem` no log mais recente.
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
  - log: `[MODS] Trying to load from folder: 'FerroEngrenagem'` → `Loaded Mod: FerroEngrenagem (0.1.0)` →
    `[MODS] Loading localization from mod: FerroEngrenagem`; nenhum ERR/WRN do mod.
  - tela: menu criativo, busca "test" → "Item de Teste Ferro & Engrenagem (1435) feTestItem", ícone laranja.
  - Fatos confirmados: mod XML-only carrega por junction; `Config/Localization.csv` com o cabeçalho completo
    vanilla funciona; a coluna `brazilian` é usada quando o idioma da plataforma é brazilian; `CustomIcon` +
    `CustomIconTint` reaproveitam ícones vanilla.
  - Ruído vanilla do log (ignorado por `check_log.py`): notícias remotas, Xbox Live, Discord SDK 403, Twitch 404.
- Gotcha: no PowerShell 5.1, `Get-Content -Raw` lê UTF-8 sem BOM como ANSI e corrompe acentos ao regravar.
  Editar arquivos com acento só pelas ferramentas de edição ou por Python.
- **Fase 0 concluída.**

- F1-T01 testado (13:13): log limpo (`Loaded Mod: FerroEngrenagem (0.1.0)`, 0 linhas marcadas). Visual dos
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
  (só `Art/`, não tocar em `Config/`). Remoto: `origin` = GitHub `BirdRa1n/FerroEngrenagem`.

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
  - `src/FerroEngrenagem/ModApi.cs`: loga `[FerroEngrenagem] InitMod` e aplica `PatchAll` (0 patches ainda).
  - DLL gerada fica fora do git (`.gitignore`).
  - **Verificado no jogo** (15:12, `-noeac`): `Loaded assembly FerroEngrenagem` → `Found ModAPI ... creating instance`
    → `[FerroEngrenagem] InitMod: code loaded (0.1.0.0)` → `Harmony: 0 method(s) patched` →
    `Initialized code in mod 'FerroEngrenagem'`. Log sem erros. A DLL compilada com csc C# 5 contra o mscorlib
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

## Próximo passo (antigo, mantido para histórico)

Fase 1 — (feito) F1-T01: itens `feResourceIronPlate`, `feResourceIronShaft`, `feResourceGear` (+ localização,
ícones vanilla). Antes do F1-T03 resolver P14 (pasta XUi do mod).
