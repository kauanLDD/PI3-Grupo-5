# 0010: a rede escolhida repetida com mais duas sementes, só na validação

**Estado:** decidido antes de treinar; treinos executados em 26/10/2026
**Data:** 26/10/2026

## Contexto

O resultado da `cnn_lr_3e-4` vem de um único treino, com semente 42. Não sabemos quanto do CPM
de validação, 0,752, é da configuração e quanto é da semente: a semente decide a amostra de
negativos, a ordem dos lotes, o aumento de dados e os pesos iniciais. O intervalo do bootstrap
por exame não responde isso, porque mede a incerteza de amostragem dos exames com o modelo fixo.

## Decisão

**Treinamos a mesma configuração com as sementes 43 e 44, fixadas agora, e medimos as três só
na validação.** As sementes estão em `sementes_cnn` no `config.yaml` e não mudam depois de ver o
resultado. Nenhuma das novas redes vai ao teste, nem substitui a rede congelada pela decisão
0008: o objetivo é medir estabilidade, não escolher modelo.

Fica igual ao treino original, porque vem da variante `lr_3e-4` do YAML: arquitetura
`CNN3D_3conv_16_32_64`, recortes V2 de 34 voxels cortados para 32, normalização [0, 1], mesma
divisão (`divisao.csv`), 40 épocas, batch 32, Adam com learning rate 0,0003 e weight decay
0,00001, dropout 0,3, entropia cruzada, 20 negativos por positivo, `WeightedRandomSampler` com
reposição, aumento de dados ligado, GPU com determinismo parcial (decisão 0007).

Muda só a semente de treino. O script 18 ganhou `--semente`; sem a opção, o comportamento é o
de antes. A semente do bootstrap do avaliador oficial continua 42 (`seed_avaliacao` no run), para
as três redes serem medidas nas mesmas 1.000 reamostras dos mesmos 89 exames.

O protocolo não escolhe época: o checkpoint é sempre o da época 40, e a validação não é
consultada durante o treino. A "melhor época" de cada semente é, portanto, a 40.

O que reportamos, por `scripts/28_resumir_sementes_cnn.py`: CPM e as sete sensibilidades de
cada semente, média, desvio padrão amostral (n − 1), mínimo, máximo e amplitude do CPM. O script
recusa juntar sementes cuja configuração ou dados difiram da original.

## Como executar

Na máquina com o LUNA16, os recortes em `dados/processado/patches` e a RTX 4050:

```bash
.venv-cnn-gpu/bin/python scripts/18_treinar_cnn.py --variante lr_3e-4 --semente 43 --saida modelos/cnn_lr_3e-4_semente_43
.venv-cnn-gpu/bin/python scripts/18_treinar_cnn.py --variante lr_3e-4 --semente 44 --saida modelos/cnn_lr_3e-4_semente_44
.venv/bin/python scripts/28_resumir_sementes_cnn.py
```

Cada treino levou cerca de 1.300 segundos na GPU na semente 42 (`docs/11-experimentos-validacao.md`).

## O que descartamos

**Treinar de novo a semente 42 junto.** Na GPU o PyTorch não garante pesos idênticos (decisão
0007); a semente original já tem resultado registrado e é ela que entra na tabela.

**Variar também a amostra de negativos com uma semente separada, ou fixá-la.** A semente única
é o que o protocolo usa desde o início; separar as fontes de variação seria outro experimento.

**Avaliar as três sementes no teste.** Seria o terceiro, quarto e quinto uso do teste, e a
tentação de reportar a melhor.

## Consequências

Três sementes dão uma estimativa grosseira da variação: o desvio padrão de três valores é
instável, e reportamos também mínimo e máximo. Variação entre sementes, intervalo de confiança
do bootstrap e desvio padrão são três coisas diferentes e aparecem separadas no relatório.

`scripts/18_treinar_cnn.py` é dependência dos estágios `treinar_cnn` e
`treinar_cnn_variante@*` do DVC. Como sem `--semente` o comportamento não muda, esses estágios
devem ser registrados com `dvc commit -f` na máquina que tem os dados, em vez de reexecutados,
como em `docs/11-experimentos-validacao.md`. Isso ainda não foi feito.

## Resultado

Executado pelo Kauan em 26/10/2026 na RTX 4050, cerca de 940 s de treino por semente. O script 28
aceitou as três pastas sem diferença de configuração. CPM na validação: 0,752 (42), 0,790 (43) e
0,790 (44); média 0,777, desvio padrão amostral 0,022, amplitude 0,039, menor que a largura do
IC95% de cada semente. Detalhes e leitura em `docs/14-baseline-literatura-sementes-e-teste-rf.md`,
seção 4.
