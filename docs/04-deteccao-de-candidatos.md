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
`dados/intermediario/cobertura_candidatos_proprios.csv`, no mesmo formato da tabela que
`scripts/08_comparar_candidatos.py` grava para as duas listas prontas, para comparar lado a lado.

**A rodada nos 888 exames ainda não aconteceu.** Esta sessão implementou e testou o código com
volumes sintéticos (`testes/test_blobs.py`), mas não tem acesso ao LUNA16 nem aos `.mha`
pré-processados nesta máquina — o `configuracao/config.yaml` aponta para o disco de quem rodou o
pré-processamento por último. Falta, com o disco montado:

```
python scripts/07_preprocessar_base.py   # se dados/processado/volumes ainda não existir
python scripts/10_detectar_candidatos.py
```

e preencher aqui a tabela de cobertura contra os 1.186 nódulos e os 98,3% de teto do
`candidates_V2.csv`, ajustando `min_sigma`, `max_sigma` e `threshold` no `config.yaml` se a
cobertura ficar longe disso.

## O que ainda não existe

Redução de falsos positivos sobre os candidatos gerados aqui.
