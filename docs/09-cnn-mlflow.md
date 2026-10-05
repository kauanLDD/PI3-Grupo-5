# Integração e reprodução da CNN

Executado em **05/10/2026**. A integração, o rastreamento e a repetição funcionam
em CPU. A avaliação abaixo é uma reprodução técnica em **seis exames reais**;
o treinamento e a avaliação da CNN na divisão completa continuam pendentes.

## Código e artefatos localizados

`notebooks/curvafroc_pesquisa.ipynb` contém código Python exportado, apesar da
extensão `.ipynb`. Nele encontramos a CNN, o treino, a inferência e os caminhos
dos artefatos produzidos no Kaggle:

- `/kaggle/working/models/cnn3d_baseline.pt`: pesos.
- `/kaggle/working/data/metadata/project_metadata.json`: métricas e configuração.
- `/kaggle/working/results/`: figuras da pesquisa.

Esses arquivos de saída antigos não foram encontrados na cópia local, no Drive
do projeto ou nos branches remotos consultados. O arquivo de pesquisa também
não contém saídas de células com resultados verificáveis. As previsões e
métricas registradas nesta entrega foram **geradas novamente**, não recuperadas
de uma execução antiga.

O código efetivo é uma CNN3D com canais 16/32/64, BatchNorm, MaxPool, pooling
adaptativo e duas camadas lineares. O nome `resnet18_3d` na configuração antiga
não corresponde à implementação. As épocas efetivas eram 15, embora a
configuração declarasse 100. Não havia augmentation ou early stopping em uso.

`src/experimentos/cnn.py` preserva a arquitetura e os nomes do `state_dict`.
O novo fluxo usa os recortes V2 de 34³ já produzidos pelo repositório, com crop
central de 32³. Isso inclui a máscara pulmonar e o pré-processamento atual;
portanto, não é uma reprodução idêntica do pré-processamento antigo do Kaggle.

## Integração com o rastreamento existente

O branch local `Lucas`, base `accb02c`, diverge do `main`. Conservamos os recortes
locais e trouxemos de `main@7ec3da3` o módulo de MLflow, a divisão por paciente,
os scripts de divisão/painel, a configuração e o registro do primeiro Random
Forest. Não fizemos merge dos demais estágios do `main`.

Cada execução da CNN guarda no MLflow:

- Parâmetros efetivos, semente 42, device, versão do PyTorch e escopo.
- SHA-256 da divisão, lista V2, anotações incluídas/excluídas e cada NPZ usado.
- Versão dos dados agregada a partir desses hashes.
- Commit base, estado local do Git, ZIP do código/configuração e ambiente instalado.
- Pesos, candidatos de treino selecionados, histórico por época, divisão e previsões.
- FROC oficial completa, limiares, análise de acertos/erros, figura, log e bootstrap.
- Métricas de classificação por candidato, CPM e sensibilidades com IC por ponto.

O banco fica em `dados/intermediario/mlflow/mlflow.db`; os artefatos, em
`dados/intermediario/mlflow/artefatos`. Ambos devem ser preservados juntos.
O banco local desta máquina é novo; o run anterior do Random Forest está
documentado no registro do modelo, mas seus artefatos não foram copiados para cá.

`requirements-cnn.lock.txt` registra o ambiente executado: Python 3.14.6,
Windows x64 e PyTorch 2.14.0+cpu. O lock é específico desse ambiente.

## Protocolo da reprodução técnica

A população está congelada em `configuracao/cnn_reproducao_exames.csv`: dois
exames do subset 0 para treino, dois do 7 para validação e dois do 8 para teste.
A seleção inicial usou os dois menores NPZ com nódulo anotado de cada subset,
antes de calcular escores. Ela é intencionalmente pequena e não representativa.

O mapa completo de pacientes não estava disponível nesta máquina. Nesta amostra
restrita usamos aliases por exame, apoiados na medição da decisão 0003: o único
paciente com duas séries está nos subsets 2/6, ausentes da amostra. Para uma
rodada completa, usar o mapa real e `scripts/13_criar_divisao.py`.

O treino usa todos os positivos e até cinco negativos por positivo, somente
nos exames de treino. O sampler ponderado amostra com reposição. Validação e
teste recebem **todos** os seus candidatos, sem balanceamento nem limiar prévio.
O teste é lido após o treinamento, sem acompanhamento por época ou escolha
de checkpoint. As 15 épocas e os demais parâmetros são fixos.

| Partição | Exames | Candidatos usados | Positivos V2 | Nódulos incluídos na avaliação |
|---|---:|---:|---:|---:|
| Treino | 2 | 18 | 3 | — |
| Validação | 2 | 1.092 | 7 | 5 |
| Teste | 2 | 1.032 | 9 | 4 |

