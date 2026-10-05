# Primeiro treino do Random Forest

Treinamos o baseline com os candidatos V2 do LUNA16 e as sete características de
intensidade extraídas dos patches. Esse modelo reduz falsos positivos da lista V2.
Ele ainda não representa o desempenho do fluxo com o detector LoG próprio.

## Configuração inicial

Fixamos 200 árvores, profundidade máxima de 20, mínimo de dois candidatos por folha,
seleção de características por `sqrt`, pesos `balanced` e semente 42. Limitamos a
execução a dois processos. Esses valores são uma configuração inicial, sem busca
de hiperparâmetros ou escolha baseada no resultado da validação.

Os pesos aumentam a participação da classe rara no ajuste das árvores. Mantivemos
todos os candidatos de treino e a distribuição original da validação. Usamos as
sete características explicitamente; identificadores, coordenadas, partição e
rótulo não entram como características do modelo.

O script confere os identificadores, coordenadas e rótulos contra a lista V2 e a
divisão antes de treinar. Recusa candidatos descartados, exames com falha e
pacientes compartilhados entre treino e validação. A partição de teste não entra
no ajuste nem na geração de probabilidades desta etapa.

## Execução e arquivos

Com o ambiente instalado e as features prontas:

```bash
.venv/bin/dvc repro treinar_random_forest
```

O comando direto é `.venv/bin/python scripts/17_treinar_random_forest.py`.
Usar o comando direto não atualiza o lock do DVC. Os caminhos e parâmetros ficam
em `configuracao/config.yaml`.

Em `modelos/random_forest_v2/`, fora do Git, ficam:

- `modelo.joblib`: estimador, ordem das features, parâmetros, versão do scikit-learn e run ID.
- `probabilidades_validacao.csv`: identidade e coordenadas de cada candidato com seu escore.
- `execucao.json`: contagens, tempo, parâmetros e identificação da execução.

O MLflow recebe cópias desses arquivos, hashes das entradas, ambiente e código
utilizado. Antes de publicar os arquivos, recarregamos o modelo salvo e conferimos
que reproduz as previsões em memória. Uma nova execução substitui os arquivos
locais desse estágio; os registros anteriores permanecem nos artefatos do MLflow.

## Limite do resultado

As probabilidades são escores do classificador, sem calibração. Não calculamos
acurácia como medida de detecção. Esta etapa não produz curva FROC, CPM ou avaliação
final no teste. A avaliação oficial também considera as anotações excluídas e os
nódulos que não possuem candidato na lista. Contar acertos por linha do CSV não
substitui essa avaliação.
