# Plano de craft em cadeia: "modo Create" (proposta D11, pedido do usuário 2026-11-23)

O objetivo é deixar o jogo mais difícil e mais próximo do Create: nenhum item avançado sai de uma bancada com um
clique. Cada item passa por uma **linha de produção**: fundir, moldar, prensar, misturar, montar. As máquinas são
ligadas por canos, calhas e esteiras, e alimentadas pelos baús.

Este documento:
1. define os **processos** (os verbos da produção);
2. lista as **máquinas e blocos novos** que eles pedem;
3. traz exemplos completos, a começar pela munição;
4. dá um **modelo de cadeia** para cada grupo de receitas do jogo, para cobrir todos os itens;
5. divide o trabalho em fases e lista as decisões em aberto.

Os números (litros, tempos, quantidades) são **propostas**. Eles serão ajustados na conversa de balanceamento.

---

## 1. Princípios

1. **Cada material muda de forma, não só de nome.** Sucata → metal fundido (fluido) → peça moldada → peça usinada.
   Isso cria espaço para as máquinas e para a logística.
2. **Cada passo usa um recurso do mod:** torque, vapor, eletricidade, água, calor ou combustível. Uma linha parada
   por falta de energia é o "desafio".
3. **Reaproveitar o que já existe:**
   - rede de fluidos: canos, Caixa d'Água, Despejador, Envasadora;
   - esteiras, Funil, Filtro, Armazém de Esteira;
   - receita fixa (AutoCraft);
   - torque e vapor.
4. **O começo do jogo continua jogável.** O tier primitivo continua na mão do jogador: flecha de pedra, Blunderbuss,
   ferramentas de pedra e comida da Fogueira. A cadeia vale do tier de ferro em diante.
5. **Itens de loot e trader não mudam** nesta etapa. Quanto se encontra pronto é assunto do balanceamento.
6. **Tudo é dado, não código, sempre que der.** Um arquivo de processos (seção 6) diz o que cada máquina faz. Assim,
   cobrir os 600 itens é trabalho de tabela e não de C#.

---

## 2. Processos (os verbos)

| Processo | O que faz | Máquina | Entrada → saída | Energia |
|---|---|---|---|---|
| **Fundir** | Derrete sucata ou lingote em metal líquido | Fundição (M01) | item → fluido "metal fundido" | Combustível (calor) |
| **Moldar** | Despeja o metal líquido num molde e espera esfriar | Mesa de Moldagem (nova) | fluido + molde → peça | Nenhuma (tempo); água acelera |
| **Prensar** | Achata ou estampa uma peça | Prensa (M02) ou Prensa em Linha (nova) | item → item | Torque |
| **Tornear / furar** | Usina uma peça bruta | Torno (M03) | item → item | Torque |
| **Triturar** | Mói minério, carvão ou pedra | Triturador (novo) | item → pó (às vezes 2 saídas, com chance) | Torque alto |
| **Lavar** | Separa o pó na água | Lavadora (nova) ou ventilação com água em cima da esteira | pó + água → pó limpo + resíduo | Água |
| **Misturar** | Junta vários itens e fluidos | Misturadora (M08) | itens + fluido → item ou fluido | Torque |
| **Secar / aquecer** | Tira a umidade, cozinha ou cura | Secador (novo, a vapor) | item úmido → item | Vapor |
| **Destilar / refinar** | Separa fluidos | Refinaria (M09) | fluido → fluidos | Vapor ou calor |
| **Fiar / tecer** | Fibra → fio → tecido | Tear (M07) | item → item | Torque |
| **Montar** | Junta componentes prontos | Montadora (M05) e as outras bancadas finais | componentes → produto | Eletricidade |
| **Montar em sequência** | O item passa por várias estações em ordem e só fica pronto no fim (estilo Create) | Estações em Linha sobre a esteira (novas) | item incompleto → … → produto | Depende da estação |

---

## 3. Blocos e máquinas novas

