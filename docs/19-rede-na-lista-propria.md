# A rede escolhida na nossa lista de candidatos, 01/11/2026

Pedido do professor na pré-banca e de novo no feedback da Sprint 4: a FROC com a lista de
candidatos que nós geramos por LoG (`docs/04`), e não só com a lista V2 que o desafio entrega.

Aplicamos a rede escolhida, `cnn_lr_3e-4`, congelada e sem treino novo, aos candidatos da nossa
lista nos 89 exames de validação (111 nódulos), e avaliamos com o avaliador oficial do LUNA16. A
rede foi treinada só com candidatos da V2. O teste não foi usado.

Todos os números deste documento foram medidos em 01/11/2026 com:

```bash
.venv-cnn-gpu/bin/python scripts/31_avaliar_lista_propria_cnn.py
```

As saídas versionadas ficam em `relatorios/experimentos/lista_propria_cnn/` (resumo em
`resumo.json`). As 1.407.860 marcas e as avaliações completas ficam fora do git, em
`dados/intermediario/lista_propria_cnn/`. As anotações e a lista V2 vieram de uma cópia local com
o mesmo md5 do `dvc.lock`, porque o HD estava desligado.

## 1. Como avaliamos

A nossa lista tem mediana de 15.625 candidatos por exame na validação, contra 763 da V2. Os cubos
dela não estão em disco: o script recorta cada cubo de 32 mm na hora, do volume pré-processado,
convertendo a coordenada em mm pela origem e pelo espaçamento de cada exame
(`src/detection/recorte.py`, função `recortar`, com testes em `testes/test_patches.py`).

Antes de pontuar a nossa lista, o script recorta na hora os candidatos da V2 de 3 exames e compara
com as probabilidades já gravadas a partir dos cubos em disco. A maior diferença foi 3,0e-08, e o
script para se passar de 1e-05.

Avaliamos duas versões, fixadas antes de rodar:

- **Lista inteira**, como o LoG entrega.
- **Lista com supressão de vizinhos**: em cada exame, do maior escore para o menor, a marca a até
  5 mm de uma marca mantida sai (`suprimir_vizinhos` em `src/detection/candidatos.py`). Os dois
  nódulos anotados mais próximos de um mesmo exame estão a 5,92 mm um do outro (`annotations.csv`,
  medido em 01/11/2026), então essa supressão não junta dois nódulos verdadeiros. Sobram 731.745
  marcas, mediana de 8.150 por exame.

O avaliador guarda as 100 marcas de maior escore de cada exame, como em todas as nossas avaliações.

## 2. Resultado

| Lista | CPM (IC95%) | Sens. a 1 FP | Sens. a 4 FP (IC95%) | Nódulos achados entre as 100 marcas |
|---|---:|---:|---:|---:|
| V2 do desafio | 0,752 (0,681 a 0,819) | 0,784 | 0,883 (0,805 a 0,945) | 107 de 111 |
| Nossa, inteira | 0,465 (0,400 a 0,532) | 0,441 | 0,712 (0,621 a 0,790) | 100 de 111 |
| Nossa, com supressão | 0,481 (0,424 a 0,555) | 0,459 | 0,730 (0,659 a 0,827) | 100 de 111 |

Os sete pontos com IC95% estão em `pontos_operacao.csv` de cada versão, e a figura em `froc.png`.

Diferença pareada de CPM contra a V2, nas mesmas 1.000 reamostras de exames do avaliador oficial:
-0,287 (IC95% -0,345 a -0,225) para a lista inteira e -0,270 (-0,318 a -0,203) para a lista com
supressão. Em nenhuma reamostra a nossa lista ficou acima da V2. A diferença entre as duas versões
da nossa lista (0,016 no CPM) fica dentro dos intervalos de cada uma.

A distância é maior com poucos falsos positivos: a 0,125 FP por exame, 0,144 contra 0,505 da V2; a
8 FP, 0,829 (com supressão) contra 0,892.

## 3. Cobertura das listas na validação

Quantos dos 111 nódulos têm ao menos um candidato dentro do raio, antes de qualquer escore (mesmo
critério de `docs/04`, `alcancados` em `src/detection/candidatos.py`):

| Lista | Nódulos com candidato | Cobertura (IC95%) |
|---|---:|---:|
| V2 | 109 | 0,982 (0,956 a 1,000) |
| Nossa, inteira e com supressão | 106 | 0,955 (0,909 a 0,992) |

## 4. O que os números mostram e o que não mostram

A cobertura da nossa lista é próxima da V2 (106 contra 109 nódulos), mas a sensibilidade com
poucos falsos positivos é muito menor. Com a V2 a rede põe 107 nódulos entre as 100 marcas de cada
exame; com a nossa, 100.

Inferência, não medida: a rede aprendeu a separar nódulo de não nódulo entre os candidatos da V2,
e a nossa lista traz cerca de 20 vezes mais candidatos, de tipos que a rede não viu no treino. Com
16 mil candidatos por exame, basta uma fração pequena receber escore alto para empurrar o nódulo
para baixo no ranking do exame. Em 01/11 não tínhamos medido quais candidatos da nossa lista
recebem escore alto; a seção 5 faz isso. A rede não foi treinada com eles.

Os números são da validação, o mesmo conjunto em que a rede foi escolhida entre as variantes
(`docs/11`), e de uma lista que a rede nunca viu.

