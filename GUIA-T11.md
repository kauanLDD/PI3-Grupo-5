# Guia da task S4-T11

Este documento explica tudo o que foi feito na task S4-T11, comparar a lista própria com a lista
V2, por que foi feito assim, e o passo a passo completo para rodar a medição que falta na máquina
que tem a base. Ele foi escrito para quem vai executar sem ter acompanhado o trabalho.

O trabalho está no branch `deteccao/t11-lista-propria-v2`.

| Task | Card | Situação |
|---|---|---|
| S4-T11, comparar a lista própria com a lista V2 | https://trello.com/c/gX7CNZwj | Decisão escrita em `docs/decisoes/0007`, com código, testes e estágio do DVC prontos. Falta rodar o `18` na base real e escrever o cruzamento nódulo a nódulo na decisão. |

**O script novo não rodou na base real.** A máquina onde o código foi escrito não tem o LUNA16.
A tabela da decisão 0007 usa somente números que já estavam medidos no repositório (seção 3.2).
O script foi verificado com testes sintéticos e com uma base de mentira, montada só para rodá-lo
de ponta a ponta. O número que ainda não existe é o cruzamento: quantos nódulos só uma das duas
listas alcança.

---

## Sumário

1. [Resumo em cinco linhas](#1-resumo-em-cinco-linhas)
2. [O que o card pede](#2-o-que-o-card-pede)
3. [A decisão 0007](#3-a-decisão-0007)
4. [O que foi implementado](#4-o-que-foi-implementado)
5. [Configurar a máquina](#5-configurar-a-máquina)
6. [Passo a passo para testar e rodar](#6-passo-a-passo-para-testar-e-rodar)
7. [Como ler os resultados](#7-como-ler-os-resultados)
8. [Onde escrever os números depois da rodada](#8-onde-escrever-os-números-depois-da-rodada)
9. [Problemas comuns](#9-problemas-comuns)
10. [Lista de arquivos alterados](#10-lista-de-arquivos-alterados)
11. [O que ficou em aberto](#11-o-que-ficou-em-aberto)

---

## 1. Resumo em cinco linhas

- As duas listas foram comparadas nos mesmos 888 exames e nos mesmos 1.186 nódulos, pelo mesmo
  critério de acerto (`alcancados`, em `src/detection/candidatos.py`).
- A lista própria tem 19 vezes mais candidatos por exame (16.114,9 contra 850,2), alcança oito
  nódulos a menos (1.158 contra 1.166) e ocupa 23,8 vezes mais disco (1,60 GiB contra 68,7 MiB).
- A decisão está em `docs/decisoes/0007-lista-de-candidatos-por-experimento.md`: os
  classificadores e a FROC usam o V2, e a lista própria é avaliada como detector, ao lado dele.
- O `scripts/18_comparar_lista_propria_v2.py` refaz a tabela na base, confere que as entradas
  batem, e mede quais nódulos cada lista alcança e a outra não.
- Falta rodar o `18` na máquina com a base (seção 6) e escrever o resultado na decisão
  (seção 8).

---

## 2. O que o card pede

> Comparar as duas listas na mesma base. A comparação deve mostrar cobertura, quantidade de
> candidatos, tempo e espaço. No fim, registrar qual lista será usada em cada experimento e por
> quê.

A checklist do card, e onde cada item foi atendido:

| Item | Onde |
|---|---|
| Usar os mesmos exames e nódulos nas duas listas. | O `18` filtra as duas listas pelo `inventario_volumes.csv` e usa o mesmo `annotations.csv` para as duas. A decisão 0007, seção "Mesma base, mesma régua". |
| Conferir se as quantidades de entrada batem. | O `18` imprime a tabela "conferência da entrada" e para com erro se as duas listas não estiverem sobre os mesmos exames, se houver coordenada ausente, ou se a lista própria tiver exame em falha ou pendente. |
| Comparar cobertura e candidatos por exame. | A tabela da decisão 0007 e o `comparacao_propria_v2.csv`. |
| Comparar tempo de geração e espaço usado. | A tabela da decisão 0007, com a origem de cada número. O `18` mede o espaço pelo tamanho do arquivo e estima o tempo pela calibração. |
| Registrar vantagens, limitações e a decisão final. | A decisão 0007, seções "O que a tabela diz", "Decisão", "A alternativa que descartamos" e "Consequências". |
| Não chamar cobertura de FROC. | Está escrito na decisão, na docstring do módulo e do script, e na saída do script. |

O número da decisão é **0007** porque o card atual diz "usar o próximo número disponível", e a
última decisão era a 0006. Uma versão antiga da descrição do card falava em 0008.

---

## 3. A decisão 0007

### 3.1 O que foi decidido

| Experimento | Lista | Por quê |
|---|---|---|
| Random Forest, baseline | V2 | já foi treinado nela em 04/10/2026, e a seção 4.3 do enunciado descreve o baseline sobre a lista pronta |
| CNN 3D, redução de falsos positivos | V2 | a mesma entrada do baseline isola o efeito do classificador |
| FROC na validação e no teste | V2 | é a lista da trilha de redução de falsos positivos do desafio, contra a qual os resultados publicados se comparam |
| Avaliação do detector LoG | própria | é o produto da etapa de detecção, medido por cobertura e quantidade contra o V2 |

A lista própria não alimenta classificador nesta fase. A decisão é reaberta, num registro novo
que referencia a 0007, se um corte de escala medido no desenvolvimento e conferido na validação
chegar perto de 850 candidatos por exame sem perder nódulo para o V2.

### 3.2 De onde vêm os números da tabela

Nenhum número da decisão foi medido nesta task. Todos já estavam no repositório:

| Número | Fonte |
|---|---|
| Própria: 14.310.042 candidatos, 16.114,9 por exame, 1.158 de 1.186, IC de 96,71% a 98,57% | `docs/04-deteccao-de-candidatos.md` e `docs/historico-do-projeto.md`, rodada de 03/10/2026 conferida em 05/10/2026 |
| V2: 754.975 candidatos, 850,2 por exame, 1.166 de 1.186 | `docs/criterios_inclusao_luna16.md`, `scripts/08_comparar_candidatos.py` de 09/09/2026 |
| Própria: 1.714.804.240 bytes; V2: 72.058.556 bytes | campo `size` do `dvc.lock`, estágio `deteccao` |
| Própria: de 23,6 a 27,4 s por exame | rodada curta de 13/09/2026 e configuração `inicial` da calibração de 20/09/2026 (`docs/05-calibracao-detector.md`) |

**O tempo da rodada completa nunca foi registrado.** O `10_detectar_candidatos.py` só grava o
tempo dos exames que falham, e a rodada foi interrompida depois de 218 exames. Por isso o tempo
é estimado: 888 vezes a faixa medida dá de 5,8 a 6,8 horas de processamento. A decisão diz
explicitamente que isso é aritmética, não medição.

O IC do V2 aparece como "não registrado" na tabela da decisão. O `18` mede esse intervalo, e ele
entra na decisão depois da rodada.

### 3.3 Por que a diferença de cobertura não decide

O intervalo de 95% da lista própria, de 96,71% a 98,57%, contém os 98,3% do V2. Oito nódulos em
1.186 é pouco para dizer que o V2 cobre mais. O que decide é a quantidade: com cobertura parecida,
a lista própria entrega 19 vezes mais pontos para o classificador descartar.

### 3.4 Por que o cruzamento importa

Duas listas com cobertura parecida podem alcançar nódulos diferentes. Se a lista própria alcançar
nódulos que o V2 perde, a união das duas tem teto maior, e isso é resultado que vale escrever,
mesmo que a união herde os 16 mil candidatos por exame. As coberturas foram contadas separadamente
até hoje, então esse número não existe. É o principal motivo de rodar o `18`.

---

## 4. O que foi implementado

### 4.1 `src/detection/comparacao.py`

Módulo novo, com quatro funções e sem ler arquivo nenhum, para poder ser testado com dados
pequenos:

```python
from detection import comparacao

# Conta pontos lidos, pontos de exames fora do inventário, exames com e sem candidato.
# Levanta ValueError se faltar coluna ou se houver coordenada ausente ou infinita.
comparacao.conferir_entrada(lista, exames)

# Candidatos por exame, com zero para exame sem candidato.
comparacao.candidatos_por_exame(lista, exames)

# Uma linha da tabela: pontos, média, mediana, mínimo e máximo por exame,
# alcançados, cobertura e IC por bootstrap de exame (reaproveita detection.candidatos.cobertura).
comparacao.resumir(nome, lista, exames, nodulos, alcancado, reamostras, confianca, semente)

# Nódulos alcançados pelas duas, só pela primeira, só pela segunda, por nenhuma, e a união.
comparacao.cruzar(alcance_a, alcance_b)
```

O critério de acerto não mudou: continua sendo `detection.candidatos.alcancados`, o mesmo do
`08` e do `10`.

### 4.2 `scripts/18_comparar_lista_propria_v2.py`

O que ele faz, na ordem:

1. Lê o `inventario_volumes.csv` (888 exames) e o `annotations.csv`, e fica só com os nódulos dos
   exames do inventário (1.186).
2. Para com erro se algum dos dois arquivos de lista não existir.
3. Se o `situacao_deteccao.csv` existir, para com erro se houver exame em `falha` ou `pendente`,
   ou se ele não cobrir exatamente os exames do inventário. Exame sem rodar baixaria a cobertura
   da lista própria por erro de execução, e não do método.
4. Lê as duas listas, só as colunas `seriesuid`, `coordX`, `coordY` e `coordZ`, e imprime a
   conferência da entrada.
5. Calcula o tempo da lista própria. Se a situação tiver o tempo de todos os exames, soma. Se
   não, usa a média por exame da configuração `inicial` em
   `dados/intermediario/calibracao_log/resultados_por_exame.csv` vezes 888. O V2 entra com zero,
   porque vem pronto.
6. Para cada lista, mede alcance, cobertura e IC, candidatos por exame, tamanho do arquivo e
   bytes por candidato.
7. Cruza os dois alcances nódulo a nódulo e imprime quantos nódulos cada lista alcança sozinha
   e o teto da união.
8. Grava `dados/intermediario/comparacao_propria_v2.csv` e
   `dados/intermediario/alcance_por_nodulo_propria_v2.csv`.
9. Imprime a faixa de diâmetro dos nódulos alcançados por uma lista só.

Ele não abre volume nenhum e não depende de GPU.

### 4.3 Configuração e DVC

Duas chaves novas no bloco `caminhos` do `configuracao/config.yaml`, relativas e sem precisar
mexer:

```yaml
  comparacao_propria_v2: "dados/intermediario/comparacao_propria_v2.csv"
  alcance_por_nodulo_propria_v2: "dados/intermediario/alcance_por_nodulo_propria_v2.csv"
```

Um estágio novo no `dvc.yaml`, `comparar_propria_v2`, com as duas saídas em `cache: false` e
`persist: true`, como os outros estágios recentes. O pipeline passa de 16 para 17 estágios.
**O `dvc.lock` ainda não tem esse estágio.** Ele entra na primeira vez que o `dvc repro` rodar
na máquina com a base.

### 4.4 Testes

`testes/test_comparacao_listas.py`, 9 testes, todos com dados sintéticos:

- a conferência conta os pontos de exames fora do inventário;
- a conferência recusa coordenada ausente;
- a conferência recusa lista sem coluna de coordenada;
- exame sem candidato entra no denominador da média;
- ponto de exame fora do inventário não entra na conta;
- o resumo junta quantidade e cobertura;
- o cruzamento separa o que cada lista alcança sozinha;
- mesma cobertura não quer dizer os mesmos nódulos;
- o cruzamento recusa alcances de tamanhos diferentes.

Na máquina sem a base, `pytest testes/test_comparacao_listas.py testes/test_candidatos.py` deu
`28 passed`.

### 4.5 O que foi verificado com a base de mentira

Numa cópia do repositório, com três exames, três nódulos e listas pequenas:

- a conferência mostrou o ponto de exame fora do inventário e o exame sem candidato;
- o cruzamento separou corretamente os nódulos alcançados só por uma lista;
- o tempo caiu na estimativa pela calibração quando a situação não tinha tempo;
- com um exame marcado como `falha` na situação, o script parou com
  `ValueError: 1 exames da lista própria em falha ou pendentes`.

---

## 5. Configurar a máquina

Se a máquina já rodou o T10 e a calibração, quase tudo está pronto. Confira cada passo mesmo
assim, porque eles são rápidos.

### 5.1 Pré-requisitos

- O ambiente `.venv` do projeto, com o `requirements.txt` e o `requirements-rastreamento.lock.txt`
  instalados. O `18` usa só pandas, numpy e pyyaml, e o `dvc` para rodar pelo estágio.
- O `annotations.csv` e o `candidates_V2.csv` do LUNA16 no HD, nos caminhos do `config.yaml`.
- As saídas do T10 e da calibração em `dados/intermediario/`. A lista abaixo está no passo 5.4.
- **Memória:** o `candidatos.csv` tem 1,6 GiB e 14,3 milhões de linhas. O `10` já lê esse arquivo
  inteiro no final dele, então a máquina que rodou o `10` aguenta. Feche o que estiver pesado
  antes de rodar.
- **Não precisa** dos volumes pré-processados, de GPU, nem do MLflow aberto.

### 5.2 Pegar o código

```bash
cd PI3-Grupo-5
git fetch origin
git checkout deteccao/t11-lista-propria-v2
git pull
```

Confira:

```bash
git branch --show-current
```

Tem que mostrar `deteccao/t11-lista-propria-v2`. Depois que a PR entrar na `main`, use a `main`.

### 5.3 Conferir o `config.yaml`

O `config.yaml` deste branch mantém os caminhos do HD do Kauan. As duas chaves que o `18` lê do
HD são estas:

```yaml
  luna16_anotacoes: "/media/kauan/HD Samuel/luna/archive/annotations.csv"
  luna16_candidatos: "/media/kauan/HD Samuel/luna/archive/candidates_V2/candidates_V2.csv"
```

Com o HD montado, confira:

```bash
ls -la "/media/kauan/HD Samuel/luna/archive/annotations.csv"
ls -la "/media/kauan/HD Samuel/luna/archive/candidates_V2/candidates_V2.csv"
```

O `candidates_V2.csv` tem que ter **72058556** bytes, que é o tamanho registrado no `dvc.lock`.
Se o seu `config.yaml` local tiver caminhos diferentes, o `git pull` pode ter dado conflito
nele. Mantenha os seus caminhos e as duas chaves novas da seção 4.3.

### 5.4 Garantir que os arquivos de entrada existem

```bash
ls -la dados/intermediario/inventario_volumes.csv
ls -la dados/intermediario/candidatos.csv
ls -la dados/intermediario/situacao_deteccao.csv
ls -la dados/intermediario/calibracao_log/resultados_por_exame.csv
```

O que esperar:

| Arquivo | Esperado | Se faltar |
|---|---|---|
| `inventario_volumes.csv` | existe, 888 linhas de exame | `.venv/bin/python scripts/02_inventario_volumes.py` |
| `candidatos.csv` | **1714804240** bytes | é a saída do T10; sem ela não dá para comparar. Não rode o `10` de novo sem conversar com o grupo: são horas. |
| `situacao_deteccao.csv` | existe, 888 linhas | também sai do `10`. Sem ele o `18` roda, mas não confere falhas. |
| `calibracao_log/resultados_por_exame.csv` | existe | sem ele o tempo da lista própria sai como "não registrado". Não rode a calibração de novo: o estágio está congelado de propósito. |

Para conferir o tamanho e a contagem de linhas da lista própria:

```bash
stat -c %s dados/intermediario/candidatos.csv
wc -l dados/intermediario/candidatos.csv
```

O `wc -l` tem que dar **14310043**, os 14.310.042 candidatos mais o cabeçalho. Se o tamanho ou a
contagem forem outros, a lista em disco não é a da rodada registrada. Pare e veja a seção 9.

---

## 6. Passo a passo para testar e rodar

Siga na ordem. Cada passo diz o que esperar.

### 6.1 Rodar os testes

```bash
.venv/bin/python -m pytest testes/test_comparacao_listas.py testes/test_candidatos.py -v
```

Tem que passar tudo: 9 testes do arquivo novo e os de `test_candidatos.py`. Depois a suíte
inteira:

```bash
.venv/bin/python -m pytest testes -q
```

Em 04/10/2026 a suíte passava em 103 testes, e na integração da PR #4 em 126 casos. Com os 9
novos, espere esse total mais 9, com zero falhas. Anote o número que aparecer, porque ele vai
para o histórico.

### 6.2 Conferir o que o DVC vai rodar

```bash
.venv/bin/dvc status
.venv/bin/dvc repro --dry --single-item comparar_propria_v2
```

O `--dry` só mostra o que faria, sem rodar nada. Ele tem que listar apenas o estágio
`comparar_propria_v2`. O `--single-item` é importante: sem ele, o DVC pode tentar refazer
estágios anteriores que ele considere desatualizados, incluindo a detecção, que leva horas.

### 6.3 Rodar a comparação

```bash
.venv/bin/dvc repro --single-item comparar_propria_v2
```

Isso roda `.venv/bin/python scripts/18_comparar_lista_propria_v2.py` e grava o hash das entradas
e saídas no `dvc.lock`. O comando direto dá no mesmo, mas não atualiza o lock:

```bash
.venv/bin/python scripts/18_comparar_lista_propria_v2.py
```

O tempo não foi medido. A parte mais lenta deve ser ler o `candidatos.csv` de 1,6 GiB. A busca
dos nódulos e o bootstrap são rápidos.

**Guarde a saída do terminal inteira**, por exemplo assim:

```bash
.venv/bin/dvc repro --single-item comparar_propria_v2 2>&1 | tee comparacao_t11.txt
```

O `comparacao_t11.txt` fica na raiz e não deve ser commitado. Ele serve para copiar os números
para a decisão.

### 6.4 O que a saída tem que mostrar

Na ordem em que aparece:

1. **`1186 nódulos anotados em 601 exames, de 888 no inventário`.** Qualquer outro número quer
   dizer que o `annotations.csv` ou o inventário não é o oficial.

2. **A conferência da entrada.** O esperado:

   | lista | lidos | fora | exames |
   |---|---|---|---|
   | `candidatos.csv (próprio)` | 14310042 | 0 | 888 |
   | `candidates_V2.csv` | 754975 | 0 | 888 |

   As colunas `com cand.` e `sem` dizem quantos exames têm algum candidato. Esses números ainda
   não foram medidos para nenhuma das duas listas. Anote.

3. **A linha `as duas listas medidas sobre os mesmos 888 exames e os mesmos 1186 nódulos`.**

4. **A tabela principal.** O esperado, pelo que já está medido:

   | lista | por exame | alcançados | cobertura | IC 95% | disco |
   |---|---|---|---|---|---|
   | própria | 16114,9 | 1158 de 1186 | 97,6% | 96,7% a 98,6% | 1635,4 MiB |
   | V2 | 850,2 | 1166 de 1186 | 98,3% | a medir | 68,7 MiB |

   O IC da lista própria tem que bater com o do T10, porque usa a mesma função, a mesma semente e
   o mesmo número de reamostras. O IC do V2 é número novo.

5. **As linhas do tempo.** O esperado para a lista própria é algo como
   `estimado: média de 33 exames da calibração, 27,0 s por exame`, porque a configuração
   `inicial` rodou em 21 exames de desenvolvimento e 12 de validação. Na tabela, a coluna tempo
   deve mostrar perto de 6,7 h. Para o V2: `pronta: vem do desafio e não é gerada aqui`.

6. **O cruzamento:**
   `dos 1186 nódulos: A pelas duas, B só pela própria, C só pelo V2, D por nenhuma`.
   As contas que têm que fechar: `A + B = 1158`, `A + C = 1166` e `A + B + C + D = 1186`. Se não
   fecharem, há erro. Pare e leve ao grupo.

7. **A união:** `a união das duas alcançaria N`, com `N = A + B + C`.

8. **Os diâmetros** dos nódulos alcançados por uma lista só.

### 6.5 Conferir que terminou

```bash
ls -la dados/intermediario/comparacao_propria_v2.csv dados/intermediario/alcance_por_nodulo_propria_v2.csv
.venv/bin/dvc status
git status
```

- Os dois CSV têm que existir.
- O `dvc status` não pode apontar o estágio `comparar_propria_v2` como alterado.
- O `git status` tem que mostrar o `dvc.lock` modificado, com o estágio novo. Os CSV não aparecem,
  porque `dados/intermediario/` fica fora do git.

---

## 7. Como ler os resultados

Os arquivos ficam em `dados/intermediario/`, fora do git, como todo dado gerado.

### 7.1 `comparacao_propria_v2.csv`

Uma linha por lista:

| Coluna | Conteúdo |
|---|---|
| `lista` | `candidatos.csv (próprio)` ou `candidates_V2.csv`. |
| `exames` | Exames do inventário, o denominador. Tem que ser 888 nas duas. |
| `pontos` | Candidatos dentro dos exames do inventário. |
| `por_exame`, `mediana_por_exame`, `minimo_por_exame`, `maximo_por_exame` | Candidatos por exame, contando zero para exame sem candidato. |
| `alcancados`, `nodulos`, `cobertura` | Nódulos alcançados, nódulos de referência e a fração. |
| `ic_inferior`, `ic_superior` | Intervalo de 95% por bootstrap de exame. |
| `bytes`, `bytes_por_candidato` | Tamanho do arquivo da lista em disco. |
| `segundos_geracao`, `origem_tempo` | Tempo para gerar a lista e de onde ele veio: medido, estimado ou pronta. |

### 7.2 `alcance_por_nodulo_propria_v2.csv`

Uma linha por nódulo de referência: `seriesuid`, `coordX`, `coordY`, `coordZ`, `diameter_mm`,
`alcancado_propria` e `alcancado_v2`. Para ver os nódulos que só a lista própria alcança:

```bash
.venv/bin/python -c "
import pandas as pd
n = pd.read_csv('dados/intermediario/alcance_por_nodulo_propria_v2.csv')
print(n[n.alcancado_propria & ~n.alcancado_v2])
print(n[~n.alcancado_propria & n.alcancado_v2])
"
```

### 7.3 Como **não** reportar esses números

- Não chame a cobertura de sensibilidade da FROC nem de resultado do modelo. Ela é teto.
- Não chame candidatos por exame de falso positivo por exame.
- Não chame o tempo da lista própria de medido enquanto a coluna `origem_tempo` disser
  "estimado".
- Reporte a cobertura sempre com o intervalo.
- Não use o cruzamento para escolher parâmetro do detector. Ele inclui os exames de teste.

---

## 8. Onde escrever os números depois da rodada

O projeto tem a regra de que todo número vem com a data e o script que o mediu ao lado.

1. **`docs/decisoes/0007-lista-de-candidatos-por-experimento.md`**:
   - na linha **Estado**, trocar por `decidido e verificado`, se as contas da seção 6.4 fecharam;
   - na tabela "As duas listas", trocar o "não registrado" do IC do V2 pelo intervalo medido;
   - na alternativa "Juntar as duas listas", trocar o parágrafo que diz que o cruzamento não foi
     medido pelos números A, B, C e D, a união e a data, com o comando
     `.venv/bin/dvc repro --single-item comparar_propria_v2`;
   - na seção "Como verificar", tirar a frase "Quando rodar na máquina com a base, os números do
     cruzamento entram aqui, com a data".

   **Se o cruzamento mudar a conclusão**, por exemplo se a lista própria alcançar muitos nódulos
   que o V2 perde, não reescreva a decisão. Leve ao grupo. Decisão que muda ganha registro novo
   que referencia a antiga, pela regra de `docs/decisoes/README.md`.

2. **`docs/historico-do-projeto.md`**: uma atualização nova com a data, o comando, o cruzamento e
   a contagem de testes da seção 6.1.

3. **`docs/criterios_inclusao_luna16.md`**, seção "A lista própria contra o V2": se quiser, uma
   frase com o cruzamento.

4. **Commit**: o `dvc.lock` e os documentos. Nunca os CSV de `dados/`.

5. **Trello**: marcar os itens da checklist do card e anexar o link da PR.

---

## 9. Problemas comuns

**`... não existe. A comparação precisa das duas listas`.** O arquivo da lista citado não está no
caminho. Para o V2, confira o HD e o `config.yaml` (passo 5.3). Para a lista própria, o
`candidatos.csv` do T10 não está em `dados/intermediario/` (passo 5.4).

**`N exames da lista própria em falha ou pendentes`.** O `situacao_deteccao.csv` tem exame sem
terminar. A rodada do T10 registrada não tinha falhas, então esse arquivo pode ser de outra
rodada. Confira com o passo 5.9 do `GUIA-T5-T10.md` antes de rodar qualquer coisa.

**`a situação da detecção não cobre os mesmos exames do inventário`.** O inventário ou a situação
foram regerados separadamente. Confira se os dois têm 888 linhas de exame.

**`lista com coordenada ausente ou infinita`.** O `candidatos.csv` está corrompido, por exemplo
por cópia interrompida. Confira o tamanho e a contagem de linhas (passo 5.4).

**`KeyError: 'comparacao_propria_v2'`.** O `config.yaml` não tem as chaves novas. Confira o
branch e se uma mudança local no config sobrescreveu as chaves (seção 4.3).

**`ModuleNotFoundError: No module named 'detection.comparacao'`.** O branch não está atualizado.
Rode `git pull` e confira que `src/detection/comparacao.py` existe.

**O processo morre ao ler o `candidatos.csv` (`Killed` ou `MemoryError`).** Falta memória. Feche
outros programas e rode de novo. Se continuar, avise: dá para ler o `seriesuid` como categoria e
economizar boa parte da memória, mas isso não foi feito para não mudar o código sem testar na base.

**O `dvc repro` quer rodar outros estágios.** Faltou o `--single-item`. Interrompa com Ctrl+C e
rode como no passo 6.3.

**O tempo da lista própria saiu como "não registrado".** O
`calibracao_log/resultados_por_exame.csv` não está na máquina. A comparação vale mesmo assim, mas
a decisão continua com a estimativa que já está escrita.

**A cobertura da lista própria não deu 1.158.** O `candidatos.csv` em disco não é o da rodada
registrada, ou o `annotations.csv` não é o oficial. Não escreva o número novo na decisão. Leve ao
grupo.

---

## 10. Lista de arquivos alterados

| Arquivo | O que mudou |
|---|---|
| `docs/decisoes/0007-lista-de-candidatos-por-experimento.md` | Novo. A comparação, a decisão por experimento, a alternativa descartada e as consequências. |
| `docs/decisoes/README.md` | A 0007 no índice. |
| `src/detection/comparacao.py` | Novo. Conferência da entrada, candidatos por exame, resumo e cruzamento. |
| `scripts/18_comparar_lista_propria_v2.py` | Novo. Refaz a comparação na base e mede o cruzamento. |
| `testes/test_comparacao_listas.py` | Novo. 9 testes. |
| `configuracao/config.yaml` | Chaves `comparacao_propria_v2` e `alcance_por_nodulo_propria_v2`. |
| `dvc.yaml` | Estágio `comparar_propria_v2`. O `dvc.lock` ainda não tem esse estágio. |
| `docs/criterios_inclusao_luna16.md` | Seção "A lista própria contra o V2" e o `18` em "Como verificar". |
| `docs/04-deteccao-de-candidatos.md` | Seção "A lista própria contra o V2". |
| `docs/07-dvc-mlflow.md` | O estágio novo na lista, e 17 estágios. |
| `docs/historico-do-projeto.md` | Atualização de 05/10/2026. |
| `README.md` | O `18` na receita e na tabela dos scripts, e a frase sobre a decisão 0007. |
| `GUIA-T11.md` | Este documento. |

Nenhum código existente foi alterado. O `alcancados`, a `cobertura`, o `10` e o `08` continuam
iguais.

---

## 11. O que ficou em aberto

1. **Rodar o `18` na base**, seguindo a seção 6, e escrever o cruzamento e o IC do V2 na decisão
   0007 (seção 8).
2. **Gravar o tempo por exame na rodada do detector.** O `10` só registra o tempo dos exames que
   falham, e por isso o custo da lista própria continua estimado pela calibração. A decisão 0007
   registra isso como consequência. É uma mudança pequena no `10`, mas que só vale para uma rodada
   nova.
3. **Reconfirmar com o grupo a decisão 0007**, como o card pede para decisões que fecham porta.
4. **Corte de escala na lista própria.** A decisão diz quando ela volta a ser candidata para os
   classificadores. Esse experimento não foi feito.
5. **Atualizar a contagem de testes do README e do histórico** na máquina com a base.
