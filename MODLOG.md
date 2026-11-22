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

## Próximo passo

Fase 1 — F1-T01: itens `feResourceIronPlate`, `feResourceIronShaft`, `feResourceGear` (+ localização,
ícones vanilla). Antes do F1-T03 resolver P14 (pasta XUi do mod).
