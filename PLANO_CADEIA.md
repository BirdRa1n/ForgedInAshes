# Plano da cadeia completa: todos os itens do jogo pelo mod (proposta D12, pedido do usuário 2026-11-24)

**Status: PROPOSTA.** Nada daqui foi aplicado. O usuário lê, marca o que entra e responde as decisões da seção 11.

Este plano continua o [PLANO_CRAFT.md](PLANO_CRAFT.md) (D11), que já trouxe a metalurgia, a química da pólvora e o
arquivo de processos. Ele junta as fases F8.3 a F8.11 que faltavam e acrescenta o que foi pedido agora:

1. **nenhum item normal do jogo fica sem receita**, e todos podem ser feitos pelas máquinas do mod;
2. **borracha a partir da seiva de árvore**, com um processo completo até os pneus;
3. **petróleo e derivados** numa refinaria de verdade (torre de destilação);
4. **tanques de líquido e de gás, pressão e controle de passagem** (válvulas, registros, divisores);
5. **menus próprios** fora da interface nativa, também nas máquinas que já existem;
6. **comida** numa máquina simples que junta os ingredientes;
7. maneiras interessantes de fabricar cada grupo de itens, com a cara do **Create**.

Os números (litros, tempos, quantidades, pressão) são **propostas** para a conversa de balanceamento.

---

## Sumário

1. Princípios
2. O mapa de cobertura (600 receitas)
3. Itens que o jogo não deixa fabricar (só loot ou desmanche)
4. Sistemas novos: fluidos 2.0 (tanques, gases, pressão, válvulas) e passagem nas esteiras
5. Menus próprios (interface do mod)
6. Cadeias novas, grupo por grupo
7. Máquinas e blocos novos (tabela completa)
8. Três fábricas de exemplo
9. Como fica no código
10. Fases
11. Decisões em aberto

---

## 1. Princípios

1. **Todo item tem um caminho no mod.** Para cada uma das receitas do jogo existe pelo menos uma rota pelas
   máquinas do mod. Um validador novo (`tools/check_coverage.py`) falha o build se algum item ficar sem rota.
2. **O item muda de forma em cada etapa.** O material passa por sólido, pó, fluido, peça bruta, peça acabada e
   montagem. É isso que dá espaço para esteiras, canos e máquinas, como no Create.
3. **O começo do jogo continua na mão.** O tier primitivo (pedra, madeira, osso, Fogueira, armas de cano) não muda.
   A cadeia começa no tier de ferro.
4. **A bancada vanilla deixa de ser atalho** para os itens avançados. Eles são removidos ou ficam muito mais caros
   (decisão D11-2, repetida em D12-4).
5. **Cada energia tem o seu papel:**

   | Energia | Uso |
   |---|---|
   | Torque | mover, moer, prensar |
   | Vapor | aquecer, secar, cozinhar |
   | Eletricidade | controlar, aquecer forte, montar |
   | Calor de combustível | fundir, craquear |
   | Pressão | gases, vulcanizar, polimerizar |

6. **Tudo é dado, não código, sempre que der.** Máquinas novas entram como linhas no `fe_processes.xml`. O C# só
   cresce quando aparece um *tipo* novo de comportamento (gás com pressão, estação em linha, menu).
7. **Reaproveitar antes de criar.** Uma máquina nova só entra quando nenhuma das atuais faz o verbo. A seção 7 diz,
   para cada máquina, por que ela é nova.

---

## 2. O mapa de cobertura (600 receitas)

Saída do `tools/craft_matrix.py` (jogo 3.4.0 B10). A coluna "Cadeia" diz como o grupo passa a ser feito.
A seção 6 detalha cada um.

| Grupo | Receitas | Cadeia proposta | Fase |
|---|---|---|---|
| Sem mudança (primitivo, inventário, plantio, variantes) | 119 | Igual ao jogo | — |
| Variantes `use_smelter` removidas | 33 | Já cobertas pela Fundição | feito |
| Mods de arma, armadura, ferramenta, veículo, drone | 74 | Óptica (vidro), Torno, Prensa, Eletrônica, Têxtil → **Montadora com baús** | F9.6 |
| Armaduras, roupas, mochilas | 68 | Têxtil (Fiadeira, Tear) + Curtume + Prensa (placas) → Montadora | F9.7 |
| Munição (bala, cartucho, torreta, gasolina) | 46 | Metalurgia + Química + **montagem em sequência** sobre a esteira | F9.2 |
| Comida e bebida | 46 | **Cozinha Industrial** (uma máquina, receita escolhida) + Moinho + Prensa de Suco | F9.10 |
| Serralheria: portas, cofres, garagens, escadas | 43 | Chapas e perfis (Prensa, Dobradeira) + Fechadura + Dobradiça → Serralheria | F9.8 |
| Ferramentas e armas brancas | 38 | Molde de cabeça + Prensa (forjar) + Esmeril + cabo da Serraria → Montadora | F9.6 |
| Elétrica, armadilhas, luzes, torretas | 28 | Trefila (fio) + Bobinadeira + Placa de Circuito → Bancada Eletrônica | F9.9 |
| Armas de fogo e arcos | 19 | Cano (Molde de Tubo + Torno), Mecanismo, Coronha → Montadora | F9.6 |
| Veículos | 16 | Chassi (Dobradeira + Soldadora), Rodas (**pneu de borracha**), Motor → Garagem | F9.9 |
| Remédios | 13 | Fermentação + Centrífuga + Destilação + Secador | F9.10 |
| Metal (lingote, prego, cano, lente, barras) | 12 | Fundição + Moldes + Trefila + Esmeril | F9.5 |
| Explosivos e armas de arremesso | 11 | Carcaça moldada + Pólvora / Gasolina + Bico Dosador | F9.6 |
| Flechas e virotes | 10 | Serraria (haste) + Molde de ponta + Pena colada → em linha | F9.2 |
| Materiais de construção | 8 | Triturar + Forno + Misturar (concreto fluido, **asfalto de betume**, vidro) | F9.8 |
| Química (gasolina, óleo, cola, tinta, papel, bateria) | 7 | **Refinaria (torre)** + Autoclave + Misturador Químico | F9.3 |
| Robótica | 5 | Eletrônica + Servo + Bateria → Robótica | F9.9 |
| Foguetes | 4 | Carcaça moldada + Pólvora + Ponta → em linha | F9.2 |

Ao todo, **448 receitas ganham cadeia** e 152 ficam como estão.

---

## 3. Itens que o jogo não deixa fabricar (só loot ou desmanche)

Para "não faltar craft dos itens normais", estes ingredientes também precisam de uma rota. Hoje eles só vêm de
loot ou desmanche.

