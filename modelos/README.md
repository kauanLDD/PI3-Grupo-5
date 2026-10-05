# Modelos

O peso não entra no git, o registro entra. Cada modelo treinado ganha uma linha aqui, e o
arquivo fica nesta pasta, cortado pelo `.gitignore`.

Toda linha identifica o estado do código que gerou o modelo. Enquanto a entrega
não foi commitada, registramos o commit base e o run do MLflow, que guarda a cópia
do código, o ambiente e os hashes das entradas. O commit base sozinho não reproduz
as alterações locais dessa execução.

| Arquivo | O que é | Commit | Dado de treino | Resultado no teste |
|---|---|---|---|---|
| `random_forest_v2/modelo.joblib` | Random Forest inicial, 200 árvores | Base `c87bf93`, com alterações locais; run `1663d6b906ee486bb0cfff9fdd09457d` | 529.500 candidatos V2 de 622 pacientes | Não avaliado; teste reservado |
| `cnn3d_2026-10-05_final/modelo.pt` | CNN3D 16/32/64, 15 épocas, CPU | Base `accb02c`, alterações locais guardadas no MLflow; run `594440921c0c448cbf9b6e431861b68a` | Reprodução técnica: 18 candidatos V2 (3 positivos) de 2 exames, subset 0; seed 42 | 2 exames do subset 8, 1.032 candidatos, 4 nódulos; CPM 0,000; sensibilidade a 4 FP/exame 0,000, IC bootstrap 95% [0,000; 0,000] |
| `cnn3d_2026-10-05_repeticao/modelo.pt` | Repetição determinística da CNN acima | Base `accb02c`, alterações locais guardadas no MLflow; run `539fe19dfd0547529bc951b290457284` | Mesmas entradas e parâmetros, hashes conferidos | Pesos, probabilidades e curvas idênticos; CPM 0,000 |

Nome: `<abordagem>_<data>_<commit-curto>.<ext>`, por exemplo `baseline-rf_2026-09-14_a3f21c.joblib`.

Junto do peso precisam estar a semente, a versão do `config.yaml`, o arquivo de divisão usado e
a identificação das entradas. Quando houver avaliação no teste, registrar a métrica
com intervalo de confiança, sem substituir resultados de validação por resultados de teste.

O primeiro treino foi executado em 04/10/2026 por
`scripts/17_treinar_random_forest.py`. O ajuste levou 145,01 segundos e produziu
75.063 escores de validação. O run do MLflow contém os artefatos e a procedência.
FROC e CPM ainda não foram medidos. Ver `docs/08-primeiro-treino.md`.

A CNN foi integrada e repetida em 05/10/2026. A curva inteira, os 10.000 pontos
do bootstrap e a procedência estão no MLflow e em
[`relatorios/experimentos/cnn_reproducao`](../relatorios/experimentos/cnn_reproducao/).
Os resultados acima são de uma amostra técnica pequena, sem inferência sobre os
888 exames. O treino e a avaliação completos da CNN continuam pendentes.
O IC degenerado da amostra não prova ausência de sensibilidade na população.
Ver [Integração da CNN](../docs/09-cnn-mlflow.md) para comandos, versão dos dados,
adaptação do avaliador oficial e a distinção entre esta execução e a pesquisa do Kaggle.
