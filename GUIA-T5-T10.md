# Guia das tasks S3-T5 e S4-T10

Este documento explica tudo o que foi feito nas duas tasks do Trello atribuídas ao Arthur, por
que foi feito assim, e o passo a passo completo para configurar a máquina, testar e rodar. Ele
foi escrito para quem vai executar a rodada nos 888 exames sem ter acompanhado o trabalho.

O trabalho está no branch `deteccao/t10-cobertura-888`.

| Task | Card | Situação |
|---|---|---|
| S3-T5, configurar as marcações excluídas da avaliação | https://trello.com/c/EyxS45yf | Código, testes e script prontos. Falta o avaliador do T4 existir para receber o arquivo, e falta rodar o `12` na base real. |
| S4-T10, medir a cobertura da busca nos 888 exames | https://trello.com/c/YRPIKraC | Código, testes e documentação prontos. Falta confirmar os parâmetros do T9 e rodar nos 888, na máquina que tem os volumes. |

Nenhum número da base real foi medido neste trabalho. A máquina onde o código foi escrito não tem
o LUNA16, então tudo foi verificado com testes sintéticos e com um LUNA16 de mentira montado só
para rodar os scripts de ponta a ponta. Os números de verdade saem da rodada descrita na
seção 5.

---

## Sumário

