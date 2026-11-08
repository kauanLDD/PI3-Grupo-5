# 0012: na nossa lista de candidatos, suprimimos vizinhos a 16 mm depois da rede

**Estado:** decidido e verificado na validação
**Data:** 08/11/2026

## Contexto

Na nossa lista (LoG), a rede escolhida `cnn_lr_3e-4` faz CPM médio de 0,496 nas sementes 42, 43
e 44, contra 0,777 na V2 (`docs/19`, seção 7). Treinar a rede com pontos da nossa lista não
resolveu (decisão 0011). Os detectores publicados de 2020 em diante suprimem marcas repetidas a uma
distância da ordem do diâmetro do nódulo, e a nossa supressão era de 5 mm.

## Decisão

**Na nossa lista, depois da rede, mantemos em cada exame a marca de maior escore e descartamos as
que ficam a até 16 mm dela.** A rede continua a mesma, sem treino novo.

Fixamos antes de rodar três variantes e a regra (`config.yaml`, seção `supressao_lista_propria`;
`docs/19`, seção 8): supressão a 10 mm, supressão a 16 mm e média das notas das três sementes.

## Verificação

Medido em 08/11/2026 com `scripts/34_supressao_lista_propria.py`, na validação (89 exames, 111
nódulos), avaliador oficial, 1.000 reamostras por exame com semente 42:

| Variante | Média de CPM nas três sementes | Diferença pareada contra a lista inteira |
|---|---:|---|
| Lista inteira | 0,496 ± 0,047 | |
| Supressão 10 mm | 0,588 ± 0,052 | positiva nas três sementes |
| Supressão 16 mm | 0,769 ± 0,037 | de +0,260 a +0,281, IC95% acima de zero nas três |
| Média das sementes | 0,525 | negativa contra a semente 44 |

As duas supressões passam na regra, e fica a de maior média. A média das sementes não passa.

## O que descartamos

**Suprimir pelo raio que o LoG estima para cada ponto.** 97,6% dos pontos da validação têm o mesmo
raio, 1,73 mm, e o raio de supressão ficaria perto de 3,5 mm, abaixo dos 5 mm já medidos.

**A média das sementes.** Não passou na regra.

**Medir no teste.** Nada desta decisão usou o teste.

## Consequências

Na nossa lista, reportamos a rede com a supressão a 16 mm. Na validação, nenhum par de nódulos de
um mesmo exame fica a menos de 19,46 mm. No conjunto todo há um par a 5,92 mm, que essa supressão
junta em uma marca só. Com a semente 42, 98 dos 111 nódulos ficam entre as 100 marcas de cada
exame, contra 100 da lista inteira. A supressão não foi aplicada à V2.
