# Modelos

O peso não entra no git, o registro entra. Cada modelo treinado ganha uma linha aqui, e o
arquivo fica nesta pasta, cortado pelo `.gitignore`.

Toda linha aponta para o commit que gerou o modelo. Sem commit não há reprodução, e resultado
que não se reproduz não conta.

| Arquivo | O que é | Commit | Dado de treino | Resultado no teste |
|---|---|---|---|---|
| | | | | |

Nome: `<abordagem>_<data>_<commit-curto>.<ext>`, por exemplo `baseline-rf_2026-09-14_a3f21c.joblib`.

Junto do peso precisam estar a semente, a versão do `config.yaml`, o arquivo de divisão usado e
a métrica no conjunto de teste com intervalo de confiança.
