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
- D6: Carga será combustível com Harmony. Infra C#: `src/FerroEngrenagem` (entrada `IModApi` + Harmony `PatchAll`), `tools/build.ps1`; `check_log.py` mostra as linhas `[FerroEngrenagem]`.
- F2-T02: itens Carga (`feCharge`) e Carvão Vegetal (`feResourceCharcoal`); Carvoeira (`feCharcoalKiln`, coletor: 5 Madeira → 1 Carvão Vegetal) com receita no inventário.
- F2-T03: Gerador a Carvão (`feCoalGenerator`, coletor com catalisador: 1 Carvão Vegetal → 5 Cargas por Volante), Volante de Inércia (`feFlywheel`, no Torno); Prensa e Torno passam a ter slot de combustível e, por patch Harmony, queimam só Carga.
- F2-T04: Manivela (`feCrank`): cada golpe nela gasta estamina e dá 1 Carga (gancho em `buffStatusCheck01` + GameEvent `fe_crank_charge`); receita no inventário.
- F2-T07: Manivela com 25% de chance de Carga por golpe (aprovado). F2-T05 resolvida na T03. **F2-T06 (servidor dedicado) adiada** pelo usuário.

### Fase 3
- F3-T01: proposta automática de remapeamento das 600 receitas (`tools/remap_proposal.py`, seção 10.1 do plano).
- F3-T02: 10 máquinas novas (Prensa de Munição, Montadora, Bancada de Mods, Tear, Refinaria, Laboratório, Cozinha, Bancada Eletrônica, Serralheria, Serraria), todas a Carga; 9 itens intermediários (fio de latão, bobina, lubrificante, tábua, viga, rolo de tecido, cano, mecanismo e coronha de arma) e Peças Elétricas fabricáveis; gerador `tools/gen_phase3.py`; patch de combustível ligado por `FeChargeOnly`.
- F3-T03: 328 receitas vanilla remapeadas para as máquinas (Forja, Estação Química e Bancada esvaziadas, exceto fase 4); gerador `tools/gen_remap.py` com checagem de `craft_tool`. Bancada vanilla sem as receitas do inventário.
- F3-T04: armas e ferramentas da Montadora passam a exigir Cano, Mecanismo, Coronha, Eixo, Chapa, Engrenagem ou Bobina (`tools/gen_parts.py`).
- F3-T05: Mechanical Parts e Spring fora do loot e do trader; Engine desmanchado vira ferro.
- F3-T06: máquinas sempre liberadas (D3); a habilidade de estações mostra Fundição, Montadora e Refinaria.
- F3-T07: Forja, Bancada e Estação Química vanilla não são mais fabricáveis nem aparecem no criativo; quests, loot e trader dão as máquinas do mod.
- F3-T08: checagem final `tools/check_phase3.py` (18/18).
- F3-T03b: receitas industriais do inventário (mina, ferramentas de ferro, portas de ferro, equipamento de bioma…) vão para as máquinas.

### Fase 4
- F4-T01: Misturadora de Concreto, Garagem e Oficina de Robótica; Engine fabricável na Garagem; veículos, robôs e concreto saem da Bancada e da Betoneira vanilla (agora ocultas).
- F4-T02: Gerador, Banco de baterias e Painel solar (agora fabricável) exigem peças do mod na Bancada Eletrônica.
- F4-T03: Gerador de Carga a Gasolina (latas de gasolina → Carga, com Motores como catalisador).
