# Pré-processamento

Deixar um exame comparável com qualquer outro, antes de procurar nódulo em qualquer um deles.
São três operações, e a ordem entre elas importa.

O código está em `codigo/pi3/preprocessamento/volume.py` e roda por
`scripts/04_preprocessar.py`.

## A ordem

**Primeiro a janela de HU**, cortando a intensidade em −1000 e 400. Vem antes da interpolação
para que um voxel de costela, que passa de 400, não vaze para dentro do pulmão quando os
vizinhos forem misturados na reamostragem.

**Depois a reamostragem** para voxel de 1 mm isotrópico. O volume usa interpolação linear e a
máscara usa vizinho mais próximo, para continuar binária.

**Por último a máscara**, aplicada ao volume já reamostrado, para não interpolar a borda dura
entre pulmão e o lado de fora. O que fica fora do pulmão recebe −1000, que é ar, e não zero,
que na escala Hounsfield é água.

## O que muda em um exame

Um exame típico, de 512 por 512 por 123 voxels de 0,82 por 0,82 por 2,5 mm, sai como 420 por
420 por 308 voxels de 1 por 1 por 1 mm. A extensão física é preservada dentro de meio voxel, e
o pulmão fica sendo 8,3% do volume.

A figura `relatorios/figuras/preprocessamento.png` mostra a mesma posição física antes e
depois, com um nódulo de 32,3 mm circulado nos dois lados. À esquerda o tórax inteiro, à
direita só os dois pulmões.

## Onde isso quebra em silêncio

Reamostrar muda o espaçamento. Um volume gravado com a geometria antiga, ou uma coordenada
convertida com o espaçamento velho, desloca todo recorte feito depois sem levantar erro.

Por isso a reamostragem mantém origem e direção intactas e altera apenas espaçamento e
dimensão, e por isso existe teste que põe um objeto denso numa posição conhecida, reamostra, e
exige que ele continue na mesma posição em milímetro. Existe também o teste espelhado, que
prova que a fórmula sem a geometria nova cai em outro voxel: sem ele, o primeiro passaria
mesmo com o código errado.

## A máscara de pulmão

Usamos a máscara que o desafio entrega, sem dilatar. A justificativa e a medição que a
sustentam estão em `documentacao/decisoes/0002-mascara-de-pulmao-sem-dilatacao.md`.

Em resumo: 29 dos 615 nódulos têm o centro fora da máscara, o que à primeira vista parece
perda. Mas o critério de acerto do desafio não exige acertar o centro, e sim chegar a menos de
um raio dele. Medido com esse critério, **os 615 continuam alcançáveis** e a máscara não custa
nódulo nenhum.

## O que ainda não existe

A reamostragem roda hoje em um exame por vez, para verificação. Processar os 445 e gravar em
disco é passo seguinte, assim como o recorte dos cubos ao redor de cada candidato, o baseline
e a avaliação FROC.
