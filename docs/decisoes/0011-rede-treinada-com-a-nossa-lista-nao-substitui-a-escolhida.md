# 0011: a rede treinada também com a nossa lista não substitui a rede escolhida

**Estado:** decidido e verificado
**Data:** 07/11/2026

## Contexto

Na nossa lista de candidatos (LoG), a rede escolhida `cnn_lr_3e-4` faz CPM 0,465 na validação,
contra 0,752 na V2 (`docs/19`, seção 2). Medimos que muitos dos pontos que passam na frente dos
nódulos ficam a poucos milímetros de um nódulo (`docs/19`, seção 5), um tipo de ponto que a rede
quase não viu no treino.

Treinamos então a mesma rede, com os mesmos hiperparâmetros, usando também pontos da nossa lista
(`docs/19`, seção 6). Fixamos antes duas variantes e uma regra. Com a semente 42, a variante A
(negativos da nossa lista por sorteio uniforme) passou na regra: +0,049 no CPM da nossa lista,
IC95% da diferença pareada de +0,016 a +0,092, sem perda na V2. A variante B (metade dos negativos
vizinhos de nódulo) subiu 0,210 na nossa lista, mas caiu 0,072 na V2 e não passou.

Um resultado de uma semente não separa o efeito da configuração do efeito da semente (decisão
0010). Por isso fixamos uma segunda regra, também antes de rodar, e repetimos a A e a rede antiga
com as sementes 43 e 44.

## Decisão

**Mantemos a `cnn_lr_3e-4`, congelada pela decisão 0008, como a rede do projeto, nas duas
listas.** A variante A não se confirmou nas três sementes.

A regra (`config.yaml`, seção `sementes_lista_propria`) pedia duas coisas: (1) média de CPM na
nossa lista acima da média da rede antiga, com diferença pareada positiva nas três sementes; (2)
queda média de CPM na V2 de no máximo 0,022.

## Verificação

Medido em 07/11/2026 com `scripts/33_sementes_lista_propria.py`, na validação (89 exames, 111
nódulos), avaliador oficial, 1.000 reamostras por exame com semente 42:

| Semente | Nossa lista, antiga | Nossa lista, A | Diferença pareada (IC95%) | V2, antiga | V2, A | Diferença pareada (IC95%) |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 0,465 | 0,514 | +0,049 (+0,016 a +0,092) | 0,752 | 0,764 | +0,013 (-0,023 a +0,043) |
| 43 | 0,474 | 0,537 | +0,063 (-0,005 a +0,123) | 0,790 | 0,770 | -0,021 (-0,062 a +0,003) |
| 44 | 0,551 | 0,487 | -0,064 (-0,106 a -0,021) | 0,790 | 0,725 | -0,066 (-0,115 a -0,028) |
| Média ± desvio | 0,496 ± 0,047 | 0,513 ± 0,025 | | 0,777 ± 0,022 | 0,753 ± 0,025 | |

- Condição 1: a média na nossa lista sobe 0,016, mas a diferença pareada é negativa na semente
  44. Não vale.
- Condição 2: a média na V2 cai 0,024, acima do limite de 0,022. Não vale.

## O que descartamos

**Adotar a A pelo resultado da semente 42.** Ela passou na regra da Fase 2, mas a variação da
rede antiga entre sementes na nossa lista (0,465 a 0,551) é maior que o ganho medido com uma
semente (0,049).

**Adotar a B.** Não passou na regra da V2 com a semente 42 e não foi repetida com outras
sementes. O ganho dela na nossa lista vem de uma execução só.

**Uma terceira variante, escolhida depois de ver a B.** Seria escolha guiada pela validação, e o
tempo de GPU até o Review foi para as sementes.

**Filtrar a nossa lista antes da rede.** Os pontos que passam na frente dos nódulos têm o mesmo
perfil de raio e de distância à borda dos falsos positivos comuns (`docs/19`, seção 5), então não
havia um corte simples que os separasse.

**Medir no teste.** Nenhuma das redes desta frente foi ao teste.

## Consequências

A rede do projeto continua a `cnn_lr_3e-4`, com o resultado no teste da decisão 0008. Na nossa
lista, a rede antiga passa a ser reportada pela média das três sementes, 0,496 ± 0,047, e não só
pela semente 42.

Os cinco modelos novos ficam fora do git, registrados em `modelos/README.md`. O código que monta
o treino misto (`selecionar_misto`, `montar_cubos`, `treinar_cubos` em `src/experimentos/cnn.py`,
opção `--lista-propria` do script 18) continua no repositório.
