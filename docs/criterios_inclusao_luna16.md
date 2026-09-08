# Critérios de inclusão

Quais exames e quais nódulos entram no estudo, e por quê. Medido em 03/09/2026 sobre a cópia
do LUNA16 em disco, com `scripts/02_inventario_volumes.py` e leitura direta dos CSV do desafio.

## A regra é do desafio, e adotamos inteira

O LUNA16 já é o LIDC-IDRI filtrado. Os organizadores descartaram exames com fatia mais grossa
que 2,5 mm, descartaram achados menores que 3 mm, e só chamaram de nódulo o que **pelo menos
três dos quatro radiologistas** marcaram. De 1.010 pacientes do LIDC sobraram 888 exames.

Adotamos esse critério integralmente, sem acrescentar filtro nosso.

O motivo não é preguiça. Todo trabalho que publica número no LUNA16 mede sobre exatamente esses
888 exames e esses 1.186 nódulos. Filtrar diferente seria medir outra coisa e chamar pelo mesmo
nome, e perderíamos a comparação com o ranking público, que é o motivo de termos escolhido esta
base. É a mesma razão de não segmentarmos pulmão e de não escrevermos curva FROC própria.

## O que entra

| | |
|---|---|
| Exames | 888, os dez subsets completos |
| Pacientes | 887, porque um tem duas séries |
| Nódulos de referência | 1.186, em 601 exames |
| Exames sem nódulo elegível | 287, e entram na avaliação mesmo assim |
| Lista de candidatos | `candidates_V2.csv`, com 754.975 pontos |

Os dez subsets são as dobras oficiais de validação cruzada do desafio. Não inventamos divisão
nossa.

## Os casos de borda

Quatro situações precisaram de decisão explícita porque contrariam, à primeira vista, o próprio
critério do desafio.

### Dois exames aparentam ter fatia acima de 2,5 mm

O cabeçalho de `1.3...2873394709` e `1.3...0416228517` traz espaçamento em z de
`2.500000238418579`. É a representação em float32 do número 2,5. Arredondando para quatro casas,
**nenhum exame dos 888 passa de 2,5 mm**.

Não são exceção ao critério, são ruído de precisão. Entram normalmente, e comparações com o
limite de 2,5 mm no nosso código usam tolerância em vez de igualdade exata.

### Dois nódulos passam de 30 mm

São de 30,61 mm e 32,27 mm. A definição clínica de nódulo vai até 30 mm, e acima disso o achado
chama massa. O desafio incluiu os dois assim mesmo, e eles constam do `annotations.csv`.

Mantemos os dois. Sair deles seria divergir da lista de referência contra a qual todo mundo é
avaliado. O de 32,27 mm tem consequência prática: ele não cabe num recorte de 32 voxels a 1 mm
isotrópico, o que obriga o recorte a ser de 34.

### Um paciente aparece em duas dobras

`LIDC-IDRI-0332` tem duas séries, uma no subset 2 e outra no subset 6. Como os subsets são as
dobras, esse paciente cai em treino e em teste na mesma rodada.

Está medido e registrado em `docs/decisoes/0003-um-paciente-em-duas-dobras.md`, com o tratamento
ainda em aberto. Não é critério de inclusão: os dois exames entram, e o que falta decidir é como
a divisão os trata.

### Qual lista de candidatos usar

O desafio entrega duas, e a escolha muda o teto do que conseguimos alcançar. Medimos as duas
contra os 1.186 nódulos de referência:

| Lista | Pontos | Positivos | Por exame | Nódulos alcançados | Teto |
|---|---|---|---|---|---|
| `candidates.csv` | 551.065 | 1.351 | 621 | 1.120 de 1.186 | 94,4% |
| `candidates_V2.csv` | 754.975 | 1.557 | 850 | 1.166 de 1.186 | **98,3%** |

**Adotamos o `candidates_V2.csv`.** Ele alcança 46 nódulos a mais, subindo o teto de 94,4% para
98,3%, ao custo de 37% mais pontos para classificar.

Os 850 candidatos por exame e a cobertura de 98,3% que medimos batem com o que Setio et al.
(2017) descrevem para a lista combinada do desafio, o que indica que o V2 é essa lista. A
correspondência é leitura do artigo, não medição nossa. Ela é a entrada da trilha
de redução de falsos positivos, que é o que a seção 4.3 do enunciado descreve para o nosso
baseline.

Vinte nódulos continuam sem nenhum candidato em cima, mesmo no V2. Esses são inalcançáveis por
qualquer método que use só a lista pronta, e são o argumento para gerarmos candidatos próprios
na etapa de Transformação.

## O que fica fora da conta na avaliação

O `annotations_excluded.csv` traz 35.192 achados espalhados pelos 888 exames: nódulo abaixo do
critério, achado não nodular, e anotação com concordância insuficiente.

Candidato que casa com um deles **não é acerto nem alarme falso: sai da conta**. Ignorar isso
infla o número de falso positivo e o resultado deixa de ser comparável com qualquer publicação.

## Como verificar

```
.venv/bin/python scripts/02_inventario_volumes.py
.venv/bin/python -m pytest testes -q
```

O inventário imprime a contagem por subset, a distribuição de espaçamento em z e quantos exames
passam de 2,5 mm. A suíte confere a divisão por paciente.