## 5. Quem passa na frente dos nódulos, medido em 07/11/2026

Comando: `.venv-cnn-gpu/bin/python scripts/32_intrusos_lista_propria.py`. Lê as notas que o script 31
gravou, sem pontuar nada de novo. Exames lidos 89, com erro 0, descartados 0; máscaras de pulmão do
desafio lidas 89. Saídas em `relatorios/experimentos/intrusos_lista_propria/` (`intrusos_por_faixa.csv`,
`nodulos.csv`, `resumo.json`, `intrusos.png`); a medida de cada ponto fica em
`dados/intermediario/intrusos_lista_propria/`.

Chamamos de intruso de um nódulo todo falso positivo do mesmo exame com nota maior que a do melhor
candidato dentro do raio daquele nódulo. Um falso positivo conta uma vez só. Faixas e tamanho da
amostra foram escritos no `config.yaml` (seção `intrusos`) antes da primeira execução. Depois dela
acrescentamos, sem mudar a definição nem as faixas, o recorte dos intrusos que entram nas 100 marcas
de maior nota de cada exame, a distância do melhor acerto ao centro do nódulo e a contagem de
intrusos com nódulo dentro do cubo; o `resumo.json` lista esses acréscimos.

| | Nossa lista | V2 |
|---|---:|---:|
| Intrusos | 14.251, em 27 exames | 763, em 16 exames |
| Nódulos com ao menos um intruso | 43 | 26 |
| Intrusos entre as 100 marcas de cada exame | 699 | 321 |
| Intrusos nas 100 com nódulo a até 16 mm | 265 de 699 (0,379) | 23 de 321 (0,072) |
| Intrusos nas 100 com nota 0,9 ou mais e nódulo a até 16 mm | 262 de 509 | 15 de 84 |

Os intrusos se concentram em poucos nódulos: um nódulo de 4,96 mm responde por 11.221 dos 14.251,
e três nódulos por 93%. Esse nódulo tem melhor candidato com nota 0,002 na nossa lista, a 2,3 mm do
centro, e 0,823 na V2, a 1,1 mm. Somando todos os nódulos com candidato nas duas listas (105), a
distância mediana do melhor candidato ao centro é a mesma, 0,65 mm na nossa e 0,66 mm na V2.

Por faixa, proporção de cada grupo (contagens em `intrusos_por_faixa.csv`; a amostra de falsos
positivos comuns tem 2.000 pontos sorteados com semente 42 entre os que não são intrusos):

| Faixa | Intrusos | Intrusos nas 100 | Acertos | Falsos positivos comuns |
|---|---:|---:|---:|---:|
| Raio do LoG 1,7 (menor escala) | 0,968 | 0,911 | 0,556 | 0,973 |
| Borda a até 3 mm | 0,634 | 0,435 | 0,414 | 0,638 |
| Borda acima de 10 mm | 0,289 | 0,449 | 0,361 | 0,278 |
| Nódulo a até 10 mm | 0,008 | 0,122 | 0,911 | 0 |
| Nódulo de 10 a 30 mm | 0,040 | 0,318 | 0,089 | 0,015 |
| Exame sem nódulo | 0 | 0 | 0 | 0,374 |

Nenhum ponto da nossa lista cai fora da máscara de pulmão; na V2, 90 dos 763 intrusos caem.

**O que a tabela mostra.** Pelo raio do LoG e pela distância à borda, o conjunto inteiro de intrusos
tem o mesmo perfil dos falsos positivos comuns: 97% na menor escala e cerca de 63% a até 3 mm da
parede. Quem difere são os acertos, com 44% fora da menor escala. Entre os intrusos que entram nas
100 marcas, que são os que mexem na FROC, 38% têm um nódulo verdadeiro a até 16 mm, metade do lado do
cubo de 32 mm que a rede vê, contra 7% na V2. Nos doze de maior nota (`intrusos.png`) o nódulo
aparece dentro do recorte, ao lado da marca, a 8 a 14 mm dela.

**O que a tabela não mostra.** Ela não diz por que a rede dá nota alta a esses pontos.
Inferência, não medida: a rede responde à presença de um nódulo em qualquer lugar do cubo, e não só
no centro, porque entre os candidatos da V2 do treino há poucos pontos a alguns milímetros de um
nódulo sem estar sobre ele. A contagem de intrusos depende de poucos nódulos, então as proporções da
primeira coluna descrevem sobretudo três exames. Os números são da validação, uma execução, e não
foram conferidos no treino.

## 6. A rede treinada também com pontos da nossa lista, desenho fixado em 07/11/2026

Escrito antes de treinar. A configuração está no `config.yaml`, seção `treino_lista_propria`.

Treinamos de novo a variante `lr_3e-4`, com os mesmos hiperparâmetros (cubo de 32, lote 32, 40
épocas, Adam a 0,0003, dropout 0,3, aumento ligado, semente 42). Só muda o conjunto de treino, montado
nos 623 exames de treino:

- **Positivos:** os 1.098 da V2 e os 1.368 pontos da nossa lista que `rotular` marca como acerto.
- **Negativos:** 20 por positivo da V2, 21.960. Metade sai da V2 (10.980, sorteio com semente 42) e
  metade da nossa lista (10.980). Os acertos da nossa lista não aumentam o número de negativos.
