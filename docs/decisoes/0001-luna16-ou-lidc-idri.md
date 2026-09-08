# 0001: qual base o Grupo 5 usa, LUNA16 ou LIDC-IDRI

**Estado:** decidido, com atualizações em 26/08, 30/08 e 07/09/2026
**Data:** 25/08/2026

## Contexto

O enunciado do professor traz duas indicações diferentes.

A seção 4.2, que descreve o LIDC-IDRI, diz "principal uso neste projeto: Grupos 3, 4 e 5".
A seção 7.2, que é o plano do Grupo 5, diz "Dataset principal: LUNA16 (candidates.csv +
annotations.csv fornecidos pelo desafio)". As atividades da seção 7.4 e o baseline da
seção 7.3 são escritos sobre o LUNA16.

Fonte: `PIEX3_projeto-grupo5_2026-08-03.pdf`.

## Decisão

Adotamos o LUNA16 como base principal. O `candidates.csv`, que é a entrada do baseline
obrigatório da seção 7.3, existe só nele.

Mantemos o LIDC-IDRI em disco pela anotação individual dos quatro radiologistas, que o
LUNA16 consolida em um nódulo por achado.

## Alternativa considerada

Reconstruir os volumes do LUNA16 a partir do DICOM do LIDC-IDRI, baixando só os CSVs.

Não seguimos por esse caminho. As coordenadas do `annotations.csv` estão em espaço de
mundo definido contra a origem dos volumes `.mhd` do desafio, e a reconstrução exigiria
reproduzir origem e espaçamento idênticos aos dele. Baixamos o LUNA16 em 25/08.

## O que foi medido

Todos os números abaixo saíram de leitura direta dos arquivos em 25/08/2026, cruzando
`Luna16/archive/annotations.csv`, `Luna16/archive/candidates.csv` e
`LIDC-IDRI/Imagens LIDC-IDRI/metadata/metadata.csv`, por leitura direta dos arquivos.

Cruzamento dos identificadores: os 601 `seriesuid` do `annotations.csv` aparecem todos
entre os 1308 `SeriesInstanceUID` do LIDC-IDRI em disco. Zero ausentes.

`annotations.csv`: 1.186 nódulos em 601 scans. Média de 1,97 nódulo por scan, máximo 12.
Diâmetro de 3,25 a 32,27 mm, mediana 6,43.

`candidates.csv`: 551.065 candidatos em 888 scans, 1.351 positivos, 0,2452%. De 32 a
1.468 candidatos por scan.

Cabeçalhos `.mhd` de dois volumes do subset0: `TransformMatrix` identidade, orientação
RAI, espaçamento em z de 2,5 mm em um e 0,625 mm no outro, com 121 e 538 fatias.

LIDC-IDRI: 1010 pacientes, 1308 séries, 133,1 GB, todas com `completion_status: success`.

## O que está em disco

Do LUNA16: `annotations.csv`, `candidates.csv`, `candidates_V2`, `sampleSubmission.csv`,
subsets 0 a 4, `seg-lungs-LUNA16` e `evaluationScript`, este último contendo
`noduleCADEvaluationLUNA16.py`, `annotations.csv` e `annotations_excluded.csv`.

Os subsets 5 a 9 não foram baixados.

O zip do Kaggle extrai com a pasta repetida: `subset0/subset0/`,
`seg-lungs-LUNA16/seg-lungs-LUNA16/`, `evaluationScript/evaluationScript/`.

## Ainda não verificado

A diferença entre os 888 scans do `candidates.csv` e os 601 do `annotations.csv` não foi
investigada. A leitura de que os 287 restantes não têm nódulo elegível pelo critério do
desafio é dedução a partir da documentação, não conferência arquivo a arquivo.

O papel do `annotations_excluded.csv` no cálculo saiu da leitura do
`noduleCADEvaluationLUNA16.py` e da página do desafio. Não foi confirmado rodando o
script.

Nenhum cabeçalho DICOM do LIDC-IDRI foi lido. A separação entre séries de TC e outras
modalidades ainda é dedução por tamanho de arquivo.

## Atualização de 26/08/2026

O LIDC-IDRI saiu do projeto. A parte desta decisão que dizia mantê-lo em disco pela anotação
individual dos quatro radiologistas **não vale mais**, e com ela saíram a tabela de nódulos por
radiologista e a figura de concordância que a análise exploratória teria.

O que continua valendo é o resto: usamos o LUNA16 como base, pelo motivo escrito acima, e o
`annotations.csv` dele é a nossa verdade de campo, com o nódulo já consolidado e sem dizer
quem marcou o quê.

## Atualização de 30/08/2026

Os dez subsets estão em disco. São os 888 exames do desafio, e conferimos que a lista em disco
fecha exatamente com o `seriesuids.csv` oficial, sem exame a mais nem a menos, e que os três
CSV têm md5 idêntico ao que o desafio publica.

Com isso, a frase acima de que os subsets 5 a 9 não foram baixados **não vale mais**, e o
caminho vigente é `luna/archive` e não `Luna16/archive`. O que continua valendo é o resto: a
base é o LUNA16, pelo motivo escrito no começo.

## Atualização de 07/09/2026

Passamos a usar o `candidates_V2.csv` no lugar do `candidates.csv`. A medição acima, de 551.065
candidatos com 1.351 positivos, continua correta para o arquivo que ela mediu, mas não é mais a
lista que alimenta o nosso baseline: o V2 tem 754.975 candidatos com 1.557 positivos e alcança
1.166 dos 1.186 nódulos, contra 1.120 do primeiro. O critério inteiro está em
`criterios_inclusao_luna16.md`.

Na mesma conferência respondemos o que ficou aberto em "Ainda não verificado": os 287 exames que
aparecem na lista de candidatos e não aparecem no `annotations.csv` são exames sem nódulo elegível
pelo critério do desafio, e isso agora é contagem feita nos arquivos, não dedução.
