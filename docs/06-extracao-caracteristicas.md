# Extração de características de intensidade

Usamos os candidatos de `candidates_V2.csv` e a divisão por paciente de
`dados/processado/divisao.csv`. O extrator mantém o índice original da lista como
`candidate_id`, junto com exame, paciente, partição, coordenadas e classe.

Para cada candidato, extraímos um cubo de 34 voxels por eixo do volume processado.
O SimpleITK converte a posição em milímetros usando origem, espaçamento e direção
do próprio volume. O fundo externo ao volume é preenchido com zero. Centros fora
do volume e valores não finitos são registrados na auditoria.

Calculamos média, desvio padrão populacional, curtose de Fisher com o estimador
padrão do SciPy, mínimo, máximo e percentis 25 e 75. A curtose de patches constantes
é definida como zero por convenção do extrator. As intensidades já estão em [0, 1].
A curtose tem outra escala e não é limitada a esse intervalo.

## Executar

```bash
.venv/bin/python scripts/14_extrair_caracteristicas.py --amostra
.venv/bin/python scripts/14_extrair_caracteristicas.py --particao treino
.venv/bin/python scripts/14_extrair_caracteristicas.py --particao validacao
```

A amostra contém 50 positivos e 50 negativos do treino, com semente 42. Ela serve
para conferir a implementação. A extração completa mantém todos os candidatos e
o desbalanceamento original. O script não aceita a partição teste.

O código reutilizável está em `src/detection/features.py`. Os caminhos, o tamanho
do patch, a semente e o número de processos são lidos de `configuracao/config.yaml`.

## Saídas e retomada

Cada partição tem seu CSV de características, seu CSV de auditoria por candidato
e seu CSV de falhas por exame, em `dados/intermediario/`. Os arquivos por exame
ficam em `caracteristicas_cache/`, separados por uma chave calculada a partir
do código, das listas de entrada, dos parâmetros e dos metadados dos volumes
da partição. Os metadados incluem caminho, tamanho e data de modificação;
não são hashes do conteúdo dos volumes.

Uma execução interrompida pode ser retomada com o mesmo comando. O cache exige
a correspondência dos identificadores produzidos com a auditoria. Erros de exame
são tentados novamente. As gravações de cada CSV usam um arquivo temporário,
renomeado ao terminar. Um lote com falhas termina com código diferente de zero;
seus CSVs não devem ser tratados como uma extração completa.

Alterar o código ou as entradas muda a chave do cache. Os caches de treino gerados
antes desta versão ficam em disco, mas não são reaproveitados pela nova chave.

## Verificar

```bash
.venv/bin/python -m pytest testes/test_features.py testes/test_extracao_caracteristicas.py -q
```

Os testes cobrem direção LPI, preservação de rótulos, seleção da partição,
recusa de pacientes entre partições, retomada de erro de leitura e rejeição
de cache incompleto ou com identificadores trocados.

## Execução medida em 04/10/2026

Com `--particao validacao`, produzimos 75.063 linhas dos 89 exames de validação:
74.943 candidatos negativos e 120 positivos. Foram zero exames com erro e zero
candidatos descartados. A extração levou 183 segundos. Repetir o mesmo comando
recuperou os 89 exames do cache.

Conferimos os identificadores, rótulos e coordenadas contra a lista V2 associada
à divisão por paciente. Não encontramos valores ausentes ou infinitos nas features,
nem pacientes compartilhados com o CSV de treino. Os 120 positivos são candidatos
rotulados; essa contagem não representa a quantidade de nódulos detectados.

O SHA-256 do CSV de validação foi
`957645749dece20dcb91be42274681736695fc01ae40f02e194ad121f80c0022`.
O CSV de treino preservou o SHA-256
`752a1e69779bfa3bcde08368a2008642970775b02601d99c28190a602deeac43`.
A suíte completa passou com 93 testes, pelo comando
`.venv/bin/python -m pytest -q`.

A extração produz entradas para o classificador. Não mede FROC nem desempenho de
modelo treinado.