- **Fora do treino:** os 18.487 pontos da nossa lista que caem em achado excluído (ignorados).

Testamos duas variantes, fixadas juntas antes de treinar qualquer uma:

- **A, `uniforme`:** os 10.980 negativos da nossa lista saem por sorteio uniforme entre os
  10.079.848 falsos positivos.
- **B, `vizinhos`:** metade deles (5.490) sai dos falsos positivos com um nódulo a até 16 mm, metade
  do lado do cubo, e a outra metade do resto. Criamos a B porque, na seção 5, 38% dos intrusos que
  entram nas 100 marcas têm um nódulo a até 16 mm, e no treino esses pontos são 28.723 dos 10.079.848
  falsos positivos: por sorteio uniforme a A traria uns 31 deles. Na B tiramos do treino os falsos
  positivos a menos de um diâmetro do centro de um nódulo, porque o nódulo ainda fica quase no centro
  do cubo e chamar esse ponto de negativo ensinaria a rede a ignorar nódulo.

Contagem conferida em 07/11/2026 nos dados reais, sem treinar (função `selecionar_misto` de
`src/experimentos/cnn.py`): 10.099.703 candidatos da nossa lista nos 623 exames de treino, 1.368
acertos, 18.487 ignorados, 10.079.848 falsos positivos. Na B, 23.957 vizinhos disponíveis para as
5.490 vagas e 7.694 pontos colados fora do treino. As duas variantes somam 24.426 cubos. O cubo da V2
recortado na hora do volume ficou igual ao cubo em disco em 3 exames de treino (maior diferença 0).

Os cubos da V2 vêm do disco; os da nossa lista são recortados na hora com `recortar`. A nossa lista
é lida em blocos de 2 milhões de linhas: cada falso positivo recebe uma chave aleatória e ficam os de
menor chave, o que dá o mesmo sorteio qualquer que seja o tamanho do bloco (teste em
`testes/test_treino_misto.py`).

Avaliamos só na validação, com o avaliador oficial e as mesmas 1.000 reamostras por exame, na nossa
lista inteira, na nossa lista com supressão a 5 mm e na V2. A diferença pareada contra a rede antiga
sai do script 27.

**Regra de decisão, fixada antes de rodar.** A rede nova fica se valerem as duas condições:

1. o CPM na nossa lista inteira sobe em relação aos 0,465 da rede antiga, com o IC95% da diferença
   pareada acima de zero;
2. o CPM na V2 não cai mais que 0,022 em relação aos 0,752 da rede antiga. 0,022 é o desvio padrão
   entre as três sementes da rede antiga (`relatorios/experimentos/sementes_cnn/resumo.json`).

Se as duas variantes passarem, fica a de maior CPM na nossa lista inteira. O teste não é usado nesta
etapa.

### 6.1 Resultado, medido em 07/11/2026

Comandos, para cada variante (`uniforme` e `vizinhos`):

```bash
.venv-cnn-gpu/bin/python scripts/18_treinar_cnn.py --variante lr_3e-4 --lista-propria uniforme \
    --saida modelos/cnn_lr_3e-4_lista_propria_uniforme
.venv-cnn-gpu/bin/python scripts/31_avaliar_lista_propria_cnn.py --modelo modelos/cnn_lr_3e-4_lista_propria_uniforme \
    --saida relatorios/experimentos/lista_propria_cnn_uniforme --completa dados/intermediario/lista_propria_cnn_uniforme
.venv-cnn-gpu/bin/python scripts/27_comparar_froc.py \
    --avaliacao "Rede nova=dados/intermediario/lista_propria_cnn_uniforme/sem_supressao" \
    --avaliacao "Rede antiga=dados/intermediario/lista_propria_cnn/sem_supressao" \
    --titulo "Validação, nossa lista inteira" --saida relatorios/experimentos/rede_lista_propria_uniforme/lista_inteira
.venv-cnn-gpu/bin/python scripts/27_comparar_froc.py \
    --avaliacao "Rede nova=modelos/cnn_lr_3e-4_lista_propria_uniforme/avaliacao_validacao" \
    --avaliacao "Rede antiga=modelos/cnn_lr_3e-4/avaliacao_validacao" \
    --titulo "Validação, lista V2" --saida relatorios/experimentos/rede_lista_propria_uniforme/v2
```

Uma execução por variante, semente 42, RTX 4050. Validação: 89 exames, 111 nódulos, o teste não foi
usado. Montagem dos cubos: 623 exames lidos, com erro 0, descartados 0. Pontuação da nossa lista:
89 exames lidos, com erro 0, descartados 0, 1.407.860 candidatos. A conferência do recorte deu
diferença 0 nos cubos de treino e 2,96e-08 nas probabilidades da validação.

CPM com IC95% (1.000 reamostras por exame, avaliador oficial):

| Lista | Rede antiga | A, uniforme | B, vizinhos |
|---|---:|---:|---:|
| Nossa, inteira | 0,465 (0,400 a 0,532) | 0,514 (0,451 a 0,588) | 0,674 (0,574 a 0,773) |
| Nossa, com supressão | 0,481 (0,424 a 0,555) | 0,534 (0,470 a 0,604) | 0,685 (0,581 a 0,779) |
| V2 | 0,752 (0,681 a 0,819) | 0,764 (0,690 a 0,823) | 0,680 (0,570 a 0,778) |