| Item do jogo | Usado em (receitas) | Rota nova no mod |
|---|---|---|
| Mola (`resourceSpring`) | 84 | **feito** no Torno (F3). Passa para a **Enroladora de Molas**: fio de aço (Trefila) → mola |
| Peças Mecânicas (`resourceMechanicalParts`) | muitas | **feito** no Torno (F3). Passa a ser montagem: Engrenagem + Mola + Eixo → Montadora |
| Peças Elétricas (`resourceElectricParts`) | muitas | Fio de Latão + Bobina + Chapa → Bancada Eletrônica |
| Polímero (`resourceScrapPolymers`) | rodas, bateria, mods | **Reator de Polimerização** (nafta) → Injetora → Polímero |
| Ácido (`resourceAcid`) | 9 | **Torre de Lavagem de Gás**: gás de xisto + água → Ácido (e Enxofre) |
| Gordura Animal (`resourceAnimalFat`) | 20 | Continua da caça; nova rota: Prensa de Óleo (milho, girassol de vaso) → Gordura Vegetal |
| Kit de Costura (`resourceSewingKit`) | 21 | Agulha (Trefila de aço + Esmeril) + Linha (Fiadeira) → Montadora |
| Farol (`resourceHeadlight`) | 12 | Refletor (chapa prensada) + Lente (vidro) + Lâmpada → Bancada Eletrônica |
| Motor Pequeno (`smallEngine`) | 7 | **feito** na Garagem (F4). Passa para a montagem em sequência (seção 6.9) |
| Radiador (`resourceRadiator`) | 2 | Tubinho de latão (Trefila) + Chapa de latão → Montadora |
| Béquer (`toolBeaker`) | 1 | Vidro fundido → Molde de Béquer |
| Vitaminas (`drugVitamins`) | 4 | Frutas → Prensa de Suco → Concentrado → Secador → Vitaminas |
| Comida enlatada (`foodCan*`) | 11 | **Enlatadora** (opcional, D12-5): lata (chapa) + comida pronta + vapor |
| Carvão mineral, xisto, salitre, chumbo, plantas, ovos, mel | — | Matéria-prima: continua vindo do mundo (mineração, plantio, animais) |
| Peças Lendárias, Moedas, Diamante, Extrato de Testosterona | — | **Continuam só loot.** São recompensa, não material de fábrica |

---

## 4. Sistemas novos

### 4.1 Fluidos 2.0: líquidos e gases

Hoje cada rede de canos leva **um fluido**, em litros, e casa a oferta com a demanda a cada 0,5 s. Isso continua
valendo. Entram três coisas novas.

**a) Duas classes de fluido**

| Classe | Fluidos | Como anda |
|---|---|---|
| Líquido | água, óleo cru, gasolina, nafta, óleo combustível, lubrificante, látex, ácido, betume quente, concreto fresco, mosto, metal fundido (só em calha) | Como hoje: a bomba empurra e a vazão depende das RPM ou dos watts |
| Gás | vapor, gás de xisto, gás combustível, ar comprimido | **Com pressão** (bar). O gás vai sozinho da pressão alta para a baixa; o compressor aumenta a pressão |

**b) Pressão (só gases)**

- **Pressão da rede** = gás guardado ÷ volume da rede (canos + tanques). Um cano tem volume pequeno, um tanque tem
  volume grande. O manômetro e o Painel de Rede (5.4) mostram o valor em bar.
- **Fontes** (caldeira, Motor a Vapor, Retorta) empurram gás até a pressão de trabalho delas, por exemplo 4 bar.
  Com a rede cheia, a fonte para de produzir ou solta pela válvula de alívio.
- O **Compressor** (torque) leva o gás de uma rede de pressão baixa para uma de pressão alta: até 10 bar no Tanque
  de Gás.
- **Consumidores pedem uma pressão mínima:**

  | Consumidor | Pressão mínima |
  |---|---|
  | Queimador a Gás | 1 bar |
  | Prensa de Vulcanização | 3 bar de vapor |
  | Reator de Polimerização | 6 bar |

  Abaixo disso a máquina para e mostra "pressão baixa".
- **Limite do cano:**

  | Cano | Limite |
  |---|---|
  | Cano comum | 4 bar |
  | Cano de Alta Pressão | 12 bar (aço + juntas de borracha) |

  Acima do limite, o cano **vaza**: perde gás e solta vapor no ar. Se o cano estoura, isso é a decisão D12-3.
- **Vapor dos motores atuais:** o Motor a Vapor e a Condensadora passam a trabalhar a 2 bar. Isso não muda nada para
  quem já montou a linha, porque o cano comum aguenta 4 bar.

**c) Tanques**

| Bloco | Guarda | Detalhe |
|---|---|---|
| **Tanque de Líquido** | 8.000 L por bloco | Estilo Create: tanques encostados (em cima e dos lados) **viram um tanque só**, até 3×3×6. O nível aparece no vidro. Entrada e saída por qualquer face com cano |
| **Tanque de Gás** (cilindro) | 2.000 L a 1 bar por bloco (20.000 L a 10 bar) | Também se junta com os vizinhos. Precisa de Cano de Alta Pressão acima de 4 bar |
| Caixa d'Água (já existe) | 4.000 L | Continua como tanque barato de começo de jogo |

O tanque não perde o conteúdo ao ser quebrado com a chave (como a Caixa d'Água), para dar para mudar a fábrica de
lugar.

**d) Controle de passagem (canos)**

| Bloco | O que faz | Comando |
|---|---|---|
| **Registro** | Abre e fecha o cano | Na mão (E) ou por **fio elétrico**: aberto quando recebe energia, o que liga em interruptor, sensor ou timer vanilla |
| **Válvula Reguladora** | Limita a vazão em L/min (líquido) ou a pressão de saída em bar (gás) | Menu próprio com controle deslizante (5.3) |
| **Válvula de Retenção** | Deixa passar só num sentido (a seta no bloco) | — |
| **Válvula de Alívio** | Solta gás no ar acima de uma pressão escolhida; protege os canos | Menu (5.3) |
| **Separador de Fluido** | Junta duas redes e deixa passar **só um fluido**. Exemplo: o tanque misturado da destilação manda só a gasolina para um lado | Menu: escolhe o fluido |
| **Manômetro / Medidor** | Mostra a pressão, a vazão e o fluido ao olhar, e manda sinal elétrico acima ou abaixo de um valor | Menu: limite |

O manômetro com sinal fecha o ciclo de automação: com o tanque cheio, o sinal fecha o registro, ou desliga o motor
pela Embreagem. Isso já existe na rede de torque; basta ligar a Embreagem ao fio.

### 4.2 Passagem nas esteiras

| Bloco | O que faz |
|---|---|
| **Divisor de Esteira** | Uma entrada e até três saídas. Divide em rodízio ou por proporção (menu: 1:1, 2:1, …) |
| **Comporta** | Para a esteira enquanto recebe energia (sinal) |
| **Contador** | Conta os itens que passam e manda um pulso a cada N (menu) |
| **Braço Mecânico** (D12-7) | Pega da esteira, de um baú ou da saída de uma máquina e põe em até 4 destinos escolhidos no menu, em alcance de 2 blocos. É o "Mechanical Arm" do Create e resolve linhas apertadas |
| Esteira com Filtro (já existe) | Ganha o menu de escolha de item (5.3) em vez de copiar o item da mão |
| Funil (já existe) | Ganha quantidade por vez e filtro no menu |

---

## 5. Menus próprios (interface do mod)