| ID | Bloco | Função | Base técnica existente |
|---|---|---|---|
| N01 | **Calha de Metal** | Cano só para metal fundido. Não leva água nem óleo, e o cano comum não leva metal. Visual de calha aberta com o metal brilhando. | rede de fluidos (canos) |
| N02 | **Mesa de Moldagem** | Recebe metal pela calha e tem um slot de molde. Quando enche a dose do molde, espera esfriar e solta a peça na esteira da frente (ou na mão). Água num cano ao lado acelera o resfriamento. | Envasadora (Bottler) |
| N03 | **Moldes** (itens) | Cada molde aceita só alguns metais e faz uma peça. Exemplos na seção 4.1. | itens + propriedade `FeMoldMetals` |
| N04 | ~~Revestimento de molde~~ | **Retirado (usuário, 2026-11-23).** No pt-BR do jogo, "Revestimento de balas" é a cápsula: o pedido era o molde fazer a cápsula. | — |
| N05 | **Triturador** | Rodas de moer. Consome torque alto. Recebe por esteira, solta na esteira da frente. | esteira + máquina de torque |
| N06 | **Lavadora** | Tanque com água e peneira. | rede de fluidos + esteira |
| N07 | **Secador a Vapor** | Estufa ligada ao vapor (Condensadora / Motor a Vapor). | rede de fluidos (vapor) |
| N08 | **Estações em Linha**: Prensa em Linha, Bico Dosador, Encaixador, Crimpadora | Ficam **em cima** de uma esteira. O item que passa embaixo para, recebe o passo e segue. É a "montagem em sequência" do Create. | `BeltTicker` (o item já para no fim da esteira) |
| N09 | **Montadora com baús ligados** | Com uma receita fixa escolhida, puxa os ingredientes de **todos os baús ligados a ela** (encostados nela ou encostados uns nos outros, até 16 baús). Monta quando tem tudo e põe o produto na saída. Um Funil leva para a esteira. | AutoCraft + Funil (leitura de baús) |
| N10 | **Painel de receita** | O jogador escolhe na máquina o que ela produz, sem ter que fabricar uma vez à mão (o problema atual da receita fixa). | lista de receitas da estação |

---

## 4. Exemplos completos

### 4.1 Munição 9mm (o exemplo do pedido)

O jogo base hoje faz assim:
- Bala 9mm = 1 Ponta + 1 Pólvora + 1 Cápsula, na Bancada;
- Cápsula = 5 latão + argila, na Forja;
- Ponta = 2 chumbo + argila, na Forja;
- Pólvora = carvão + salitre, na mão ou na Estação Química.

Com o mod, a mesma bala tem três linhas.

**Linha A: cápsula (latão)**
1. Esteira de sucata de latão → **Fundição**: 1 Sucata de Latão = 10 L de Latão Fundido.
2. **Calha** → **Mesa de Moldagem** com o **Molde de Cápsula**:
   - 25 L = 5 Cápsulas Brutas, 6 s esfriando (3 s com água);
   - o Molde de Cápsula aceita latão e recusa chumbo e ferro.
3. Esteira → **Prensa em Linha** (repuxo): Cápsula Bruta → **Cápsula** (`resourceBulletCasing`).

**Linha B: ponta (chumbo)**
1. Sucata de Chumbo → **Fundição**: 1 = 10 L de Chumbo Fundido.
2. **Mesa de Moldagem** com o **Molde de Ponta** (aceita chumbo): 20 L = 10 Pontas (`resourceBulletTip`).

**Linha C: pólvora (química)**
1. Carvão → **Triturador** → Pó de Carvão.
2. Salitre bruto (o `resourcePotassiumNitratePowder` dos ninhos) → **Lavadora** com água → Salitre Purificado
   (mais Lama, que vira argila).
3. **Misturadora**: 1 Pó de Carvão + 2 Salitre Purificado + 1 L de água → Pólvora Úmida.
4. **Secador a Vapor** → **Pólvora** (`resourceGunPowder`).

