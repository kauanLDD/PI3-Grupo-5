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

Nome: `<abordagem>_<data>_<commit-curto>.<ext>`, por exemplo `baseline-rf_2026-09-14_a3f21c.joblib`.

Junto do peso precisam estar a semente, a versão do `config.yaml`, o arquivo de divisão usado e
a identificação das entradas. Quando houver avaliação no teste, registrar a métrica
com intervalo de confiança, sem substituir resultados de validação por resultados de teste.

O primeiro treino foi executado em 04/10/2026 por
`scripts/17_treinar_random_forest.py`. O ajuste levou 145,01 segundos e produziu
75.063 escores de validação. O run do MLflow contém os artefatos e a procedência.
FROC e CPM ainda não foram medidos. Ver `docs/08-primeiro-treino.md`.