1. [Resumo em cinco linhas](#1-resumo-em-cinco-linhas)
2. [S3-T5: as marcações excluídas](#2-s3-t5-as-marcações-excluídas)
3. [S4-T10: a cobertura nos 888 exames](#3-s4-t10-a-cobertura-nos-888-exames)
4. [Configurar a máquina do zero](#4-configurar-a-máquina-do-zero)
5. [Passo a passo para testar e rodar](#5-passo-a-passo-para-testar-e-rodar)
6. [Como ler os resultados](#6-como-ler-os-resultados)
7. [Onde escrever os números depois da rodada](#7-onde-escrever-os-números-depois-da-rodada)
8. [Problemas comuns](#8-problemas-comuns)
9. [Lista de arquivos alterados](#9-lista-de-arquivos-alterados)
10. [O que ficou em aberto](#10-o-que-ficou-em-aberto)

---

## 1. Resumo em cinco linhas

- O caminho do `annotations_excluded.csv` agora está no `config.yaml`, na chave
  `caminhos.luna16_anotacoes_excluidas`.
- A regra do avaliador oficial do LUNA16 para esses achados (candidato em cima de um deles não é
  acerto nem falso positivo) virou a função `rotular` em `src/detection/candidatos.py`, com testes.
- O `scripts/12_marcacoes_excluidas.py` mede quanto essa regra tira do falso positivo da lista
  `candidates_V2`.
- O `scripts/10_detectar_candidatos.py` agora roda os 888 exames de forma retomável, registra a
  situação de cada exame e calcula cobertura com intervalo de confiança, candidatos por exame e
  a troca entre os dois.
- Os testes passam: 71 aprovados e 17 pulados numa máquina sem a base. Os pulados são os que
  abrem volume real, e rodam na máquina que tem o disco.

---

## 2. S3-T5: as marcações excluídas

### 2.1 O que o card pede

> O LUNA16 tem marcações que devem ser ignoradas na contagem de falsos positivos. Precisamos
> configurar o caminho de `annotations_excluded.csv`, passar o arquivo ao avaliador e conferir
> com um caso pequeno que a regra está funcionando.

Checklist do card:

1. Adicionar o caminho no arquivo de configuração.
2. Carregar o caminho pela configuração do projeto.
3. Passar o arquivo ao avaliador oficial.
4. Criar um caso pequeno com um achado excluído.
5. Confirmar que esse achado não vira falso positivo.

### 2.2 O que são as marcações excluídas

O `annotations_excluded.csv` vem dentro do pacote oficial de avaliação do desafio, na pasta
`annotations/`. Ele traz 35.192 achados nos 888 exames que o desafio decidiu não pontuar: nódulo
abaixo de 3 mm, achado que não é nódulo, e anotação que não teve a concordância de três dos
quatro radiologistas.

Candidato que cai em cima de um desses **não é acerto nem falso positivo: sai da conta.** Se a
gente ignorar isso, esses pontos viram alarme falso, o falso positivo por exame infla, e o nosso
resultado deixa de ser comparável com qualquer publicação do LUNA16. A curva FROC tem falso
positivo por exame no eixo x, então isso mexe direto na métrica do projeto.

O arquivo tem as mesmas colunas do `annotations.csv`:

```
seriesuid,coordX,coordY,coordZ,diameter_mm
1.3.6.1.4.1.14519.5.2.1.6279.6001.100225287222365663678666836860,-131.8964945,-155.0567015,-317.8,-1
```

**30.513 dos 35.192 achados têm `diameter_mm = -1`.** São os achados que não são nódulo, e por
isso não têm diâmetro medido. Isso importa na regra, como explicado abaixo.

### 2.3 A regra, conferida no código do avaliador oficial

Antes de escrever código, a regra foi lida no próprio avaliador do desafio
(`noduleCADEvaluationLUNA16.py`, no pacote `evaluationScript`). O trecho que manda é este:

```python
diameter = float(noduleAnnot.diameter_mm)
if diameter < 0.0:
  diameter = 10.0
radiusSquared = pow((diameter / 2.0), 2.0)
...
if dist < radiusSquared:
    if (noduleAnnot.state == "Included"):
        # acerto: o candidato sai da lista de falsos positivos
    elif (noduleAnnot.state == "Excluded"):
        # ignorado: o candidato sai da lista sem contar como nada
```

Disso saem três detalhes que mudam a contagem, e os três foram reproduzidos:

1. **Achado sem diâmetro vale 10 mm.** O `-1` é trocado por 10 mm, então o raio é de 5 mm. Se o
   `-1` fosse usado como está, o raio seria negativo e nenhum dos 30.513 achados casaria com
   candidato nenhum, sem erro nenhum.
2. **O nódulo de verdade vem antes do achado excluído.** O avaliador monta a lista com os nódulos
   do `annotations.csv` primeiro e os excluídos depois. Um candidato em cima dos dois é acerto,
   e não ignorado.
3. **A distância é estritamente menor que o raio** (`dist < radiusSquared`). Candidato exatamente
   na borda não casa.

### 2.4 O que foi implementado

**A chave no config** (`configuracao/config.yaml`, bloco `caminhos`, logo abaixo de
`luna16_avaliacao`, como o card pede):

```yaml
luna16_avaliacao: "/media/kauan/HD Samuel/luna/archive/evaluationScript/evaluationScript"
luna16_anotacoes_excluidas: "/media/kauan/HD Samuel/luna/archive/evaluationScript/evaluationScript/annotations/annotations_excluded.csv"
```

O nome da chave é o que o card sugere. O card pede para combinar o nome no grupo antes do
commit, então confirme antes de integrar.

**A regra** (`src/detection/candidatos.py`):

```python
from detection import candidatos as det

rotulos = det.rotular(lista_de_candidatos, nodulos, excluidos)
# um rótulo por candidato, na mesma ordem: "acerto", "ignorado" ou "falso_positivo"
```

- `lista_de_candidatos`: DataFrame com `seriesuid`, `coordX`, `coordY`, `coordZ`, em mm de mundo.
- `nodulos`: o `annotations.csv`, com `diameter_mm`.
- `excluidos`: o `annotations_excluded.csv`.
- As constantes `det.ACERTO`, `det.IGNORADO`, `det.FALSO_POSITIVO` e
  `det.DIAMETRO_SEM_MEDIDA_MM` (10,0) ficam no mesmo módulo.

A função trabalha exame por exame, e um achado de um exame nunca tira da conta candidato de
outro exame.

**O script de medição** (`scripts/12_marcacoes_excluidas.py`): lê o arquivo pela chave do config,
rotula todos os candidatos do `candidates_V2.csv` e, se a lista própria do T10 já existir, a
lista própria também. Grava `dados/intermediario/marcacoes_excluidas.csv` e imprime:

- quantos achados excluídos existem e quantos não têm diâmetro;
- para cada lista: pontos, acertos, ignorados, falsos positivos, e o falso positivo por exame
  **sem** a regra e **com** a regra;
- uma conferência contra o rótulo do próprio desafio: o `candidates_V2.csv` tem a coluna `class`,
  e nenhum candidato de classe 1 deveria sair como falso positivo ou ignorado. Se sair, o nosso
  critério de casamento está diferente do que o desafio usou para rotular a lista.

O falso positivo por exame divide pelos 888 exames, incluindo os 287 sem nódulo, pelo mesmo
motivo registrado em `docs/02-analise-exploratoria.md`.

O script também foi declarado como estágio `marcacoes_excluidas` no `dvc.yaml`, do mesmo jeito
que o estágio `candidatos` do `08`.

**Os testes do caso pequeno** (`testes/test_candidatos.py`):

| Teste | O que ele prende |
|---|---|
| `test_candidato_em_achado_excluido_nao_vira_falso_positivo` | O caso do card: um nódulo, um achado excluído e três candidatos saem como acerto, ignorado e falso positivo. |
| `test_sem_a_lista_de_excluidos_o_mesmo_candidato_vira_falso_positivo` | O contraste: sem a lista, o mesmo candidato é falso positivo. Prova que é a lista que muda o rótulo. |
| `test_achado_excluido_sem_diametro_vale_raio_de_5_mm` | O `-1` vira raio de 5 mm: 4,9 mm do centro é ignorado, 5,1 mm é falso positivo. |
| `test_candidato_em_nodulo_e_em_excluido_ao_mesmo_tempo_e_acerto` | O nódulo vem antes do excluído. |
| `test_achado_excluido_de_outro_exame_nao_tira_candidato_da_conta` | Achado de um exame não afeta outro. |
| `test_rotular_usa_distancia_estritamente_menor_como_o_avaliador` | Na borda exata não casa. |
| `test_rotular_preserva_a_ordem_com_exames_intercalados` | O rótulo volta na ordem dos candidatos, mesmo com exames misturados. |

### 2.5 Como os itens do checklist ficaram

| Item | Situação |
|---|---|
| 1. Adicionar o caminho no config | Feito. |
| 2. Carregar o caminho pela configuração | Feito. O `12` lê por `cfg["caminhos"]["luna16_anotacoes_excluidas"]`, sem caminho no código. |
| 3. Passar o arquivo ao avaliador oficial | **Aberto.** O avaliador do card T4 não existe no repositório. A função `rotular` está pronta para ele usar, lendo o arquivo pela mesma chave. |
| 4. Caso pequeno com um achado excluído | Feito, nos testes acima. |
| 5. Confirmar que não vira falso positivo | Feito nos testes, e conferido também rodando o `12` num LUNA16 sintético: o candidato em cima do achado excluído saiu como ignorado, e o falso positivo por exame caiu de 0,8 para 0,6. |

### 2.6 Uma divergência para o grupo decidir

O avaliador oficial casa candidato e nódulo com distância **estritamente menor** que o raio. A
função `alcancados`, que já existia e mede a cobertura das listas (`08` e `10`), usa **menor ou
igual**, e o teste `test_a_borda_do_raio_conta_como_acerto` afirma que "o desafio usa distância
menor ou igual ao raio", o que não bate com o código oficial.

Na prática, com coordenada em float, a diferença só aparece em empate exato na borda, que é
raríssimo. Mesmo assim as duas funções divergem. Isso **não foi alterado** neste trabalho,
porque mudar o `alcancados` mexe numa medição já publicada no repositório (a tabela das listas
em `docs/criterios_inclusao_luna16.md`). A divergência está registrada nesse mesmo documento até
o grupo decidir.

---

## 3. S4-T10: a cobertura nos 888 exames

### 3.1 O que o card pede

> Rodar o detector próprio na base inteira e medir quantos nódulos ele encontra e quantos
> candidatos gera por exame. Esses números mostram o limite máximo do sistema.

Comentário do card: só começar depois de fechar o T9, e o limiar de 0,20 não pode ser usado
como vencedor, porque perdeu um nódulo na validação.

Checklist do card:

1. Confirmar a configuração antes da execução.
2. Rodar os 888 exames de forma retomável.
3. Registrar exames concluídos, falhas e exames sem candidato.
4. Calcular a fração de nódulos encontrados.
5. Calcular a média de candidatos por exame.
6. Registrar a troca entre cobertura e quantidade de candidatos.
7. Não chamar cobertura de FROC.

### 3.2 Por que isso é o "limite máximo do sistema"

O sistema tem duas etapas. A primeira, a busca por blob detection, aponta pontos suspeitos. A
segunda, o classificador de redução de falsos positivos, decide quais desses pontos são nódulo.
O classificador só consegue acertar nódulo que tenha candidato em cima. Então a fração de
nódulos que a busca alcança é o teto de sensibilidade do sistema inteiro, e a quantidade de
candidatos por exame é o tamanho do trabalho que sobra para o classificador.

O número a bater é o do `candidates_V2.csv` do desafio: **1.166 dos 1.186 nódulos (98,3%), com
850 candidatos por exame**, medido em `docs/criterios_inclusao_luna16.md`. A amostra de 8
exames de 13/09 deu 14.036 candidatos por exame, 16 vezes mais.

### 3.3 Como cada item do checklist foi atendido

**1. Confirmar a configuração.** A rodada grava uma pasta, `dados/intermediario/rodada_deteccao/`,
e dentro dela um `parametros.json` com os parâmetros do `blob_log` com que a rodada começou. Se
alguém mudar o `config.yaml` no meio e rodar de novo, o script se recusa a continuar e diz o que
mudou:

```
.../rodada_deteccao foi gerada com outros parâmetros (threshold: 0.1 -> 0.2). Volte o
config.yaml para os parâmetros da pasta ou apague a pasta para recomeçar.
```

Sem essa trava, metade dos exames sairia de um limiar e metade de outro, numa lista só, sem erro
nenhum. O script também imprime os parâmetros no começo de toda rodada.

**2. Rodar de forma retomável.** Cada exame grava o próprio arquivo,
`rodada_deteccao/<seriesuid>.csv`. Rodar o mesmo comando de novo pula os exames que já têm
arquivo. A gravação é atômica: o arquivo é escrito como `.csv.tmp` e só depois renomeado. Assim,
uma queda no meio da escrita não deixa um arquivo pela metade que seria contado como pronto e
nunca refeito. Uma queda custa só o exame que estava rodando.

**3. Registrar concluídos, falhas e exames sem candidato.** Cada tentativa vira uma linha em
`rodada_deteccao/registro.csv`. No fim, o script grava `dados/intermediario/situacao_deteccao.csv`,
com uma linha por exame e um destes estados:

| Estado | Significado |
|---|---|
| `concluido` | Rodou e achou ao menos um candidato. |
| `sem_candidato` | Rodou e não achou nada. **É resultado, não falha.** Entra na média de candidatos por exame. |
| `falha` | Deu erro ao abrir o volume ou ao detectar. É tentado de novo na rodada seguinte. |
| `pendente` | Ainda não rodou, por exemplo porque a rodada foi interrompida. |

O que manda no estado é a existência do arquivo do exame na pasta. O registro só traz o tempo e
a mensagem de erro. Um exame que falhou e depois deu certo aparece como `concluido`.

**4. Fração de nódulos encontrados.** É calculada pela função `cobertura` em
`src/detection/candidatos.py`, com intervalo de confiança de 95% por bootstrap. As reamostras e
o nível de confiança vêm do `config.yaml` (`avaliacao.bootstrap_reamostras` e
`avaliacao.intervalo_confianca`), e a semente é o `seed` do config, então o intervalo se
reproduz.

Dois cuidados:

- **O bootstrap é por exame, e não por nódulo.** Os nódulos de um mesmo exame são buscados no
  mesmo volume, então não são independentes. Reamostrar nódulo solto daria um intervalo mais
  estreito do que deveria.
- **A cobertura é medida só nos exames que rodaram.** Um exame que falhou não teve busca, e
  contar os nódulos dele como perdidos misturaria falha de execução com falha do método. As
  falhas ficam contadas à parte, na situação.

O critério de "alcançar" é o mesmo do `08`: um candidato a menos de metade do diâmetro do centro
do nódulo (função `alcancados`).

**5. Média de candidatos por exame.** O script imprime a média, a mediana, o mínimo e o máximo.
O denominador são os exames que rodaram, incluindo os sem candidato. O tempo médio por exame e o
total em horas também saem no terminal.

**6. Troca entre cobertura e quantidade de candidatos.** O script grava
`dados/intermediario/troca_cobertura_candidatos.csv` com:

- a lista própria inteira;
- a lista própria cortando as escalas menores do `blob_log`, com um filtro `raio >= r` para cada
  raio distinto que a busca produziu. É o jeito de ver quanto de cobertura se perde ao ter menos
  pontos, sem rodar de novo;
- o `candidates.csv` e o `candidates_V2.csv` do desafio, medidos sobre os mesmos exames.

Cada linha tem candidatos por exame, nódulos alcançados, cobertura e intervalo.

**7. Não chamar cobertura de FROC.** A cobertura é o teto de sensibilidade da lista, sem escore
e sem contagem de falso positivo. A curva FROC só existe quando houver um classificador dando
nota a cada candidato. Isso está escrito na doc, na docstring da função e na saída do script
("é teto de sensibilidade da lista, não ponto da curva FROC").

### 3.4 A coluna do raio

O card antigo pedia uma coluna `raio_mm`. O card atual diz que "a saída atual usa a coluna raio",
e foi mantido assim: a lista sai com `seriesuid, coordX, coordY, coordZ, raio`, com as
coordenadas em mm de mundo e o raio em mm.

A conversão de índice para mundo, que o card antigo alertava ser o ponto onde tudo dá errado em
silêncio (o `blob_log` devolve `z, y, x`), já estava resolvida em `src/detection/blobs.py` e é
presa pelo teste `test_candidatos_do_exame_concorda_com_a_formula_do_projeto`, que roda sobre
exames reais. Nada disso foi mexido.

### 3.5 O que o script 10 faz, do começo ao fim

1. Lê o inventário e mantém só os exames com volume `.mha` em `dados/processado/volumes/`.
2. **Demonstração num exame:** roda no exame de maior nódulo e grava a figura
   `relatorios/figuras/deteccao_candidatos.png`. Isso já existia e não mudou.
3. Escolhe o lote: os 888, ou uma amostra por subset se receber um número como argumento.
4. Confere os parâmetros contra o `parametros.json` da pasta da rodada.
5. Roda os exames que faltam, gravando um arquivo e uma linha de registro por exame, e mostra o
   progresso a cada 25 exames com uma estimativa do tempo que falta.
6. Grava a situação de cada exame.
7. Junta tudo em `dados/intermediario/candidatos.csv`.
8. Calcula a cobertura com intervalo e grava `cobertura_candidatos_proprios.csv`.
9. Calcula a troca e grava `troca_cobertura_candidatos.csv`.

### 3.6 O que foi verificado

Além dos testes de unidade (seção 5.2), o script foi rodado de ponta a ponta num LUNA16
sintético, com volumes `.mha` contendo bolinhas gaussianas, um exame sem nódulo, um volume
zerado, um volume corrompido e um exame do inventário sem volume:

- a rodada foi derrubada de propósito no terceiro exame, e a retomada pulou os dois prontos e
  fez os cinco restantes;
- a situação saiu com 4 concluídos, 2 sem candidato e 1 falha (o volume corrompido);
- trocar o `threshold` no meio fez o script recusar continuar;
- uma terceira rodada refez só o exame que tinha falhado;
- a cobertura e a troca saíram com as três listas lado a lado.

Esse teste mostrou um defeito que foi corrigido: a mensagem de erro do SimpleITK tem várias
linhas e quebrava o CSV. Agora só a primeira linha é guardada, como o `07` já fazia.

---

## 4. Configurar a máquina do zero

Se a máquina já roda o pipeline (`07`, `08`, `10`), pule para a seção 5. Só confira o passo 4.4.

### 4.1 Pré-requisitos

- Python 3.12 ou mais novo (`python3 --version`).
- git.
- O LUNA16 em disco, com os dez subsets, as máscaras, as listas de candidatos e o pacote de
  avaliação. São cerca de 112 GB.
- Os 888 volumes pré-processados em `dados/processado/volumes/`, que ocupam 8,6 GiB. Ou eles
  já estão na máquina, ou saem do `07` (veja o passo 4.5).
- Para a rodada inteira, umas seis horas de máquina ligada (888 × 23,6 s por exame, medido em
  13/09/2026 em outra máquina).

### 4.2 Pegar o código

```bash
git clone https://github.com/kauanLDD/PI3-Grupo-5.git
cd PI3-Grupo-5
git fetch origin
git checkout deteccao/t10-cobertura-888
```

Se o repositório já existe na máquina:

```bash
git fetch origin
git checkout deteccao/t10-cobertura-888
git pull
```

### 4.3 Ambiente Python

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

No Ubuntu, se o `venv` reclamar: `sudo apt install python3.12-venv`.

Se o `pip install` ficar parado sem baixar nada, rode de novo sem o cache:

```bash
PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 .venv/bin/pip install -r requirements.txt
```

Para os testes e os scripts deste trabalho bastam SimpleITK, scikit-image, numpy, pandas, scipy,
pyyaml, matplotlib e pytest. O `torch` do `requirements.txt` não é usado aqui.

### 4.4 Apontar o `config.yaml` para os dados

Abra `configuracao/config.yaml`. No bloco `caminhos`, todos os caminhos do LUNA16 precisam
apontar para onde a base está **nesta máquina**. Os valores atuais são os do HD do Kauan:

```yaml
caminhos:
  luna16: "/media/kauan/HD Samuel/luna/archive"
  luna16_anotacoes: "/media/kauan/HD Samuel/luna/archive/annotations.csv"
  luna16_candidatos: "/media/kauan/HD Samuel/luna/archive/candidates_V2/candidates_V2.csv"
  luna16_candidatos_original: "/media/kauan/HD Samuel/luna/archive/candidates.csv"
  luna16_mascaras: "/media/kauan/HD Samuel/luna/archive/seg-lungs-LUNA16/seg-lungs-LUNA16"
  luna16_avaliacao: "/media/kauan/HD Samuel/luna/archive/evaluationScript/evaluationScript"
  luna16_anotacoes_excluidas: "/media/kauan/HD Samuel/luna/archive/evaluationScript/evaluationScript/annotations/annotations_excluded.csv"
```

A chave nova é a última, `luna16_anotacoes_excluidas`. Confira que o arquivo existe mesmo nesse
caminho:

```bash
ls -la "/media/kauan/HD Samuel/luna/archive/evaluationScript/evaluationScript/annotations/annotations_excluded.csv"
wc -l  "/media/kauan/HD Samuel/luna/archive/evaluationScript/evaluationScript/annotations/annotations_excluded.csv"
```

O `wc -l` tem que dar **35193** (35.192 achados mais o cabeçalho). Se o pacote de avaliação
estiver em outra pasta, corrija só essa linha. Se o arquivo não existir, ele vem no pacote
`evaluationScript` do desafio, no Zenodo.

Os caminhos relativos do config, como `dados/intermediario` e `dados/processado/volumes`, são
relativos à raiz do repositório e não precisam mudar.

Os caminhos novos deste trabalho, também relativos e sem precisar mexer:

```yaml
  rodada_deteccao: "dados/intermediario/rodada_deteccao"
  situacao_deteccao: "dados/intermediario/situacao_deteccao.csv"
  troca_cobertura_candidatos: "dados/intermediario/troca_cobertura_candidatos.csv"
```

### 4.5 Garantir que os arquivos de entrada existem

```bash
ls dados/intermediario/inventario_volumes.csv
ls dados/processado/volumes/*.mha | wc -l
```

- O inventário tem que existir. Se não existir: `.venv/bin/python scripts/02_inventario_volumes.py`.
- A contagem de volumes tem que dar **888**. Se der menos, há duas saídas:
  - rodar `.venv/bin/python scripts/07_preprocessar_base.py`, que leva cerca de 40 minutos e
    ocupa 8,6 GiB;
  - ou baixar os volumes do Drive (PI3-Grupo-5 / Dataset / processado / volumes) para
    `dados/processado/volumes/`. Atenção: os volumes do Drive são de 10/09, de antes da mesclagem
    da normalização. A diferença medida foi de um bit de float, mas regerar a partir da `main`
    tira a dúvida se algo parecer estranho.

---

## 5. Passo a passo para testar e rodar

Siga na ordem. Cada passo diz o que esperar.

### 5.1 Conferir que está no branch certo

```bash
git branch --show-current
```

Tem que mostrar `deteccao/t10-cobertura-888`.

### 5.2 Rodar os testes

```bash
.venv/bin/python -m pytest testes -q
```

Numa máquina **sem** a base, o resultado foi `71 passed, 17 skipped`. Na máquina **com** a base,
os pulados passam a rodar, então espere mais testes aprovados e nenhum falho. Se algum falhar,
pare e veja a seção 8.

Para rodar só os testes deste trabalho:

```bash
.venv/bin/python -m pytest testes/test_rodada.py testes/test_candidatos.py -v
```

Os testes novos:

- `testes/test_rodada.py`, 9 testes da rodada retomável: pasta nova e retomada, recusa de
  parâmetro diferente, pular o que rodou, exame sem candidato contando como rodado, gravação sem
  arquivo temporário sobrando, os quatro estados, falha que depois dá certo, e junção da lista.
- `testes/test_candidatos.py`, 5 testes da `cobertura` (fração, intervalo fechado quando acerta
  tudo, bootstrap por exame, reprodutibilidade com semente, caso sem nódulo) e os 7 da `rotular`
  descritos na seção 2.4.

### 5.3 S3-T5: rodar a medição das marcações excluídas

É rápido, não abre volume nenhum, e não depende do T9.

```bash
.venv/bin/python scripts/12_marcacoes_excluidas.py
```

O que esperar:

1. A primeira linha tem que dizer **35192 achados excluídos em 888 exames, 30513 sem diâmetro**.
   Se der outro número, o arquivo não é o oficial ou o inventário não tem os 888.
2. A segunda diz **1186 nódulos de referência em 888 exames**.
3. A conferência do V2 diz quantos candidatos de classe 1 saíram como falso positivo e como
   ignorados. O esperado é zero ou muito perto disso. Se der um número grande, o critério de
   casamento diverge do desafio, e isso precisa ser investigado antes de usar a regra.
4. A tabela mostra, para o V2, os acertos, os ignorados e o falso positivo por exame sem e com
   a regra. A diferença entre as duas colunas é o quanto o falso positivo inflaria sem a regra.

A saída fica em `dados/intermediario/marcacoes_excluidas.csv`.

Pelo DVC dá no mesmo, e ele registra o hash no `dvc.lock`:

```bash
.venv/bin/dvc repro marcacoes_excluidas
```

### 5.4 S4-T10: confirmar a configuração (item 1 do checklist)

**Este passo é obrigatório antes de rodar os 888.**

O card diz que a rodada só começa depois do T9, que escolhe os parâmetros do `blob_log`. Esses
parâmetros **não estão no repositório**: o `config.yaml` continua com os de partida.

```yaml
deteccao:
  blob_log:
    min_sigma: 1.0
    max_sigma: 5.0
    num_sigma: 5
    threshold: 0.1
```

Faça assim:

1. Abra o card do T9 (https://trello.com/c/jJinT6vu) e pegue os parâmetros escolhidos.
2. Ponha esses valores em `deteccao.blob_log` no `configuracao/config.yaml`.
3. Confira que o `threshold` **não é 0,20**, que o card do T10 proíbe porque perdeu um nódulo
   na validação.
4. Se o T9 ainda não fechou, a decisão de rodar com os parâmetros de partida é do grupo. Se
   rodar assim, registre isso junto dos números.

### 5.5 S4-T10: rodada curta de conferência

Antes de soltar seis horas de máquina, rode uma amostra de 8 exames, um por subset:

```bash
.venv/bin/python scripts/10_detectar_candidatos.py 8
```

O que esperar no terminal:

1. A linha do inventário, com **888 exames com volume pré-processado em disco, 0 sem**.
2. O exame de demonstração e a figura `relatorios/figuras/deteccao_candidatos.png`. Abra a
   figura: o círculo verde (o nódulo anotado) tem que ter candidatos vermelhos por perto.
3. `parâmetros da rodada: ...`, que **têm que ser os do T9**.
4. `rodada nova, 0 de 8 exames já prontos, 8 por fazer`.
5. O progresso, a situação dos 8, os candidatos por exame, a cobertura com intervalo e a tabela
   da troca.

Com os parâmetros de partida, a amostra de 13/09 deu cerca de 14 mil candidatos por exame e
23,6 s por exame. Números muito diferentes disso com os mesmos parâmetros indicam algum
problema.

**Depois da rodada curta, apague a pasta da rodada** antes de soltar os 888. Os 8 exames
seriam reaproveitados, o que está certo se os parâmetros forem os mesmos, mas começar limpo
evita dúvida:

```bash
rm -rf dados/intermediario/rodada_deteccao
```

### 5.6 S4-T10: a rodada nos 888 (itens 2 a 6 do checklist)

Leva umas seis horas. Rode num terminal que sobreviva a fechar a janela.

Com `tmux` (recomendado):

```bash
tmux new -s deteccao
.venv/bin/python scripts/10_detectar_candidatos.py 2>&1 | tee dados/intermediario/rodada_deteccao.log
# para sair sem parar a rodada: Ctrl+B e depois D
# para voltar: tmux attach -t deteccao
```

Ou com `nohup`:

```bash
nohup .venv/bin/python scripts/10_detectar_candidatos.py > dados/intermediario/rodada_deteccao.log 2>&1 &
tail -f dados/intermediario/rodada_deteccao.log
```

Desligue a suspensão automática da máquina durante a rodada.

O log mostra o progresso a cada 25 exames, com uma estimativa do tempo restante:

```
25/888  590s, faltam uns 20370s
```

### 5.7 Se a rodada cair no meio

Rode exatamente o mesmo comando de novo. O script diz quantos exames já estão prontos e continua
dos que faltam:

```
.../rodada_deteccao: retomando, 412 de 888 exames já prontos, 476 por fazer
```

Não apague a pasta `rodada_deteccao` e não mude o `config.yaml` entre uma tentativa e outra. Se
mudar, o script recusa continuar (veja a seção 3.3, item 1).

Os exames que falharam são tentados de novo automaticamente toda vez que o comando roda. Se um
exame falhar sempre, a mensagem de erro dele está na coluna `erro` de `situacao_deteccao.csv`.

### 5.8 Rodar o `12` de novo com a lista própria

Com o `candidatos.csv` dos 888 pronto, rode o `12` outra vez. Agora ele inclui a lista própria e
mostra quantos dos nossos candidatos caem em achados excluídos:

```bash
.venv/bin/python scripts/12_marcacoes_excluidas.py
```

### 5.9 Conferir que terminou

```bash
.venv/bin/python -c "
import pandas as pd
s = pd.read_csv('dados/intermediario/situacao_deteccao.csv')
print(len(s), 'exames')
print(s.status.value_counts())
print(s[s.status == 'falha'][['seriesuid', 'erro']])
"
```

O esperado é 888 exames, nenhum `pendente`, e de preferência nenhuma `falha`.

---

## 6. Como ler os resultados

Os arquivos ficam em `dados/intermediario/`, fora do git, como todo dado gerado.

### 6.1 `candidatos.csv`

A lista própria, uma linha por candidato:

| Coluna | Conteúdo |
|---|---|
| `seriesuid` | O exame. |
| `coordX`, `coordY`, `coordZ` | Centro do candidato, em mm de mundo, o mesmo espaço do `annotations.csv`. |
| `raio` | Raio estimado, em mm (`sigma * sqrt(3) * espaçamento`). |

Esse arquivo não vai para o GitHub. O card manda entregar o número e as contagens. O arquivo em
si fica na máquina, ou vai para o Drive se o grupo precisar.

### 6.2 `situacao_deteccao.csv`

Uma linha por exame: `seriesuid`, `status`, `candidatos`, `segundos`, `erro`, `subset`. Os
estados estão na seção 3.3, item 3.

### 6.3 `cobertura_candidatos_proprios.csv`

Uma linha só, com a cobertura da lista própria:

| Coluna | Conteúdo |
|---|---|
| `lista`, `filtro` | Nome da lista e filtro aplicado (`nenhum`). |
| `exames` | Exames que rodaram, que são o denominador. |
| `pontos`, `por_exame` | Total de candidatos e média por exame. |
| `alcancados`, `nodulos` | Nódulos alcançados e nódulos nos exames que rodaram. |
| `cobertura` | `alcancados / nodulos`. |
| `ic_inferior`, `ic_superior` | Intervalo de 95% por bootstrap de exame. |

### 6.4 `troca_cobertura_candidatos.csv`

As mesmas colunas, uma linha por lista ou corte. Leia assim: cada linha é um ponto de operação
possível, e quanto mais à direita na quantidade de candidatos, mais cobertura. A pergunta que
ela responde é quanto de cobertura cada redução de candidatos custa, e onde a lista própria fica
em relação ao V2.

### 6.5 `marcacoes_excluidas.csv`

Uma linha por lista: `pontos`, `acertos`, `ignorados`, `falsos_positivos`,
`fp_por_exame_sem_regra` e `fp_por_exame_com_regra`.

### 6.6 Como **não** reportar esses números

- Não chame a cobertura de sensibilidade da FROC nem de resultado do modelo. Ela é teto.
- Não chame candidatos por exame de falso positivo por exame. Quase todos os candidatos são
  falsos positivos antes do classificador, mas o número da FROC só existe depois dele e
  descontando os ignorados.
- Reporte sempre com o intervalo, como o projeto exige.

---

## 7. Onde escrever os números depois da rodada

O projeto tem a regra de que todo número vem com a data e o script que o mediu ao lado.

1. **`docs/04-deteccao-de-candidatos.md`**, seção "A rodada nos 888 exames", subseção "O que ela
   mediu". Hoje ela diz que a rodada não foi feita. Substitua por:
   - a data da rodada e o comando;
   - os parâmetros usados, os do T9;
   - a situação dos 888: concluídos, sem candidato, falhas;
   - a cobertura, com intervalo de 95% e o número de reamostras;
   - candidatos por exame: média, mediana, mínimo e máximo;
   - o tempo por exame e o total;
   - a tabela da troca, com o V2 ao lado.

   Atualize também a frase "A rodada nos 888 exames não aconteceu" da seção "O que os parâmetros
   de partida entregam".

2. **`docs/criterios_inclusao_luna16.md`**, seção "O que fica fora da conta na avaliação". Troque
   a frase "Esse número ainda não foi medido" pelo resultado do `12`: quantos candidatos do V2
   são ignorados e o falso positivo por exame com e sem a regra, com a data.

3. **`README.md`**, na seção "O que já funciona": acrescentar a rodada nos 888 e a regra das
   marcações excluídas. Na seção de testes, a frase "São 73 testes, verificados em 15/09/2026"
   precisa da contagem nova, feita na máquina com a base (`pytest testes -q`).

4. **`docs/historico-do-projeto.md`**: uma entrada nova contando a rodada, se o grupo mantiver o
   histórico.

5. **Trello**: marcar os itens do checklist e anexar os números ou o link do PR, como os cards
   pedem.

---

## 8. Problemas comuns

**`nenhum volume pré-processado em dados/processado/volumes`.** Os volumes não estão na pasta.
Veja o passo 4.5.

**`FileNotFoundError` com `annotations_excluded.csv`.** A chave `luna16_anotacoes_excluidas`
aponta para um caminho que não existe nesta máquina. Corrija no `config.yaml` (passo 4.4).

**`KeyError: 'luna16_anotacoes_excluidas'` ou `KeyError: 'rodada_deteccao'`.** O
`config.yaml` é de antes deste branch. Confira `git branch --show-current` e
`git status configuracao/config.yaml`. Se houver mudança local no config, ela pode ter
sobrescrito as chaves novas.

**`... foi gerada com outros parâmetros (...)`.** O `config.yaml` mudou desde que a pasta da
rodada começou. Ou volte o config para os parâmetros da pasta (estão em
`dados/intermediario/rodada_deteccao/parametros.json`), ou apague a pasta para recomeçar do
zero.

**Exames em `falha` na situação.** Veja a coluna `erro`. O mais comum é o volume `.mha`
corrompido ou incompleto, por exemplo numa cópia do Drive interrompida. Regere o volume com o
`07` ou baixe de novo e rode o `10` outra vez. Ele refaz só os que falharam.

**A rodada está muito mais lenta que 23,6 s por exame.** Esse tempo foi medido em outra
máquina. Volumes num HD externo lento ou na nuvem sincronizada pesam. Copiar os volumes para o
disco interno ajuda.

**O `pip install` fica parado.** Rode com `PIP_NO_CACHE_DIR=1` (passo 4.3).

**A conferência do V2 no `12` mostra muitos candidatos de classe 1 como falso positivo.**
Confira se o `annotations.csv` do config é o oficial (1.186 nódulos) e se o inventário tem os
888 exames. Se estiver tudo certo e o número continuar alto, a regra diverge do critério do
desafio. Pare e leve ao grupo antes de usar.

**Os testes com volume real falham.** Eles abrem os exames nos extremos de espaçamento e um de
direção invertida. Uma falha ali indica volume pré-processado diferente do esperado, por exemplo
os do Drive de antes da mesclagem. Regere com o `07`.

---

## 9. Lista de arquivos alterados

| Arquivo | Task | O que mudou |
|---|---|---|
| `configuracao/config.yaml` | T5 e T10 | Chave `luna16_anotacoes_excluidas` (T5). Chaves `rodada_deteccao`, `situacao_deteccao` e `troca_cobertura_candidatos` (T10). |
| `src/detection/candidatos.py` | T5 e T10 | `rotular` e as constantes da regra dos excluídos (T5). `cobertura`, com bootstrap por exame (T10). O `alcancados` não mudou. |
| `src/detection/rodada.py` | T10 | Novo. Pasta da rodada, trava de parâmetros, gravação atômica, registro, situação e junção. |
| `scripts/10_detectar_candidatos.py` | T10 | A parte da base foi reescrita para ser retomável e medir tudo do checklist. A demonstração num exame não mudou. |
| `scripts/12_marcacoes_excluidas.py` | T5 | Novo. Mede o efeito da regra no V2 e na lista própria. |
| `testes/test_candidatos.py` | T5 e T10 | 5 testes da `cobertura` e 7 da `rotular`. |
| `testes/test_rodada.py` | T10 | Novo. 9 testes da rodada retomável. |
| `dvc.yaml` | T5 | Estágio `marcacoes_excluidas`. O `dvc.lock` ainda não tem esse estágio, e ele entra na primeira vez que o `dvc repro` rodar. |
| `docs/criterios_inclusao_luna16.md` | T5 | A regra, os três detalhes do avaliador oficial, a divergência de `<` e `<=`, e onde estão o teste e o script. |
| `docs/04-deteccao-de-candidatos.md` | T10 | Seção "A rodada nos 888 exames": como rodar, o que grava, as decisões e o espaço para os números. |
| `README.md` | T5 e T10 | O `12` na receita e na tabela dos scripts, a descrição nova do `10`, e os nove estágios do DVC. |
| `GUIA-T5-T10.md` | as duas | Este documento. |

---

## 10. O que ficou em aberto

1. **Rodar os 888** (T10, itens 2 a 6), na máquina com os volumes, seguindo a seção 5.
2. **Os parâmetros do T9** no `config.yaml` (T10, item 1). Não estão no repositório.
3. **Rodar o `12` na base real** (T5) e escrever o número na doc.
4. **Passar o arquivo ao avaliador oficial** (T5, item 3). Depende do avaliador do card T4
   existir. Quando existir, ele deve ler o arquivo pela chave `luna16_anotacoes_excluidas` e
   aplicar `detection.candidatos.rotular`, sem caminho escrito no código.
5. **Combinar no grupo o nome da chave** `luna16_anotacoes_excluidas`, como o card da T5 pede.
6. **Decidir a divergência de `<` e `<=`** entre o `alcancados` e o avaliador oficial
   (seção 2.6).
7. **Atualizar a contagem de testes do README** na máquina com a base.
8. **Commit e PR**: as mudanças ainda não foram commitadas.
