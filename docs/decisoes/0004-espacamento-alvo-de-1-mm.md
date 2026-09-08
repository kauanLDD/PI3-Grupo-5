# 0004: o espaçamento alvo da reamostragem é 1 mm isotrópico

**Estado:** decidido e verificado
**Data:** 07/09/2026. Medido em 02/09/2026 e refeito em 07/09/2026 com resultado idêntico.

## Contexto

Os volumes do LUNA16 não têm voxel cúbico. O espaçamento no plano vai de 0,46 a 0,98 mm e o
espaçamento entre fatias vai de 0,45 a 2,5 mm, um fator de cinco entre o exame mais fino e o mais
grosso. Sem reamostrar, um nódulo de 6 mm ocupa treze fatias num exame e duas em outro, e o
modelo aprende a espessura de corte em vez de aprender o nódulo.

O enunciado manda reamostrar e **não diz para quanto**: a tabela do KDD lista "ressampling" e
nada mais. O feedback do professor nomeia 1 mm isotrópico na descrição das etapas do
pré-processamento.

O problema é que o valor de 1 mm não entrou aqui por medição nossa. Ele está no
`configuracao/config.yaml` desde o commit `1c2ef4d`, de 25/08/2026, que é o primeiro commit do
repositório e só criou a estrutura de pastas. O script que mede alguma coisa a respeito,
`scripts/06_escolher_espacamento.py`, só apareceu no commit `e370aa4`, de 02/09/2026. Por oito
dias o parâmetro central do pré-processamento foi herança, e a justificativa que dávamos para ele
era racionalização escrita depois.

Este registro existe para desfazer isso: ou o número se sustenta na medição, ou muda.

## Decisão

Mantemos **1,0 mm isotrópico**, agora com medição atrás e não por herança.

## O que medimos

`scripts/06_escolher_espacamento.py` compara oito espaçamentos em três eixos: o quanto o nódulo se
destaca do tecido em volta, quantos nódulos deixam de caber no recorte, e quanto custa em voxels.

O contraste é a diferença entre a mediana de HU dentro do nódulo e a mediana num cubo três vezes
maior em volta dele, sobre uma amostra estratificada por diâmetro de 39 nódulos em volumes de
direção identidade, com intervalo de 95% por bootstrap de 1.000 reamostras. As outras três colunas
são calculadas sobre a população inteira: os 1.186 nódulos anotados e os 888 exames do inventário.

| Alvo (mm) | Contraste (HU), mediana e IC 95% | Nódulo mediano em voxels | Não cabem em 32 | Volume (Mvox) |
|---|---|---|---|---|
| 0,5 | 257 [220, 294] | 12,9 | 112 | 315 |
| 0,625 | 237 [193, 282] | 10,3 | 50 | 161 |
| 0,7 | 235 [170, 296] | 9,2 | 23 | 115 |
| 0,8 | 228 [188, 267] | 8,0 | 6 | 77 |
| **1,0** | **245 [192, 282]** | **6,4** | **1** | **39** |
| 1,25 | 180 [130, 242] | 5,1 | 0 | 20 |
| 1,5 | 149 [119, 215] | 4,3 | 0 | 12 |
| 2,0 | 121 [94, 165] | 3,2 | 0 | 5 |

Três leituras saem daí.

**Reamostrar mais fino que 1 mm não compra contraste.** De 0,5 a 1,0 mm os intervalos de confiança
se sobrepõem todos, e a mediana em 1,0 mm é maior que em 0,8 e 0,7. O que 0,5 mm compra é custo:
315 milhões de voxels por volume contra 39, oito vezes mais, para uma diferença que a nossa
amostra não distingue.

**O único espaçamento que a medição separa é 2,0 mm.** O intervalo dele, de 94 a 165 HU, não toca
o de 1,0 mm, de 192 a 282. O de 1,5 mm encosta.

**Reamostrar mais fino piora o recorte.** A 0,5 mm, 112 dos 1.186 nódulos ficam maiores que um
cubo de 32 voxels. A 1,0 mm sobra um só.

## A alternativa que descartamos

**1,25 mm.** É a candidata séria, e não a descartamos por medição: custa metade dos voxels de
1,0 mm, nenhum nódulo deixa de caber no recorte, e o intervalo de contraste dele, de 130 a 242,
ainda se sobrepõe ao de 1,0 mm. **Com 39 nódulos não conseguimos separar os dois.**

Ficamos em 1,0 mm por dois motivos que não são estatísticos e que declaramos como tais. É o valor
que a literatura do LUNA16 usa, e sair dele introduz uma diferença nossa contra o baseline público
sem ganho medido, que é o mesmo argumento de não segmentarmos pulmão e de não escrevermos curva
FROC própria. E é o valor que o professor nomeia no feedback.

Se em algum momento o custo de processar os 888 virar o gargalo, 1,25 mm é a primeira coisa a
testar, e esta tabela é o ponto de partida.

**0,5 mm.** Descartado por medição: oito vezes o custo, sem contraste a mais, e com 112 nódulos
que não cabem no recorte.

**Não reamostrar.** Descartado por definição do problema. O modelo veria a espessura de corte como
se fosse anatomia.

## Consequências

**O recorte de 32 voxels não serve.** A 1,0 mm, o nódulo de 32,27 mm do `annotations.csv` fica de
fora. Conferido: a 1,0 mm são 1 nódulo fora com recorte de 32 e 0 com recorte de 34. O
`candidatos.patch` do `config.yaml` precisa virar 34 antes de qualquer recorte ser extraído.

**O nódulo mediano ocupa 6,4 voxels de ponta a ponta.** É pequeno, e é o que justifica o recorte
ser dezenas de vezes maior que o alvo: o modelo precisa do contexto em volta para separar nódulo
de vaso.

**O volume reamostrado cresce em relação ao original nos exames grossos.** O exame de teste, de
2,5 mm entre fatias, sai de 512 × 512 × 123 para 420 × 420 × 308, e ocupa 7,1 MB em inteiro de 16
bits comprimido.

**O valor está declarado no `dvc.lock`.** Mudar `pre_processamento.espacamento_alvo` no
`config.yaml` marca os estágios `preprocessar` e `eda` como desatualizados, então a tabela acima e
o valor em uso não podem mais divergir em silêncio. Ver a decisão 0005.