Diferença pareada de CPM contra a rede antiga, nas mesmas reamostras (script 27):

| Lista | A, uniforme | B, vizinhos |
|---|---:|---:|
| Nossa, inteira | +0,049 (+0,016 a +0,092); nova acima em 99,8% das reamostras | +0,210 (+0,107 a +0,304); acima em 100% |
| V2 | +0,013 (-0,023 a +0,043); acima em 71,9% | -0,072 (-0,158 a +0,005); acima em 3,5% |

Na lista com supressão não há diferença pareada: a supressão guarda a marca de maior nota em cada
vizinhança, então cada rede fica com um conjunto diferente de marcas (733.034 marcas com a A,
731.745 com a rede antiga), e o script 27 recusa comparar avaliações com candidatos diferentes.
Para essa lista reportamos o CPM de cada rede com o seu próprio intervalo. A regra de decisão não
usa essa lista.

Sensibilidade por ponto de operação (os IC95% estão nos `pontos_operacao.csv` de
`relatorios/experimentos/rede_lista_propria_<variante>/`, com a figura em `froc.png`):

| FP por exame | 0,125 | 0,25 | 0,5 | 1 | 2 | 4 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Nossa lista, rede antiga | 0,144 | 0,225 | 0,369 | 0,441 | 0,550 | 0,712 | 0,811 |
| Nossa lista, A | 0,171 | 0,369 | 0,414 | 0,486 | 0,613 | 0,739 | 0,802 |
| Nossa lista, B | 0,477 | 0,514 | 0,586 | 0,703 | 0,793 | 0,811 | 0,838 |
| V2, rede antiga | 0,505 | 0,631 | 0,730 | 0,784 | 0,838 | 0,883 | 0,892 |
| V2, A | 0,604 | 0,649 | 0,712 | 0,766 | 0,829 | 0,892 | 0,901 |
| V2, B | 0,396 | 0,568 | 0,622 | 0,730 | 0,784 | 0,820 | 0,838 |

Tempo de treino, incluindo a montagem dos cubos: 1.199 s na A (439 s de montagem) e 1.188 s na B
(428 s). Os dois treinos usaram 24.426 cubos, 2.466 deles positivos.

**A regra aplicada.**

- A, uniforme: condição 1 vale (IC da diferença na nossa lista de +0,016 a +0,092, acima de zero);
  condição 2 vale (a V2 subiu 0,013, não caiu). Passa.
- B, vizinhos: condição 1 vale (+0,107 a +0,304); condição 2 não vale (a V2 caiu 0,072, acima do
  limite de 0,022). Não passa.

Pela regra fixada antes de rodar, fica a rede A, `cnn_lr_3e-4_lista_propria_uniforme`.
A seção 7 repete a A com as sementes 43 e 44; ela não se confirmou (decisão 0011).

**O que os números não mostram.** Cada variante rodou uma vez, com uma semente; a variação entre
sementes da rede antiga foi de 0,022 no CPM da V2. Os números são da validação. A queda da B na V2
tem IC que encosta em zero (-0,158 a +0,005).

## 7. A rede A repetida com as sementes 43 e 44, medido em 07/11/2026

Regra fixada antes de rodar, no `config.yaml` (seção `sementes_lista_propria`): a A fica
confirmada se a média de CPM das três sementes na nossa lista inteira ficar acima da média da rede
antiga, com diferença pareada positiva semente a semente, e se a média na V2 não cair mais que
0,022. A rede antiga das sementes 43 e 44 já existia (decisão 0010), mas nunca tinha sido medida na
nossa lista.

Comandos:

```bash
.venv-cnn-gpu/bin/python scripts/31_avaliar_lista_propria_cnn.py --modelo modelos/cnn_lr_3e-4_semente_43 \
    --saida relatorios/experimentos/lista_propria_cnn_semente_43 --completa dados/intermediario/lista_propria_cnn_semente_43
.venv-cnn-gpu/bin/python scripts/18_treinar_cnn.py --variante lr_3e-4 --lista-propria uniforme --semente 43 \
    --saida modelos/cnn_lr_3e-4_lista_propria_uniforme_semente_43
.venv-cnn-gpu/bin/python scripts/31_avaliar_lista_propria_cnn.py --modelo modelos/cnn_lr_3e-4_lista_propria_uniforme_semente_43 \
    --saida relatorios/experimentos/lista_propria_cnn_uniforme_semente_43 \
    --completa dados/intermediario/lista_propria_cnn_uniforme_semente_43
.venv-cnn-gpu/bin/python scripts/33_sementes_lista_propria.py
```

e os mesmos com 44. Cada pontuação da nossa lista leu 89 exames, com erro 0, descartados 0, e
conferiu o recorte na hora contra a V2 (maior diferença de probabilidade 2,97e-08). Cada treino
montou cubos de 623 exames, com erro 0, descartados 0, e levou 1.175 s (semente 43) e 1.160 s
(semente 44), montagem incluída. O script 33 conferiu que, dentro de cada rede, as três sementes
só diferem na semente e usaram os mesmos dados.

CPM na validação (89 exames, 111 nódulos), com IC95%:

| Semente | Nossa lista, antiga | Nossa lista, A | V2, antiga | V2, A |
|---:|---:|---:|---:|---:|
| 42 | 0,465 (0,400 a 0,532) | 0,514 (0,451 a 0,588) | 0,752 (0,681 a 0,819) | 0,764 (0,690 a 0,823) |
| 43 | 0,474 (0,399 a 0,571) | 0,537 (0,478 a 0,612) | 0,790 (0,725 a 0,862) | 0,770 (0,695 a 0,830) |
| 44 | 0,551 (0,472 a 0,632) | 0,487 (0,402 a 0,571) | 0,790 (0,728 a 0,858) | 0,725 (0,646 a 0,796) |
| Média ± desvio | 0,496 ± 0,047 | 0,513 ± 0,025 | 0,777 ± 0,022 | 0,753 ± 0,025 |

Diferença pareada A menos antiga, mesma semente, mesmas reamostras:

| Semente | Nossa lista (IC95%) | V2 (IC95%) |
|---:|---:|---:|
| 42 | +0,049 (+0,016 a +0,092) | +0,013 (-0,023 a +0,043) |
| 43 | +0,063 (-0,005 a +0,123) | -0,021 (-0,062 a +0,003) |
| 44 | -0,064 (-0,106 a -0,021) | -0,066 (-0,115 a -0,028) |

**A regra aplicada.** Na nossa lista a média sobe 0,016, mas a diferença pareada é negativa na
semente 44: a condição 1 não vale. Na V2 a média cai 0,024, acima de 0,022: a condição 2 não vale.
A A não se confirmou, e a rede do projeto continua a `cnn_lr_3e-4` (decisão 0011).

As sete sensibilidades de cada rede e semente estão em
`relatorios/experimentos/sementes_lista_propria/sementes.csv`, as diferenças em
`diferencas_pareadas.csv`, a regra em `resumo.json` e a figura em `cpm_por_semente.png`.

**O que os números mostram.** Na nossa lista, a rede antiga varia de 0,465 a 0,551 só trocando a
semente, uma amplitude de 0,086. O ganho da A medido com a semente 42 (0,049) cabe dentro dessa
variação.

**O que os números não mostram.** Três sementes dão uma estimativa grosseira da variação. A
variante B não foi repetida com outras sementes; o ganho dela na nossa lista (0,210 com a semente
42) é maior que a amplitude entre sementes da rede antiga, mas isso vem de uma execução só e não
foi testado. Nada desta seção usou o teste.

## 8. Supressão com raio maior e média das sementes, desenho fixado em 08/11/2026

Sem treino novo. Partimos das notas que a rede antiga, com as sementes 42, 43 e 44, já deu a cada
ponto da nossa lista inteira na validação (script 31), e mudamos só o que acontece depois da rede.
Três variantes, fixadas em `config.yaml` (seção `supressao_lista_propria`) antes de rodar:

- **Supressão a 10 mm** e **supressão a 16 mm**: em cada exame, do maior escore para o menor, a
  marca a até esse raio de uma marca mantida sai (`suprimir_vizinhos`, a mesma função dos 5 mm da
  seção 1). Cada uma é medida nas três sementes.
- **Média das sementes**: a nota de cada ponto passa a ser a média das notas das três sementes,
  sem supressão nova.

Os detectores publicados de 2020 em diante suprimem marcas repetidas com sobreposição baixa entre
caixas (IoU de 0,1 a 0,22), o que equivale a algo da ordem do diâmetro do nódulo; 16 mm é também a
faixa em que a seção 5 mediu os intrusos. Pensamos em suprimir pelo raio que o LoG estima para
cada ponto e descartamos: 97,6% dos pontos da validação têm o mesmo raio, 1,73 mm (a menor escala),
e o raio de supressão ficaria perto de 3,5 mm, abaixo dos 5 mm já medidos.

Na validação, os dois nódulos anotados mais próximos de um mesmo exame estão a 19,46 mm (medido em
08/11/2026), e nenhum dos dois raios junta dois nódulos verdadeiros ali. No conjunto todo há um par
a 5,92 mm, que os dois raios juntariam.

**A comparação pareada.** O avaliador oficial sorteia os exames de cada reamostra só a partir da
lista de exames e da semente (`generateBootstrapSet` em `third_party/luna16`), sem olhar as marcas.
Com os mesmos 89 exames e a semente 42, a reamostra *k* é a mesma nas duas avaliações, e a
diferença de CPM réplica a réplica é pareada por exame mesmo quando as marcas diferem. O script 27
recusava esse caso porque confere também os candidatos; o script 34 confere só exames e protocolo.

**A regra.** Uma supressão fica se a média de CPM das três sementes passar a média da lista inteira
(0,496, seção 7) e a diferença pareada contra a lista inteira for positiva nas três sementes. Se as
duas passarem, fica a de maior média. A média das sementes fica se o CPM dela passar 0,496 e a
diferença pareada contra cada semente for positiva.

### 8.1 Resultado, medido em 08/11/2026

Medido com:

```bash
.venv-cnn-gpu/bin/python scripts/34_supressao_lista_propria.py
```

Exames lidos 89, com erro 0, descartados 0; 1.407.860 pontos por semente. Validação, 111 nódulos,
avaliador oficial, 1.000 reamostras por exame com semente 42. O teste não foi usado. Na primeira
execução o script calculou e gravou as duas tabelas e parou ao gravar o `resumo.json`, por um tipo
booleano do NumPy que o `json` não aceita. Corrigimos a conversão e geramos o `resumo.json` e a
figura a partir das tabelas já gravadas, com as mesmas funções do script.

