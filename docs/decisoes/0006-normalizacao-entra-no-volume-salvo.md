# 0006: a normalização [0, 1] entra no volume salvo

**Estado:** decidido e verificado
**Data:** 07/09/2026

## Contexto

O feedback do professor lista cinco etapas para o pré-processamento: carregamento MetaImage pelo
SimpleITK, reamostragem para 1 mm isotrópico, janelamento HU de -1000 a 400, **normalização
[0, 1]**, e máscara binária do parênquima. Tínhamos quatro. A normalização não existia em lugar
nenhum do repositório, conferido por busca em `src/`, `scripts/`, `testes/` e `configuracao/`.

Escrever a função é trivial. O que precisava de decisão é **onde ela roda**, porque isso muda o
tipo do arquivo que fica em disco:

- Se a normalização entra no `preprocessar()`, o volume salvo deixa de ser inteiro de 16 bits em
  HU e passa a ser float de 32 bits em [0, 1].
- Se ela fica fora, o disco guarda HU e cada leitura de recorte normaliza de novo na hora do
  treino.

A suspeita inicial era que guardar em float quadruplicaria o disco, porque um voxel de 32 bits
ocupa o dobro de um de 16, e valor fracionário comprime pior que inteiro repetido.

## O que medimos

Sobre o exame de teste, de 420 × 420 × 308 voxels, gravando com o `ImageFileWriter` do SimpleITK:

| | Cru | Comprimido |
|---|---|---|
| Inteiro de 16 bits, em HU | 108,7 MB | 7,1 MB |
| Float de 32 bits, em [0, 1] | 217,3 MB | **9,7 MB** |

**A suspeita estava errada.** Cru o float dobra, como esperado, mas comprimido a diferença é de
37%, não de 300%. O motivo é que quase todo o volume fora do pulmão é o mesmo valor repetido, e a
compressão resolve isso igual nos dois tipos.

Extrapolando para os 888 exames pelo tamanho de um só, o que é ordem de grandeza e não medição:
cerca de 6,3 GB guardando HU contra 8,6 GB guardando normalizado, uma diferença de 2,3 GB. O disco
interno tem 223 GB livres, medido com `df -h` em 07/09/2026.

## Decisão

**A normalização entra no `preprocessar()` e o volume salvo já sai em [0, 1].**

O custo medido de 2,3 GB no total não compra nada em troca. E normalizar uma vez por volume é mais
barato que normalizar a cada recorte lido: são 754.975 candidatos contra 888 exames.

A ordem das etapas é janela, reamostragem, máscara, normalização. A normalização vai por último
porque o preenchimento de fora do pulmão é `hu_min`, e normalizar depois faz esse fundo virar
exatamente 0.

## A alternativa que descartamos

**Guardar HU em inteiro e normalizar na carga.** Descartada pela medição acima: economiza 2,3 GB
num disco com 223 GB livres, e paga isso repetindo a conta em cada um dos 754.975 recortes.

**Guardar em inteiro de 8 bits, de 0 a 255.** Descartada sem medir, e o motivo é aritmético: a
janela tem 1.400 HU de largura, então cada passo de 8 bits valeria 5,5 HU. Nódulo pequeno se separa
do vaso por diferença de dezenas de HU, e não vamos jogar fora resolução para economizar disco que
sobra.

## Verificação

Quatro testes novos em `testes/test_preprocessamento.py`, e a suíte inteira passa em 43.

Confirmamos que eles protegem de verdade, quebrando a função de propósito de quatro jeitos:

| Mutação | Testes que quebram |
|---|---|
| Tirar o deslocamento por `hu_min` | 5 |
| Dividir só por `hu_max` em vez da largura da janela | 3 |
| Voltar a devolver float de 64 bits | 1 |
| `preprocessar` parar de normalizar | 2 |

O teste de 64 bits existe por um erro que cometemos: a primeira versão da função dividia por um
escalar, e o SimpleITK promove o resultado a float de 64 bits nesse caso. O volume saiu com 434,6
MB crus em vez de 217,3, o dobro do necessário, sem nenhum aviso. A função multiplica pelo inverso
justamente por isso, e o teste tranca esse comportamento.

## O que quebrou em silêncio quando ligamos

A figura `relatorios/figuras/preprocessamento.png` desenha o volume antes e depois lado a lado, e
usava a janela de HU para os dois painéis. Com o volume de saída em [0, 1], o painel da direita
virou **um retângulo cinza chapado**, sem nenhum erro: o pipeline rodou até o fim, o DVC gravou o
lock, e a figura entrou no repositório sem informação nenhuma.

A função passou a receber o intervalo de cinza de cada painel separadamente, em vez de assumir
que os dois estão na mesma escala.

Dois testes novos em `testes/test_figuras.py` cobrem isso, medindo quanto da metade direita da
imagem é coberta pelo tom de cinza mais repetido: com a faixa certa fica em 23%, e com a faixa
errada sobe para 74%. Um deles desenha de propósito com a faixa errada e exige que a figura saia
chapada, para o teste continuar valendo se alguém reescrever a função.

## Consequências

**O que está em `dados/processado/` deixa de ser HU.** Quem abrir um `.mha` de lá vê valores de 0 a
1. Para voltar a HU, multiplica pela largura da janela e soma `hu_min`, que estão no `config.yaml`.

**O pré-processamento passa a ter as cinco etapas que o professor lista.** Era a última que
faltava.

**O `06_escolher_espacamento.py` não muda de resultado.** Ele chama `janela` e `reamostrar`
direto, e não o `preprocessar`, porque mede contraste em HU de propósito. A tabela da decisão 0004
continua valendo.
