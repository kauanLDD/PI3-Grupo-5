# Geração de candidatos

Olhar o pulmão pré-processado e apontar os pontinhos suspeitos, para o modelo de redução de
falsos positivos decidir depois quais são nódulo de verdade. É o produto central do grupo e a
etapa de Transformação do KDD.

O código está em `src/detection/blobs.py` e roda por `scripts/10_detectar_candidatos.py`.

## Por que blob detection, e não threshold adaptativo

O card do Sprint 3 já indica as duas opções. Ficamos com blob detection 3D por Laplacian of
Gaussian, pronto no `skimage.feature.blob_log`: nódulo é uma bolinha mais clara que o tecido em
volta, e o LoG é feito para achar exatamente isso, em várias escalas de tamanho ao mesmo tempo.
Threshold adaptativo com componentes conexos precisaria de um passo a mais para separar
componentes por tamanho e formato, que o blob_log já devolve pronto como `sigma`.

## Como funciona

O volume de entrada é o `.mha` pré-processado: pulmão isolado, voxel isotrópico de 1 mm,
intensidade normalizada em [0, 1] (`docs/03-pre-processamento.md`). O `blob_log` varre esse
volume em várias escalas de desvio padrão gaussiano (`sigma`, de `min_sigma` a `max_sigma`) e
aponta onde a resposta do Laplaciano é máxima. Cada blob sai como `(z, y, x, sigma)`, em índice
de voxel.

**Sigma vira raio.** A resposta do LoG é máxima quando o raio do blob é `sigma * sqrt(3)` em três
dimensões. Como o voxel é isotrópico de 1 mm, multiplicar por `sqrt(3)` já dá o raio em
milímetro; a fórmula em `blobs.raio_mm` multiplica também pelo espaçamento do arquivo, para
continuar certa se o espaçamento alvo do pré-processamento mudar.

**Índice vira coordenada de mundo.** O `.mha` pré-processado carrega a própria origem, o próprio
espaçamento e a própria direção, herdados do volume original pela reamostragem
(`src/preprocessing/volume.py`). Por isso a conversão usa `imagem.TransformContinuousIndexToPhysicalPoint`
direto no arquivo, em vez de reconstruir a geometria a mão como faz
`src/preprocessing/coordenadas.py` para os volumes originais, ainda não reamostrados.

**Os parâmetros de partida** são os do card: `min_sigma=1`, `max_sigma=5`, `threshold=0.1`,
guardados em `configuracao/config.yaml`, chave `deteccao.blob_log`. Ajustar é mudar o número ali,
não no código.

## Como validar um exame antes de soltar nos 888

`scripts/10_detectar_candidatos.py` primeiro roda num exame só, o de maior nódulo entre os de
direção identidade (o mesmo critério de escolha de `scripts/04_preprocessar.py`), mostra quantos
blobs saíram e quantos dos nódulos anotados daquele exame têm candidato em cima, e desenha a
fatia do nódulo com os candidatos por perto em `relatorios/figuras/deteccao_candidatos.png`
(verde = nódulo anotado, vermelho = candidato do `blob_log`). Só depois disso ele passa para os
888.

## A cobertura, e o teto das listas prontas do desafio

O critério de acerto é o mesmo de `src/detection/candidatos.py`, usado em
`docs/criterios_inclusao_luna16.md` para comparar `candidates.csv` e `candidates_V2.csv`: um
nódulo é alcançado quando existe candidato a menos de um raio do centro dele. Rodar
`scripts/10_detectar_candidatos.py` grava a cobertura da lista própria em
`dados/intermediario/cobertura_candidatos_proprios.csv`, na mesma tabela que
`scripts/08_comparar_candidatos.py` grava para as duas listas prontas, menos a coluna
`positivos`, que só existe onde há rótulo de classe.

## O que os parâmetros de partida entregam

A rodada nos 888 exames não aconteceu. O que medimos, em 13/09/2026, foi uma amostra de 8 exames,
um por subset, com `python scripts/10_detectar_candidatos.py 8`:

| | |
|---|---|
| Candidatos | 112.287 nos 8 exames, 14.036 por exame |
| Nódulos alcançados | 6 de 6 |
| Tempo | 189 s nos 8 exames, 23,6 s por exame |

Para comparar, o `candidates_V2.csv` do desafio tem 850,2 candidatos por exame e alcança 1.166
dos 1.186 nódulos, 98,3%, medido em 03/09/2026 com `scripts/08_comparar_candidatos.py` e
registrado em `docs/criterios_inclusao_luna16.md`. A nossa lista sai com 16 vezes mais pontos por
exame, e os 8 exames da amostra têm 6 nódulos anotados, que é pouco para comparar cobertura.

## O que ainda não existe

A calibração de `min_sigma`, `max_sigma` e `threshold` contra a cobertura nos 888 exames, e a
redução de falsos positivos sobre os candidatos gerados aqui.
