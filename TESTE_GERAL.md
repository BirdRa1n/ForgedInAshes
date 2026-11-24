# Roteiro de teste geral (D9, D10 e fase 6)

Antes de começar:

- Use o save de teste (ModTester2) com o modo criativo para pegar os blocos.
- **Pegue e coloque de novo** tudo o que foi colocado antes destas mudanças: Condensadora, Refinaria e as máquinas de
  produção. Blocos antigos ficam com o modelo novo, mas sem as células ou registros novos.
- No fim, feche o jogo e peça para ler o log. As linhas `[FerroEngrenagem] belt -> ...` e `autocraft at ...` mostram
  o que as esteiras entregaram ou recusaram e quando a receita fixa ligou.

## 1. Condensadora

1. Coloque de novo a Condensadora e os canos dela.
2. Confira:
   - o braço do cano de vapor (atrás, em cima) se junta à entrada;
   - a ventoinha gira;
   - o nível de vapor e o de água (azul) mudam.

## 2. Esteiras

1. **Linha reta:** monte uma linha reta com um eixo na lateral de qualquer esteira.
   - Solte itens em cima.
   - Eles andam e param em fila no fim.
2. **Curva:** coloque uma esteira ao lado da ponta, apontando para fora.
   - A curva mostra o anel com ripas girando no canto.
   - O item faz o arco.
3. **Divisão em 2:** esteiras dos dois lados da ponta.
   - Aparece a mesa de esferas com o divisor em V.
   - Os itens se alternam entre os lados.
4. **Divisão em 3:** mais uma esteira na frente. Agora a mesa fica sem o V.
5. **Subida:** Esteira de Subida na frente de uma esteira; esteira um bloco acima e um à frente.
6. **Descida:**
   - Coloque uma esteira num nível mais alto.
   - Na frente dela, um bloco abaixo, coloque a Esteira de Descida, apontando para o mesmo lado.
   - Os itens descem e seguem na esteira da frente.
7. **Filtro:**
   - Coloque uma Esteira com Filtro.
   - Com um item na mão, segure E e escolha "Ajustar filtro". O item fica flutuando em cima dela.
   - Coloque esteiras apontando para fora nas laterais e uma na frente.
   - O item do filtro vai para os lados e o resto segue em frente.
8. **Salvar:** saia e entre de novo. Os itens continuam nas esteiras e o filtro continua ajustado.

## 3. Funil, Armazém e máquinas

1. **Funil num baú:**
   - Coloque um baú (qualquer um) e um Funil com as costas no baú.
   - Ponha uma esteira na frente do Funil.
   - Encha o baú: o Funil põe até 16 itens por vez na esteira.
   - Abra o baú: o Funil espera enquanto ele estiver aberto.
2. **Armazém de Esteira:** uma esteira apontando para qualquer lado dele guarda os itens. Cheio ou aberto: os itens
   esperam.
3. **Motor a Vapor:**
   - Uma esteira apontando para uma entrada amarela leva Carvão para o combustível e Lubrificante para os slots.
   - Com o motor cheio, o Carvão espera na esteira.
4. **Fundição:** uma esteira com Carvão (combustível) e com material fundível (sucata) entrega cada um no seu lugar.
5. **Gerador a Carvão e Motor a Carvão:** a esteira leva Carvão para o combustível.

## 4. Receita fixa

1. Numa máquina (por exemplo a Prensa), fabrique uma receita uma vez à mão.
2. Com ela ainda na fila, segure E e escolha "Receita fixa liga/desliga". Aparece "Receita fixa: <item>".
3. Leve os ingredientes por esteira até a máquina. A leitura dela mostra os ingredientes guardados.
4. Quando a fila esvazia e tem tudo, a máquina fabrica sozinha. O resultado fica na saída.
5. Ponha um Funil com as costas na máquina e uma esteira na frente: o resultado sai pela esteira.
6. Desligue a receita fixa: os ingredientes guardados caem no chão.

