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
  (só `Art/`, não tocar em `Config/`). Remoto: `origin` = GitHub `BirdRa1n/ForgedInAshes` (repositório
  renomeado de `FerroEngrenagem` em 2026-11-22; URL local atualizada).

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
  - **F2-T04b: Manivela "segurar E"** em C# (`src/FerroEngrenagem/Crank.cs`, `Class=FerroEngrenagem.FeCrank,
    FerroEngrenagem`): rotor e polia giram, estamina 25/s (`FeCrankStaminaPerSecond`), 1 Carga a cada 2,5 s
    (`FeCrankChargeSeconds`), agachar + E recolhe. Substitui o gancho de `buffs.xml` + `gameevents.xml`
    (esvaziados). Testado por ele no jogo.
  - **Primeiro modelo próprio integrado:** `Resources/ferroengrenagem.unity3d` (projeto em `Art/UnityProject`,
    `FeBuild.cs`); `Model="#@modfolder:Resources/ferroengrenagem.unity3d?feCrankPrefab"` (sintaxe lida em
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

## Próximo passo (antigo, mantido para histórico)

Fase 1 — (feito) F1-T01: itens `feResourceIronPlate`, `feResourceIronShaft`, `feResourceGear` (+ localização,
ícones vanilla). Antes do F1-T03 resolver P14 (pasta XUi do mod).
