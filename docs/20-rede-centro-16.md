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

## As duas redes na nossa lista, medido em 28/11/2026

Repetimos a média das duas redes na nossa lista (LoG), com a supressão suave linear a 16 mm do
sistema final aplicada depois da média. A rede de 16 pontuou a nossa lista na validação; as notas
da rede de 32 são as que o script 31 gravou. O desenho e a regra de leitura foram escritos no
`config.yaml` (seção `combinacao_redes_lista_propria`) antes de rodar. O teste não foi usado.

```bash
.venv-cnn-gpu/bin/python scripts/42_combinar_redes_lista_propria.py
```

Exames lidos 89, com erro 0, descartados 0; 111 nódulos; 1.407.860 pontos pontuados na GPU em 84 s.
O recorte de 16 feito na hora, conferido contra as notas da V2 gravadas pela rede de 16 em 3 exames,
deu diferença máxima de 2,98e-08. A rede de 32 com supressão reproduziu o CPM gravado em
`relatorios/experimentos/supressao_suave/validacao.csv` (linear, semente 42). Avaliador oficial,
1.000 reamostras por exame com semente 42.

| Versão, todas com supressão suave a 16 mm | CPM (IC95%) | Sens. a 0,125 FP | Sens. a 1 FP | Sens. a 4 FP |
|---|---:|---:|---:|---:|
| Rede de 32 (sistema final) | 0,745 (0,651 a 0,820) | 0,541 | 0,784 | 0,847 |
| Rede de 16 | 0,764 (0,687 a 0,838) | 0,568 | 0,802 | 0,874 |
| Média das duas | 0,833 (0,762 a 0,896) | 0,712 | 0,856 | 0,892 |

Diferença pareada de CPM contra a rede de 32: +0,019 (IC95% -0,039 a +0,105) para a rede de 16 e
+0,088 (+0,037 a +0,161) para a média, que ficou acima em 99,9% das reamostras. Pela regra fixada,
só a média fica registrada como acima da rede de 32.

Falsos positivos entre as 100 marcas de cada exame a até 16 mm do centro de um nódulo (cartão T27):

| Versão | Falsos positivos nas 100 marcas | A até 16 mm de um nódulo | Nódulos com marca nas 100 |
|---|---:|---:|---:|
| Rede de 32 | 8.362 | 433 | 97 de 111 |
| Rede de 16 | 8.354 | 87 | 101 de 111 |
| Média das duas | 8.314 | 304 | 101 de 111 |

As tabelas estão em `relatorios/experimentos/combinacao_redes_lista_propria/` (`versoes.csv`,
`diferencas_pareadas.csv`, `vizinhos_de_nodulo.csv`, `resumo.json`, e a avaliação de cada versão
numa subpasta). As notas de cada ponto ficam fora do git, em
`dados/intermediario/combinacao_redes_lista_propria/`.

**O que os números não mostram.** É a validação, com uma semente de cada rede e uma execução. A
média não faz parte do sistema final, que foi ao teste pela decisão 0013, e não foi medida no teste.
