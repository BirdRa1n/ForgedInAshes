# Changelog

Formato: uma entrada por tarefa (`F<fase>-T<n>`).

## [Não lançado]

### Fase 0
- F0-T01: caminho da instalação e versão do jogo (3.4.0 B10) registrados.
- F0-T02: estrutura do repositório, `.gitignore`, `CHANGELOG.md`.
- F0-T03: `ModInfo.xml` no formato do `0_TFP_Harmony` (versão 0.1.0).
- F0-T04: ferramentas `check_xpath.py`, `recipe_report.py`, `find_sources.py`, `install.ps1` e módulo `fe_common.py`.
- F0-T05: fontes de Mechanical Parts, Spring e Engine (P05) e nomes vanilla confirmados (P12) no plano.
- F0-T06: item de teste `feTestItem` + `Localization.csv`; `tools/check_log.py`; mod instalado por junction; verificado no jogo.

### Fase 1
- F1-T01: itens `feResourceIronPlate`, `feResourceIronShaft`, `feResourceGear` (ícones vanilla tingidos, material de Forged Iron) + localização EN/PT-BR.
- F1-T02: blocos `feFoundry` (M01), `fePress` (M02), `feLathe` (M03) com `craft_area` próprio e janelas vanilla via `WorkstationWindow`; receitas de construção no inventário.
- F1-T03: não necessária na fase 1 (máquinas usam janelas vanilla via `WorkstationWindow`).
- F1-T04: receitas da Fundição (Forged Iron, Pregos, Cano + 6 receitas de fundição, cópias exatas da Forja), da Prensa (Chapa) e do Torno (Eixo, Engrenagem, Mechanical Parts, Spring); ferramenta `tools/copy_recipes.py`.
- F1-T04 (correção): Fundição só com receitas de sucata direta e janela sem fundição (o filtro de variantes do jogo só vale para `forge`).
- `ART_BRIEF.md`: briefing para a sessão de arte em paralelo.
- F1-T05: desmanche de blocos não dá mais Mechanical Parts nem Spring (drops `Harvest` removidos, drops `Destroy` viram Sucata de ferro); loot de MP e Spring cortado pela metade; ferramenta `tools/loot_scale.py`.
- F1-T06: fatia vertical testada em sobrevivência e aprovada pelo usuário. **Fase 1 concluída.**

### Fase 2
- F2-T01: pesquisa de energia (P02, P03, P04 resolvidas no papel); proposta de Rota A 100% XML; ferramenta `tools/il_inspect.ps1`.
