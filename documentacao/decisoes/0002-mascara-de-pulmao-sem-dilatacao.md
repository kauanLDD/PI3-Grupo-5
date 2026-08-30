# 0002: como aplicamos a máscara de pulmão do desafio

**Estado:** decidido e verificado
**Data:** 29/08/2026

## Contexto

O enunciado põe a máscara de pulmão na etapa de Pré-processamento do KDD, com a finalidade
de "restringir a região de busca". Fonte: `PIEX3_projeto-grupo5_2026-08-03.pdf`, seção 2.

Ao gerar a figura de antes e depois do pré-processamento, notamos um nódulo encostado na
borda da máscara, aparentemente cortado. Medimos, e 29 dos 615 nódulos anotados dos subsets
0 a 4 têm o centro fora da máscara. Isso levantou a suspeita de que a máscara removeria
nódulo justapleural, aqueles colados na parede do pulmão.

A literatura reforça a suspeita. Li et al. (2023) e Shen et al. registram que de 5% a 17%
dos nódulos se perdem na etapa de segmentação do pulmão, os dois citando Armato e Sensakovic
(2004). O TiCNet (Ma et al., 2024) lista "nódulos fora do parênquima fornecido oficialmente"
entre as causas dos seus falsos negativos.

## O que medimos

O critério de acerto do desafio não exige que o candidato caia no centro do nódulo. A página
de avaliação do LUNA16 define acerto como candidato a menos de R do centro, com R igual ao
diâmetro dividido por dois. Um nódulo com o centro fora da máscara continua detectável desde
que sobre qualquer parte dele dentro.

Refizemos a contagem com esse critério, nos 615 nódulos anotados dos subsets 0 a 4, em
29/08/2026:

| Como binarizamos a máscara | Nódulos alcançáveis | Perda |
|---|---|---|
| `mascara > 0` | 615 de 615 | 0,00% |
| `mascara == 3 ou == 4` | 613 de 615 | 0,33%, IC95% [0,00%, 0,81%] |

Os rótulos presentes nas máscaras são 0, 3, 4 e 5, contados com `numpy.unique` sobre as 445
máscaras dos subsets que temos.

Os dois nódulos que se perdem com `3` e `4` medem 14,2 mm e 13,9 mm e estão no mesmo exame.

## Decisão

Aplicamos a máscara como o desafio entrega, sem dilatar, binarizando com `mascara > 0`.

Usar `> 0` em vez de `== 3 ou == 4` é escolha nossa e recupera dois nódulos. Toda a linhagem
de código pública do LUNA16, grt123, DeepLung, NoduleNet e DeepSEED, usa `3` e `4` e perde
esses dois.

## Alternativas consideradas e descartadas

**Dilatar a máscara antes de aplicar.** Descartamos porque não há o que recuperar: a perda
já é zero. Além disso, os quatro raios que a literatura publica não vêm com métrica ao lado.
São 10 mm em Setio et al. (2017), aplicados a filtrar uma lista de candidatos já pronta e
não a definir onde buscar; 10 mm em Fotin et al. (2019), em 706 exames privados que não são
o LUNA16; esfera de raio 6 em Zheng et al. (2022); e 10 iterações de voxel em Liao et al.
(2017), cujo próprio artigo declara que o sistema de avaliação do LUNA16 não serve para
medir o método deles. Nenhum dos quatro reporta sensibilidade ou CPM em função do raio.

**Não usar máscara nenhuma.** O nnDetection e o tutorial de detecção do MONAI treinam sobre
o volume inteiro. Descartamos porque o enunciado pede a máscara na etapa de
Pré-processamento, e porque ela reduz a região de busca sem nos custar nódulo.

## Uma armadilha que evitamos

O `prepare.py` do grt123, que é a receita mais copiada do campo, dilata **antes** de
reamostrar, com `generate_binary_structure(3, 1)`. Como o espaçamento em z do LUNA16 vai de
0,5 a 2,5 mm, o mesmo número de iterações vale distâncias físicas diferentes em cada exame,
e a conectividade 6 produz uma bola de norma L1 e não uma esfera.

Nosso `preprocessar()` reamostra para 1 mm isotrópico antes de aplicar a máscara, então
qualquer operação morfológica futura acontece em grade uniforme e o raio é o mesmo em todos
os exames.

## Como verificar

```
.venv/bin/python -m pytest testes/test_preprocessamento.py -v
```

O teste `test_rotulo_zero_recupera_dois_nodulos_que_o_padrao_perde` carrega o exame dos dois
nódulos e falha se alguém trocar a binarização para o padrão da literatura.

## Consequências

O `preprocessar()` de `codigo/pi3/preprocessamento/volume.py` não tem passo de dilatação, e
a máscara não impõe teto de sensibilidade nenhum sobre os nossos 615 nódulos.

Quando os subsets 5 a 9 chegarem, a medição precisa ser refeita sobre os 1.186 nódulos, e o
número desta página passa a valer só para os subsets 0 a 4.

## Em aberto

Preenchemos o lado de fora do pulmão com -1000 HU, que é ar. A linhagem grt123 preenche com
um valor de cinza médio. Não encontramos medição que compare as duas escolhas, e não trocamos
por imitação. Vira experimento quando houver modelo para medir a diferença.
