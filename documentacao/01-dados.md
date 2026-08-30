# Os dados

O que é o LUNA16, o que temos em disco, e o que cada campo significa. Todos os números desta
página foram medidos em 29/08/2026, e ao lado de cada um está o script que mediu.

## De onde vem

O LUNA16 sai de dentro do LIDC-IDRI, uma base pública de tomografias de tórax anotadas por
quatro radiologistas. O desafio filtrou essa base com regra própria: descartou exames com
fatia mais grossa que 2,5 mm, e só considerou nódulo o achado de 3 mm ou mais que pelo menos
três dos quatro radiologistas marcaram.

Sobraram 888 exames. É essa filtragem que torna o LUNA16 comparável entre trabalhos: todo
mundo mede a mesma coisa sobre os mesmos exames.

## O que temos

Baixamos os subsets 0 a 4, que dão **445 exames** dos 888. Os subsets 5 a 9 não foram
baixados, e isso é declarado em todo resultado.

Os dez subsets não são divisão nossa: são as dobras oficiais de validação cruzada do desafio.
Usar as dobras dele é o que mantém a comparação com o ranking público válida.

## Os arquivos do desafio

Os dois CSV descrevem os **888 exames**, não só os nossos 445. Ou seja, os rótulos dos exames
que ainda não baixamos já estão em disco.

**`annotations.csv`** traz os nódulos que passaram no critério de inclusão. São 1.186 linhas
em 601 exames, com `seriesuid`, as três coordenadas em milímetro e o diâmetro. O diâmetro vai
de 3,25 a 32,27 mm, com mediana de 6,43. Destes, 615 caem nos nossos 445 exames.

**`candidates.csv`** traz os pontos suspeitos que servem de entrada para o baseline. São
551.065 linhas em 888 exames, com as mesmas coordenadas mais a coluna `class`, que é 1 para
nódulo verdadeiro e 0 para falso positivo. Só 1.351 são positivos, ou 0,2452%. Nos nossos
subsets são 275.358 candidatos com 721 positivos.

**`annotations_excluded.csv`** traz 35.192 achados que o desafio tira da conta. Candidato que
casa com um deles não é acerto nem alarme falso. Ignorar isso infla o número de falso positivo
e o resultado deixa de ser comparável.

**`seg-lungs-LUNA16`** traz as máscaras de pulmão prontas, uma por exame, nos 888. Não
segmentamos pulmão: já vem feito.

**`evaluationScript`** traz o `noduleCADEvaluationLUNA16.py`, o script oficial que calcula a
curva FROC. Não escrevemos FROC própria pelo mesmo motivo.

## Os volumes

Cada exame é um par de arquivos MetaImage, o `.mhd` com o cabeçalho em texto e o `.raw` com os
voxels. O inventário dos 445 está em `dados/intermediario/inventario_volumes.csv`, gerado por
`scripts/02_inventario_volumes.py` lendo só o cabeçalho, sem abrir o `.raw`.

| Campo | Unidade | O que é |
|---|---|---|
| `seriesuid` | texto | identificador do exame, a chave que liga tudo |
| `origem_x`, `origem_y`, `origem_z` | mm | o `Offset` do cabeçalho, em (x, y, z) |
| `espacamento_x`, `espacamento_y`, `espacamento_z` | mm | o tamanho do voxel, em (x, y, z) |
| `dim_x`, `dim_y`, `dim_z` | voxels | as dimensões, em (x, y, z) |
| `direcao` | adimensional | a matriz de orientação dos eixos, nove valores |
| `matriz_identidade` | booleano | se a direção é identidade dentro de 1e-6 |
| `orientacao` | texto | RAI em 434 exames e LPI em 11 |
| `extensao_z_mm` | mm | a altura física do volume |
| `tamanho_raw_mb` | MB | tamanho do `.raw` em disco |

**Os exames não são todos iguais.** O espaçamento entre fatias varia de 0,5 a 2,5 mm, um fator
de 5, e o número de fatias vai de 95 a 538. É isso que obriga a reamostragem antes de comparar
qualquer coisa entre exames.

## A armadilha das coordenadas

É o jeito mais provável de este projeto dar errado em silêncio, e por isso tem seção própria.

As coordenadas dos CSV estão em **milímetro no espaço do mundo**. O array da imagem está em
**índice de voxel**. A ponte entre os dois usa a origem, o espaçamento **e a direção**, e os
três mudam de exame para exame.

Dos nossos 445 volumes, 434 têm direção identidade e orientação RAI, e **11 têm orientação
LPI**, com a matriz `-1 0 0 0 -1 0 0 0 1`, que espelha x e y. Nesses 11, a fórmula simples,
sem a direção, joga os 19 nódulos anotados para fora do volume. Medido com
`scripts/03_verificar_coordenadas.py`.

A conversão correta é:

```
índice = transposta(D) · (mundo − origem) / espaçamento
mundo  = D · (índice · espaçamento) + origem
```

Está em `codigo/pi3/preprocessamento/coordenadas.py`, com teste em
`testes/test_coordenadas.py`.

**Há ainda uma segunda troca que engana.** O cabeçalho declara origem, espaçamento e dimensão
em (x, y, z), e é isso que o leitor devolve. Mas o array da imagem vem em **(z, y, x)**.
Inverter um e não o outro produz erro que só aparece em volume não cúbico, e todo volume aqui
é não cúbico.

Errar qualquer uma das duas desloca o recorte, não levanta exceção, não quebra teste nenhum, e
o modelo treina ruído com uma curva de perda que parece saudável.

## Como sabemos que está certo

Teste automatizado e figura. Um sem o outro não basta.

O teste roda a ida e a volta em volumes de espaçamento diferente, incluindo os dois extremos
de 0,5 e 2,5 mm e um dos volumes invertidos, e confere contra a conversão do próprio leitor de
imagem.

A figura pega um nódulo anotado, converte a coordenada, e desenha um círculo do diâmetro
anotado na fatia correspondente. Se o círculo cai em cima do nódulo, está certo. São
`relatorios/figuras/coordenada_rai.png` e `coordenada_lpi.png`, e a segunda é a que importa,
porque nos volumes RAI a fórmula errada também funcionaria.