Hoje a interação é o texto de mira mais o menu radial (segurar E). A janela de Receitas mostrou que a janela própria
do XUi funciona (`Config/XUi_InGame`, controller `FerroEngrenagem.XUiC_*`). A proposta tem cinco janelas, todas no
mesmo estilo (cabeçalho, ícones do atlas do mod, cores do jogo).

### 5.1 Painel da Máquina (todas as máquinas de processo)

Abre com E (toque curto) nas máquinas que hoje não têm janela: Triturador, Lavadora, Secador, Misturador,
Biodigestores, Fundição como fonte, Mesa de Moldagem e todas as novas.

```
┌ Triturador ─────────────────────────── [ligado ●] ┐
│ Receita: [ícone] Pó de Carvão        [Trocar…]    │
│ ████████████░░░░░░  62 %   (2 s restantes)        │
│ Entrada: [carvão ×14]    Saída: [pó ×6]  [Retirar]│
│ Torque: 128 / 128 UT  ✔   Água: —   Vapor: —      │
│ Motivo de parada: —                               │
│ Lados: ◀ esteira  ▶ esteira  ▼ calha  ▲ —         │
└───────────────────────────────────────────────────┘
```

- Barras de fluido com cor (água azul, óleo preto, látex branco, metal laranja) e pressão quando for gás.
- Estoque interno com botão para retirar (hoje só pela esteira).
- "Lados" mostra que porta é cada face. Ajuda a montar a linha sem errar.
- Liga e desliga sem quebrar a máquina.

### 5.2 Seletor de Receita

Substitui o ciclo "Escolher receita" (que dava uma volta a cada clique):

- uma grade de **ícones** das receitas da máquina, com busca por nome;
- cada receita mostra entradas e saídas com ícone, tempo e energia;
- em vermelho, **o que falta** agora (ingrediente, torque, água, pressão);
- vale também para as bancadas do mod (Montadora, Torno, Prensa…). Isso substitui o "fabrique uma vez à mão" da
  receita fixa.

### 5.3 Configurador (blocos de controle)

Uma janela pequena e genérica com controles deslizantes, botões e escolha de item. Serve para a Válvula Reguladora,
a Válvula de Alívio, o Separador, o Manômetro, o Divisor, o Contador, o Filtro de Esteira, o Funil e o Braço
Mecânico. A escolha de item usa a grade do inventário do jogador, sem precisar ter o item na mão.

### 5.4 Painel de Rede

Abre com a **Chave de Engenheiro** (item novo; o alicate vanilla continua para os fios) em qualquer cano, eixo ou
esteira:

- **Torque:** fontes, consumidores, UT usado/disponível, RPM e quem está sobrecarregando. Hoje isso só aparece no log.
- **Fluido:** o fluido, o volume, a pressão, a vazão, quem oferece e quem pede, e o motivo de bloqueio ("dois
  fluidos na mesma rede: água e óleo, no cano em X,Y,Z").
- **Esteira:** itens em trânsito e onde está parado.

### 5.5 Guia de Produção (o "JEI/Ponder" do mod)

Um livro, o **Manual do Engenheiro**, que o jogador começa com. Também abre por uma tecla configurável ou pelo
botão "Como fazer?" no tooltip do item.

- **Buscar qualquer item do jogo** mostra a árvore da cadeia, de baixo para cima:

  ```
  Pneu ← Prensa de Vulcanização ← Composto de Borracha ← Misturadora ← Borracha Crua + Negro de Fumo + Enxofre
  ```

  Cada nó mostra o ícone, a máquina e a energia, e clicar num nó abre o item.
- **"Onde é usado"**, a lista inversa.
- **Uma página por máquina**, com as portas (desenho simples em blocos) e as receitas.
- É gerado sozinho a partir do `fe_processes.xml` e das receitas. O mesmo `check_coverage.py` garante que todo item
  tem página.

### 5.6 Retrofit das máquinas antigas

| Já existe | Ganha |
|---|---|
| Motor a Vapor, Caldeira, Condensadora | Painel da Máquina (água, vapor e pressão em barras) |
| Embreagem, Regulador, Caixa de Velocidade | Configurador (relação, limite de UT); Embreagem por sinal elétrico |
| Esteira com Filtro, Funil | Configurador com escolha de item |
| Bancadas do mod (Montadora, Torno, Prensa…) | Seletor de Receita no lugar do ciclo |
| Biodigestores, Triturador, Lavadora, Secador, Misturador | Painel da Máquina + Seletor |
| Mesa de Moldagem, Moldadora | Painel (molde atual, metal aceito, peças esperando) |
| Todos os canos, eixos e esteiras | Painel de Rede pela Chave de Engenheiro |
| Janela de Receitas (texto) | Substituída pelo Guia de Produção |

O texto de mira fica curto (nome + estado em uma linha), porque o detalhe vai para os painéis. Isso resolve de vez o
texto pequeno.

---

## 6. Cadeias novas, grupo por grupo

### 6.1 Petróleo e Refinaria

O jogo hoje transforma 1 xisto em 2 latas de gasolina na Estação Química. Com o mod, isso vira uma refinaria.

```
Xisto ─► Triturador ─► Xisto Moído ─► Retorta de Xisto (calor) ─┬► Óleo Cru (líquido) ──► Torre de Destilação
                                                                ├► Gás de Xisto (gás) ──► Torre de Lavagem
                                                                └► Cinza de Xisto ──► (cimento, 6.8)
```

**Retorta de Xisto** (2×2×2): aquece o xisto sem ar, com carvão, Queimador a Gás ou eletricidade.

| Entra | Sai | Tempo |
|---|---|---|
| 10 Xisto Moído | 40 L Óleo Cru + 60 L Gás de Xisto (1 bar) + 2 Cinza | 60 s |

**Torre de Destilação** (multibloco montado pelo jogador, estilo Create):

- **Base:** a Caldeira da Torre (vapor ou queimador a gás) recebe o Óleo Cru.
- **Em cima dela, 1 a 4 Seções de Torre empilhadas.** Cada seção tem uma porta de saída e solta **uma fração**. Mais
  seções, mais frações:

  | Seção (de baixo para cima) | Fração | Uso |
  |---|---|---|
  | Base (fundo) | **Betume** (líquido quente) | Asfalto (6.8), impermeabilizante |
  | Seção 1 | **Óleo Combustível** | Queimadores, Motor a Carvão adaptado, craqueamento |
  | Seção 2 | **Óleo Base** | Lubrificante (+ aditivo), `resourceOil` (Envasadora) |
  | Seção 3 | **Gasolina** | Envasadora → `ammoGasCan`, motores, gerador |
  | Seção 4 (topo) | **Nafta** + Gás Combustível | Polímeros (6.3), Queimadores |

- A torre só com a seção 1 já dá gasolina "suja": menos gasolina, mais óleo. O jogador começa pequeno e cresce,
  como o Create.

  | Entra | Sai | Tempo |
  |---|---|---|
  | 100 L Óleo Cru | 25 Gasolina + 20 Óleo Base + 20 Óleo Combustível + 15 Nafta + 10 Betume + 10 Gás | 30 s |

**Craqueador Catalítico** (elétrico, 400 W): quebra óleo pesado em gasolina. É o melhor uso do óleo que sobra.

| Entra | Sai |
|---|---|
| 50 L Óleo Combustível | 30 L Gasolina + 10 L Gás |

**Torre de Lavagem de Gás**: tira o enxofre do gás de xisto com água. Dá o **Ácido** que o jogo não deixa fabricar e
o **Enxofre** que a borracha usa.

| Entra | Sai |
|---|---|
| 100 L Gás de Xisto + 20 L água | 80 L Gás Combustível + 1 Ácido (`resourceAcid`) + 2 Enxofre |

**Gás Combustível:**
- vai por cano ao **Queimador a Gás**, que se encosta na Fundição, na Retorta, na Caldeira ou na Torre e substitui o
  carvão;
- ou vai para o **Motor a Gás** (fonte de torque nova, sem esteira de combustível).

| Hoje no jogo | No mod |
|---|---|
| `ammoGasCan` (xisto na Estação Química) | Gasolina da torre → Envasadora + lata vazia (chapa) |
| `resourceOil` | Óleo Base → Envasadora com pote |
| `terrAsphalt` | Betume + areia + cascalho → Misturadora |
| `resourceAcid` | Torre de Lavagem |
| Lubrificante (mod) | Óleo Base + Gordura → Misturador Químico |

### 6.2 Borracha da seiva de árvore → pneus

O pedido: borracha tirada da árvore, com um processo inteiro. O 7DTD não tem árvore de selva, então a proposta tem
duas fontes (decisão D12-2).

**Fonte A: Seringueira (árvore nova).**
- A semente vem do trader ou da Fiadeira (procurando no algodão; detalhe para o balanceamento).
- Ela é plantada e cresce como o carvalho plantado do jogo, usando o mesmo modelo com casca e folhas tingidas.
- Dá muito látex.

**Fonte B: árvores do jogo.** Carvalho e bordo dão pouco látex (seiva grossa). Isso permite começar sem plantar.

**Linha:**

1. **Sangrador de Seiva:** um bloco pequeno preso no tronco (encosta num bloco de árvore viva). O látex pinga e sai
   por um cano: 2 L/min na Seringueira, 0,3 L/min no carvalho. Vários sangradores numa floresta plantada, ligados
   por canos, enchem um tanque. É a "fazenda de látex".
2. **Tanque de Coagulação** (o Misturador Químico, receita nova): 20 L Látex + 1 L Ácido diluído → 1 **Coágulo de
   Borracha**. Pode usar Vinagre do Biodigestor no lugar do ácido (D12-2).
3. **Calandra** (máquina nova, 2 rolos, torque): o coágulo passa entre rolos com água por cima → **Folha de Borracha
   Crua** (lavada e prensada).
4. **Secador a Vapor** (já existe; é a defumação da borracha): folha → **Borracha Crua**.
5. **Misturadora** (já existe): 4 Borracha Crua + 1 **Negro de Fumo** (fuligem da Retorta ou Pó de Carvão) + 1
   **Enxofre** (Torre de Lavagem) → **Composto de Borracha**.
6. **Prensa de Vulcanização** (máquina nova): vapor a 3 bar + torque + um **molde**. Composto → peça vulcanizada:

   | Molde | Peça | Usada em |
   |---|---|---|
   | Molde de Pneu | **Pneu** | Rodas de todos os veículos |
   | Molde de Junta | **Junta de Vedação** (×8) | Cano de Alta Pressão, Tanque de Gás, motores |
   | Molde de Correia | **Correia de Borracha** | Esteira Rápida (tier novo), Motor Pequeno |
   | Molde de Mangueira | **Mangueira** | Cano Flexível (passa em diagonal e em curva, decorativo) |
   | Molde de Sola | **Sola** | Botas das armaduras (6.7) |

**Rota sintética (fim de jogo):** Nafta → Reator de Polimerização com o catalisador "borracha" → Borracha Sintética,
que substitui a Borracha Crua no passo 5. Dá para viver sem árvores, mas custa pressão e eletricidade.

**Rodas (`vehicleWheels`):**
- **Aro:** chapa de aço na Dobradeira.
- **Cubo:** Torno.
- **Roda** = Aro + Cubo + Pneu → Montadora.

A receita vanilla (polímero + óleo + carvão + ácido) sai.

### 6.3 Plásticos (polímeros)

1. **Reator de Polimerização** (2×2×3, 300 W, 6 bar): 40 L Nafta + catalisador (Pó de Carvão ou Enxofre) → 40 L
   **Polímero Fundido**. Ele sai por uma calha própria, como o metal.
2. **Injetora de Plástico** (moldes, como a Mesa de Moldagem, com pressão):

   | Molde | Peça |
   |---|---|
   | Pellet | `resourceScrapPolymers` (o polímero do jogo) |
   | Placa de Circuito | Base da placa (6.9) |
   | Caixa de Bateria | Bateria do carro (6.9) |
   | Coronha Sintética | Coronha das armas do tier 3 |
   | Corpo de Lanterna | Lanterna, luzes |

3. **Reciclagem:** polímero de desmanche → Triturador → Pó de Polímero → Injetora (o loot vira matéria-prima).

### 6.4 Vidro e cerâmica

A Fundição ganha mais um fluido: **Vidro Fundido**, de 4 Areia (Triturador) + 1 Cinza (Retorta ou madeira queimada).

| Molde (Mesa de Moldagem) | Peça | Depois |
|---|---|---|
| Pote | `drinkJarEmpty` | Cozinha, Envasadora |
| Lente Bruta | → **Esmeril** (polir) → `resourceScopeLens` | Miras, faróis, lanternas |
| Béquer | `toolBeaker` | Laboratório |
| Placa de Vidro | `glassBlock`, vidro à prova de bala (com polímero em camadas) | Construção |
| Bulbo | → Bancada Eletrônica com filamento (fio de aço fino) → **Lâmpada** | Luzes, Farol |

**Cerâmica:** argila na Mesa de Moldagem **sem metal**, com Molde de Isolador ou de Vela. A peça vai ao **Forno**
(Retorta em modo cerâmica) → Isolador (elétrica) e Vela de Ignição (motores).

### 6.5 Metal avançado

| Peça | Máquina | Cadeia |
|---|---|---|
| Aço (`resourceForgedSteel`) | **Conversor de Aço** (novo, na saída da Fundição) | Ferro Fundido + Pó de Carvão → Aço Fundido. Ar comprimido (Compressor) acelera ×2. Hoje o aço só vem de fundir lingote |
| Fio (latão, aço) | **Trefila** (estação em linha) | Vareta moldada passa 3 vezes: grossa → média → fio. Cada passagem é uma Trefila em sequência na esteira |
| Prego (`resourceNail`) | Cortadora (Prensa em Linha com Matriz de Prego) | Fio de aço → pregos ×10 |
| Mola | **Enroladora de Molas** (Torno com acessório) | Fio de aço → Mola |
| Cano de metal | Molde de Tubo → Torno (rosca) | `resourceMetalPipe` |
| Chapa, perfil | Prensa; **Dobradeira** (nova, em linha) | Chapa → Perfil em U, Aro, Calha decorativa |
| Peças Mecânicas | Montadora | Engrenagem + Mola + Eixo |
| Barras e treliças | Prensa + Soldadora | Perfil → treliça |

### 6.6 Armas, ferramentas, explosivos e mods

**Armas** (já desenhado no PLANO_CRAFT 4.2), por tier:

| Tier | Cano | Mecanismo | Coronha |
|---|---|---|---|
| T1 | Ferro (Molde de Tubo + Torno: furar, estriar) | Engrenagem + Mola + Chapa | Madeira (Serraria + Torno) |
| T2 | Aço | Mecanismo + Gatilho de Aço | Madeira tratada (Autoclave com óleo) |
| T3 | Aço temperado (**Forno de Têmpera**: vapor + óleo) | Mecanismo + **Placa de Circuito** (miras, rajada) | Polímero (Injetora) |

Os "Parts" das armas (`gun*Parts`) passam a ser **montados** com essas peças.

**Ferramentas:** Molde de Cabeça (machado, picareta, pá, marreta) → Prensa (forjar) → Esmeril (afiar) → + Cabo
(Serraria + Torno) → Montadora. As T3 elétricas (motosserra, broca, pregadora, parafusadeira) somam Motor Elétrico
Pequeno (Bobina + Eixo + Carcaça) + Bateria.

**Explosivos:**

| Item | Cadeia |
|---|---|
| Granada | Carcaça (molde de ferro) → Bico Dosador (pólvora) → Encaixador (pino + mola) |
| Dinamite | Papel (6.11) + Pólvora + Cola → em linha |
| Coquetel Molotov | Pote + Gasolina (Envasadora) + Tecido |
| Bomba de Cano | Cano + Pólvora + Pregos + Encaixador |
| Carga Temporizada | Carcaça + Pólvora + Placa de Circuito + Relógio |

**Mods (74):** cada mod é feito por um tipo de peça base. O Guia lista todos.

| Família | Peça base | Máquinas |
|---|---|---|
| Miras e laser | Lente polida + Tubo + Placa | Vidro, Esmeril, Eletrônica |
| Cano (silenciador, freio de boca, extensor, choke) | Tubo de aço | Torno |
| Gatilhos (semi, rajada, auto) | Mecanismo + Mola + Placa | Montadora |
| Carregadores | Chapa dobrada + Mola | Dobradeira |
| Placas de armadura | Chapa de aço temperada | Prensa + Forno de Têmpera |
| Bolsos e encaixes | Tecido + Couro Curtido + Fivela | Têxtil |
| Mods de arma branca | Pontas, correntes, lâminas | Prensa, Esmeril, Trefila |
| Mods de veículo | Chapa, Correia, Motor, Tanque | Garagem |
| Mods de drone | Placa, Servo, Lâmpada | Robótica |

### 6.7 Têxtil, couro e armaduras

- **Fiadeira** (nova, torque): Algodão ou Fibra de Iúca → Linha. Ela substitui o "algodão → tecido" na mão para
  o tier de ferro em diante. O Pano vanilla continua na mão para os curativos.
- **Tear** (já existe, `feLoom`): Linha → Rolo de Tecido. Ganha a versão com receita escolhida e esteira.
- **Curtume** (tanque novo, água por cano): Couro + Ácido (ou Casca de Árvore triturada) + 10 min → **Couro
  Curtido**. A armadura de couro do tier 1 em diante pede couro curtido.
- **Armaduras:** Tecido + Couro Curtido + Sola (borracha) + Placas (Prensa) → Montadora, conjunto por conjunto. Os
  17 conjuntos seguem três "moldes de costura" (leve, médio, pesado), para não precisar de 68 cadeias diferentes.
- **Mochilas:** Tecido + Couro + Fivela (Prensa) + Zíper (Trefila).

### 6.8 Construção

- **Concreto fluido** (PLANO_CRAFT 4.4): Cimento (Cinza + Pedra moída no forno) + Areia + Cascalho + água →
  Misturadora → **Concreto Fresco** por cano → Mesa de Moldagem com **Molde de Bloco** (sai o bloco pronto) ou
  Envasadora em saco (`resourceConcreteMix`).
- **Asfalto:** Betume quente (Torre) + Areia + Cascalho → Misturadora → `terrAsphalt`.
- **Portas, cofres, garagens (43):** Chapas + Perfis + **Dobradiça** (Prensa) + **Fechadura** (Mecanismo + Mola +
  Chave) → Serralheria. As portas motorizadas pedem também um Motor Elétrico Pequeno.
- **Vidro:** 6.4.

### 6.9 Eletrônica, elétrica, veículos e robótica

**Placa de Circuito:**
1. base de polímero (Injetora);
2. **Bico Dosador** de trilhas: o jogo não tem cobre, então as trilhas são de pó de latão (latão no Triturador);
3. **Encaixador** de componentes (resistor de cerâmica, capacitor, chip de desmanche);
4. **Forno de Refusão** (estação em linha, elétrica).

**Peças Elétricas:** Fio + Bobina + Isolador (cerâmica) → Bancada Eletrônica.

**Bateria do Carro (`carBattery`):** placas de chumbo moldadas + Caixa de Bateria (Injetora) + Ácido (Bico Dosador
com ácido) → em linha. Ela sai da Estação Química.

**Elétrica, armadilhas e torretas (28):** Fio + Placa + Carcaça (chapa) + Lâmpada/Sensor → Bancada Eletrônica. As
torretas pedem também Mecanismo e Cano.

**Motor Pequeno (`smallEngine`)**, montagem em sequência na esteira:
1. Bloco de Motor moldado (Molde grande) passa no Torno (cilindro);
2. Encaixador: Pistão (moldado + Torno);
3. Encaixador: Virabrequim (aço + Torno);
4. Encaixador: Vela (cerâmica);
5. Bico Dosador: Lubrificante;
6. Crimpadora: tampa com Junta de Vedação.

**Veículos:**

| Peça | Cadeia |
|---|---|
| Chassi | Perfis (Dobradeira) → **Soldadora** (estação em linha, elétrica) |
| Guidão | Tubo → Dobradeira |
| Rodas | Pneu + Aro + Cubo (6.2) |
| Assento | Tecido + Couro + Espuma de polímero |
| Acessórios | Farol + Radiador + Bateria |

A montagem final continua na Garagem (`feGarage`), agora puxando de baús ligados.

**Robótica:** Servo (Motor Elétrico Pequeno + Engrenagem + Placa) + Bateria + Carcaça → Robótica.

### 6.10 Remédios e comida

**Remédios** (Laboratório, `feLab`, e máquinas de apoio):

| Item | Cadeia |
|---|---|
| Antibiótico | Cogumelos + Pão → **Tanque de Fermentação** (5 min, água morna do vapor) → Caldo de Cultura → **Centrífuga** → Extrato → Secador → Antibiótico. É a penicilina de verdade |
| Antibiótico Herbal | Goldenrod + Babosa → Prensa de Suco → Destilação no Laboratório |
| Fortbites, Recog, Esteroides | Extrato + Mel / Café / Testosterona (loot) → Misturador Químico → Secador |
| Kit de Primeiros Socorros | Curativo + Bolsa de Sangue + Álcool (Destilação do Mosto) + Kit de Costura → Montadora |
| Gesso | Gesso em pó (pedra → Triturador → Forno) + Tecido → Montadora |
| Vitaminas | Frutas → Prensa de Suco → Concentrado → Secador |

**Comida.** O pedido é uma máquina simples que junta os ingredientes:

- **Cozinha Industrial** (1 máquina, 2×1, vapor ou queimador):
  - recebe os ingredientes por esteira em qualquer lado e água por cano;
  - a receita é escolhida no Seletor (5.2), com as **mesmas 46 receitas do jogo**, as mesmas quantidades e o mesmo
    resultado;
  - cozinha em **lote de 4** com metade do tempo por unidade;
  - a saída vai pela frente para a esteira ou para um baú com Funil.
- **Moinho** (torque, opcional): Milho → Fubá (`foodCornMeal`) para os pães. Hoje é na mão.
- **Prensa de Suco** (torque): frutas → bebidas e concentrados (suco de iúca, chás). A Cozinha pode usar no lugar
  da fruta.
- **Água fervida em escala:** água do cano + potes vazios (6.4) → Cozinha → `drinkJarBoiledWater` ×4. Fecha o ciclo
  da água sem coletor de orvalho.
- **Enlatadora** (opcional, D12-5): lata (chapa) + comida pronta → comida enlatada. Ela não estraga e é boa para
  vender ao trader. É um uso para o excesso das fazendas.
- **A Fogueira e a Panela continuam funcionando** igual ao jogo (princípio 3).

### 6.11 Química restante

| Item | Cadeia |
|---|---|
| Cola (`resourceGlue`) | Ossos + água → **Autoclave** (vapor 3 bar, nova) → Cola. Hoje é na Panela |
| Fita (`resourceDuctTape`) | Cola + Tecido → Calandra (fita) |
| Tinta (`resourcePaint`) | Crisântemo → Prensa de Suco → Pigmento + Óleo Base → Misturador Químico |
| Papel (`resourcePaper`) | Madeira → Triturador → Polpa + água → **Calandra** (folha) → Secador |
| Pólvora em lote | Já feita (F8.2) |

---

## 7. Máquinas e blocos novos (tabela completa)

Legenda: **P** = só dado (`fe_processes.xml`, sem C# novo); **C** = precisa de comportamento novo em C#;
**M** = modelo 3D novo. As que já existem aparecem só quando ganham receita nova.

| # | Máquina / bloco | Grupo | Energia | Tamanho | Por que é nova | Tipo |
|---|---|---|---|---|---|---|
| 1 | Retorta de Xisto | Petróleo | calor (carvão/gás/elétrico) | 2×2×2 | Pirólise; tem 3 saídas (líquido, gás, item) | P+M |
| 2 | Caldeira da Torre | Petróleo | vapor ou gás | 3×3×1 | Base do multibloco | C+M |
| 3 | Seção de Torre | Petróleo | — | 3×3×1 | Empilha; uma fração por seção | C+M |
| 4 | Craqueador Catalítico | Petróleo | 400 W | 2×2×2 | Óleo pesado → gasolina | P+M |
| 5 | Torre de Lavagem de Gás | Petróleo | — | 1×1×3 | Gás + água → ácido + enxofre | P+M |
| 6 | Queimador a Gás | Calor | gás 1 bar | 1×1 | Fonte de calor encostável (troca o carvão) | C+M |
| 7 | Motor a Gás | Torque | gás | 2×1 | Fonte de torque sem esteira | P+M (como o Motor a Gasolina) |
| 8 | Reator de Polimerização | Plástico | 300 W + 6 bar | 2×2×3 | Pressão + catalisador | P+M |
| 9 | Injetora de Plástico | Plástico | torque | 2×1 | Mesa de Moldagem com pressão | P+M |
| 10 | Sangrador de Seiva | Borracha | — | pequeno | Lê a árvore encostada, pinga látex | C+M |
| 11 | Seringueira (árvore) | Borracha | — | árvore | Planta nova | XML (modelo do carvalho tingido) |
| 12 | Calandra | Borracha, papel | torque | 2×1 | Rolos: folha de borracha, papel, fita | P+M |
| 13 | Prensa de Vulcanização | Borracha | vapor 3 bar + torque | 2×2×2 | Moldes de borracha | P+M |
| 14 | Tanque de Líquido | Fluidos | — | 1×1, junta até 3×3×6 | Tanque que se junta | C+M |
| 15 | Tanque de Gás | Fluidos | — | 1×1, junta | Pressão | C+M |
| 16 | Compressor | Fluidos | torque | 1×2 | Sobe a pressão | C+M |
| 17 | Cano de Alta Pressão | Fluidos | — | 1×1 | 12 bar | C (tier de cano) |
| 18 | Registro | Fluidos | sinal | 1×1 | Abre/fecha | C+M |
| 19 | Válvula Reguladora | Fluidos | — | 1×1 | Limita vazão/pressão | C+M |
| 20 | Válvula de Retenção | Fluidos | — | 1×1 | Um sentido | C+M |
| 21 | Válvula de Alívio | Fluidos | — | 1×1 | Solta acima de X bar | C+M |
| 22 | Separador de Fluido | Fluidos | — | 1×1 | Ponte de um fluido entre redes | C+M |
| 23 | Manômetro | Fluidos | — | 1×1 | Leitura + sinal | C+M |
| 24 | Divisor de Esteira | Esteira | — | 1×1 | Rodízio/proporção | C+M |
| 25 | Comporta | Esteira | sinal | 1×1 | Para a esteira | C+M |
| 26 | Contador | Esteira | — | 1×1 | Pulso a cada N | C+M |
| 27 | Braço Mecânico | Esteira | 60 W | 1×1 | Pega e põe (D12-7) | C+M |
| 28 | Prensa em Linha | Em linha | torque | sobre esteira | (já planejada, F8.3) | C+M |
| 29 | Bico Dosador | Em linha | — | sobre esteira | Põe fluido ou pó no item | C+M |
| 30 | Encaixador | Em linha | torque | sobre esteira | Põe uma peça no item | C+M |
| 31 | Crimpadora | Em linha | torque | sobre esteira | Fecha o item | C+M |
| 32 | Trefila | Em linha | torque | sobre esteira | Vareta → fio (em passagens) | P+M (usa a estação em linha) |
| 33 | Esmeril | Em linha | torque | sobre esteira | Afiar, polir lente | P+M |
| 34 | Soldadora | Em linha | 200 W | sobre esteira | Perfis → chassi | P+M |
| 35 | Dobradeira | Em linha | torque | sobre esteira | Chapa → perfil, aro | P+M |
| 36 | Forno de Refusão | Em linha | 150 W | sobre esteira | Placa de circuito | P+M |
| 37 | Montadora com baús | Montagem | elétrica | (Montadora atual) | Puxa de até 16 baús (F8.3) | C |
| 38 | Conversor de Aço | Metal | calor + ar | 2×2×2 | Ferro → aço fundido | P+M |
| 39 | Enroladora de Molas | Metal | torque | 1×1 | Fio → mola | P+M |
| 40 | Forno de Têmpera | Metal | vapor + óleo | 2×1 | Aço temperado | P+M |
| 41 | Fiadeira | Têxtil | torque | 1×2 | Fibra → linha | P+M |
| 42 | Curtume | Têxtil | água | 2×2 | Couro → couro curtido | P+M |
| 43 | Tanque de Fermentação | Remédio/comida | vapor (morno) | 1×1×2 | Cultura, vinagre, álcool | P+M |
| 44 | Centrífuga | Remédio | elétrica | 1×1 | Separa caldo | P+M |
| 45 | Autoclave | Química | vapor 3 bar | 1×1×2 | Cola, esterilizar, madeira tratada | P+M |
| 46 | Cozinha Industrial | Comida | vapor/gás | 2×1 | Junta ingredientes, lote de 4 | P+M (reaproveita a `feKitchen`) |
| 47 | Moinho | Comida | torque | 1×1 | Milho → fubá | P+M |
| 48 | Prensa de Suco | Comida/química | torque | 1×1 | Frutas → suco/pigmento/óleo | P+M |
| 49 | Enlatadora | Comida | vapor | 1×2 | Opcional (D12-5) | P+M |
| 50 | Chave de Engenheiro | Ferramenta | — | item | Abre o Painel de Rede | C |
| 51 | Manual do Engenheiro | Guia | — | item | Abre o Guia de Produção | C |

São **49 blocos e 2 itens**. Cerca de 30 são "P+M": só dado e modelo, com o mesmo `ProcessMachine` de hoje.

**Itens intermediários novos** (cerca de 70): Xisto Moído, Óleo Cru e as frações (fluidos), Gás de Xisto e Gás
Combustível, Cinza, Enxofre, Negro de Fumo, Látex, Coágulo, Folha de Borracha, Borracha Crua, Composto de Borracha,
Pneu, Junta de Vedação, Correia, Mangueira, Sola, Polímero Fundido, Vidro Fundido, Lente Bruta, Bulbo, Lâmpada,
Isolador, Vela, Vareta, Fio de Aço, Perfil, Aro, Cubo, Dobradiça, Fechadura, Fivela, Zíper, Linha, Couro Curtido,
Placa de Circuito (e a base), Motor Elétrico Pequeno, Servo, Pistão, Virabrequim, Bloco de Motor, Carcaça de
Granada, Caldo de Cultura, Extrato, Concentrado, Polpa, Pigmento, Cola Quente, Concreto Fresco (fluido), Betume
(fluido) e os moldes novos (Pote, Béquer, Lente, Placa, Bulbo, Bloco, Pneu, Junta, Correia, Mangueira, Sola,
Cabeças de ferramenta, Carcaça, Bloco de Motor, Pistão, Pellet, Caixa de Bateria, Coronha Sintética).

---

## 8. Três fábricas de exemplo

### 8.1 Fábrica de pneus (meio de jogo)

```
[Seringueiras plantadas] ─ sangradores ─ cano de látex ─► [Tanque de Líquido]
                                                               │
[Torre de Lavagem] ─ cano de ácido ─────────────► [Tanque de Coagulação] ─ esteira ─► [Calandra] ─► [Secador a Vapor]
        └─ esteira de enxofre ──────────────────────────────┐                                            │
[Retorta] ─ esteira de negro de fumo ──────────────► [Misturadora] ◄────────── esteira de borracha crua ┘
                                                          │
                                                          ▼
                       [Prensa de Vulcanização + Molde de Pneu] ◄── vapor 3 bar (Caldeira + Compressor)
                                                          │
                                                          ▼  esteira
                              [Montadora com baús: Pneu + Aro + Cubo] ─► Roda
```

### 8.2 Refinaria (fim do meio de jogo)

```
Xisto (mineração) ─► Triturador ─► Retorta ─┬─ Óleo Cru ─► Caldeira da Torre + 4 seções ─┬─ Gasolina ─► Envasadora ─► Latas
                                             │                                            ├─ Óleo Base ─► Envasadora ─► Óleo
                                             │                                            ├─ Óleo Combustível ─► Craqueador ─► + Gasolina
                                             │                                            ├─ Nafta ─► Reator de Polimerização ─► Injetora
                                             │                                            └─ Betume ─► Misturadora ─► Asfalto
                                             └─ Gás de Xisto ─► Torre de Lavagem ─┬─ Ácido / Enxofre
                                                                                  └─ Gás Combustível ─► Compressor ─► Tanque de Gás
                                                                                                          └─► Queimadores (Fundição, Retorta, Caldeira)
```

Manômetro no Tanque de Gás ligado a um Registro: com o tanque cheio, o registro fecha e a Retorta para.

### 8.3 Linha de munição 9mm (já desenhada; agora em sequência)

```
Cápsula (Molde) ─ esteira ─► [Prensa em Linha: repuxo] ─► [Bico Dosador: pólvora] ─► [Encaixador: ponta] ─► [Crimpadora] ─► Bala 9mm
```

---

## 9. Como fica no código

1. **`fe_processes.xml` ganha campos:**
   - `outputs` com várias saídas, sólidas e fluidas, e chance;
   - `gas` e `pressure` (mínima pedida, de saída);
   - `heat` (o calor vem do Queimador encostado ou do combustível);
   - `mold` para a Injetora e a Vulcanização;
   - `inline="true"` para as estações sobre a esteira.

   O `check_processes.py` confere todos os campos novos.
2. **Gases (`FluidNetwork.cs`):**
   - `FluidClass` (líquido/gás) por fluido;
   - `FluidNet.Volume` (soma dos canos e tanques) e `Pressure`;
   - as fontes param na pressão de trabalho; o compressor liga duas redes; o cano tem `MaxBar`;
   - o vazamento solta partícula de vapor (o `FxVisual` já tem).

   O formato de gravação ganha colunas no fim, como fizemos com a `Pick`, então os mundos antigos continuam abrindo.
3. **Tanques que se juntam:** uma busca (BFS) pelos tanques encostados do mesmo tipo forma um "tanque lógico"; o
   nível vai para todos os blocos. É o padrão de multibloco que já usamos (`ParentOf`).
4. **Válvulas e controle:**
   - o Registro é um consumidor elétrico vanilla (`BlockPowered`): aberto enquanto tem energia;
   - o Manômetro é uma fonte de sinal (como o sensor de movimento), para ligar no fio do jogo;
   - a Embreagem ganha a mesma entrada de sinal.
5. **Torre de Destilação:** a Caldeira conta as seções empilhadas em cima e decide as frações por seção; cada seção
   é uma porta de saída.
6. **Estações em linha:** como o PLANO_CRAFT 6.5. O item para no meio da esteira, recebe o passo e o "passo atual"
   vai em `ItemValue.Meta`.
7. **Sangrador de Seiva:** a cada 10 s olha o bloco em que está preso. Se for árvore viva (`BlockModelTree` ou uma
   tag nossa na Seringueira), produz látex na porta.
8. **Menus (XUi):**
   - cinco janelas em `Config/XUi_InGame/windows.xml`, controllers `XUiC_FePanel`, `XUiC_FeRecipePicker`,
     `XUiC_FeConfig`, `XUiC_FeNetwork` e `XUiC_FeGuide`;
   - ícones pelo atlas do mod;
   - a escolha de item usa o `ItemStack` do inventário;
   - as ações do menu passam por uma única função (`FeCommands.Apply(pos, cmd, args)`). No multiplayer essa função
     vira um `NetPackage`; no single-player ela chama direto. Assim o multiplayer, no fim, só troca o transporte.
9. **Cobertura:** `tools/check_coverage.py` lê as receitas vanilla e as do mod e o `fe_processes.xml`.
   - Ele falha se algum item do jogo (fora a lista "continua loot" da seção 3) não tem rota no mod.
   - Ele falha se algum item avançado ainda sai de bancada vanilla.
   - Ele gera os dados do Guia de Produção.
10. **Desempenho:** gás e tanques no mesmo tick de 0,5 s; redes sem mudança não são recalculadas; as máquinas longe
    da câmera não animam (já é assim no `FxVisual`).

---

## 10. Fases

Esta tabela substitui a lista F8.3–F8.11 do PLANO_CRAFT. A ordem segue a dependência: menus e fluidos primeiro,
porque quase tudo depois usa.

| Fase | Entrega | Prova no jogo |
|---|---|---|
| **F9.0** Base | `check_coverage.py`; Seletor de Receita (5.2); Painel da Máquina (5.1) nas máquinas de processo atuais | Escolher a receita do Triturador pelos ícones; o painel mostra o progresso |
| **F9.1** Fluidos 2.0 | Gás e pressão; Tanque de Líquido e de Gás; Compressor; Cano de Alta Pressão; Registro, Reguladora, Retenção, Alívio, Separador, Manômetro; Configurador (5.3); Painel de Rede + Chave (5.4) | O manômetro fecha o registro com o tanque cheio |
| **F9.2** Montagem | Montadora com baús; Prensa em Linha, Bico Dosador, Encaixador, Crimpadora; Divisor, Comporta, Contador; **toda a munição, flechas e foguetes** | Bala 9mm sai sozinha; flecha de ferro em linha |
| **F9.3** Petróleo | Retorta de Xisto, Torre de Destilação, Craqueador, Torre de Lavagem, Queimador a Gás, Motor a Gás; gasolina, óleo, ácido, asfalto pelo mod | Lata de gasolina vinda da torre; ácido da lavagem |
| **F9.4** Plástico e borracha | Reator de Polimerização, Injetora, Sangrador, Seringueira, Calandra, Prensa de Vulcanização; pneus, juntas, correias | **Roda feita da seiva até o pneu** |
| **F9.5** Vidro e metal | Vidro fundido e moldes; cerâmica; Conversor de Aço; Trefila, Enroladora, Esmeril, Dobradeira, Soldadora, Forno de Têmpera; pregos, molas e peças mecânicas e elétricas em cadeia | Lente polida; mola do fio |
| **F9.6** Armas e ferramentas | Armas (os 3 tiers), ferramentas, explosivos, os 74 mods | Pistola e Picareta de Aço pela linha |
| **F9.7** Têxtil | Fiadeira, Tear com receita, Curtume; armaduras e mochilas | Armadura de couro curtido |
| **F9.8** Construção | Concreto fluido, asfalto, vidro, serralheria (portas, cofres, garagens) | Bloco de concreto moldado; porta de aço |
| **F9.9** Eletrônica e veículos | Placa de circuito, Forno de Refusão, bateria, Motor Pequeno em sequência, chassi, veículos, robótica | Minimoto inteira pela linha |
| **F9.10** Remédio e comida | Tanque de Fermentação, Centrífuga, Autoclave, Cozinha Industrial, Moinho, Prensa de Suco (Enlatadora se aprovada) | Antibiótico; ensopado em lote de 4 |
| **F9.11** Fechamento | Guia de Produção (5.5); retrofit dos menus (5.6); remoção ou encarecimento das receitas vanilla (D12-4); `check_coverage.py` com 0 itens sem rota | Nenhum item avançado sai de bancada vanilla; todo item tem página no Guia |

Depois disso vêm o **balanceamento** e o **multiplayer**, como combinado. Cada fase tem roteiro no `TESTE_GERAL.md`
e commit próprio.

**Tamanho:** são 12 fases. As mais longas são a F9.1 (C# novo de pressão e tanques) e a F9.2 (estações em linha).
Da F9.3 em diante, a maior parte do trabalho é dado, modelo e ícone.

---

## 11. Decisões em aberto

| ID | Decisão | Opções | Recomendação |
|---|---|---|---|
| D12-1 | "Penels" no pedido | (a) **pneus**; (b) painéis (solares?) | **(a)**: borracha → pneus é a cadeia natural. Se era painel, a borracha entra como junta e isolante do painel solar |
| D12-2 | De onde vem o látex | (a) só Seringueira nova; (b) só árvores do jogo; (c) as duas (Seringueira rende muito mais) | **(c)** |
| D12-3 | Pressão alta demais | (a) o cano só vaza; (b) o cano estoura e vira sucata | **(a)** no começo; (b) como opção de dificuldade |
| D12-4 | Receitas vanilla dos itens avançados | (a) remover; (b) manter ×3 mais caras; (c) opção no config | **(c)**, padrão "remover" (era a D11-2) |
| D12-5 | Enlatadora (comida enlatada fabricável, o jogo não tem receita) | entra / não entra | **Entra**, opcional no config |
| D12-6 | O Painel da Máquina substitui a janela vanilla das bancadas do mod? | (a) não: as bancadas ficam com a janela vanilla + Seletor; (b) sim, tudo igual | **(a)**: menos risco, a janela de craft do jogo já funciona |
| D12-7 | Braço Mecânico | entra na F9.2 / fica para depois | **Entra na F9.2**: é a cara do Create e resolve linhas apertadas |
| D12-8 | Diesel e querosene | (a) não (o jogo não usa); (b) sim, como combustíveis melhores para motores | **(a)**: menos fluidos, menos confusão |
| D12-9 | Comida: a Cozinha Industrial muda as quantidades? | (a) igual ao jogo, só em lote; (b) rende mais | **(a)** + lote de 4 com metade do tempo |
| D12-10 | Armaduras: 17 conjuntos com cadeia própria ou 3 "moldes de costura" | própria / 3 moldes | **3 moldes** (leve, médio, pesado) e o material muda o conjunto |
| D12-11 | Guia de Produção abre por | (a) livro; (b) tecla; (c) botão no tooltip | **(a) + (c)**. Tecla nova em mod é frágil |

**Para começar:** com as decisões respondidas, começo pela **F9.0** (cobertura + Seletor + Painel). Ela não muda
nada do que já funciona e melhora já as máquinas atuais.