## 5. Fluidos novos

1. **Despejador:**
   - Coloque um Despejador com um cano na frente, ligado a uma Caixa d'Água vazia.
   - Com Óleo na mão, segure E e escolha "Despejar o item da mão" (ou leve por esteira).
   - O cano mostra "Óleo: X L/min" e a caixa enche.
2. **Envasadora:**
   - Ligue a caixa a uma Envasadora pelo cano de trás e ponha uma esteira na frente.
   - A Envasadora põe Óleo na esteira (ou entrega na mão com E).
3. **Gasolina e Lubrificante:**
   - Repita com Latas de Gasolina e com Lubrificante.
   - Misturar dois fluidos no mesmo cano deve mostrar "BLOQUEADO".
4. **Refinaria:**
   - Ligue a receita fixa do Lubrificante (2 Óleo).
   - Leve Óleo fluido pelo cano até a porta de trás.
   - A Refinaria fabrica sozinha.

## 6. Modelos das máquinas

1. Coloque cada máquina de produção:
   - Fundição, Prensa, Torno e Carvoeira;
   - Prensa de Munição, Montadora, Bancada de Mods e Tear;
   - Refinaria, Laboratório, Cozinha e Bancada Eletrônica;
   - Serralheria, Serraria, Misturadora, Garagem e Robótica.
2. Confira para cada uma:
   - se está no chão (sem afundar nem flutuar);
   - se ocupa os blocos certos (2 ou 3 de largura nas grandes);
   - se a janela de fabricação abre.
3. Com uma receita na fila, as partes se mexem:
   - a Prensa e a Serralheria sobem e descem;
   - a Serraria, o Torno e o Laboratório giram rápido;
   - o Tear, a Misturadora e o braço da Robótica giram devagar.

## 7. Escolher produção (F8.0)

1. Numa máquina do mod (por exemplo a Prensa), segure E e escolha "Próxima produção".
   - Aparece "Produção 1/N: <item>" e a receita fixa liga sem fabricar à mão.
   - "Próxima produção" e "Produção anterior" percorrem a lista; ao trocar, os ingredientes guardados caem no chão.
2. Leve os ingredientes por esteira: a máquina fabrica sozinha, como na parte 4.
3. No log, ao abrir o jogo, aparece `[FerroEngrenagem] processes: 0 active, 10 planned`.

## 8. Metalurgia (F8.1)

Antes: pegue e coloque de novo a Fundição (ela passa a ter o tanque de metal). Fabrique os blocos e moldes no modo
criativo: Calha de Metal, Mesa de Moldagem e os moldes (Cápsula, Ponta, Lingote, Chapa, Tubo, Engrenagem).

1. **Derreter:**
   - Ponha combustível (Carvão ou madeira) na Fundição.
   - Com Sucata de Latão na mão, segure E na Fundição e escolha "Derreter o item da mão". Ou leve a sucata por esteira.
   - A leitura da Fundição mostra "Latão Fundido: X / 200 L" e o calor.
2. **Calha:**
   - Ligue a Calha de Metal em qualquer lado de fora da parte de baixo da Fundição até as costas de uma Mesa de Moldagem.
   - Os braços da calha se juntam à Fundição e à Mesa; um cano comum ao lado NÃO se liga à calha.
   - Olhando a calha: "Latão Fundido: X L/min".
