# Pré-processamento

Deixar um exame comparável com qualquer outro, antes de procurar nódulo em qualquer um deles.
São quatro operações, e a ordem entre elas importa.

O código está em `src/preprocessing/volume.py` e roda por
`scripts/04_preprocessar.py`.

## A ordem

**Primeiro a janela de HU**, cortando a intensidade em −1000 e 400. Vem antes da interpolação
para que um voxel de costela, que passa de 400, não vaze para dentro do pulmão quando os
vizinhos forem misturados na reamostragem.

**Depois a reamostragem** para voxel de 1 mm isotrópico. O volume usa interpolação linear e a
máscara usa vizinho mais próximo, para continuar binária.

**Depois a máscara**, aplicada ao volume já reamostrado, para não interpolar a borda dura
entre pulmão e o lado de fora. O que fica fora do pulmão recebe −1000, que é ar, e não zero,
que na escala Hounsfield é água.

**Por último a normalização**, que leva a janela de HU para o intervalo de 0 a 1. Vai depois da
máscara justamente porque o preenchimento de fora do pulmão é −1000, o piso da janela, e
normalizar em seguida faz esse fundo virar exatamente 0. Guardamos o volume já normalizado, e o
motivo está em `docs/decisoes/0006-normalizacao-entra-no-volume-salvo.md`.

## O que muda em um exame

Um exame típico, de 512 por 512 por 123 voxels de 0,82 por 0,82 por 2,5 mm, sai como 420 por
420 por 308 voxels de 1 por 1 por 1 mm. A extensão física é preservada dentro de meio voxel, e
o pulmão fica sendo 8,3% do volume.

Os valores saem entre 0 e 1, e não mais em HU. O arquivo ocupa 9,7 MB em float de 32 bits
comprimido, contra 7,1 MB se guardássemos o HU em inteiro de 16 bits.

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
sustentam estão em `docs/decisoes/0002-mascara-de-pulmao-sem-dilatacao.md`.

Em resumo: 51 dos 1.186 nódulos têm o centro fora da máscara, o que à primeira vista parece
perda grande. Mas o critério de acerto do desafio não exige acertar o centro, e sim chegar a
menos de um raio dele. Medido com esse critério, **1.185 dos 1.186 continuam alcançáveis**: a
máscara custa exatamente um nódulo, de 5 mm, ou 0,08%.

A forma como lemos a máscara importa. Usando os rótulos 3 e 4, como faz toda a linhagem de
código pública do LUNA16, a perda sobe para quatro nódulos. Usamos `> 0`, que inclui o rótulo
5, e isso recupera três deles.

## A rodada na base completa

Rodamos nos 888 exames em 07/09/2026, com `scripts/07_preprocessar_base.py`. O relatório por
exame fica em `dados/intermediario/preprocessamento.csv`.

| | |
|---|---|
| Exames na lista | 888 |
| Gravados | 888 |
| Sem volume em disco | 0 |
| Sem máscara do desafio | 0 |
| Erro na leitura ou no pré-processamento | 0 |
| Tempo total | 41 minutos |
| Tempo por exame | mediana 2,6 s, de 1,3 a 5,6 |
| Tamanho por exame | mediana 10,0 MB, de 3,2 a 51,1 |
| Total em disco | 8,6 GiB |

Depois da reamostragem os volumes vão de 236 a 500 voxels no plano, com mediana de 360, e de 166
a 416 fatias, com mediana de 318.

## A máscara é larga demais em 37 exames

O volume que a máscara do desafio marca como pulmão tem mediana de 4,87 litros nos 888 exames, o
que é a capacidade pulmonar de um adulto. Mas **37 exames passam de 8 litros**, e o maior chega a
31 litros, o que nenhum pulmão humano tem.

Não é máscara trocada nem invertida: o HU mediano dentro dela é de -968 nesse exame extremo, ou
seja, ar. É máscara larga, que vazou para o ar em volta do paciente, que tem a mesma densidade do
ar dentro do pulmão.

Isso **não perde nódulo**, porque região a mais não corta nada. O que ele custa é área de busca,
e o efeito prático aparece só quando gerarmos candidatos próprios por detecção de blob: nesses 37
exames a busca sairia do corpo do paciente. Fica registrado aqui para ser tratado lá, e não agora.

Medido com `scripts/07_preprocessar_base.py` e conferido lendo o HU dentro da máscara nos cinco
exames de maior fração.

## O que ainda não existe

O recorte dos cubos ao redor de cada candidato, o baseline e a avaliação FROC.
