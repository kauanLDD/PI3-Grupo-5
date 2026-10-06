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

Em 03/10/2026, concluímos a rodada nos 888 exames com
`.venv/bin/python scripts/10_detectar_candidatos.py`. O processo foi interrompido depois de 218
exames e retomado a partir dos arquivos por exame, sem recalcular o que já estava completo.

| | |
|---|---|
| Exames no inventário | 888 |
| Exames processados | 888 |
| Exames com erro | 0 |
| Candidatos | 14.310.042 |
| Candidatos por exame | 16.114,9 |
| Nódulos alcançados | 1.158 de 1.186, 97,6% |

O CSV consolidado tem os mesmos 14.310.042 registros que a soma dos 888 arquivos por exame e
contém exatamente os 888 identificadores do inventário. O relatório
`dados/intermediario/falhas_deteccao.csv` ficou sem linhas de falha.

Para comparar, o `candidates_V2.csv` do desafio tem 754.975 candidatos, 850,2 por exame, e
alcança 1.166 dos 1.186 nódulos, 98,3%. A nossa lista tem 19 vezes mais candidatos por exame e
alcança oito nódulos a menos. Contagem de candidatos por exame não é FP por exame: a lista
ainda não passou por um classificador nem pelo script oficial da FROC.

### Rodada curta anterior

Em 13/09/2026, antes da rodada completa, medimos uma amostra de 8 exames, um de cada um dos
subsets 0 a 7, com `python scripts/10_detectar_candidatos.py 8`:

| | |
|---|---|
| Candidatos | 112.287 nos 8 exames, 14.036 por exame |
| Nódulos alcançados | 6 de 6 |
| Tempo | 189 s nos 8 exames, 23,6 s por exame |

Naquela amostra, a lista saía com 16 vezes mais pontos por exame que o `candidates_V2`, mas os
8 exames tinham somente 6 nódulos anotados. A rodada completa substitui essa amostra como
medição da cobertura e da quantidade de candidatos.

## Calibração exploratória

Em 20/09/2026, comparamos quatro configurações em 21 exames de desenvolvimento e conferimos
a escolhida em 12 exames de validação. O limiar 0,20 reduziu os candidatos em 68,9% no
desenvolvimento e preservou 23 de 23 nódulos. Na validação, reduziu 67,1%, mas alcançou 10 de
11 nódulos, contra 11 de 11 da configuração inicial. As 108 execuções terminaram sem falhas.

O critério definido antes da comparação reprovou o limiar 0,20. Mantivemos os parâmetros
iniciais no detector de produção. O protocolo, os intervalos de confiança e as limitações da
amostra estão em `docs/05-calibracao-detector.md`.

## A rodada nos 888 exames

É o card S4-T10. Ela mede duas coisas: quantos dos nódulos anotados a busca alcança e quantos
candidatos ela gera por exame. Os dois números juntos dão o limite máximo do sistema, porque o
classificador que vem depois só pode acertar nódulo que tenha candidato em cima, e cada candidato
a mais é mais um falso positivo em potencial para ele descartar.

**Cobertura não é FROC.** A cobertura é o teto de sensibilidade da lista, sem escore e sem
contagem de falso positivo. A curva FROC só existe quando houver um classificador dando nota a
cada candidato, e os números desta seção não podem ser reportados como ponto dela.

### Como rodar

```bash
.venv/bin/python scripts/10_detectar_candidatos.py 8    # rodada curta, para conferir
.venv/bin/python scripts/10_detectar_candidatos.py      # os 888
```

A rodada usa dois processos e reaproveita os arquivos por exame em
`dados/intermediario/deteccao_log/<chave>/por_exame/`. A chave considera o código
do detector, seus parâmetros e o relatório de pré-processamento. Conferimos as
colunas, a identidade do exame e os valores finitos antes de reutilizar um CSV.

Volumes ausentes interrompem a rodada. Falhas de processamento são registradas
em `falhas_deteccao.csv` e impedem a substituição das saídas finais. Os arquivos
já concluídos ficam disponíveis para a retomada.

**Antes de soltar os 888, confirme a configuração.** Os parâmetros que valem são os registrados
no card S4-T9, e o limiar de 0,20 não pode ser o escolhido, porque perdeu um nódulo na
validação. O script imprime os parâmetros no começo da rodada.

### O que ela grava

| Arquivo | O que tem |
|---|---|
| `dados/intermediario/candidatos.csv` | a lista, uma linha por candidato: `seriesuid`, `coordX`, `coordY`, `coordZ` em mm de mundo e `raio` em mm |
| `dados/intermediario/situacao_deteccao.csv` | uma linha por exame: concluído, sem candidato, falha ou pendente, com contagem, tempo e erro |
| `dados/intermediario/cobertura_candidatos_proprios.csv` | nódulos alcançados, cobertura e intervalo de 95% |
| `dados/intermediario/troca_cobertura_candidatos.csv` | cobertura contra candidatos por exame, para a lista própria e para as duas do desafio |

**Exame sem candidato é resultado, não falha.** Ele entra no denominador da média de candidatos
por exame, como vai entrar na média de falso positivo da FROC.

**Só publicamos a cobertura quando todo o lote termina.** Falhas ficam registradas
separadamente e fazem o comando terminar com erro, preservando as saídas anteriores.

**O intervalo de 95% é por bootstrap de exame**, com as reamostras de
`avaliacao.bootstrap_reamostras`. Os nódulos de um mesmo exame não são independentes, e
reamostrar nódulo solto estreitaria o intervalo sem motivo. A função é
`detection.candidatos.cobertura`.

**A troca entre cobertura e quantidade de candidatos.** Dentro da lista própria, cortar as
escalas menores do `blob_log` (filtro `raio >= r`) dá menos pontos sem rodar de novo, e a tabela
mostra quanto de cobertura cada corte custa. Na mesma tabela entram o `candidates.csv` e o
`candidates_V2.csv`, medidos sobre os mesmos exames. O número a bater é o do V2: 1.166 dos
1.186 nódulos, com 850 candidatos por exame.

### O que ela mediu

Os 888 exames foram processados com a configuração inicial, sem falhas, conforme
o registro acima. A integração da PR #4 acrescenta a situação por exame, o
intervalo de confiança e a tabela de comparação por escala, reutilizando os
candidatos já gerados.

## A lista própria contra o V2

Em 05/10/2026 comparamos as duas listas nos mesmos 888 exames e 1.186 nódulos, com cobertura,
candidatos por exame, tempo de geração e espaço em disco. O V2 continua sendo a entrada dos
classificadores, e a lista própria é avaliada como detector, ao lado dele. A tabela e o motivo
estão em `docs/decisoes/0007-lista-de-candidatos-por-experimento.md`, e o
`scripts/18_comparar_lista_propria_v2.py` refaz a comparação e mede quais nódulos cada lista
alcança e a outra não.

## O que ainda não existe

A redução de falsos positivos sobre os candidatos gerados aqui, o modelo treinado e a
avaliação FROC no conjunto de teste.
