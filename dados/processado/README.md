# Processado

O que entra no modelo. Hoje são os 888 volumes pré-processados, em `volumes/`, com as cinco
etapas aplicadas e 8,6 GiB no total, a divisão por paciente em `divisao.csv` e o exame de
demonstração que o `04_preprocessar.py` grava solto aqui.

Ainda vão entrar os cubos ao redor de cada candidato. A divisão é por paciente, nunca por
imagem, e sai de script com semente fixa.
