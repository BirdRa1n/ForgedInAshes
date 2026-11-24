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
