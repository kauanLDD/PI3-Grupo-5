# Pré-processamento

Deixar um exame comparável com qualquer outro, antes de procurar nódulo em qualquer um deles.
São quatro operações, e a ordem entre elas importa.

O código está em `src/preprocessing/volume.py` e roda por
`scripts/04_preprocessar.py`.

## A ordem

**Primeiro a janela de HU**, cortando a intensidade em −1000 e 400. Vem antes da interpolação
para que um voxel de costela, que passa de 400, não vaze para dentro do pulmão quando os
vizinhos forem misturados na reamostragem.

**Depois a reamostragem** para voxel de 1 mm isotrópico. O volume usa interpolação linear e a
máscara usa vizinho mais próximo, para continuar binária.

**Depois a máscara**, aplicada ao volume já reamostrado, para não interpolar a borda dura
entre pulmão e o lado de fora. O que fica fora do pulmão recebe −1000, que é ar, e não zero,
que na escala Hounsfield é água.

**Por último a normalização**, que leva a janela de HU para o intervalo de 0 a 1. Vai depois da
máscara justamente porque o preenchimento de fora do pulmão é −1000, o piso da janela, e
normalizar em seguida faz esse fundo virar exatamente 0. Guardamos o volume já normalizado, e o
motivo está em `docs/decisoes/0006-normalizacao-entra-no-volume-salvo.md`.

## O que muda em um exame

Um exame típico, de 512 por 512 por 123 voxels de 0,82 por 0,82 por 2,5 mm, sai como 420 por
420 por 308 voxels de 1 por 1 por 1 mm. A extensão física é preservada dentro de meio voxel, e
o pulmão fica sendo 8,3% do volume.

Os valores saem entre 0 e 1, e não mais em HU. O arquivo ocupa 9,7 MB em float de 32 bits
comprimido, contra 7,1 MB se guardássemos o HU em inteiro de 16 bits.

A figura `relatorios/figuras/preprocessamento.png` mostra a mesma posição física antes e
depois, com um nódulo de 32,3 mm circulado nos dois lados. À esquerda o tórax inteiro, à
direita só os dois pulmões.

## Evidência da normalização no volume bruto

Em 15/09/2026 reproduzimos a evidência do exame
`1.3.6.1.4.1.14519.5.2.1.6279.6001.979083010707182900091062408058` com
`.venv/bin/python scripts/11_evidencia_normalizacao.py`, usando `janela` e `normalizar`
de `src/preprocessing/volume.py`. No volume bruto inteiro, de 140 por 512 por 512 voxels,
o intervalo original foi de -3024 a 1651 HU; após janela e normalização, o mínimo foi 0,
o máximo 1, a média 0,408845 e o desvio padrão 0,331430. São estatísticas do tórax inteiro,
incluindo mesa e corpo, sem máscara nem reamostragem. Não descrevem os volumes finais do
pipeline. A figura `relatorios/figuras/normalizacao_hu.png` mostra o corte axial 61 e seus
histogramas; a tabela com o identificador do exame fica em
`dados/intermediario/evidencia_normalizacao.csv`. O estágio `evidencia_normalizacao` do DVC
rastreia os dois arquivos. O corte é escolhido pela maior área na faixa de HU configurada,
dentro da metade central do volume; sem voxels nessa faixa, usamos o corte do meio.

## Onde isso quebra em silêncio

Reamostrar muda o espaçamento. Um volume gravado com a geometria antiga, ou uma coordenada
convertida com o espaçamento velho, desloca todo recorte feito depois sem levantar erro.

Por isso a reamostragem mantém origem e direção intactas e altera apenas espaçamento e
dimensão, e por isso existe teste que põe um objeto denso numa posição conhecida, reamostra, e
exige que ele continue na mesma posição em milímetro. Existe também o teste espelhado, que
prova que a fórmula sem a geometria nova cai em outro voxel: sem ele, o primeiro passaria
mesmo com o código errado.

## A máscara de pulmão

Usamos a máscara que o desafio entrega, sem dilatar. A justificativa e a medição que a
sustentam estão em `docs/decisoes/0002-mascara-de-pulmao-sem-dilatacao.md`.

Em resumo: 51 dos 1.186 nódulos têm o centro fora da máscara, o que à primeira vista parece
perda grande. Mas o critério de acerto do desafio não exige acertar o centro, e sim chegar a
menos de um raio dele. Medido com esse critério, **1.185 dos 1.186 continuam alcançáveis**: a
máscara custa exatamente um nódulo, de 5 mm, ou 0,08%.

A forma como lemos a máscara importa. Usando os rótulos 3 e 4, como faz toda a linhagem de
código pública do LUNA16, a perda sobe para quatro nódulos. Usamos `> 0`, que inclui o rótulo
5, e isso recupera três deles.

## A rodada na base completa

Rodamos nos 888 exames em 08/09/2026, com `scripts/07_preprocessar_base.py`, e refizemos a
rodada em 10/09/2026 quando o recorte passou de 32 para 34 voxels. Os números abaixo são os da
segunda rodada, que é a que está em `dados/intermediario/preprocessamento.csv`.

| | |
|---|---|
| Exames na lista | 888 |
| Gravados | 888 |
| Sem volume em disco | 0 |
| Sem máscara do desafio | 0 |
| Erro na leitura ou no pré-processamento | 0 |
| Tempo total | 39,8 minutos |
| Tempo por exame | mediana 2,52 s, de 0,92 a 5,67 |
| Tamanho por exame | mediana 10,0 MB, de 3,2 a 51,1 |
| Total em disco | 8,6 GiB |

Depois da reamostragem os volumes vão de 236 a 500 voxels no plano, com mediana de 360, e de 166
a 416 fatias, com mediana de 318.

## A máscara é larga demais em 37 exames

O volume que a máscara do desafio marca como pulmão tem mediana de 4,87 litros nos 888 exames, o
que é a capacidade pulmonar de um adulto. Mas **37 exames passam de 8 litros**, e o maior chega a
31 litros, o que nenhum pulmão humano tem.

Não é máscara trocada nem invertida: o HU mediano dentro dela é de -968 nesse exame extremo, ou
seja, ar. É máscara larga, que vazou para o ar em volta do paciente, que tem a mesma densidade do
ar dentro do pulmão.

Isso **não perde nódulo**, porque região a mais não corta nada. O que a máscara larga custa é área
de busca, e a região que ela acrescenta fica fora do corpo do paciente.

O litro sai de `dados/intermediario/preprocessamento.csv`, que
`scripts/07_preprocessar_base.py` grava: como o volume é isotrópico de 1 mm, a fração de pulmão
vezes as três dimensões dá o volume em milímetros cúbicos direto. A contagem dos 37 está trancada
por teste em `testes/test_base_preprocessada.py`, que guarda quais são os exames e não só quantos.

O HU mediano dentro da máscara não está nesse relatório. Ele foi lido uma vez, em 08/09/2026,
direto do volume bruto e da máscara do desafio no HD, nos cinco exames de maior fração de pulmão:
deu -968, -328, -934, -929 e -917, contra -870, -866 e -884 em três exames de fração típica.

## O que ainda não existe

O recorte dos cubos tem código e teste em `src/detection/patches.py`, e nunca rodou na base. Não
existem as features de intensidade, o baseline, o modelo treinado nem a avaliação FROC.
