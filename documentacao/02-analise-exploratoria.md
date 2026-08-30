# Análise exploratória

Cinco figuras, e a regra que decide o que entra é uma só: **cada figura responde a uma
pergunta que muda uma decisão de pré-processamento.** Figura que não muda decisão nenhuma sai,
por mais bonita que seja.

É isso que separa análise exploratória de galeria de gráficos. Quando perguntarem por que
normalizamos de um jeito e não de outro, a resposta é uma figura, não uma opinião.

Todas as figuras estão em `relatorios/figuras/` e são geradas por `scripts/05_eda.py`. Os
números abaixo saíram dos 445 exames dos subsets 0 a 4, medidos em 29/08/2026.

## Espaçamento entre fatias

`eda_espacamento_z.png`

A pergunta é se dá para tratar os 445 exames como se fossem do mesmo tamanho físico. Não dá:
o espaçamento em z assume nove valores distintos e vai de 0,5 a 2,5 mm, um fator de 5. A
maior parte está em 2,5 mm, com 135 exames, e em 1,25 mm, com 112.

Um cubo de 32 voxels cobre 16 mm num exame de 0,5 mm e 80 mm num de 2,5 mm. Sem reamostrar,
estaríamos mostrando ao modelo coisas de tamanho físico diferente como se fossem iguais.

**Decidimos reamostrar tudo para 1 mm isotrópico** antes de recortar qualquer coisa.

## Diâmetro dos nódulos

`eda_diametro.png`

A pergunta é se o cubo de 32 voxels cobre o nódulo inteiro. A distribuição tem pico entre 4 e
8 mm, mediana de 6,7 mm, e uma cauda longa e fina à direita. A 1 mm isotrópico, o cubo cobre
32 mm, e **apenas 1 dos 615 nódulos passa disso**, com 32,3 mm.

**Mantivemos o cubo de 32 voxels** e registramos esse nódulo como perda conhecida, em vez de
aumentar o recorte e trazer mais fundo que sinal.

## Nódulos por exame

`eda_nodulos_por_scan.png`

A pergunta é o que fazer com exame que não tem nódulo nenhum. São **134 dos 445**, e eles
entram na avaliação do desafio mesmo assim: se o detector apontar alguma coisa neles, conta
como alarme falso.

**A média de falso positivo por exame usa 445 no denominador**, não os 311 que têm nódulo.
Usar 311 inflaria o número em quase metade, sem que nada acusasse o erro.

## Intensidade dentro do pulmão

`eda_hu.png`

A pergunta é onde cortar a escala de intensidade. A escala Hounsfield mede densidade: ar fica
perto de −1000, água em 0, osso passa de 400.

Calculamos o histograma **dentro da máscara de pulmão**, não no volume inteiro, porque o
pulmão é uma fração pequena da imagem e o resto é ar externo, mesa e parede torácica. Um
histograma do volume todo mediria a sala, não o paciente. A amostra é de 30 exames sorteados.

O resultado tem um pico grande perto de −850, que é o pulmão cheio de ar, uma corcova menor
perto de zero, que são vasos e tecido, e uma cauda que se arrasta até acima de 3.000.

**A janela de −1000 a 400 guarda 98,7% dos voxels do pulmão.** O que fica de fora é osso,
calcificação e metal, e sem o corte um voxel desses domina a escala de qualquer recorte na
hora de normalizar.

## Desbalanceamento dos candidatos

`eda_desbalanceamento.png`

A pergunta é o que a proporção de positivos faz com a escolha de métrica. Nos nossos subsets
são 275.358 candidatos, dos quais **721 são nódulo, ou 0,2618%**.

Um classificador que responde sempre "não é nódulo" acerta **99,74%** e não serve para nada.

**Por isso a métrica é a curva FROC e não acurácia**, e por isso o treino vai precisar
reamostrar as classes em vez de usar a proporção natural do arquivo.

## O que a análise exploratória não é

Ela não diz se dá para detectar nódulo, nem quão bem. Não mede desempenho de nada, porque
ainda não há modelo. O que ela entrega é o direito de tomar as cinco decisões acima, e a prova
de que cada uma tinha motivo medido.
