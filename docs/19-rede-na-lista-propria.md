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
(`src/detection/patches.py`, função `recortar`, com testes em `testes/test_patches.py`).

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
para baixo no ranking do exame. Não medimos quais candidatos da nossa lista recebem escore alto nem
treinamos a rede com eles.

Os números são da validação, o mesmo conjunto em que a rede foi escolhida entre as variantes
(`docs/11`), e de uma lista que a rede nunca viu.
