# 0003 - Arquivos com DVC e MLflow no lugar de banco de dados

Status: Aceito
Data: 2026-11-24

Contexto
O dado de entrada são 888 volumes de tomografia, além das listas de candidatos (754.975 na V2 e
14.310.042 na nossa). As saídas são volumes processados, cubos recortados, pesos de modelo e
tabelas de notas. Precisávamos saber de onde veio cada resultado e não podíamos colocar imagem
médica no git.

Decisão
Não usamos banco de dados. Tudo é arquivo: CSV para tabelas, NPZ para os cubos, `.pt` e
`.joblib` para os modelos. A base fica fora do repositório, num HD externo e numa cópia no Drive
do grupo, e o caminho de cada máquina fica em `configuracao/caminhos.local.yaml`. O que o pipeline
produz vai para `dados/`, também fora do git.

Para rastrear, usamos o DVC só para declarar o pipeline (`dvc.yaml` e `dvc.lock` com o hash de cada
entrada e saída), sem remote, e o MLflow local para registrar parâmetros, semente, hash dos dados e
métricas de cada treino. A escolha do DVC está registrada com mais detalhe na decisão 0005 do PI3
(`docs/decisoes/0005-dvc-para-o-pipeline-e-nao-para-o-dado.md`).

Consequências
Melhora: nenhum dado de paciente entra no GitHub, e cada número tem o hash da entrada que o gerou.
Piora: sem remote do DVC, quem clona o repositório precisa baixar o LUNA16 e rodar o pipeline, ou
pedir ao grupo a cópia do Drive. Não há consulta a resultados como num banco.
