# Pipeline e registro de experimentos

Usamos o DVC para relacionar código, parâmetros, entradas e saídas. O MLflow
registra execuções com parâmetros, métricas e arquivos de procedência.

## Ambiente

Instalamos DVC 3.67.1 e MLflow 3.16.1 em 04/10/2026, sem alterar as versões que
já estavam instaladas para o processamento de imagens. O arquivo
`requirements-rastreamento.lock.txt` contém as versões do ambiente conferido
nesta etapa, incluindo dependências transitivas. Ele não declara um ambiente
de treinamento de CNN: PyTorch e a configuração de GPU serão tratados nessa etapa.

```bash
.venv/bin/python -m pip install -r requirements-rastreamento.lock.txt
.venv/bin/python -m pip check
```

## DVC

O `dvc.yaml` contém 17 estágios após expandir treino e validação:

- Oito estágios anteriores de inventário, coordenadas, pré-processamento e análise.
- Divisão por paciente.
- Detecção própria de candidatos.
- Calibração exploratória encerrada, congelada.
- Extração de features do treino.
- Extração de features da validação.
- Conferência das features e registro no MLflow.
- Treinamento do Random Forest e probabilidades da validação.
- Conferência das marcações excluídas nas listas V2 e própria.
- Comparação da lista própria com o V2, que sustenta a decisão 0007.

As novas saídas usam `cache: false`: o DVC registra seus hashes sem duplicar os
volumes ou as tabelas grandes no cache. Usamos `persist: true` nessas saídas
para conservá-las durante a reprodução. O cache por exame continua sendo
responsabilidade do extrator e do detector.

A lista V2 e as anotações externas passaram a ser dependências explícitas das
etapas novas que as utilizam. São lidas no HD pelos caminhos do YAML; não são
copiadas nem modificadas. As dependências dos estágios anteriores mantêm o
escopo descrito na decisão 0005.

A calibração fica congelada porque seu protocolo preserva o ambiente e os hashes
da execução encerrada. Descongelar esse estágio não é uma rotina de reprodução:
uma nova calibração com entradas diferentes exige outra pasta de experimento.
O congelamento impede a reexecução automática e a verificação das dependências
desse estágio; o protocolo original continua sendo a referência dessa medição.

```bash
.venv/bin/dvc status
.venv/bin/dvc dag
source .venv/bin/activate
dvc repro --dry registrar_preparacao
dvc repro registrar_preparacao
```

Ativar a `.venv` é necessário para os comandos dos oito estágios antigos,
que usam `python`. As novas etapas usam explicitamente `.venv/bin/python`.
Quando houver mudanças, `repro` pode executar as dependências do alvo;
o modo `--dry` permite conferir isso antes.

Não configuramos remote. O estado local não é um backup, e `dvc push/pull`
ainda não compartilha esses dados com o grupo.

## Registro inicial das saídas existentes

Conferimos os hashes dos candidatos próprios e dos CSVs de features contra os
valores registrados nas execuções anteriores. Também conferimos os quatro
arquivos de código da calibração contra o protocolo original.

Registramos os seis estágios novos no lock com:

```bash
.venv/bin/dvc commit -f divisao deteccao calibracao features@treino features@validacao registrar_preparacao
```

Esse comando do DVC aceita os arquivos existentes e registra o estado atual.
Ele não executa os scripts nem cria commit no Git. Portanto, essa adoção não é
evidência de que todo o pipeline foi reexecutado com o ambiente atual. As
medições anteriores preservam seus próprios registros.

## MLflow

O módulo `src/experimentos/rastreamento.py` inicia e encerra as execuções.
Registra o commit de base, indica se há alterações locais, calcula os hashes das
entradas e guarda um ZIP do código atual, a configuração e as versões instaladas.
Assim, o commit de base não é apresentado como se contivesse alterações ainda
não publicadas. Uma exceção marca a execução como `FAILED`.

O banco SQLite e os artefatos ficam em
`dados/intermediario/mlflow/`, ignorados pelo Git. O banco guarda parâmetros,
métricas e referências; a pasta de artefatos guarda a procedência. Ambos são
necessários para preservar os registros locais.

```bash
.venv/bin/python scripts/15_registrar_preparacao.py
.venv/bin/python scripts/16_abrir_mlflow.py
```

O painel abre em `http://127.0.0.1:5000`, somente nesta máquina.
Os caminhos, nome do experimento, endereço e porta vêm do `config.yaml`.
Interromper o servidor não apaga os registros.

O script 15 confere identificadores, coordenadas, rótulos e valores finitos
antes de registrar a preparação. O recibo fica em
`dados/intermediario/mlflow_preparacao.json`. Reexecutar esse script cria
outra execução de conferência. O DVC evita repeti-lo enquanto suas dependências
e o recibo estiverem atualizados.

O banco e a pasta de artefatos não são saídas do DVC, pois recebem várias
execuções ao longo do projeto. Se esses arquivos forem perdidos, um recibo
existente não os restaura: será necessário restaurar um backup ou registrar
novamente a preparação.

O primeiro registro é do tipo `preparacao`: 529.500 candidatos de treino
e 75.063 de validação, sem descartes. Ele não contém modelo treinado, FROC
ou resultado de desempenho. O treinamento tem um registro separado do tipo
`treinamento`, com modelo, parâmetros e probabilidades da validação. A execução
está descrita em [Primeiro treino do Random Forest](08-primeiro-treino.md).

Referências: [DVC commit](https://dvc.org/doc/command-reference/commit) e
[MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/quickstart/).