O número de candidatos positivos não é o número de nódulos: vários candidatos
podem corresponder ao mesmo nódulo.

## Avaliação e resultado

Executamos o programa do pacote oficial LUNA16 em `third_party/luna16`, com
anotações incluídas/excluídas, lista de exames e CSV de coordenadas/probabilidade.
O próprio programa aplica o limite de 100 marcas por exame. Mantivemos os
originais e registramos os hashes das cópias adaptadas para Python 3.

Além da compatibilidade de sintaxe/CSV/Matplotlib, corrigimos um caso de borda:
o sklearn produz TPR `NaN` quando nenhum positivo foi detectado. Nessa condição,
o adaptador usa sensibilidade zero, preservando os nódulos perdidos no
denominador. A correção também vale para reamostras sem acertos e tem teste
específico. As tentativas anteriores com erro/NaN ficaram como `FAILED` no MLflow.

| Métrica | Validação | Teste |
|---|---:|---:|
| CPM, média dos sete pontos oficiais | 0,000 | 0,000 |
| Sensibilidade a 1 FP/exame | 0,000 | 0,000 |
| Sensibilidade a 4 FP/exame | 0,000 | 0,000 |
| IC 95% bootstrap a 4 FP/exame | [0,000; 0,000] | [0,000; 0,000] |
| Nódulos detectados entre as marcas retidas | 0/5 | 0/4 |

Foram 1.000 reamostras por exame, com semente 42. O IC degenerado desta amostra
minúscula não prova sensibilidade zero na população. O modelo não atende à
meta de 0,80 a 4 FP/exame; esta rodada comprova o funcionamento do fluxo.

Resultados agregados versionados em
[`relatorios/experimentos/cnn_reproducao`](../relatorios/experimentos/cnn_reproducao/):
curvas pontuais completas, curvas de bootstrap com **10.000 pontos cada**,
sete pontos de operação, análises e recibos. Previsões completas e pesos ficam
nas pastas dos modelos e nos artefatos do MLflow, fora do Git.

## Repetição conferida

Primeiro run válido: `594440921c0c448cbf9b6e431861b68a`.
Repetição: `539fe19dfd0547529bc951b290457284`.

As duas execuções produziram pesos tensoriais idênticos, com SHA-256
`fba14f68492bae989ff6b25b2f082828ded9dbc117f5f4de994ffc7e9d3f4bb4`.
Os CSVs de probabilidades, curvas FROC e curvas de bootstrap da validação e do
teste também são idênticos byte a byte. `--reproduzir-de` recusa divergências.
O arquivo `.pt` contém o run ID e pode ter hash de arquivo diferente; a comparação
dos pesos usa os nomes e os bytes dos tensores, sem metadados variáveis.

Versão dos dados:
`eb7b84a6e51f994464d3b4b31b726340fd81333ca143bb9bb0a302d480b7b36d`.

## Comandos

Na raiz do repositório, em PowerShell e com o ambiente disponível:

```powershell
# Preparar em outra máquina. A pasta de saída deve ser nova.
.venv/Scripts/python.exe scripts/19_preparar_reproducao_cnn.py --dataset "G:\Meu Drive\PI3-Grupo-5\Dataset"

.venv/Scripts/python.exe scripts/18_treinar_cnn.py --dados dados/processado/cnn_reproducao --escopo reproducao_tecnica_6_exames --saida modelos/cnn3d_nova_execucao

.venv/Scripts/python.exe scripts/18_treinar_cnn.py --dados dados/processado/cnn_reproducao --escopo reproducao_tecnica_6_exames --saida modelos/cnn3d_nova_repeticao --reproduzir-de modelos/cnn3d_nova_execucao

.venv/Scripts/python.exe scripts/16_abrir_mlflow.py
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m pip check
```

No Linux, substituir `.venv/Scripts/python.exe` por `.venv/bin/python`.
As execuções existentes são preservadas: cada `--saida` precisa ser uma pasta nova.

Para a divisão completa, ajustar os caminhos externos do YAML, gerar a divisão
com o mapa real e executar o script 18 **sem `--dados`**, apontando `--saida`
para uma nova pasta. O script 18 ainda não é um estágio do DVC.

Validação desta entrega: **60 testes passaram, 17 foram ignorados** por dependerem
de arquivos externos ausentes nos caminhos configurados; `pip check` passou.
Há testes de vazamento por paciente, identidade/coordenadas dos candidatos,
amostragem só no treino, inferência completa, checkpoint e contagem oficial
de nódulos perdidos/marcações excluídas. A repetição real foi conferida à parte.
