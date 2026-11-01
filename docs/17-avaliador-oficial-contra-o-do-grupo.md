# Avaliador oficial contra o cálculo do grupo, 01/11/2026

Pedido do professor no feedback da Sprint 4: mostrar que o avaliador oficial do LUNA16 que usamos
(`third_party/luna16`) dá o resultado certo, e comparar com a FROC que o grupo calculava no
notebook `curvafroc_pesquisa`, levada para `src/experimentos/froc_grupo.py`.

Todos os números deste documento foram medidos em 01/11/2026 com:

```bash
.venv-cnn-gpu/bin/python scripts/30_conferir_avaliador_oficial.py --avaliador "<pasta evaluationScript>"
```

A pasta usada foi uma cópia local do `evaluationScript`, com `annotations.csv` e
`annotations_excluded.csv` de mesmo md5 que o `dvc.lock`. As saídas ficam em
`relatorios/experimentos/avaliador_oficial/`, e o resumo em `conferencia.json`.

## 1. O exemplo do pacote

O pacote do desafio traz uma submissão de exemplo (`sampleSubmission.csv`, 551.065 marcas nos 888
exames) e a saída que o programa original gerou para ela. Essa saída é anterior ao limite de 100
marcas por exame, então rodamos a nossa cópia sem o limite para comparar.

| | Saída do pacote | Nossa cópia, sem limite |
|---|---:|---:|
| Acertos | 1.120 | 1.120 |
| Nódulos sem marca | 66 | 66 |
| Total de marcas | 551.065 | 551.065 |
| Marcas duplas sobre um nódulo | 231 | 231 |
| Marcas ignoradas sobre excluídas | 1.294 | 6.555 |
| Falsos positivos | 548.420 | 543.159 |
| CPM | 0,004456757 | 0,004456757 |

Os sete pontos da FROC são iguais (maior diferença 0,0). As duas contagens que diferem dependem da
lista de excluídas: a soma de ignoradas e falsos positivos é a mesma nos dois lados (549.714), e
inferimos que a saída do pacote foi gerada com uma lista de excluídas mais antiga que a
distribuída. Não temos essa lista antiga para confirmar.

Com o limite de 100 marcas, como usamos no projeto, o mesmo exemplo dá 244 acertos e CPM
0,004456757 (`exemplo_com_limite_100_CADAnalysis.txt`).

Nessa execução sem limite usamos 10 reamostras de bootstrap, e não 1.000
(`bootstrap_exemplo_sem_limite` no `config.yaml`): com 551.065 marcas, as 1.000 levariam cerca de
7 horas, medido pelo ritmo de 11 reamostras em 5 minutos em 27/10. O intervalo desse exemplo não
entra em nenhuma conclusão.

## 2. As avaliações do projeto

O script reavaliou com o oficial as previsões gravadas em `modelos/` e reproduziu os números
gravados nas três (`reproduz_resultado_gravado` em `conferencia.json`).

| Avaliação | CPM oficial (IC95%) | CPM do grupo (IC95%) | Diferença |
|---|---:|---:|---:|
| CNN no teste, 176 exames | 0,724 (0,670 a 0,778) | 0,611 (0,557 a 0,670) | -0,112 |
| CNN na validação, 89 exames | 0,752 (0,681 a 0,819) | 0,630 (0,554 a 0,703) | -0,122 |
| Random Forest centro na validação | 0,409 (0,323 a 0,505) | 0,351 (0,273 a 0,438) | -0,058 |

Os sete pontos de cada uma estão em `oficial_vs_grupo.csv`. O cálculo do grupo fica abaixo do
oficial em todos os pontos; o mais próximo é a CNN na validação a 8 FP (0,8917 contra 0,8919). Na
CNN a distância é maior nas taxas baixas de falso positivo: no teste, -0,157 a 0,125 FP por exame e -0,018 a 8.

## 3. Por que os dois diferem

O cálculo do grupo e o oficial contam coisas diferentes:

- **Acerto por candidato, não por nódulo.** No teste, 339 candidatos caem dentro de algum dos 223
  nódulos. O cálculo do grupo divide os acertos por 339 marcas positivas; o oficial conta cada
  nódulo uma vez e ignora a segunda marca sobre ele.
- **Excluídas viram falso positivo.** As 1.727 marcas sobre achados excluídos do teste (746 na
  validação) entram como falso positivo no cálculo do grupo. O oficial tira essas marcas da conta.
- **Sem limite de marcas.** O cálculo do grupo usa todas as marcas do exame; o oficial guarda até
  100.

Os números do projeto gravados em `modelos/` saem do avaliador oficial. O cálculo do grupo fica no
repositório só para esta comparação, com o teste de igualdade contra a função original do notebook
em `testes/test_froc_grupo.py`.
