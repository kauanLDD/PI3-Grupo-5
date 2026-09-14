# Intermediário

As tabelas que os scripts produzem e que ainda não são entrada de modelo: o inventário dos
volumes, o mapa de exame para paciente, o relatório da rodada de pré-processamento, a comparação
das listas de candidatos do desafio e a lista de candidatos que geramos.

Os volumes reamostrados não ficam aqui, ficam em `dados/processado/volumes`.

Gerado pelos scripts, fora do git. Some quando alguém clona, e volta rodando os scripts na ordem
do `README.md` da raiz, ou `dvc repro`. O `pacientes.csv` é a exceção: ele sai do
`01_pacientes.py`, que lê o metadata do LIDC-IDRI e só roda em máquina que o tenha.
