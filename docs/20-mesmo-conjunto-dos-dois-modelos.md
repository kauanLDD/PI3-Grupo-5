# A rede e o Random Forest usam os mesmos candidatos? 09/11/2026

Pedido do professor no feedback da Sprint 4: responder com números se o Random Forest e a rede
usam os mesmos candidatos, e mostrar que nenhum paciente aparece em mais de um conjunto (T21).

Não treinamos, não pontuamos e não avaliamos nada de novo. O script só lê o que os treinos e as
avaliações já gravaram: a divisão congelada junto da rede escolhida, a lista de treino da rede e as
previsões dos dois modelos na validação e no teste. O teste não é usado de novo: as previsões do
teste são as gravadas em 13/10/2026 (rede, decisão 0008) e em 26/10/2026 (Random Forest centro,
decisão 0009).

Todos os números deste documento foram medidos em 09/11/2026 com:

```bash
.venv/bin/python scripts/38_conferir_mesmo_conjunto.py
.venv/bin/python -m pytest -q testes/test_mesmo_conjunto.py testes/test_divisao.py
```

As saídas ficam em `relatorios/experimentos/mesmo_conjunto/` (`divisao.csv`, `contagens.csv`,
`comparacao_pontos.csv`, `resumo.json`). Os arquivos lidos estão na seção `mesmo_conjunto` do
`configuracao/config.yaml`.

## 1. A resposta

**Na validação e no teste, sim:** os dois modelos dão nota exatamente aos mesmos candidatos, ponto a
ponto. **No treino, não:** a rede treina com uma amostra da lista que o Random Forest usa inteira.
Nos três conjuntos os exames e os pacientes são os mesmos para os dois modelos, e nenhum paciente
aparece em mais de um conjunto.

## 2. A divisão por paciente

Lida de `modelos/cnn_lr_3e-4/divisao.csv`, a divisão congelada junto da rede escolhida. As três
cópias versionadas (sementes 42, 43 e 44) têm o mesmo sha256, `45b22b5e1d546841...`.

| Conjunto | Subsets | Exames | Pacientes | Paciente com mais de uma série |
|---|---|---:|---:|---|
| Treino | 0 a 6 | 623 | 622 | LIDC-IDRI-0332, as duas séries no treino |
| Validação | 7 | 89 | 89 | nenhum |
| Teste | 8 e 9 | 176 | 176 | nenhum |
| **Total** | | **888** | **887** | |

**Como conferimos.** Agrupamos a divisão por paciente e contamos em quantas partições cada um
aparece (`pacientes_em_mais_de_um_conjunto` no script 38, a mesma conta que `cnn.conferir_divisao`
faz antes de todo treino). Encontramos: 0 exames repetidos e 0 pacientes em mais de um conjunto. O
único paciente com duas séries, o LIDC-IDRI-0332 (decisão 0003), tem as duas no treino.

Os testes de `testes/test_divisao.py` fazem a mesma conferência sobre o mapa de pacientes do
LIDC-IDRI (`dados/intermediario/pacientes.csv`), que só existe na máquina com a base. Nesta máquina
eles rodaram assim: 3 passaram (os que montam divisões de exemplo e conferem que um paciente
repetido é recusado) e 5 foram pulados por falta do `pacientes.csv`. Por isso acrescentamos em
`testes/test_mesmo_conjunto.py` um teste que roda sem a base, sobre a divisão versionada, e confere
0 pacientes em dois conjuntos e as contagens da tabela acima. Ele passou.

## 3. Contagens por conjunto e por modelo

| Conjunto | Modelo | Exames | Pacientes | Candidatos | Positivos | Negativos | De onde |
|---|---|---:|---:|---:|---:|---:|---|
| Treino | Rede | 623 | 622 | 23.058 | 1.098 | 21.960 | `cnn_lr_3e-4/candidatos_treino.csv` |
| Treino | Random Forest | 623 | 622 | 529.500 | 1.098 | 528.402 | `random_forest_centro/execucao.json` |
| Validação | Rede | 89 | 89 | 75.063 | 120 | 74.943 | `cnn_lr_3e-4/probabilidades_validacao.csv` |
| Validação | Random Forest | 89 | 89 | 75.063 | 120 | 74.943 | `random_forest_centro/probabilidades_validacao.csv` |
| Teste | Rede | 176 | 176 | 150.412 | 339\* | 150.073\* | `cnn_lr_3e-4_teste_final/predicoes.csv` |
| Teste | Random Forest | 176 | 176 | 150.412 | 339\* | 150.073\* | `random_forest_centro_teste_final/probabilidades_teste.csv` |

\* Os arquivos do teste gravados no git não têm o rótulo de cada candidato, e a lista V2 não estava
nesta máquina. Os 339 positivos e 150.073 negativos são os do dossiê (`docs/13`, seção 5), medidos
sobre a V2; o total, 150.412, bate com o que contamos aqui. O script deixa essas duas células vazias
em `contagens.csv` em vez de copiar o número.

Os positivos são candidatos, não nódulos: um nódulo pode ter mais de um candidato em cima. Na
validação os 120 candidatos positivos correspondem a 111 nódulos avaliados; no teste, 339 a 223.

## 4. Ponto a ponto

| Conjunto | Chave | Só na rede | Só no Random Forest | Nos dois |
|---|---|---:|---:|---:|
| Validação | `candidate_id` | 0 | 0 | 75.063 |
| Validação | exame e coordenadas | 0 | 0 | 75.063 |
| Teste | exame e coordenadas | 0 | 0 | 150.412 |

Na validação as duas listas têm o `candidate_id` da V2, e conferimos também exame e coordenadas. No
teste a lista da rede não tem `candidate_id`, então comparamos por exame e coordenadas; nenhum ponto
se repete em nenhuma das duas listas. Os rótulos de validação do Random Forest saem da lista da rede
pelo `candidate_id`, e os 75.063 casam.

## 5. Por que o treino é diferente

O Random Forest treina com todos os candidatos V2 dos 623 exames de treino: 529.500, dos quais
1.098 positivos (`scripts/25_treinar_random_forest_centro.py`, com pesos `balanced`). A rede treina
com os mesmos 1.098 positivos e um sorteio fixo de 20 negativos por positivo, 21.960, com semente 42
(`docs/13`, seção 9). Os 23.058 `candidate_id` da rede são todos de exames de treino e não se
repetem.

Que esses 23.058 estão dentro dos 529.500 do Random Forest decorre de os dois saírem da mesma
lista V2 nos mesmos exames, mas não conferimos ponto a ponto: a lista de treino do Random Forest
(`dados/intermediario/caracteristicas_centro/treino.csv`) fica fora do git. Rodado na máquina que
tem esse arquivo, o script 38 faz a comparação do treino também e grava o resultado em
`resumo.json` (`treino_rede_dentro_do_random_forest`); nesta execução o campo ficou `null`.

## 6. O que os números mostram e o que não mostram

**Mostram** que a comparação entre os dois modelos na validação (`docs/10`) e no teste (`docs/14`)
é feita sobre os mesmos exames e os mesmos candidatos, e que nenhum paciente do treino está na
validação ou no teste.

**Não mostram** que os dois modelos aprenderam com o mesmo material: a rede viu 4,4% dos
candidatos de treino que o Random Forest viu, com a mesma quantidade de positivos. A diferença de
desempenho entre eles inclui essa diferença de amostragem, além da diferença de modelo.
