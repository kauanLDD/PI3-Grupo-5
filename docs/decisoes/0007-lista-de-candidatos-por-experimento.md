# 0007: o V2 alimenta os classificadores, e a lista própria é avaliada como detector

**Estado:** decidido; o cruzamento nódulo a nódulo ainda não foi medido
**Data:** 05/10/2026

## Contexto

Desde o card S4-T10 temos duas listas de pontos suspeitos sobre os mesmos 888 exames: o
`candidates_V2.csv`, que vem pronto do desafio, e a `candidatos.csv`, que geramos com o blob
detection 3D de `src/detection/blobs.py`. O primeiro treino do Random Forest já usou o V2
(`docs/08-primeiro-treino.md`), porque a lista própria ainda não existia nos 888 exames.

Faltava decidir, com as duas listas medidas na mesma base, qual alimenta cada experimento. A
escolha fecha porta: o classificador, as features e a curva FROC dependem de qual lista entra.

## Mesma base, mesma régua

As duas listas foram medidas contra os mesmos 888 exames do `inventario_volumes.csv` e os mesmos
1.186 nódulos do `annotations.csv`, pelo critério de acerto de `src/detection/candidatos.py`,
função `alcancados`: um nódulo é alcançado quando existe candidato a até metade do diâmetro do
centro dele. É o mesmo critério da tabela em `docs/criterios_inclusao_luna16.md`.

Nas duas, o exame sem candidato entra no denominador da média por exame. A lista própria terminou
os 888 exames com zero falhas (`docs/04-deteccao-de-candidatos.md`), então nenhum exame sai da
conta por erro de execução.

## As duas listas

| | `candidatos.csv`, própria | `candidates_V2.csv`, do desafio |
|---|---:|---:|
| Exames | 888 | 888 |
| Nódulos de referência | 1.186 | 1.186 |
| Candidatos | 14.310.042 | 754.975 |
| Candidatos por exame | 16.114,9 | 850,2 |
| Nódulos alcançados | 1.158, 97,6% | 1.166, **98,3%** |
| IC 95%, bootstrap por exame | 96,71% a 98,57% | não registrado |
| Espaço em disco | 1.714.804.240 bytes, 1,60 GiB | 72.058.556 bytes, 68,7 MiB |
| Bytes por candidato | 119,8 | 95,4 |
| Tempo para gerar | de 23,6 a 27,4 s por exame | zero, vem pronta |

De onde vem cada número:

- **Cobertura e candidatos da lista própria:** rodada completa de 03/10/2026, conferida em
  05/10/2026 com `.venv/bin/dvc repro --single-item deteccao marcacoes_excluidas`, registrada em
  `docs/04-deteccao-de-candidatos.md` e no histórico.
- **Cobertura e candidatos do V2:** `scripts/08_comparar_candidatos.py`, 09/09/2026, tabela em
  `docs/criterios_inclusao_luna16.md`.
- **Espaço:** o campo `size` do `dvc.lock`, no estágio `deteccao`, que guarda o tamanho dos dois
  arquivos no momento em que a rodada foi registrada.
- **Tempo da lista própria:** 23,6 s por exame na rodada curta de 13/09/2026, em 8 exames, e 27,4 s
  e 26,4 s por exame na configuração `inicial` da calibração de 20/09/2026, em 21 e 12 exames
  (`docs/05-calibracao-detector.md`). É a mesma configuração de produção.

**O tempo da rodada completa não foi registrado.** O `10_detectar_candidatos.py` só grava o tempo
de exame que falha, e a rodada foi interrompida depois de 218 exames e retomada. Multiplicando a
faixa medida por 888 dá de 5,8 a 6,8 horas de processamento, ou cerca de 3 a 3,4 horas de relógio
com os dois processos de `deteccao.trabalhadores`. Isso é aritmética, não medição.

Os 888 volumes pré-processados, de 8,6 GiB e 39,8 minutos, não entram no custo de nenhuma das
duas: a lista própria precisa deles para ser gerada, e o V2 precisa deles para a extração de
features. O custo é o mesmo dos dois lados.

## O que a tabela diz

**A lista própria tem 19 vezes mais candidatos e alcança oito nódulos a menos.** São 18,95 vezes
mais pontos por exame, 23,8 vezes mais disco, e algumas horas de processamento que o V2 não cobra.

**A diferença de cobertura sozinha não decide.** O intervalo da lista própria, de 96,71% a
98,57%, contém os 98,3% do V2. Oito nódulos em 1.186 é pouco para afirmar que o V2 cobre mais.
O que decide é a quantidade: com cobertura parecida, a lista própria entrega 19 vezes mais pontos
para o classificador descartar.

**Candidato por exame não é falso positivo por exame.** Nenhuma das duas passou por classificador
nem pela FROC, e as anotações excluídas ainda tiram pontos da conta. A tabela compara o teto de
sensibilidade e o volume de trabalho de cada lista, não o desempenho de detecção.

