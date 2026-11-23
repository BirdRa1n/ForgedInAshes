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
- Log: `FerroEngrenagemMod.Verbose` só com `Mods/FerroEngrenagem/debug.txt` (no .gitignore). Sem ele: a linha
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
- `blocks.xml`: os 6 blocos usam `#@modfolder:Resources/ferroengrenagem.unity3d?<bloco>Prefab`; `feShaft` virou
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
- Persistência: `FluidStore` em `<save>/FerroEngrenagem_fluids.txt` (registro dos dispositivos + níveis), salvo a cada
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

## Próximo passo (antigo, mantido para histórico)

Fase 1 — (feito) F1-T01: itens `feResourceIronPlate`, `feResourceIronShaft`, `feResourceGear` (+ localização,
ícones vanilla). Antes do F1-T03 resolver P14 (pasta XUi do mod).