3. **Moldar:**
   - Segure o Molde de Cápsula, segure E na Mesa e escolha "Trocar o molde". Aparece "Molde: Molde de Cápsula (aceita Latão Fundido)".
   - O metal enche o molde (o laranja sobe), esfria e aparece "Prontas: 5x Cápsula Bruta" com a pilha de peças.
   - Com uma esteira na frente da Mesa, as peças saem por ela. Sem esteira, use "Pegar as peças".
   - Água ao lado da Mesa (Caixa d'Água com água) esfria duas vezes mais rápido.
4. **Molde errado:** com o Molde de Ponta na Mesa, o latão não entra (a calha fica parada). Chumbo entra.
5. **Trocar molde com metal dentro:** recusa ("Tem metal no molde").
6. **Cápsula:** a Cápsula Bruta vira Revestimento de Bala na Prensa de Munição.
7. **Ferro:** Ferro Forjado derretido + Molde de Chapa = Chapa de Ferro; Molde de Lingote aceita ferro e aço.
8. Saia e entre: o metal na Fundição, o molde e as peças prontas continuam.

## 9. Química da pólvora (F8.2)

Pegue no criativo: Triturador, Lavadora, Misturador Químico, Secador a Vapor; Carvão e Salitre.

1. **Triturador:**
   - Ligue um eixo com torque na esquerda ou na direita dele (gasta 128 UT). Os rolos giram.
   - Com Carvão na mão, segure E e escolha "Colocar o item da mão" (ou leve por esteira de qualquer lado).
   - Sai Pó de Carvão na esteira da frente (ou "Pegar os produtos"). Sem torque: "Sem torque no eixo".
   - Pedras pequenas viram Areia.
2. **Lavadora:** água por trás (cano de uma bomba ou Caixa d'Água). Salitre vira Salitre Purificado.
3. **Misturador Químico:** eixo na esquerda ou direita (64 UT), água por trás. 1 Pó de Carvão + 2 Salitre Purificado + 1 L de água = 3 Pólvoras Úmidas. O agitador gira.
4. **Secador a Vapor:** vapor por trás (do Motor a Vapor). Pólvora Úmida vira Pólvora.
5. **Linha completa:** esteiras ligando Triturador e Lavadora → Misturador → Secador → Prensa de Munição. Com a Mesa de Moldagem fazendo cápsulas e pontas, a Bala 9mm sai na Prensa de Munição com "Escolher produção".
6. A leitura de cada máquina mostra o que ela faz, o que tem dentro, a água/vapor e o progresso.
7. Saia e entre: o que estava dentro das máquinas continua.

## 10. Versões industriais e Biodigestor

1. **Forno de Indução** (2x2, ligue fios de energia, 250 W):
   - Sem energia: a leitura mostra "Sem energia". Com energia: derrete o que chega por esteira (ou "Derreter o item da mão") sem combustível.
   - O metal sai pela Calha de Metal em qualquer lado de fora da parte de baixo.
2. **Moldadora Industrial** (60 W): mesmos moldes da Mesa; com energia esfria bem mais rápido.
3. **Forno de Retorta** (100 W): madeira por esteira (5 por vez), Carvão Vegetal sai na esteira da frente a cada 20 s.
4. **Biodigestor** (água por trás):
   - 5 Carne Crua → 5 Carne Podre (3 min).
   - 10 Carne Podre + 4 Ossos → 1 Terra Nitrosa (6 min). A Lavadora transforma em 4 Salitre.
   - 10 Carne Podre sem ossos (ou 12 Milho / 12 Batata) → 1 Mosto Orgânico.
5. **Biocombustível:** Refinaria, 2 Mosto Orgânico + 1 Gordura Animal. Por esteira no Motor a Gasolina: a cada 3 latas o combustível sobe 1.

## 11. Texto, Receitas e ícones
- [ ] Olhar para o Biodigestor / Triturador: o texto aparece em tamanho normal (não minúsculo).
- [ ] Segurar E em uma máquina (Triturador, Mesa de Moldagem, Fundição, Torno): opção "Receitas" abre a janela com a lista; << e >> trocam a página; OK ou Esc fecha.
- [ ] Barra e inventário: blocos e itens do mod com ícones próprios (moldes com a cavidade laranja, pós, biocombustível verde).

## 12. Escolher receita e Biodigestor Industrial
- [ ] Texto de foco do Biodigestor/Triturador em tamanho normal (a correção da seção 11 só vale agora: a pasta XUi estava errada).
- [ ] Segurar E > Receitas abre a janela (no log: `recipe book ... window=True`).
- [ ] Segurar E > Escolher receita no Biodigestor: cicla as receitas e volta para "automática"; o texto de foco mostra a escolhida.
- [ ] Com "Terra Nitrosa (carne podre + ossos)" escolhida: carne crua na esteira não entra; carne podre + ossos entram e saem Terra Nitrosa.
- [ ] Biodigestor Industrial (Montador): 2 blocos de altura, eixo na lateral com torque, água por trás; esteiras por qualquer lado; carne crua + ossos -> 2 Terra Nitrosa; agitador gira no topo.

## 13. Modelos HD e efeitos (Fundição, Calha, Mesa de Moldagem, Eixo, Condensadora, Cano, Bomba Mecânica)

Pegue e coloque de novo os sete blocos (o modelo troca sozinho, mas assim os efeitos se ligam do zero).

1. **Visual parado:** os sete têm textura (tijolo, ferro, ferrugem, tinta verde gasta), sem peças flutuando nem
   buracos. A Fundição mostra as 4 molduras de esteira (2 atrás, 1 em cada ponta) e o canal em volta da base.
2. **Fundição queimando** (combustível + sucata de ferro): frestas da porta acendem e piscam, fumaça na chaminé,
   o soprador atrás gira; com metal dentro, faíscas sobre o cadinho e o metal do cadinho/canal acende.
3. **Metal saindo:** ligue uma Calha de Metal numa face de baixo e uma Mesa de Moldagem (com molde) na ponta.
   - Aparece o jato do cadinho até o canal da Fundição.
   - Na calha, o metal brilha e "corre".
   - Na mesa, o jato cai do bico no molde e o metal sobe no molde.
4. **Resfriamento:** com o molde cheio, o metal da mesa vai de amarelo a vermelho e escurece até o fim do tempo;
   sai vapor durante o resfriamento. Quando o fluxo para, o metal parado na calha escurece em uns 10 s.
5. **Cores:** troque o metal (chumbo, latão, aço): chumbo quase não brilha (prateado), latão amarelo, aço mais claro.
6. **Canos e bomba:** o visor da cruz do cano mostra a cor do fluido (água azulada, óleo preto, gasolina âmbar);
   o visor da bomba fica com água enquanto ela bombeia; o eixo e a bomba giram com torque.
7. **Condensadora:** sai vapor pela ventoinha enquanto condensa; a água continua subindo no nível.
8. **Girar os blocos:** coloque a Fundição e a Mesa viradas para outros lados: a fumaça/vapor sobe (não sai de lado).

No fim, feche o jogo e peça para ler o log (`Player.log` quando aberto direto pelo exe).

### 13b. Rodada 2 (fogo da fornalha, despejo, nove modelos novos)

1. **Fundição:** a chama fica dentro da boca da fornalha (célula esquerda, porta aberta encostada no tijolo); nada de
   fogo atravessando o tijolo.
2. **Despejo na Mesa de Moldagem:** o metal enche o copo atrás, desce pelo canal e cai em arco fino no molde, com
   faíscas onde bate; o molde enche e depois esfria (amarelo → vermelho → escuro) soltando vapor.
3. **Motor a Vapor:** ligado, chama e brasa na fornalha, fumaça na chaminé, vapor nas purgas; sem cano na saída de
   vapor, sai a pluma de escape por cima. Pistões e volante como antes.
4. **Embreagem:** "Trocar ajuste" troca a alavanca de lado (engatada / solta) e o giro passa ou não.
5. **Caixa de Transmissão, Caixa de Velocidade, Inversor de Giro:** giram como antes (no inversor, a engrenagem
   cônica do meio também gira).
6. **Torno e Prensa de Munição:** trabalhando, a placa do torno gira e o carro anda; na prensa, a torre gira e o
   aríete desce e sobe.
7. **Triturador:** enquanto tritura, sai poeira do funil; os rolos giram em sentidos opostos.
8. **Esteira:** reta, curva, divisão em 2 e 3, filtro: todas as peças aparecem/somem como antes, sem buracos.

## 14. Duto de Esteira, Suporte, Funil girando e encaixes

1. **Duto:** monte uma linha de Dutos de Esteira com um eixo na lateral de um deles. Coloque itens com um funil:
   eles andam dentro (não aparecem), o texto de foco mostra a contagem e a velocidade. Itens jogados em cima **não**
   entram.
2. **Pontas do duto:** sem nada na frente fica tampado; apontando para uma máquina com moldura de esteira (Fundição,
   Motor a Vapor) aparece a luva entrando na boca; apontando para uma esteira aberta o fim do duto sobe e solta os
   itens em cima dela; duto/esteira chegando pelo lado abre a lateral.
3. **Esteira → máquina / duto:** a esteira aberta apontando para uma máquina ou para a traseira de um duto ganha a
   calha que desce até a boca (sem esteira flutuando na moldura).
4. **Suporte:** coloque um Suporte de Esteira e um Duto em cima: os pés do duto assentam no berço. Uma linha de
   suportes com dutos passa um bloco acima do chão.
5. **Funil girando:** coloque um baú, um funil embaixo dele virado para baixo e um duto embaixo do funil: aparece a
   escotilha no duto e os itens descem. Funil deitado na traseira de um duto: o bico desce até a boca do duto; na
   esteira aberta, o bico normal sobre a esteira.
6. **Motores e dínamos:** os cinco têm modelo novo; eixos giram como antes e o fio liga no mesmo lugar.

## 15. Motor a Vapor com virabrequim

1. Ligue o Motor a Vapor (água + combustível) e olhe pela frente/lateral: o virabrequim gira, as duas bielas sobem e
   descem presas nos pinos das manivelas (defasadas 90°), as cruzetas correm nas guias e as hastes entram nos cilindros.
2. Nada atravessa a fornalha nem a base; o volante gira na frente sem raspar no chão.
3. Desligado, tudo para na posição em que estava (sem pular). Pegue e coloque o motor de novo: continua certo.

## 16. Condensadora, máquinas de processo e Prensa de Munição

1. **Condensadora** (energia + vapor): a ventoinha gira; o ponteiro do manômetro sobe com o vapor; pingam gotas no
   visor de fluxo (frente, embaixo à esquerda); a coluna d'água sobe no visor de nível do tambor; sai vapor sobre a
   ventoinha. Nada "pulando".
2. **Biodigestor** (água + ingredientes): trabalhando, a campânula de cima gira devagar e sobe com o nível; no visor
   da frente o mosto sobe e borbulha; a tocha acende.
3. **Biodigestor Industrial**: com torque o agitador gira no poço de cima (mosto borbulhando); a coluna marrom sobe
   no visor alto; tocha acesa trabalhando.
4. **Secador a Vapor**: trabalhando, o tambor gira; sai vapor na chaminé; pinga no purgador.
5. **Misturador Químico**: com torque o agitador gira; a calda sobe com a água e gira com espuma; bolhas.
6. **Lavadora**: trabalhando, o tambor gira, o spray molha de cima e pinga na calha de água barrenta.
7. **Prensa de Munição** (fabricando): as tigelas de cima giram, a torre gira e o aríete desce; cápsulas andam do
   caixote pela mini-esteira e sobem ao prato; cartuchos prontos descem pela calha e vão até a caixa.

## 17. Livro de receitas e barra de atalhos

1. Com um item na mão, segure E na Lavadora e abra "Receitas"; feche com OK (e depois com Esc).
2. Troque de slot pelo número e pela roda do mouse: tem de funcionar na hora.
3. Repita depois de "Pôr o item da mão" na máquina. Se ainda travar, feche o jogo e peça para ler o log
   (procure "recipe book" e "stuck switching").
