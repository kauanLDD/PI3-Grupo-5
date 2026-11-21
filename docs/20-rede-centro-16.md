# Rede de 16 voxels na validação

Medido em 20/11/2026, uma execução, semente 42, subsets 0 a 4 do LUNA16.

A variante `centro_16` é a CNN3D escolhida (`cnn_lr_3e-4`) com uma única mudança: a entrada é o
cubo central de 16 voxels do recorte de 34 guardado em disco, em vez do de 32. A ideia, do Lucas
(commit `26cde3b`), é tirar da entrada o vizinho que aparece ao redor do nódulo, porque a análise de
erros (docs/15) mostrou falsos positivos de nota alta perto de nódulos verdadeiros. Os outros
parâmetros são os da rede escolhida: 40 épocas, aumento de dados, 20 negativos por positivo,
learning rate 3e-4.

Comando, a partir do commit `b00b46a`:

```
.venv-cnn-gpu/bin/python scripts/18_treinar_cnn.py --variante centro_16 --saida modelos/cnn_centro_16 --escopo divisao_completa
```

Run do MLflow `bddab830988545fdb3e7dea8f5dee70d`. Treino na RTX 4050 com 23.058 candidatos V2 de
622 pacientes; a execução inteira, treino e previsão da validação, levou cerca de 7 minutos.
Avaliação com o programa oficial do LUNA16 nos 89 exames da validação, 1.000 reamostras de
bootstrap. O teste não foi usado.

| Rede | CPM (IC95%) | Sens. a 1 FP (IC95%) | Sens. a 4 FP (IC95%) |
|---|---|---|---|
| `cnn_lr_3e-4`, cubo de 32 | 0,752 (0,681 a 0,819) | 0,784 (0,699 a 0,870) | 0,883 (0,805 a 0,945) |
| `centro_16`, cubo de 16 | 0,758 (0,680 a 0,823) | 0,802 (0,714 a 0,879) | 0,883 (0,816 a 0,950) |

Fonte das linhas: `modelos/cnn_lr_3e-4/avaliacao_validacao/pontos_operacao.csv` e
`modelos/cnn_centro_16/avaliacao_validacao/pontos_operacao.csv`, com o CPM em `avaliacao.json` da
mesma pasta.

A diferença de CPM é 0,006. Os intervalos se sobrepõem quase inteiros. Com três sementes, a rede
de 32 variou entre 0,752 e 0,790 de CPM na validação (docs/14), uma faixa maior que essa diferença.
A `centro_16` tem uma semente só, então a variação dela entre sementes não foi medida.

O que esta medida não cobre: ela usa a lista V2. O efeito sobre as marcas vizinhas de nódulo na
nossa lista LoG, que é onde o problema apareceu (docs/19), não foi medido.

## As duas redes juntas

Medido em 21/11/2026, uma execução. A regra é a do cartão T26, fixada antes de qualquer resultado:
a nota final de cada candidato é a média simples da nota da rede de 32 e da rede de 16, sem peso e
sem outra variante testada. Não houve treino novo; o script lê as notas de validação que as duas
execuções do script 18 já tinham gravado, e confere que os 75.063 candidatos dos 89 exames são os
mesmos, na mesma ordem, nas duas.

```
.venv-cnn-gpu/bin/python scripts/40_combinar_redes.py
```

| Rede | CPM (IC95%) | Sens. a 1 FP (IC95%) | Sens. a 4 FP (IC95%) |
|---|---|---|---|
| `cnn_lr_3e-4`, cubo de 32 | 0,752 (0,681 a 0,819) | 0,784 (0,699 a 0,870) | 0,883 (0,805 a 0,945) |
| `centro_16`, cubo de 16 | 0,758 (0,680 a 0,823) | 0,802 (0,714 a 0,879) | 0,883 (0,816 a 0,950) |
| Média das duas | 0,837 (0,769 a 0,898) | 0,874 (0,794 a 0,938) | 0,919 (0,864 a 0,967) |

Fonte da última linha: `relatorios/experimentos/combinacao_redes/r32_r16/pontos_operacao.csv` e
`avaliacao.json` da mesma pasta. As notas completas ficam em
`dados/intermediario/combinacao_redes/r32_r16/`, fora do git. Rodamos o script duas vezes e o resultado foi idêntico.

O CPM da média ficou acima do maior valor que a rede de 32 teve entre as três sementes (0,790,
docs/14). A correlação de Spearman entre as notas das duas redes, em todos os candidatos da
validação, foi 0,44; nos 120 candidatos positivos foi 0,88 (calculada sobre
`dados/intermediario/combinacao_redes/r32_r16/probabilidades_validacao.csv`).

## Controle: duas redes de 32

Medido em 21/11/2026, uma execução, pelo mesmo comando acima. Para separar o ganho do cubo de 16 do
ganho de juntar duas redes, fixamos depois de ver a média 32 mais 16, e antes de ver qualquer
outro par, que mediríamos os três pares possíveis da rede de 32 com sementes diferentes (docs/14),
com a mesma média simples.

| Par | CPM (IC95%) | Sens. a 1 FP | Sens. a 4 FP |
|---|---|---|---|
| 32 semente 42 + 16 semente 42 | 0,837 (0,769 a 0,898) | 0,874 | 0,919 |
| 32 semente 42 + 32 semente 43 | 0,790 (0,730 a 0,859) | 0,829 | 0,901 |
| 32 semente 42 + 32 semente 44 | 0,801 (0,732 a 0,855) | 0,829 | 0,901 |
| 32 semente 43 + 32 semente 44 | 0,806 (0,738 a 0,867) | 0,838 | 0,901 |

Fonte: `relatorios/experimentos/combinacao_redes/pares.csv` e a subpasta de cada par.

Sozinhas, as redes de 32 com sementes 43 e 44 têm CPM 0,790 cada uma, e a de 42 tem 0,752. Os
dois pares que contêm a semente 42, como o par 32 mais 16, ficaram em 0,790 e 0,801. O par 32 mais
16 ficou 0,036 a 0,047 acima deles e 0,031 acima do melhor par de 32. Os intervalos de todos os
pares se sobrepõem. Não calculamos o intervalo pareado da diferença entre pares, e o cubo de 16 tem
uma semente só, então não medimos a variação dele entre sementes.

A medida usa a lista V2, não a nossa lista LoG, e o teste não foi usado.