**Linha D: montagem**
- **Opção 1, Montadora com baús ligados** (o pedido):
  - Os baús de cápsulas, pontas e pólvora ficam encostados na Montadora, ou encostados num baú que está
    encostado nela. Cada linha enche o seu baú pela esteira.
  - O jogador escolhe "Bala 9mm" no painel.
  - A Montadora monta sempre que tem tudo nos baús.
  - Um Funil na Montadora leva as balas por esteira até o Armazém.
- **Opção 2, montagem em sequência** (mais Create, fase posterior):
  - A Cápsula anda na esteira e recebe a Pólvora no **Bico Dosador** → vira Bala Incompleta.
  - O **Encaixador** põe a Ponta → Bala Incompleta.
  - A **Crimpadora** fecha a bala → Bala 9mm.
  - Cada estação puxa o seu ingrediente de um baú ou funil ao lado.

A remoção (ou o encarecimento) da receita da Bancada fica na seção 8. Com ela removida, só se faz munição com as
três linhas.

### 4.2 Arma: Pistola (tier de ferro)

| Peça | Cadeia |
|---|---|
| Cano (`feGunBarrel`) | Aço fundido → Molde de Tubo → Tubo Bruto → **Torno** (furar) → **Torno** (estriar) → Cano |
| Mecanismo (`feGunMechanism`) | Engrenagem (Torno) + Mola (Prensa) + Chapa (Prensa) → **Montadora** |
| Coronha (`feGunStock`) | Tora → **Serraria** → Tábua → **Torno** (modelar) → Coronha |
| Pistola | Cano + Mecanismo + Coronha + Parafusos → **Montadora** com receita fixa |

### 4.3 Ferramenta: Picareta de Aço

Aço fundido → **Molde de Cabeça de Picareta** → Cabeça Bruta → **Prensa** (forjar) → **Esmeril** (afiar, estação em
linha) → Cabeça de Picareta. Mais o Cabo (Serraria + Torno) → **Montadora**.

### 4.4 Construção: Concreto

1. Pedra → **Triturador** → Cascalho + Areia (`resourceCrushedSand`).
2. Pedra moída → **Fundição** (forno) → Cimento (`resourceCement`).
3. **Misturadora**: Cimento + Cascalho + Areia + água → Concreto Fresco (**fluido**).
4. Concreto Fresco por cano → **Mesa de Moldagem** com o Molde de Bloco → bloco de concreto, ou → Envasadora →
   Concreto em saco (`resourceConcreteMix`).

### 4.5 Remédio: Antibiótico

Cogumelo / planta → **Triturador** → Pasta → **Laboratório**: destilar com vapor → Extrato → **Misturadora** com
água destilada (Condensadora) → **Secador** → comprimido.

### 4.6 Roupa e armadura: Armadura de Couro / Militar

- Algodão → **Tear** (fiar) → Fio → **Tear** (tecer) → Rolo de Tecido (`feResourceClothRoll`).
- Couro → **Curtume**: tanque com água e ácido → Couro Curtido.
- Militar: Chapa de aço (Prensa) + Tecido → **Montadora** → peça da armadura.

### 4.7 Eletrônica: Peça Elétrica / Placa de Circuito

- Latão fundido → Molde de Fio → **Trefila** (estação em linha: puxar o fio) → Fio de Latão (`feResourceBrassWire`).
- Fio + Chapa → **Bobina** (`feResourceCoil`).
- Placa: Polímero derretido (`resourceScrapPolymers` → Fundição em baixa temperatura) → Molde de Placa → **Bico
  Dosador** de Fio → Placa de Circuito.

### 4.8 Veículo: Motor (Engine)

Ferro fundido → **Molde de Bloco de Motor** (molde grande, 200 L) → Bloco Bruto → **Torno** (cilindros) → montagem
em sequência:
1. pistões (Molde de Pistão + Torno);
2. virabrequim (aço fundido + Torno);
3. velas (cerâmica + fio);
4. lubrificante (fluido, Bico Dosador).

