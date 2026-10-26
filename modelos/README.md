# Modelos

Cada modelo treinado ganha uma linha aqui. Desde 25/10/2026, três pastas entram inteiras no git,
com peso, previsões e avaliação: `cnn_lr_3e-4` (a rede escolhida), `cnn_lr_3e-4_teste_final` (a
avaliação no teste) e `random_forest_centro` (o modelo simples de comparação). Os pesos somam
cerca de 13 MB e as previsões são o que o grupo usa para avaliar e analisar erros. As outras
pastas continuam cortadas pelo `.gitignore`; os resultados delas estão em
`relatorios/experimentos/comparacao_validacao/`.

Toda linha identifica o estado do código que gerou o modelo. Enquanto a entrega
não foi commitada, registramos o commit base e o run do MLflow, que guarda a cópia
do código, o ambiente e os hashes das entradas. O commit base sozinho não reproduz
as alterações locais dessa execução.

| Arquivo | O que é | Commit | Dado de treino | Resultado no teste |
|---|---|---|---|---|
| `cnn_verificacao_4_exames/modelo.pt` | CNN3D, verificação técnica de uma época | Base `7ec3da3`, integração local da PR #5 e correções; run `9002b29b2f0d4c06a1388e8bd300baf1` | 18 candidatos de dois exames; validação em outros dois exames | Não avaliado; teste reservado |
| `cnn_v2/modelo.pt` | CNN3D 16/32/64, 15 épocas, primeiro treino completo, na RTX 4050 | Base `7ec3da3`, integração local da PR #5 e correções; run `4f52dc350af44d099574a26ac1567731` | 6.588 candidatos V2 (1.098 positivos) de 622 pacientes; validação em 75.063 candidatos de 89 pacientes | Não avaliado; teste reservado |
| `cnn_epocas_40/modelo.pt` | CNN3D, 40 épocas | Base `7ec3da3`, alterações locais da integração da PR #5 e dos experimentos de 13/10; run `a90b6d297f6d44b7bd45961673d5dff8` | 6.588 candidatos V2 de 622 pacientes | Não avaliado; teste reservado |
| `cnn_aumento/modelo.pt` | CNN3D, 40 épocas, aumento de dados | Base `7ec3da3`, alterações locais da integração da PR #5 e dos experimentos de 13/10; run `7b2c2f4356a74287aeb1f802ae880c04` | 6.588 candidatos V2 de 622 pacientes | Não avaliado; teste reservado |
| `cnn_negativos_20/modelo.pt` | CNN3D, 40 épocas, aumento, 20 negativos por positivo | Base `7ec3da3`, alterações locais da integração da PR #5 e dos experimentos de 13/10; run `5529e76dd327489d870dd51b1f875036` | 23.058 candidatos V2 de 622 pacientes | Não avaliado; teste reservado |
| `cnn_lr_3e-4/modelo.pt` | CNN3D, 40 épocas, aumento, 20 negativos, learning rate 3e-4 | Base `7ec3da3`, alterações locais da integração da PR #5 e dos experimentos de 13/10; run `2f8b0a3c57c84d9e8f51dea2eab94b7f` | 23.058 candidatos V2 de 622 pacientes | CPM 0,724 (IC95% 0,670 a 0,778); sens. 4 FP 0,883 (0,843 a 0,929); run `d754f0738780451a8a734be0ac58a435` |
| `random_forest_centro/modelo.joblib` | Random Forest, 21 features em cubos de 8, 16 e 34 voxels | Base `7ec3da3`, alterações locais da integração da PR #5 e dos experimentos de 13/10; run `5169e10d13874969804d14f29cca6ea6` | 529.500 candidatos V2 de 622 pacientes | CPM 0,420 (IC95% 0,349 a 0,490); sens. 4 FP 0,520 (0,442 a 0,603); segundo uso do teste (decisão 0009); run `41ecf929305b4edf9e14fc5839d8513b` |
| `random_forest_v2/modelo.joblib` | Random Forest inicial, 200 árvores | Base `c87bf93`, com alterações locais; run `1663d6b906ee486bb0cfff9fdd09457d` | 529.500 candidatos V2 de 622 pacientes | Não avaliado; teste reservado |

Nome: `<abordagem>_<data>_<commit-curto>.<ext>`, por exemplo `baseline-rf_2026-09-14_a3f21c.joblib`.

Junto do peso precisam estar a semente, a versão do `config.yaml`, o arquivo de divisão usado e
a identificação das entradas. Quando houver avaliação no teste, registrar a métrica
com intervalo de confiança, sem substituir resultados de validação por resultados de teste.

O primeiro treino foi executado em 04/10/2026 por
`scripts/17_treinar_random_forest.py`. O ajuste levou 145,01 segundos e produziu
75.063 escores de validação. O run do MLflow contém os artefatos e a procedência.
FROC e CPM ainda não foram medidos. Ver `docs/08-primeiro-treino.md`.

O ensaio técnico da CNN em 05/10/2026 verificou o fluxo de treinamento, salvamento
e avaliação com `scripts/18_treinar_cnn.py`. O CPM de validação foi 0 nessa pequena
amostra, sem valor como estimativa do desempenho na base completa. A configuração
e o código da execução estão no MLflow. Ver `docs/09-cnn-mlflow.md`.

O primeiro treino completo da CNN foi executado em 12/10/2026 por
`.venv/bin/dvc repro treinar_cnn`, na GPU (decisão 0007). Na validação, o CPM
oficial foi 0,268 (IC95% de 0,198 a 0,358). Ver `docs/09-cnn-mlflow.md`.

Em 13/10/2026 avaliamos os escores de validação do `random_forest_v2` com o programa
oficial, sem novo treino (run `e3ed9e0c20ac4494aa6d97af2c779baa`): CPM 0,003, IC95% de
0,000 a 0,007. Ver `docs/10-comparacao-validacao.md`.

Em 13/10/2026 treinamos quatro variantes da CNN e o Random Forest centro, só com treino e
validação. A melhor na validação foi `cnn_lr_3e-4`, com CPM 0,752 (IC95% de 0,681 a 0,819). Ver
`docs/11-experimentos-validacao.md`.

Em 13/10/2026 avaliamos `cnn_lr_3e-4` uma única vez no teste, congelada pela decisão 0008. Ver
`docs/12-avaliacao-final-teste.md`.

Em 26/10/2026 registramos, antes de executar, o segundo uso do teste só para o Random Forest
centro congelado (decisão 0009) e o treino da `cnn_lr_3e-4` com as sementes 43 e 44, medidas só
na validação (decisão 0010). No mesmo dia avaliamos o Random Forest centro uma única vez no teste,
em `random_forest_centro_teste_final`: CPM 0,420 (IC95% 0,349 a 0,490). Também em 26/10/2026 o
Kauan treinou as sementes 43 e 44 na RTX 4050, em `cnn_lr_3e-4_semente_43` e
`cnn_lr_3e-4_semente_44`: CPM de validação 0,790 nas duas. Com a semente 42, a média das três é
0,777 e o desvio padrão 0,022. Nenhuma delas foi ao teste. Ver
`docs/14-baseline-literatura-sementes-e-teste-rf.md`.
