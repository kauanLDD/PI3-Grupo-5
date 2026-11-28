# Pergunta de pesquisa

Fechada pelo grupo em 28/11/2026.

## A pergunta

Uma rede neural 3D, avaliada pelo programa oficial do LUNA16 em pacientes que ela não viu no
treino, encontra pelo menos 80% dos nódulos aceitando 4 falsos positivos por exame, tanto com a
lista de candidatos do desafio (V2) quanto com a nossa própria lista (LoG)?

## Como medimos

A medida é a curva FROC: sensibilidade em função da média de falsos positivos por exame. Reportamos
a sensibilidade a 1 e a 4 falsos positivos por exame e o CPM, sempre com o programa oficial do
LUNA16 e intervalo de confiança de 95% por bootstrap de 1.000 reamostras por exame. Acurácia e
AUC-ROC não entram, porque quase todos os candidatos não são nódulo.

A meta de 80% a 4 falsos positivos por exame vem do enunciado (seção 7.6) e foi fixada antes dos
experimentos (`docs/requisitos.md`, RNF-01).

A divisão é por paciente: 623 exames de treino, 89 de validação e 176 de teste (decisão 0003). Toda
escolha de modelo, de supressão e de raio foi feita na validação.

## A resposta medida

No teste, com o sistema final da decisão 0013 (rede `cnn_lr_3e-4` mais supressão suave linear a
16 mm), medido com `.venv-cnn-gpu/bin/python scripts/37_teste_supressao.py` e reunido por
`.venv/bin/python scripts/41_tabela_resultados.py` (`docs/21`):

| Lista | Sensibilidade a 4 FP por exame (IC95%) | CPM (IC95%) |
|---|---:|---:|
| V2 do desafio | 0,865 (0,817 a 0,913) | 0,758 (0,709 a 0,806) |
| Nossa (LoG) | 0,807 (0,758 a 0,868) | 0,691 (0,633 a 0,754) |

Nas duas listas o valor medido passa de 0,80. Na nossa lista o limite inferior do intervalo, 0,758,
fica abaixo de 0,80.

O teste foi aberto três vezes (decisões 0008, 0009 e 0013), então as comparações feitas nele são
descritivas.

## Comparação com o Random Forest

No mesmo teste e na lista V2, o Random Forest centro fez CPM 0,420 (0,349 a 0,490) e sensibilidade
de 0,520 a 4 falsos positivos por exame, contra 0,724 e 0,883 da rede sem supressão (`docs/21`). Só
a rede teve ajuste de hiperparâmetros.

## De onde a pergunta veio

A versão de 26/10/2026 perguntava pela diferença entre um Random Forest com estatísticas de
intensidade e uma CNN 3D na lista V2. Em 28/11/2026 ampliamos a pergunta para a nossa lista de
candidatos, que voltou ao resultado com a supressão (decisões 0012 e 0013), e passamos a comparação
com o Random Forest para dentro dos resultados.
