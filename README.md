# PI3 Grupo 5: detecção de candidatos a nódulos pulmonares

O câncer de pulmão mata mais que qualquer outro câncer, e o problema não é a falta de
tratamento, é a demora do diagnóstico. 54% dos pacientes descobrem no estágio IV, quando
cerca de 5% sobrevivem cinco anos; quem descobre no estágio I tem cerca de 70%.

O sinal que apareceria cedo é o nódulo, uma estrutura de 3 a 30 mm dentro do pulmão, e ele
passa batido com facilidade: um radiologista olha de 300 a 500 exames por dia, cada exame com
300 a 500 fatias, algo perto de 250 mil imagens por dia.

Este repositório é a etapa de detecção: recebemos o pulmão já separado do resto da imagem e
entregamos os pontos suspeitos. Não classificamos benigno contra maligno.

**Nenhum modelo deste projeto deve ser aplicado a decisão clínica real.**

## Dataset

**LUNA16** (Lung Nodule Analysis 2016), derivado do LIDC-IDRI e já filtrado, com o critério de
inclusão e as dobras de validação definidos pelo próprio desafio.

| | |
|---|---|
| Exames | 888, os dez subsets completos |
| Nódulos anotados | 1.186 em 601 exames |
| Candidatos | 754.975 com 1.557 positivos, ou 0,2062%, do `candidates_V2` |
| Formato | MetaImage (`.mhd` mais `.raw`), um par por exame |
| Espaçamento entre fatias | de 0,45 a 2,5 mm, em dez valores distintos |
| Máscaras de pulmão | prontas, em `seg-lungs-LUNA16` |
| Avaliação | curva FROC, com o script oficial do desafio |

Os dados não estão neste repositório. Eles vêm do
[Zenodo](https://zenodo.org/records/3723295), em dois registros, e ficam fora do git.

O critério de inclusão é o do desafio e adotamos ele inteiro. O que ele deixa entrar, o que ele
corta e os quatro casos de fronteira que conferimos estão em `docs/criterios_inclusao_luna16.md`.

## Limitações declaradas

**Acurácia não serve como métrica aqui.** Os positivos são 0,2062% dos candidatos, então
responder sempre "não é nódulo" acerta 99,79% sem servir para nada. Usamos a curva FROC.

**A máscara de pulmão do desafio custa um nódulo.** Dos 1.186 anotados, um de 5 mm fica
inalcançável depois de aplicá-la, ou 0,08% com intervalo de 95% entre 0,00% e 0,25%. O
registro em `docs/decisoes/` traz a medição e o motivo de mesmo assim não dilatarmos.

## O que já funciona

Leitura do cabeçalho dos volumes e inventário dos 888 exames. Conversão entre coordenada de
mundo em milímetro e índice de voxel, com teste e figura de verificação. Análise exploratória
com cinco figuras. Pré-processamento de um volume: janela de HU, reamostragem para voxel
isotrópico e aplicação da máscara de pulmão.

Ainda não existem: extração de patches, baseline, modelo e avaliação FROC.

## Como reproduzir

Precisa de Python 3.12 ou mais novo e do LUNA16 em disco.

**1. Ambiente**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

No Ubuntu, se o `venv` reclamar, instale antes: `sudo apt install python3.12-venv`.

**2. Apontar para os dados**

Abra `configuracao/config.yaml` e ajuste `caminhos.luna16` para onde o LUNA16 está na sua
máquina. Todos os outros caminhos derivam dele. Nenhum caminho fica escrito dentro do código.

O zip do desafio extrai com a pasta repetida, `subset0/subset0/`, e o código conta com isso.
Os dez subsets são as dobras oficiais de validação cruzada, e é por isso que não inventamos
divisão nossa.

**3. Rodar, nesta ordem**

```bash
.venv/bin/python scripts/02_inventario_volumes.py
.venv/bin/python scripts/03_verificar_coordenadas.py
.venv/bin/python scripts/04_preprocessar.py
.venv/bin/python scripts/05_eda.py
.venv/bin/python scripts/07_preprocessar_base.py
```

| Script | O que produz |
|---|---|
| `02_inventario_volumes.py` | `dados/intermediario/inventario_volumes.csv`, uma linha por exame |
| `03_verificar_coordenadas.py` | as duas figuras que provam que a conversão de coordenada está certa |
| `04_preprocessar.py` | um volume pré-processado e a figura de antes e depois |
| `05_eda.py` | as cinco figuras da análise exploratória |
| `07_preprocessar_base.py` | os 888 volumes pré-processados e o relatório da rodada |

O `02` precisa rodar primeiro: os outros leem o inventário que ele grava.

O `07` demora. São 41 minutos e 8,6 GiB medidos em 08/09/2026, e ele aceita um número de exames
como argumento para uma rodada curta de teste.

Ou deixe o DVC cuidar da ordem, que é o mesmo pipeline declarado em `dvc.yaml`:

```bash
.venv/bin/dvc repro
```

Ele executa só os estágios cujo script, módulo ou parâmetro do `config.yaml` mudou desde a
última vez, e grava no `dvc.lock` o hash do que entrou e do que saiu. É assim que se sabe qual
versão do código produziu cada figura. O registro `docs/decisoes/0005` explica por que o dado
bruto fica fora desse grafo.

**4. Testes**

```bash
.venv/bin/python -m pytest testes -q
```

São 30 testes. Os que precisam abrir volume são pulados automaticamente se o disco com o
LUNA16 não estiver acessível, e escolhem sozinhos os extremos de espaçamento do inventário.

## Estrutura

```
src/
  preprocessing/     janela de HU, reamostragem, máscara de pulmão, coordenadas
  detection/         geração de candidatos, ainda vazia
  dataset/           leitura dos volumes do desafio
  visualization/     as figuras
  config.py          lê o config.yaml e fixa a semente
configuracao/        config.yaml, único lugar com caminhos e parâmetros
dados/               fora do git, é onde o pipeline escreve
modelos/             o peso fica fora do git, o registro fica no README
docs/                o que o grupo estabeleceu, incluindo os registros de decisão
notebooks/           análise exploratória
relatorios/figuras/  as figuras que vão para a apresentação e para o artigo
scripts/             executáveis, numerados na ordem de execução
testes/              pytest
```

A semente fica em `configuracao/config.yaml` e é fixada por `config.fixar_semente()` no
início de todo script.

## Metodologia

Adotamos o KDD (Fayyad, Piatetsky-Shapiro e Smyth, 1996), com as cinco etapas de seleção,
pré-processamento, transformação, mineração e interpretação. As decisões que fecham porta
ficam registradas em `docs/decisoes/`, uma por arquivo, com o número medido ao lado.

## O grupo

Kauan Felipe Nascimento da Silva, Náthaly Alessandra Batistella, Arthur Nicolas Oliveira,
Samuel Gonçalves Malta, Gabriel Schraider da Silveira, Lucas Gabriel Teixeira da Silva.

Projeto Integrador de Extensão III, Inteligência Artificial, Biopark, 2026/2.