O resultado é o Engine.

---

## 5. Modelo de cadeia por grupo de receita (cobertura de todos os itens)

Cada uma das ~600 receitas do jogo (seção 10.1 do PLANO_MOD) recebe **um modelo** desta tabela. A planilha gerada por
script (fase F8.0) lista receita por receita com o modelo e os produtos intermediários.

| Grupo (nº de receitas) | Modelo de cadeia | Peças intermediárias típicas |
|---|---|---|
| Munição (41) | Fundir + Moldar (cápsula/ponta) + Química (pólvora) + Montar | Cápsula, Ponta, Pólvora, Chumbo Grosso, Ponta de Flecha, Ponta e Corpo de Foguete |
| Flechas e virotes | Serraria (haste) + Moldar (ponta de ferro/aço) + Tear (pena colada) + Montar | Haste, Ponta de Flecha |
| Armas (≈25) | Fundir + Moldar + Torno (cano) + Montar | Cano, Mecanismo, Coronha, Ferrolho, Mola |
| Ferramentas (≈15) | Fundir + Moldar cabeça + Prensa + Esmeril + cabo da Serraria + Montar | Cabeça Bruta, Cabo |
| Explosivos | Química (pólvora, ácido) + Moldar (carcaça) + Montar | Carcaça, Detonador |
| Mods de arma/armadura (74) | Prensa (chapa) + Torno + Eletrônica + Montar | Chapa, Lente, Mola, Placa |
| Armaduras e roupas (63) | Tear (fio, tecido) + Curtume (couro) + Prensa (placas) + Montar | Rolo de Tecido, Couro Curtido, Placa de Armadura |
| Construção: portas, cofres, garagens (29) | Fundir + Moldar chapas + Prensa + Serralheria | Chapa, Dobradiça, Fechadura |
| Materiais de construção (cimento, concreto, vidro, barras) | Triturar + Forno + Misturar + Moldar | Areia, Cascalho, Cimento, Concreto Fresco |
| Eletricidade, armadilhas, torretas (28) | Trefila + Bobina + Placa + Montar | Fio, Bobina, Placa de Circuito |
| Veículos (14) | Moldar bloco de motor + Torno + montagem em sequência | Bloco de Motor, Pistão, Virabrequim, Roda, Chassi |
| Robótica (3) | Eletrônica + Motor elétrico + Montar | Servo, Placa, Bateria |
| Remédios (7 + 5) | Triturar + Destilar + Misturar + Secar | Extrato, Pasta, Comprimido |
| Comida (41 + 12) | Fogueira continua igual; a Cozinha faz em lote com vapor e esteira (sem dificultar) | — |
| Recursos químicos (gasolina, óleo, cola, tinta, papel, bateria) (10) | Refinaria com fluidos: óleo de xisto → destilar → gasolina e óleo | Óleo Cru, Ácido, Polpa |
| Tier primitivo e do inventário (162) | **Sem mudança** | — |

---

## 6. Como fica no código (resumo técnico)

1. **Metais fundidos são fluidos.** Novas strings na rede de fluidos: `molten_brass`, `molten_lead`, `molten_iron`,
   `molten_steel`, `molten_polymer`, `concrete`.
   - A regra "dois fluidos no mesmo cano = BLOQUEADO" já existe.
   - Cano e calha recusam o fluido do outro.
   - O metal na calha esfria e vira **Metal Solidificado** se ficar 5 min parado. Isso pune linha mal feita; opcional.