| Variante | Semente 42 | Semente 43 | Semente 44 | Média ± desvio | Marcas por semente |
|---|---:|---:|---:|---:|---:|
| Lista inteira | 0,465 | 0,474 | 0,551 | 0,496 ± 0,047 | 1.407.860 |
| Supressão 10 mm | 0,553 | 0,564 | 0,647 | 0,588 ± 0,052 | cerca de 243 mil |
| Supressão 16 mm | 0,745 | 0,750 | 0,811 | 0,769 ± 0,037 | cerca de 86 mil |
| Média das sementes | | | | 0,525 | 1.407.860 |

Diferença pareada de CPM contra a lista inteira da mesma semente (IC95%):

| Variante | Semente 42 | Semente 43 | Semente 44 |
|---|---:|---:|---:|
| Supressão 10 mm | +0,089 (+0,057 a +0,130) | +0,090 (+0,057 a +0,118) | +0,097 (+0,076 a +0,132) |
| Supressão 16 mm | +0,281 (+0,210 a +0,342) | +0,277 (+0,186 a +0,351) | +0,260 (+0,188 a +0,328) |
| Média das sementes | +0,060 (+0,023 a +0,097) | +0,051 (+0,015 a +0,070) | -0,026 (-0,064 a +0,004) |

**A regra aplicada.** As duas supressões passam: a média sobe e a diferença pareada é positiva nas
três sementes, com o IC95% inteiro acima de zero em todas. Fica a de 16 mm, de maior média. A média
das sementes não passa: o CPM dela (0,525) fica acima de 0,496, mas a diferença contra a semente 44
é negativa.

Entre as 100 marcas de cada exame, a supressão a 16 mm com a semente 42 acha 98 dos 111 nódulos,
contra 100 da lista inteira (`CADAnalysis.txt` de cada avaliação).

As tabelas estão em `relatorios/experimentos/supressao_lista_propria/` (`variantes.csv`,
`diferencas_pareadas.csv`, `resumo.json` e a figura `cpm_por_variante.png`). As avaliações completas
ficam fora do git, em `dados/intermediario/supressao_lista_propria/`.

**O que os números não mostram.** Os dois raios foram fixados antes de rodar, mas foram medidos só
na validação, onde nenhum par de nódulos fica a menos de 19,46 mm. No conjunto todo há um par a
5,92 mm, que a supressão a 16 mm juntaria. A supressão não foi aplicada à V2 nesta fase.

## 9. A supressão a 16 mm também na V2, desenho fixado em 08/11/2026

Medição para comparar as duas listas com o mesmo processamento depois da rede, sem regra de adoção.
Aplicamos a supressão da decisão 0012 (16 mm, `suprimir_vizinhos`) às notas que a rede antiga, com as
sementes 42, 43 e 44, deu à V2 na validação (`probabilidades_validacao.csv` de cada modelo), e
avaliamos com o avaliador oficial. Para cada semente, duas diferenças pareadas: a V2 com supressão
contra a V2 como sai da rede, e a nossa lista com supressão (seção 8) contra a V2 com supressão.
Configuração em `config.yaml`, seção `supressao_v2`. O teste não entra.

### 9.1 Resultado, medido em 08/11/2026

Medido com:

```bash
.venv-cnn-gpu/bin/python scripts/35_supressao_v2.py
```

Exames lidos 89 por semente, com erro 0, descartados 0. A V2 tem 75.063 marcas na validação e fica
com cerca de 30,9 mil depois da supressão. Validação, 111 nódulos, avaliador oficial, 1.000
reamostras por exame com semente 42. O teste não foi usado.

| Lista | Semente 42 | Semente 43 | Semente 44 | Média ± desvio |
|---|---:|---:|---:|---:|
| V2 como sai da rede | 0,752 | 0,790 | 0,790 | 0,777 ± 0,022 |
| V2 com supressão a 16 mm | 0,798 | 0,846 | 0,847 | 0,830 ± 0,028 |
| Nossa lista com supressão a 16 mm | 0,745 | 0,750 | 0,811 | 0,769 ± 0,037 |

Diferenças pareadas de CPM (IC95%):

| Comparação | Semente 42 | Semente 43 | Semente 44 |
|---|---:|---:|---:|
| V2 com supressão contra V2 | +0,046 (-0,007 a +0,089) | +0,055 (+0,009 a +0,092) | +0,057 (+0,016 a +0,088) |
| Nossa lista contra V2, as duas com supressão | -0,053 (-0,109 a +0,002) | -0,095 (-0,153 a -0,040) | -0,036 (-0,082 a +0,003) |

As tabelas estão em `relatorios/experimentos/supressao_v2/` (`listas.csv`,
`diferencas_pareadas.csv`, `resumo.json`); as avaliações completas, em
`dados/intermediario/supressao_v2/`.

**O que os números mostram.** A supressão também sobe a V2, de 0,777 para 0,830 de média. Com o
mesmo processamento nas duas listas, a nossa fica abaixo da V2 nas três sementes, de 0,036 a 0,095;
o IC95% fica inteiro abaixo de zero na semente 43 e encosta no zero nas outras duas.

**O que os números não mostram.** Na validação nenhum par de nódulos fica a menos de 19,46 mm, então
esta medição não diz quanto a supressão a 16 mm perde quando dois nódulos estão próximos. No conjunto
todo há 16 pares a até 16 mm um do outro, 11 no treino e 5 no teste.

