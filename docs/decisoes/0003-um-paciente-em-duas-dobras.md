# 0003: um paciente aparece em duas dobras do desafio

**Estado:** medido, tratamento em aberto
**Data:** 30/08/2026

## Contexto

A seção 3.1 do enunciado exige que treino, validação e teste sejam separados **por paciente,
nunca por imagem**, e diz que misturar imagens do mesmo paciente entre treino e teste vaza
informação e infla o resultado.

Adotamos os dez subsets do desafio como dobras de validação cruzada, para manter a comparação
com o ranking público válida. Isso funciona se cada subset contiver pacientes distintos dos
outros, e o `configuracao/config.yaml` afirmava que no LUNA16 cada `seriesuid` é um paciente.

Essa afirmação é falsa.

## O que medimos

O LUNA16 identifica o exame pelo `seriesuid` e **não diz quem é o paciente**. O único lugar
onde esse mapa existe é o metadata do LIDC-IDRI, de onde o LUNA16 foi derivado.

Extraímos o mapa uma vez, em 30/08/2026, com `scripts/01_pacientes.py`, e gravamos em
`dados/intermediario/pacientes.csv`, com 888 linhas. **Depois disso o LIDC-IDRI deixou de ser
necessário**, e nada no projeto volta a lê-lo. Os 888 exames casaram, nenhum ficou sem
correspondência.

| | |
|---|---|
| Exames | 888 |
| Pacientes distintos | 887 |
| Pacientes com mais de uma série | 1 |

**`LIDC-IDRI-0332` tem duas séries**, uma no subset 2 e outra no subset 6. Como os subsets são
as dobras, esse paciente cai em treino e em teste na mesma rodada nas duas em que o subset de
teste é o 2 ou o 6. Nas outras oito as duas séries ficam juntas no treino.

Nenhum outro paciente se repete.

## Por que isso importa mesmo sendo um caso

O efeito numérico é desprezível: um paciente em 887. O efeito de banca não é. A seção 3.1
nomeia esse erro por escrito, e afirmar no repositório que cada `seriesuid` é um paciente
quando não é seria errar exatamente onde o enunciado avisa.

Vale registrar também que o problema só apareceu com o desafio completo. Nos subsets 0 a 4,
medidos em 29/08, os 445 exames eram 445 pacientes distintos, sem uma colisão sequer.

## O que fica decidido agora

Registramos a exceção e corrigimos a afirmação falsa do `config.yaml`. O tratamento fica em
aberto até existir a divisão de fato, e as duas saídas são:

**Manter as dobras do desafio como estão** e declarar a exceção em todo resultado. Preserva a
comparação com o leaderboard, que é o motivo de usar as dobras dele.

**Mover as duas séries para a mesma dobra.** Elimina o vazamento e introduz uma diferença
nossa contra o baseline público, em uma dobra de 89 exames.

Não escolhemos ainda porque a divisão ainda não existe em código. A escolha entra aqui quando
entrar, com o número que a sustentar.

## Como verificar

```
.venv/bin/python -m pytest testes/test_divisao.py -v
```

O teste lê `dados/intermediario/pacientes.csv` e falha se algum paciente além do
`LIDC-IDRI-0332` aparecer em mais de uma dobra, se esse deixar de aparecer, ou se a tabela
deixar de cobrir os 888 exames.