2. **Fundição como fonte.** A Fundição ganha uma porta de saída de fluido. O que ela derrete vai para um buffer
   (como a Caixa d'Água) e sai pela calha.
   - O metal pode ser escolhido com a receita fixa ("Fundir latão") ou ir na ordem de chegada.
3. **Mesa de Moldagem.** Um novo `FluidKind.Caster` com uma porta de demanda. Ela aceita só os metais do molde que
   está no slot e solta a peça como a Envasadora já faz.
4. **Arquivo de processos `Config/fe_processes.xml`**, lido pelo C#. Uma linha por processo:

   ```xml
   <process machine="feCaster" mold="feMoldCasing" fluid="molten_brass" liters="25" time="6"
            output="feCasingRaw" count="5"/>
   <process machine="feInlinePress" input="feCasingRaw" output="resourceBulletCasing" time="1" torque="64"/>
   <process machine="feCrusher" input="resourceCoal" output="feCoalDust" count="2"
            extra="resourceCrushedSand" chance="0.1" time="2" torque="128"/>
   ```

   - Os processos de **bancada** (Montadora, Torno, Prensa com janela) continuam nas `recipes.xml` vanilla com o
     `craft_area` do mod, que já funcionam com a receita fixa.
   - Um validador novo (`tools/check_processes.py`) confere que todo item citado existe, que todo molde tem metal e
     que toda cadeia chega ao item final.
5. **Estações em Linha.** No `BeltTicker`, quando o item chega ao meio de uma esteira que tem uma estação em cima, o
   item para, espera o tempo do processo e é trocado pela saída.
   - É a mesma lógica de "esperar no fim" que já existe.
   - O item incompleto guarda o passo atual num `ItemValue.Meta`, que já sai salvo pela gravação das esteiras.
6. **Montadora com baús ligados.**
   - Uma busca (BFS) pelos blocos de armazenamento encostados, até 16. É a mesma leitura de baú que o Funil já faz.
   - A Montadora puxa tudo só quando a receita inteira está disponível, para não deixar ingrediente pela metade.
   - Ela espera enquanto algum baú está aberto.
7. **Painel de receita (N10).** No menu de E da máquina, entra "Escolher produção" com a lista das receitas da
   estação, usando `CraftingManager.GetRecipes`. Isso substitui o "fabrique uma vez à mão".
8. **Remover as receitas vanilla** com `<remove xpath>` geradas pelo `gen_phase3.py`, como já é feito no
   remapeamento. Ou encarecer, conforme a decisão D11-2.

---

## 6.1 Versões industriais e Biodigestor (pedido do usuário, 2026-11-24)

Máquinas que dependiam do jogador (esvaziar, abastecer, esperar esfriar) ganharam uma versão **elétrica**, para a
linha rodar sozinha:

| Original | Industrial | Por que elétrica |
|---|---|---|
| Carvoeira (esvaziar à mão, abastecer à mão) | **Forno de Retorta** (100 W): madeira por esteira, carvão sai na esteira | aquecedor elétrico; nada a recolher |
| Fundição (queima combustível) | **Forno de Indução** (250 W, 2x2): derrete sem combustível, 2x mais rápido, 500 L | indução é o forno elétrico de verdade |
| Mesa de Moldagem (esfria devagar; água ajuda) | **Moldadora Industrial** (60 W): ventilador, esfria 4x mais rápido, enche 2x mais rápido | ventilador elétrico |

As que já são automáticas ficaram como estão: Triturador e Misturador (torque), Lavadora (água), Secador (vapor),
Despejador/Envasadora, e as bancadas (receita fixa + esteira + Funil). Manivelas já têm os motores.

**Biodigestor** (água por trás, lento e caro de propósito):

| Entra | Sai | Tempo |
|---|---|---|
| 5 Carne Crua + 5 L água | 5 Carne Podre | 180 s |
| 10 Carne Podre + 4 Ossos + 20 L | 1 Terra Nitrosa | 360 s |
| 15 Milho + 4 Ossos + 20 L | 1 Terra Nitrosa | 480 s |
| 10 Carne Podre + 20 L (sem ossos) | 1 Mosto Orgânico | 360 s |
| 12 Milho ou 12 Batatas + 20 L | 1 Mosto Orgânico | 300 s |

- Terra Nitrosa → **Lavadora** → 4 Salitre (a nitreira histórica: salitre de matéria orgânica podre).
- 2 Mosto Orgânico + 1 Gordura Animal → **Refinaria** → 1 Biocombustível.
- **Biocombustível queima muito mais rápido**: no Motor a Gasolina (por esteira), 3 latas valem 1 de gasolina.

## 7. Fases

| Fase | Entrega | Prova no jogo |
|---|---|---|
| **F8.0** [feito, falta teste] | Arquivo de processos, validador, planilha de cobertura (`tools/craft_matrix.py` → CSV com as ~600 receitas e o modelo de cada uma), painel de receita (N10) | Painel abre e escolhe receita; validador passa |
| **F8.1** [feito, falta teste] | Metalurgia: Fundição como fonte de fluido, Calha, Mesa de Moldagem, moldes de Cápsula, Ponta, Lingote, Chapa, Tubo e Engrenagem | Latão vira cápsula bruta; molde errado recusa |
| **F8.2** [feito, falta teste] | Química: Triturador, Lavadora, Secador, uso da Misturadora | Carvão + salitre viram pólvora sem a mão do jogador |
| **F8.3** | Montadora com baús ligados + Prensa em Linha | **Bala 9mm** sai sozinha da linha completa (exemplo 4.1) |
| **F8.4** | Toda a munição (9mm, .44, 7.62, cartucho, flecha, foguete) | Cada uma com a sua linha |
| **F8.5** | Armas e ferramentas | Pistola e Picareta de Aço |
| **F8.6** | Montagem em sequência (Bico Dosador, Encaixador, Crimpadora, Esmeril, Trefila) | Bala montada por sequência |
| **F8.7** | Armaduras, roupas e curtume | Armadura de couro |
| **F8.8** | Construção: concreto fluido, portas e cofres | Concreto moldado |
| **F8.9** | Eletrônica, veículos e robótica | Engine pela linha |
| **F8.10** | Remédios, química restante, cozinha em lote | Antibiótico |
| **F8.11** | Remover ou encarecer as receitas vanilla, revisão geral | Nenhum item avançado sai de bancada vanilla |

O multiplayer (F2-T06) continua por último, depois desta etapa, como combinado. Cada fase tem roteiro de teste e
commit próprios.

---

## 8. Decisões em aberto

| ID | Decisão | Opções | Recomendação |
|---|---|---|---|
| D11-1 | O que significa "revestimento" do molde | (a) argila que se gasta a cada N moldagens; (b) o material do molde decide os metais (molde de argila: chumbo e latão; molde de aço: ferro) | **Só (b)**: o material do molde decide o metal; sem revestimento (usuário, 2026-11-23) |
| D11-2 | Receitas vanilla dos itens avançados | (a) remover; (b) manter muito mais caras (×3) na bancada; (c) uma opção no arquivo de config | **(c)**, com "remover" como padrão |
| D11-3 | Montadora: como ligar os baús | (a) só os encostados; (b) encostados em cadeia, até 16; (c) por um cabo ou cano de itens | **(b)** agora, **(c)** na logística 2.0 |
| D11-4 | Montagem em sequência ou montadora simples para a munição | (a) só montadora; (b) as duas, e a sequência rende mais (ex.: 12 balas contra 10) | **(b)** |
| D11-5 | Metal parado na calha solidifica? | sim / não | **Não** no começo; ligar depois se ficar fácil demais |
| D11-6 | Itens incompletos podem ser carregados pelo jogador? | sim / não | **Sim** (mais simples de depurar) |
| D11-7 | Loot de peças intermediárias (cápsulas, pontas, pólvora) | manter / reduzir | Fica para o balanceamento |

---

**Aprovado pelo usuário (2026-11-23):** as recomendações de D11-1 a D11-4 valem como decididas. D11-5 a D11-7
ficam com a recomendação até o balanceamento.

## 9. Próximo passo

Fechar as decisões D11-1 a D11-4. Depois, começar a **F8.0** (arquivo de processos, painel de receita e planilha de
cobertura) e a **F8.1** (metalurgia), que já entregam a primeira metade do exemplo da munição.