## 10. Supressão suave contra a supressão dura a 16 mm, desenho fixado em 08/11/2026

A supressão dura da decisão 0012 descarta qualquer marca a até 16 mm de uma marca mantida. No
conjunto todo há 16 pares de nódulos a até 16 mm um do outro (11 no treino, 5 no teste, nenhum na
validação), e em cada par a supressão dura tende a deixar só um nódulo.

A supressão suave não descarta: em cada exame, escolhe a marca de maior nota, rebaixa a nota dos
vizinhos conforme a distância e repete, até 100 marcas (`suprimir_suave` em
`src/detection/candidatos.py`). A sobreposição entre duas marcas é 1 - d/16, zero a partir de
16 mm. Duas formas, fixadas em `config.yaml` (seção `supressao_suave`) antes de rodar:

- **Gaussiana**: a nota do vizinho é multiplicada por exp(-sobreposição²/0,5). O fator vale 0,14
  em cima da marca, 0,45 a 5,92 mm e 0,75 a 10 mm.
- **Linear**: a nota do vizinho é multiplicada por 1 - sobreposição.

Duas medições:

- **Validação**, nossa lista, rede antiga com as sementes 42, 43 e 44: CPM de cada forma, pareado
  contra a supressão dura da mesma semente.
- **Pares do treino**: pontuamos a nossa lista nos exames de treino que têm um par de nódulos a até
  16 mm, com a rede antiga e a semente 42, e contamos quantos nódulos desses exames ficam entre as
  100 marcas sem supressão, com a dura e com cada forma suave. A rede viu esses exames no treino e
  dá nota otimista aos nódulos deles; por isso ali só contamos nódulos, sem CPM.

**A regra.** Uma forma suave substitui a dura se (1) nos pares do treino mantiver mais nódulos que a
dura e (2) na validação a média de CPM das três sementes não cair mais que 0,022 em relação à dura.
Se as duas passarem, fica a de maior média.

### 10.1 Resultado, medido em 08/11/2026

Medido com:

```bash
.venv-cnn-gpu/bin/python scripts/36_supressao_suave.py
```

**Validação** (89 exames, 111 nódulos, avaliador oficial, 1.000 reamostras por exame com semente 42):

| Variante | Semente 42 | Semente 43 | Semente 44 | Média |
|---|---:|---:|---:|---:|
| Dura a 16 mm | 0,745 | 0,750 | 0,811 | 0,769 |
| Suave gaussiana | 0,743 | 0,731 | 0,802 | 0,758 |
| Suave linear | 0,745 | 0,744 | 0,810 | 0,766 |

Diferença pareada contra a dura (IC95%): gaussiana -0,003 (-0,016 a +0,000), -0,019 (-0,035 a
-0,007) e -0,009 (-0,017 a -0,001); linear +0,000 (-0,003 a +0,000), -0,006 (-0,014 a +0,000) e
-0,001 (-0,006 a +0,000), nas sementes 42, 43 e 44.

**Pares do treino.** Exames de treino com um par de nódulos a até 16 mm lidos 9, com erro 0,
descartados 0; 37 nódulos; 144.442 pontos pontuados pela rede antiga, semente 42. Nódulos que ficam
entre as 100 marcas de cada exame: 33 sem supressão, 23 com a dura, 26 com a gaussiana e 25 com a
linear. Os nódulos que a forma suave recupera e a dura perde têm 4,0, 8,0 e 15,1 mm de diâmetro
(`pares_treino.csv`).

**A regra aplicada.** As duas formas suaves mantêm mais nódulos que a dura nos pares e ficam dentro
da queda de 0,022 na validação. Fica a linear, de maior média.

As tabelas estão em `relatorios/experimentos/supressao_suave/` (`validacao.csv`,
`diferencas_pareadas.csv`, `pares_treino.csv`, `resumo.json`).

**O que os números não mostram.** A diferença nos pares é de 2 nódulos em 37, em exames que a rede
viu no treino. Mesmo a forma suave perde 8 dos 33 nódulos que ficariam entre as 100 marcas sem
supressão nesses exames.

## 11. O teste, medido em 08/11/2026 (decisão 0013)

Terceiro uso do teste, uma execução só, com o processamento congelado antes de rodar: a rede
`cnn_lr_3e-4` da decisão 0008 e a supressão suave linear a 16 mm da seção 10, nas duas listas.
Medido com:

```bash
.venv-cnn-gpu/bin/python scripts/37_teste_supressao.py
```

Exames lidos 176, com erro 0, descartados 0; 223 nódulos; 2.802.479 pontos da nossa lista
pontuados na GPU em 921 s. A conferência do recorte, na CPU contra as notas da V2 gravadas em
13/10/2026, deu diferença máxima de 2,97e-08. Avaliador oficial, 1.000 reamostras por exame com
semente 42.