## Decisão

**Os classificadores usam o V2, e a lista própria é avaliada como detector, ao lado dele.**

| Experimento | Lista | Por quê |
|---|---|---|
| Random Forest, baseline (`docs/08-primeiro-treino.md`) | V2 | já treinado nela; a seção 4.3 do enunciado descreve o baseline sobre a lista pronta |
| CNN 3D, redução de falsos positivos | V2 | a mesma entrada do baseline isola o efeito do classificador |
| FROC na validação e no teste | V2 | é a lista que os resultados publicados usam, e a comparação com eles depende dela |
| Avaliação do detector LoG | própria | é o produto da etapa de detecção, e o que se mede nela é cobertura e quantidade contra o V2 |

A lista própria **não** alimenta classificador nesta fase. Ela continua sendo reportada com a
cobertura, o intervalo e os candidatos por exame, sempre ao lado do V2, e nunca como ponto da
curva FROC.

## A alternativa que descartamos

**Treinar e avaliar os classificadores sobre a lista própria.** Descartada pela tabela acima: com
cobertura dentro do mesmo intervalo, ela entrega 19 vezes mais pontos. A ordem de grandeza do que
isso custa adiante, pelo tamanho medido das etapas que já rodaram com o V2:

- a validação teria cerca de 1,43 milhão de candidatos em vez de 75.063, e a extração das features,
  que levou 183 segundos, iria para perto de uma hora se crescer na proporção dos candidatos;
- o CSV de features do treino, de 127 MB para 529.500 candidatos, passaria de 2 GiB para os cerca
  de 10 milhões da lista própria nos 623 exames de treino;
- o Random Forest, que ajustou em 145 segundos, teria 19 vezes mais linhas, quase todas negativas,
  e a prevalência, já de 0,2062% no V2, cairia mais.

Nenhum desses três números foi medido. São o tamanho medido multiplicado pela razão de candidatos.

Ela também tiraria a comparação com o ranking público, que é o motivo de termos escolhido o
LUNA16: a trilha de redução de falsos positivos do desafio parte da lista pronta, e é contra
essa trilha que os resultados publicados se comparam.

**Juntar as duas listas.** Ainda não dá para avaliar. A união só ajuda se a lista própria
alcançar nódulos que o V2 não alcança, e isso não está medido: as duas coberturas foram contadas
separadamente. O `scripts/18_comparar_lista_propria_v2.py` mede esse cruzamento nódulo a nódulo,
mas a base não está na máquina de quem escreveu o script. Mesmo que a união ganhe nódulos, ela
herda os 16 mil candidatos por exame da lista própria.

## Isto não é fracasso do detector

A lista própria alcança 97,6% dos nódulos com um filtro LoG de cinco escalas, sem aprendizado,
contra 98,3% de uma lista que, pela leitura de Setio et al. (2017) em
`docs/criterios_inclusao_luna16.md`, combina vários sistemas de detecção. O que falta a ela é
seletividade, não alcance. A seção 3.4 do enunciado trata resultado negativo bem
fundamentado como resultado, e é assim que ele entra no relatório.

## Consequências

**O treino de 04/10/2026 continua valendo.** O Random Forest, as features de treino e validação e
os escores salvos são todos do V2, e nada precisa ser refeito.

**A seção do detector reporta as duas listas lado a lado.** Cobertura, intervalo e candidatos por
exame, com a frase de que cobertura não é FROC.

**A lista própria volta a ser candidata para os classificadores se um corte medido mudar a
tabela.** O `troca_cobertura_candidatos.csv` já mede quanto de cobertura cada corte de escala
custa. Se um corte, escolhido no desenvolvimento e conferido na validação como na calibração,
chegar perto dos 850 candidatos por exame sem perder nódulo para o V2, a decisão é reaberta num
registro novo que referencia este. O teste continua fora dessa escolha.

**O tempo por exame da rodada precisa ser gravado.** Sem isso, o custo de gerar a lista própria
continua sendo estimado pela calibração.

## Como verificar

```
.venv/bin/python -m pytest testes/test_comparacao_listas.py testes/test_candidatos.py -q
.venv/bin/dvc repro --single-item comparar_propria_v2
```

O estágio roda `scripts/18_comparar_lista_propria_v2.py`. Ele confere antes de contar que as duas
listas estão sobre os mesmos exames e os mesmos nódulos, recusa a lista própria com exame em
falha ou pendente, e grava `dados/intermediario/comparacao_propria_v2.csv`, com uma linha por
lista, e `dados/intermediario/alcance_por_nodulo_propria_v2.csv`, com o alcance de cada nódulo
nas duas. Quando rodar na máquina com a base, os números do cruzamento entram aqui, com a data.
