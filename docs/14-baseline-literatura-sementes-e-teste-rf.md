# Baseline da literatura, segundo uso do teste e sementes da rede, 26/10/2026

Este documento fecha a etapa de baseline. Ele separa dois tipos de número: **medido** (com
arquivo no repositório) e **da literatura** (publicado por outros, com outro protocolo). Enquanto
as sementes 43 e 44 não tinham sido treinadas, os campos delas ficaram como "pendente", sem
estimativa; foram preenchidos em 26/10/2026 com os arquivos do treino (seção 4).

## 1. Pesquisa de baseline na literatura

Conferimos título, autores, DOI e tabelas no texto completo de cada artigo, em 26/10/2026.

### 1.1 As duas referências citadas pelo grupo

**Zheng et al. (2022) — confirmada.** Zheng S, Kong S, Huang Z, Pan L, Zeng T, Zheng B, Yang M,
Liu Z. *A Lower False Positive Pulmonary Nodule Detection Approach for Early Lung Cancer
Screening*. Diagnostics, 12(11):2660, 2022. DOI
[10.3390/diagnostics12112660](https://doi.org/10.3390/diagnostics12112660). É o mesmo trabalho
que a decisão 0002 já cita pela dilatação da máscara com esfera de raio 6.

**Li et al. (2025) — confirmada.** Li Y, Hui L, Wang X,
Zou L, Chua S. *Lung nodule detection using a multi-scale convolutional neural network and global
channel spatial attention mechanisms*. Scientific Reports, 15:12313, 2025. DOI
[10.1038/s41598-025-97187-w](https://doi.org/10.1038/s41598-025-97187-w). Foi o único artigo de
2025 com primeiro autor Li, LUNA16 e CPM que encontramos, e a tabela de comparação dele cita
Zheng et al. com os mesmos sete valores do artigo de 2022, o que sugere que o grupo tirou as
duas referências daí. Em 26/10/2026 o grupo confirmou com o PDF do artigo que é ele: mesmo DOI,
CPM 0,929 com validação cruzada em 10 dobras, e a referência 21 é o Zheng et al. (2022) acima.
Não confundir com o "Li et al. (2023)" da decisão 0002, que é outro trabalho, sobre perda de
nódulos na segmentação.

### 1.2 Tabela

Sensibilidades e CPM copiados das tabelas dos artigos. "Sens. 1 FP" é a sensibilidade a 1 falso
positivo por exame.

| Artigo | Ano | Método | Dataset | Protocolo | CPM | Sens. 1 FP | Observações |
|---|---:|---|---|---|---:|---:|---|
| Li et al., Sci. Rep. 15:12313 | 2025 | Sistema completo: detector 3D Res2Net com atenção GCSAM e RPN (CNDNet) + rede de redução de FP em cubos de 32³ (FPRNet) | LUNA16, 888 exames, 1.186 nódulos; 754.975 candidatos para a redução de FP | Validação cruzada em 10 dobras (subsets oficiais); IC por bootstrap de 1.000; não diz se usou o script oficial | 0,929 | 0,971 | Sete pontos: 0,773 / 0,888 / 0,945 / 0,971 / 0,977 / 0,977 / 0,977. Só o detector: CPM 0,911. Gera os próprios candidatos. |
| Zheng et al., Diagnostics 12:2660 | 2022 | Sistema completo: detector 3D multiescala tipo FPN com RPN (MSFD-Net) + classificador de candidatos em 32³ (CS-Net) | LUNA16, 888 exames, 1.186 nódulos; candidates V2 no treino da redução de FP | Validação cruzada em 10 dobras; métrica do desafio; não nomeia o script | 0,906 | 0,940 | Sete pontos: 0,771 / 0,849 / 0,905 / 0,940 / 0,957 / 0,960 / 0,960. Máscara de pulmão dilatada. |
| Setio et al., Med. Image Anal. 42:1–13 ([10.1016/j.media.2017.06.015](https://doi.org/10.1016/j.media.2017.06.015)) | 2017 | Desafio LUNA16, trilha de redução de falsos positivos: CNNs sobre a lista de candidatos fornecida | LUNA16, 888 exames, 1.186 nódulos; 754.975 candidatos (V2) | Validação cruzada em 10 dobras; script oficial; até 100 marcas por exame; IC por bootstrap de 1.000 | 0,908 (melhor, CUMedVis) a 0,758 (pior, ZNET) | 0,972 a 0,793 | **Mesma tarefa e mesmo avaliador que os nossos.** Fora de 2022–2025, mas é a referência de protocolo. |
| Ma et al. (TiCNet), J. Imaging Inform. Med. 37:196–208 ([10.1007/s10278-023-00904-y](https://doi.org/10.1007/s10278-023-00904-y)) | 2024 | Sistema completo: CNN 3D codificador-decodificador com transformer | LUNA16, 888 exames, 1.186 nódulos | 10 dobras; acerto por IoU 3D > 0,1, **não** pelo raio do nódulo do script oficial | 0,907 | 0,922 | Critério de acerto diferente do oficial. |
| Wang et al., Digital Health 12 ([10.1177/20552076261419238](https://doi.org/10.1177/20552076261419238)) | 2026 (submetido em 2025) | Sistema completo em dois estágios: detector 3D em U com atenção + rede multiescala de redução de FP | LUNA16, 888 exames, 1.186 nódulos | Validação cruzada em **6** dobras; não cita o script oficial | 0,878 | 0,939 | Mostra que mudar o número de dobras já muda a régua. |

### 1.3 O que é e o que não é comparável

Nosso protocolo: redução de falsos positivos sobre a lista **candidates_V2 fornecida pelo
desafio**, avaliador oficial do LUNA16 (`third_party/luna16`), até 100 marcas por exame, divisão
fixa por paciente com treino nos subsets 0–6, validação no 7 e **teste nos subsets 8 e 9, 176
exames e 223 nódulos**, uma única vez por modelo.

- Li (2025), Zheng (2022), TiCNet e Wang são **sistemas completos**: geram os próprios
  candidatos, usam redes muito maiores e reportam a média de 10 (ou 6) dobras sobre os 888
  exames. Nosso número é de um teste fixo de 176 exames. As duas coisas medem desempenho de
  forma diferente; os números servem de **referência do estado da arte, não de comparação
  direta**.
- A única referência com a **mesma tarefa** (classificar a lista V2) e o **mesmo avaliador** é a
  trilha de redução de falsos positivos do desafio (Setio et al., 2017). Mesmo nela o protocolo
  difere no ponto da divisão: 10 dobras contra o nosso teste fixo.
- TiCNet troca o critério de acerto e Wang usa 6 dobras. Os dois ficam só como contexto.

### 1.4 Quais usar nos slides

1. **Li et al. (2025)** como estado da arte recente (CPM 0,929).
2. **Zheng et al. (2022)** (CPM 0,906): confirmado, já citado no projeto, e aparece na tabela de
   Li, o que liga as duas referências.
3. **Setio et al. (2017), trilha de redução de FP** (CPM de 0,758 a 0,908): a referência de
   protocolo, a única que mede a mesma tarefa com o mesmo programa.

Em todos os casos, o slide diz que o protocolo é diferente do nosso.

## 2. Segundo uso do teste

Registrado na decisão 0009, antes de qualquer execução, com o texto para o relatório e os
hashes do Random Forest centro congelado, da divisão e da lista V2.

## 3. Random Forest centro no teste e FROC conjunta

### 3.1 Como a rede foi avaliada no teste (material reaproveitado)

`modelos/cnn_lr_3e-4_teste_final/` foi produzido por `scripts/20_avaliar_teste_cnn.py`, que
carrega o checkpoint congelado, confere os hashes da divisão e da lista V2, prevê os 150.412
candidatos V2 dos 176 exames de teste na CPU e chama `src/experimentos/avaliacao_oficial.py`.

| Arquivo | Conteúdo |
|---|---|
| `predicoes.csv` | Escore de cada candidato, entrada do avaliador oficial |
| `seriesuids.csv` | Os 176 exames de teste |
| `curva_froc_completa.csv` | Curva FROC inteira (`froc_predicoes.txt` convertido) |
| `froc_predicoes_bootstrapping.csv` | Média e IC95% da sensibilidade em 10.000 pontos de FP, das 1.000 reamostras por exame |
| `pontos_operacao.csv` | Os sete pontos oficiais com IC95% |
| `cpm_bootstrap.csv` | CPM de cada uma das 1.000 reamostras, para o IC do CPM e a diferença pareada |
| `CADAnalysis.txt` | 223 nódulos; 218 com candidato nos 100 maiores escores |
| `avaliacao.json`, `execucao.json` | Protocolo (semente 42, 1.000 reamostras, 95%) e métricas; run `d754f073...` |

**Método do intervalo de confiança.** O projeto já tem um: o bootstrap por exame do programa
oficial, 1.000 reamostras, percentis de 95%, semente 42. O IC dos sete pontos vem do próprio
programa, e o IC do CPM vem dos 1.000 CPMs das reamostras. Usamos o mesmo método para o Random
Forest. Com a mesma semente e a mesma lista de exames as reamostras são as mesmas para os dois
modelos (a função `generateBootstrapSet` sorteia exames, não candidatos), o que permite a
diferença pareada de CPM, como em `docs/11`.

### 3.2 Resultados

| Modelo | Conjunto | CPM | IC95% | Sens. 1 FP | Sens. 4 FP | Situação |
|---|---|---:|---|---:|---:|---|
| CNN `cnn_lr_3e-4` | Teste, 176 exames | 0,724 | 0,670 a 0,778 | 0,735 | 0,883 | **Medido** em 13/10/2026 |
| Random Forest centro | Teste, 176 exames | 0,420 | 0,349 a 0,490 | 0,381 | 0,520 | **Medido** em 26/10/2026, uso único |
| CNN `cnn_lr_3e-4` | Validação, 89 exames | 0,752 | 0,681 a 0,819 | 0,784 | 0,883 | Medido |
| Random Forest centro | Validação, 89 exames | 0,409 | 0,323 a 0,505 | 0,405 | 0,559 | Medido |

Sete pontos no teste, com IC95% do bootstrap por exame
(`relatorios/experimentos/comparacao_teste/pontos_operacao.csv`):

| FP por exame | 0,125 | 0,25 | 0,5 | 1 | 2 | 4 | 8 | CPM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CNN | 0,457 | 0,574 | 0,641 | 0,735 | 0,852 | 0,883 | 0,924 | 0,724 |
| IC95% CNN | 0,364–0,555 | 0,479–0,640 | 0,561–0,728 | 0,659–0,819 | 0,801–0,896 | 0,843–0,929 | 0,883–0,962 | 0,670–0,778 |
| Random Forest centro | 0,283 | 0,332 | 0,354 | 0,381 | 0,480 | 0,520 | 0,587 | 0,420 |
| IC95% RF | 0,209–0,355 | 0,258–0,407 | 0,285–0,431 | 0,314–0,460 | 0,401–0,556 | 0,442–0,603 | 0,504–0,667 | 0,349–0,490 |

**Diferença pareada de CPM, CNN menos RF, no teste: 0,304 (IC95% 0,247 a 0,360)**, a CNN acima em
100% das 1.000 reamostras. Na validação a diferença foi 0,342 (IC95% 0,252 a 0,437). Dentro dos
100 maiores escores de cada exame, o RF alcançou 189 dos 223 nódulos e a CNN, 218
(`CADAnalysis.txt`). O RF ficou com 17.596 marcas e não 17.600 porque o avaliador oficial guarda
só os escores estritamente maiores que o 101º do exame, e o RF tem empates; é o comportamento do
programa oficial.

Figura: `relatorios/experimentos/comparacao_teste/froc.png` (as duas curvas FROC, os sete pontos
com IC95% e a faixa do bootstrap). Resultados completos do RF:
`modelos/random_forest_centro_teste_final/`, run do MLflow `41ecf929305b4edf9e14fc5839d8513b`.

### 3.3 Como a avaliação foi executada

Em 26/10/2026, na máquina do Lucas (Windows, Xeon E5-2697 v3, CPU), com a base do LUNA16 no
Google Drive do grupo e o ambiente `.venv` montado do `requirements-cnn-cpu.lock.txt`
(scikit-learn 1.9.1, a versão do treino):

```bash
.venv/Scripts/python scripts/26_avaliar_teste_random_forest.py --config _local/config_lucas.yaml
.venv/Scripts/python scripts/27_comparar_froc.py \
    --avaliacao "CNN3D (cnn_lr_3e-4)=modelos/cnn_lr_3e-4_teste_final" \
    --avaliacao "Random Forest centro=modelos/random_forest_centro_teste_final" \
    --titulo "Teste" --saida relatorios/experimentos/comparacao_teste
```

O `_local/config_lucas.yaml` (fora do git) é o `config.yaml` com só os caminhos da base trocados
para o Drive. Antes de abrir o teste, conferimos que os dados desta máquina reproduzem os do
Kauan:

- `candidates_V2.csv`, `annotations.csv` e `annotations_excluded.csv` com os mesmos md5 do
  `dvc.lock`; a `divisao.csv` restaurada do Git com o SHA-256 da decisão 0009.
- Os volumes `.mha` do Drive somam 2,7 MB a mais que os do `dvc.lock`. São comprimidos, então
  a diferença pode vir só da compressão. Para saber se importava, refizemos a avaliação de
  **validação** do RF congelado com esses dados: CPM 0,409266, igual ao versionado, as sete
  sensibilidades iguais, limites de IC diferentes em no máximo 0,0007. Só 156 de 75.063 escores
  mudaram (no máximo 0,01); nos que examinamos, a feature estava a cerca de 6×10⁻⁸ (relativo) de
  um limiar de corte das árvores, ruído de ponto flutuante entre CPUs.
- Os recortes do Drive não tinham o campo de procedência (são de 01/10). Regeneramos os 176
  exames de teste com o `scripts/09_extrair_patches.py` atual; os arrays saíram idênticos aos do
  Drive, e a procedência bate com o código do repositório. Para isso, os `.py` foram usados com
  fim de linha LF, como no Linux: com CRLF os hashes de código da procedência seriam outros.

Uma primeira execução do script 26 parou na conferência de procedência, antes de qualquer
previsão ou run do MLflow: um dos 176 recortes tinha sido regerado com uma versão antiga do
script 09 durante uma troca de branch. O arquivo foi refeito e o script rodou uma vez até o fim.
O teste foi lido uma única vez para o RF.

O run `41ecf929` anota o commit `be7b32d`, que depois teve só a mensagem reescrita para
`7af2d0b`; a árvore de arquivos dos dois é a mesma.

## 4. Três sementes da rede, na validação

Decisão 0010: sementes 43 e 44, fixadas antes de treinar; configuração idêntica; só validação.

| Seed | CPM | Sens@0,125 | Sens@0,25 | Sens@0,5 | Sens@1 | Sens@2 | Sens@4 | Sens@8 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 (original) | 0,752 | 0,505 | 0,631 | 0,730 | 0,784 | 0,838 | 0,883 | 0,892 |
| 43 | 0,790 | 0,532 | 0,721 | 0,793 | 0,829 | 0,838 | 0,901 | 0,919 |
| 44 | 0,790 | 0,577 | 0,685 | 0,793 | 0,820 | 0,847 | 0,892 | 0,919 |

Fonte: `relatorios/experimentos/sementes_cnn/sementes.csv`, gerado pelo script 28 a partir do
`execucao.json` de cada pasta. Em todas o checkpoint é o da época 40 (o protocolo não escolhe
época).

| Seed | IC95% do CPM | Loss de treino na época 40 | Run do MLflow | Pasta |
|---:|---|---:|---|---|
| 42 | 0,681 a 0,819 | 0,066 | `2f8b0a3c57c84d9e8f51dea2eab94b7f` | `modelos/cnn_lr_3e-4` |
| 43 | 0,725 a 0,862 | 0,076 | `fe45ac6a8d9e4c3dae67177750d7ec97` | `modelos/cnn_lr_3e-4_semente_43` |
| 44 | 0,728 a 0,858 | 0,072 | `8464203ec1054b54b9d44c56340c5e76` | `modelos/cnn_lr_3e-4_semente_44` |

| Métrica (CPM na validação, 3 sementes) | Resultado |
|---|---:|
| CPM médio | 0,777 |
| Desvio padrão amostral (n − 1) | 0,022 |
| CPM mínimo | 0,752 (semente 42) |
| CPM máximo | 0,790 (sementes 43 e 44) |
| Amplitude | 0,039 |
| Sensibilidade a 4 FP, média ± desvio | 0,892 ± 0,009 |

Fonte: `relatorios/experimentos/sementes_cnn/resumo.json`; gráfico em `cpm_por_semente.png`.

**Como foi executado.** O Kauan treinou as sementes 43 e 44 em 26/10/2026 na RTX 4050, com os
comandos da decisão 0010 (`torch 2.14.0+cu130`, determinismo parcial na GPU), cerca de 940 s de
treino cada. O script 28 aceitou as três pastas: fora a semente, todos os parâmetros do run são
iguais aos da semente 42, o hash dos dados é o mesmo (`14b0f7da...`), o bootstrap do avaliador usou
a semente 42 e nenhuma pasta tem `teste_utilizado`. Conferimos também, fora do script, que a
divisão (`divisao.csv`, sha256 `45b22b5e...`) e os 89 exames avaliados são os mesmos nas três. A
amostra de negativos do treino muda com a semente, como previsto na decisão 0010; o total é 23.058
candidatos nas três. Rodamos de novo o script 28 na máquina do Lucas: `sementes.csv` e
`resumo.json` saíram idênticos aos do Kauan.

**As sementes 43 e 44 têm o mesmo CPM por coincidência, não por erro.** Os pesos são diferentes
(sha256 `e3092941...` e `4a82a879...`), a correlação entre as probabilidades das duas redes nos
75.063 candidatos de validação é 0,81, e os nódulos encontrados em cada ponto diferem (59, 80, 88,
92, 93, 100 e 102 de 111 na semente 43; 64, 76, 88, 91, 94, 99 e 102 na 44). As duas somas dão
614, e como o CPM é a média dos sete pontos, com o mesmo denominador, o CPM sai igual.

**Leitura sobre estabilidade.** A amplitude entre sementes, 0,039, é bem menor que a largura do
IC95% de cada uma (cerca de 0,13 a 0,14), e os três intervalos se sobrepõem quase inteiramente.
Retreinar a mesma configuração mudou o CPM menos do que a incerteza de termos só 89 exames. A
semente 42, a que foi congelada e levada ao teste, foi a menor das três: o resultado não veio de
uma inicialização favorável. A sensibilidade a 4 FP ficou entre 0,883 e 0,901 nas três, acima da
meta de 0,80, na validação. Com três valores, o desvio padrão é uma estimativa grosseira; por isso
reportamos também mínimo, máximo e amplitude. Nenhuma das novas redes foi ao teste: o CPM de teste
continua sendo o da semente 42, 0,724.

Três análises que não se misturam:

- **IC95% do bootstrap por exame**: incerteza por termos poucos exames, com o modelo fixo.
- **Variação entre sementes**: quanto o resultado muda ao treinar de novo a mesma configuração.
- **Desvio padrão**: o resumo numérico dessa variação, com só três valores.

## 5. Baseline, resultados e metas

| Item | Número | Métrica e conjunto | Natureza |
|---|---:|---|---|
| Li et al. (2025) | CPM 0,929; 0,977 a 4 FP | 10 dobras, sistema completo | Literatura |
| Zheng et al. (2022) | CPM 0,906; 0,960 a 4 FP | 10 dobras, sistema completo | Literatura |
| Trilha de redução de FP do LUNA16 | CPM 0,758 a 0,908 | 10 dobras, lista V2, avaliador oficial | Literatura |
| Random Forest centro | CPM 0,409; 0,559 a 4 FP (IC95% 0,453 a 0,650) | Validação | Medido |
| Random Forest centro | CPM 0,420; 0,520 a 4 FP (IC95% 0,442 a 0,603) | Teste | Medido |
| CNN `cnn_lr_3e-4`, 3 sementes | CPM 0,777 ± 0,022 (0,752 a 0,790); 0,892 ± 0,009 a 4 FP | Validação | Medido |
| CNN `cnn_lr_3e-4` | CPM 0,724; 0,883 a 4 FP (IC95% 0,843 a 0,929) | Teste | Medido |
| Meta do baseline | sensibilidade ≥ 0,70 a 4 FP por exame | Um ponto da FROC | Meta, não resultado |
| Meta da CNN | sensibilidade ≥ 0,80 a 4 FP por exame | Um ponto da FROC | Meta, não resultado |

**As metas não estão na mesma métrica da literatura.** As metas do enunciado (bloco `metas` do
`config.yaml`) são a sensibilidade num único ponto, 4 FP por exame. A literatura reporta o CPM,
a média de sete pontos de 0,125 a 8 FP, que pesa muito os pontos de poucos falsos positivos. Uma
meta de 0,80 a 4 FP não equivale a CPM 0,80. Comparamos cada meta com a nossa sensibilidade a
4 FP, e o CPM com o da literatura, sempre lembrando a diferença de protocolo.

Situação das metas, sem transformar meta em resultado:

- **CNN:** no teste, 0,883 a 4 FP, com o IC95% inteiro acima de 0,80. Na validação, as três
  sementes ficaram entre 0,883 e 0,901 a 4 FP, todas acima da meta.
- **Random Forest centro:** no teste, 0,520 a 4 FP, com o IC95% (0,442 a 0,603) inteiro abaixo
  da meta de 0,70; na validação, 0,559. A meta do baseline não foi atingida.