| Lista | CPM (IC95%) | Sens. a 1 FP (IC95%) | Sens. a 4 FP (IC95%) | Nódulos entre as 100 marcas |
|---|---:|---:|---:|---:|
| Nossa, sem supressão | 0,489 (0,438 a 0,546) | 0,480 (0,412 a 0,565) | 0,686 (0,623 a 0,758) | 213 de 223 |
| Nossa, supressão suave | 0,691 (0,633 a 0,754) | 0,717 (0,645 a 0,793) | 0,807 (0,758 a 0,868) | 195 de 223 |
| V2, sem supressão (13/10) | 0,724 (0,670 a 0,778) | 0,735 (0,659 a 0,819) | 0,883 (0,843 a 0,929) | 218 de 223 |
| V2, supressão suave | 0,758 (0,709 a 0,806) | 0,812 (0,756 a 0,861) | 0,865 (0,817 a 0,913) | 218 de 223 |

Diferenças pareadas de CPM (IC95%):

| Comparação | Diferença |
|---|---:|
| Nossa com supressão contra nossa sem | +0,202 (+0,153 a +0,252) |
| V2 com supressão contra V2 sem | +0,035 (+0,001 a +0,065) |
| Nossa contra V2, as duas com supressão | -0,067 (-0,112 a -0,026) |
| Nossa contra V2, as duas sem supressão | -0,235 (-0,271 a -0,196) |

As tabelas estão em `relatorios/experimentos/teste_supressao/` (`listas.csv`,
`diferencas_pareadas.csv`, `resumo.json`, e uma figura FROC por lista contra a V2 sem supressão). As
notas e as avaliações completas ficam fora do git, em `dados/intermediario/teste_supressao/`.

**O que os números mostram.** No teste, a supressão sobe a nossa lista em 0,202 de CPM e a V2 em
0,035. A distância entre as duas listas cai de 0,235 para 0,067, e a V2 continua acima. A
sensibilidade da nossa lista a 4 FP por exame fica em 0,807, acima da meta de 0,80 no valor medido,
com o IC95% de 0,758 a 0,868.

**O que os números não mostram.** Com a supressão, a nossa lista deixa 28 nódulos fora das 100 marcas
de cada exame, contra 10 sem ela; na validação a diferença tinha sido de 2 nódulos com a supressão
dura. Não medimos aqui quais nódulos são esses nem por quê. O teste fica usado e não escolhe nada
(decisão 0013).

## 12. Quais nódulos a supressão tirou das 100 marcas no teste, desenho fixado em 09/11/2026

A seção 11 deixou uma pergunta aberta: com a supressão suave, a nossa lista deixa 28 nódulos do
teste fora das 100 marcas de cada exame, contra 10 sem ela. Esta seção diz quais são os 18 a mais e
o que os rebaixou (T30).

**É o teste já usado (decisão 0013).** A análise só lê o que o script 37 gravou em
`dados/intermediario/teste_supressao/`; não pontua, não avalia de novo e não muda raio nem forma da
supressão. Descreve, não escolhe.

**Como medimos** (`scripts/39_supressao_perdidos_teste.py`, seção `supressao_perdidos` do
`config.yaml`):

1. Comparamos o `nodulesWithoutCandidate_predicoes.txt` de `propria/` com o de `propria_suave/`, pelo
   exame e pelo centro do nódulo, e separamos os nódulos que só a versão com supressão perde. O
   script avisa se a conta não der 18, e conta também os que só a versão sem supressão perde (a
   supressão só abaixa notas, então esperamos 0).
2. Para cada exame com nódulo perdido, refazemos a `suprimir_suave` sobre as notas de
   `probabilidades.csv`, guardando a nota final de cada ponto e cada rebaixamento. A repetição tem de
   dar as mesmas 100 marcas e notas que o script 37 entregou ao avaliador
   (`propria_suave/predicoes.csv`); se não der, o script para.
3. Para cada nódulo perdido: o ponto mais perto do centro e a nota dele; o ponto que contava como
   acerto sem a supressão, que é o de maior nota dentro do raio do nódulo (o critério do avaliador);
   a nota dele antes e depois da supressão, e a nota da 100ª marca do exame; e, entre as marcas
   mantidas que rebaixaram esse ponto, a que mais rebaixou (menor fator). Medimos a distância entre o
   ponto e esse vizinho e classificamos o vizinho pela regra do avaliador: outro nódulo anotado, achado
   excluído ou falso alarme.
4. Uma figura com 4 casos, dois em que o vizinho é outro nódulo e dois em que não é, os de maior
   diâmetro primeiro: corte axial no z do nódulo, com o nódulo circulado e o vizinho marcado. A
   conversão de mm para voxel é a do `TransformPhysicalPointToIndex`, a mesma de
   `src/detection/recorte.py`.

O ponto do nódulo é o de maior nota dentro do raio, e não simplesmente o mais perto do centro,
porque é ele que punha o nódulo entre as 100 marcas sem a supressão. O mais perto do centro fica na
tabela também (`ponto_mais_perto_mm`, `nota_ponto_mais_perto`).

Saídas em `relatorios/experimentos/supressao_perdidos/`: `nodulos.csv` (um nódulo perdido por
linha), `por_causa.csv`, `casos.png` e `resumo.json`.

### 12.1 Resultado

Ainda não medido. A pasta `dados/intermediario/teste_supressao/` (643 MB) e os volumes
pré-processados não estavam na máquina em que o script foi escrito; o script foi conferido com
`testes/test_supressao_perdidos.py`, que compara a supressão repetida com a `suprimir_suave` e roda o
script de ponta a ponta num exame sintético. Comando para medir:

```bash
.venv/bin/python scripts/39_supressao_perdidos_teste.py
```
