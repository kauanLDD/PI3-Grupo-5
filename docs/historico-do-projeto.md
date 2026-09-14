# Histórico do projeto até 14/09/2026

Este documento guarda a ordem das coisas: o que foi feito, em que data, por que, e onde está a
medição que sustenta cada passo. Ele não é o dono de nenhum número. Quando um número aparece
aqui, o arquivo que manda nele está citado ao lado, e é lá que ele se corrige quando mudar.

A metodologia é o KDD, e as seções abaixo seguem as etapas dele: seleção, pré-processamento e
transformação. Mineração e avaliação ainda não começaram.

## O recorte do trabalho

Estamos na etapa de detecção. Recebemos o pulmão já separado do resto da imagem e entregamos os
pontos suspeitos. Não classificamos benigno contra maligno, isso é de outro grupo.

A métrica que vale é a curva FROC, sensibilidade em função da média de falsos positivos por
exame, com os pontos de operação em 1 e 4 FP por exame e o CPM, que é a média da sensibilidade
nos sete pontos declarados em `configuracao/config.yaml`. O enunciado declara alvo de 0,70 de
sensibilidade a 4 FP por exame para o baseline e 0,80 para a CNN, e isso é alvo, não resultado.

Acurácia e AUC-ROC não servem aqui, e o motivo está medido em `docs/02-analise-exploratoria.md`:
a prevalência é de 0,2062%, e um classificador que responde sempre "não é nódulo" acerta 99,79%
sem detectar nada.

Duas regras do protocolo entram junto com a métrica. Todo número que reportarmos vai com
intervalo de confiança de 95% por bootstrap, com o número de reamostras declarado no
`config.yaml`, e é assim que o intervalo da perda da máscara foi calculado em
`docs/decisoes/0002`. E o número que vale é o do conjunto de teste separado, não o de validação.
A avaliação do desafio também tira da conta os achados do `annotations_excluded.csv`: candidato
que casa com um deles não conta nem como acerto nem como alarme falso.

## Seleção: a base, e o que ela custou

O repositório nasceu em 03/08/2026 com um README de uma linha. Em 14/08 escrevi a motivação
clínica e declarei o LIDC-IDRI como base. Em 25/08 essa escolha mudou, e virou a decisão 0001.

O enunciado aponta os dois lados: a seção 4.2 dá o LIDC-IDRI aos grupos 3, 4 e 5, e a seção 7.2
dá o LUNA16 ao grupo 5. A decisão 0001 existe para resolver esse conflito, não por preferência.
Adotamos o LUNA16 porque o `candidates.csv` que alimenta o baseline obrigatório só existe nele.
Descartamos reconstruir os volumes a partir do DICOM do LIDC, porque as coordenadas do
`annotations.csv` estão em espaço de mundo definido contra a origem dos `.mhd` do desafio.

Em 26/08 o LIDC-IDRI saiu do projeto, e com ele a anotação individual dos quatro radiologistas.
A figura de concordância entre eles, que a análise exploratória teria, deixou de ser possível.
O LIDC voltou uma única vez, em 30/08, para extrair o mapa de exame para paciente que o LUNA16
não tem, e depois disso nada no projeto volta a lê-lo.

No mesmo 25/08 entrou a estrutura de pastas, num commit só, antes de qualquer trabalho de fase,
para que todo diff seguinte mostrasse trabalho em vez de mudança de organização.

**Até 30/08 trabalhamos com 445 exames**, que eram os subsets 0 a 4, os únicos baixados. Os dez
subsets entraram em disco em 30/08, e todo número medido antes foi refeito sobre os 888 no mesmo
dia. Duas conclusões mudaram com isso, e as duas estão registradas: a máscara de pulmão deixou
de custar zero nódulo e passou a custar um, e o paciente que aparece em duas dobras só apareceu
com o desafio completo, porque nos 445 cada exame era um paciente distinto. Na mesma conferência
verificamos que a cópia em disco é a oficial: a lista de exames fecha com o `seriesuids.csv` do
desafio, sem exame a mais nem a menos.

Os números da base, 888 exames, 601 com nódulo, 287 sem nódulo elegível e 1.186 nódulos, estão
em `docs/01-dados.md`, e os critérios de inclusão e os quatro casos de fronteira estão em
`docs/criterios_inclusao_luna16.md`.

## O que medimos antes de tocar no pré-processamento

**O inventário dos volumes.** O primeiro código que toca a base lê só o cabeçalho `.mhd` de cada
exame, sem abrir o `.raw`, e grava uma linha por exame com origem, espaçamento, dimensões,
matriz de direção, orientação, extensão física em z e tamanho do arquivo. Sai de
`scripts/02_inventario_volumes.py` e vive em `dados/intermediario/inventario_volumes.csv`. A
distribuição de espaçamento e de fatias está em `docs/01-dados.md`.

**A conversão entre milímetro e voxel.** É onde o projeto morre em silêncio se estiver errada,
porque errar não levanta erro nenhum, só desloca o recorte e faz o modelo aprender ruído. São
duas armadilhas, não uma. A primeira é a matriz de direção: 14 dos 888 exames têm orientação
LPI, e a fórmula que ignora a direção joga 24 nódulos para fora do volume. A segunda é a ordem
dos eixos, porque o cabeçalho fala em x, y, z e o array vem em z, y, x, e inverter um sem o
outro erra o lugar em todo volume que não seja cúbico, que é o caso dos 888. As duas estão
descritas em `docs/01-dados.md`, presas por `testes/test_coordenadas.py` e mostradas em
`relatorios/figuras/coordenada_rai.png` e `coordenada_lpi.png`. A figura do exame LPI é a que
prova alguma coisa, porque num exame RAI a fórmula errada também funciona.

**A análise exploratória.** Adotamos a regra de que cada figura responde a uma pergunta que muda
uma decisão de pré-processamento, e figura que não muda decisão nenhuma não entra. Ficaram
cinco: `eda_espacamento_z.png`, que mostra o fator de cinco entre o exame mais fino e o mais
grosso e é o que obriga a reamostrar; `eda_diametro.png`, que dimensiona o recorte;
`eda_nodulos_por_scan.png`, que mostra os 287 exames sem nódulo elegível e obriga a média de
falso positivo a usar 888 no denominador e não 601; `eda_hu.png`, que sustenta a janela de
-1000 a 400; e `eda_desbalanceamento.png`, que sustenta a escolha da métrica. As cinco e o que
cada uma decidiu estão em `docs/02-analise-exploratoria.md`. O `notebooks/01-eda.ipynb` é a
versão navegável delas, e os números dele foram corrigidos duas vezes, em 02/09 quando a base
passou a ser 888 e em 07/09 quando a lista de candidatos mudou.

## Pré-processamento: as cinco etapas

O feedback do professor lista cinco etapas: leitura MetaImage pelo SimpleITK, reamostragem para
1 mm isotrópico, janela de HU de -1000 a 400, normalização para [0, 1] e máscara binária do
parênquima. Chegamos nelas em duas rodadas, com quatro em 29/08 e a quinta em 08/09.

A ordem não é arbitrária, e o porquê de cada passo está em `docs/03-pre-processamento.md`. A
janela vem antes da interpolação, para que um voxel de costela não vaze para dentro do pulmão. A
máscara vem depois da reamostragem, para não interpolar a borda dura entre pulmão e o lado de
fora, e o exterior é preenchido com -1000 HU, que é ar, e não com zero, que na escala Hounsfield
é água. A normalização vem por último, o que faz o preenchimento de fora do pulmão cair
exatamente em zero.

**A rodada na base completa.** Rodei nos 888 exames em 08/09/2026 com
`scripts/07_preprocessar_base.py`, e refiz em 10/09 quando o recorte passou de 32 para 34
voxels. Zero erro nas duas. O relatório por exame fica em
`dados/intermediario/preprocessamento.csv`, e a tabela com tempo, tamanho e dimensões está em
`docs/03-pre-processamento.md`.

**A máscara do desafio é larga demais em 37 exames.** O volume que ela marca como pulmão tem
mediana de 4,87 litros nos 888, da ordem da capacidade pulmonar de um adulto [FONTE?], mas 37
exames passam de 8 litros e o maior chega a 31. Deduzo pelo HU medido dentro dela, que dá -968
nesse exame extremo, que é máscara que vazou para o ar em volta do paciente, que tem a mesma
densidade do ar dentro do pulmão. Não abrimos os 37 um a um para confirmar. Isso não perde
nódulo, região a mais não corta nada. O que custa é área de busca. A medição e a procedência
estão em `docs/03-pre-processamento.md`, e a contagem dos 37 está presa por
`testes/test_base_preprocessada.py`, que guarda quais são os exames e não só quantos.

## As seis decisões registradas

Registramos decisão quando a escolha fecha uma porta. O registro traz a medição que a sustenta e
o que foi descartado, e fica em `docs/decisoes/`. Cinco estão fechadas e uma continua em aberto.

**0001, LUNA16 em vez de LIDC-IDRI.** Fechada em 25/08, atualizada em 26/08 e em 30/08.

**0002, máscara de pulmão sem dilatação.** Fechada em 29/08 e remedida em 30/08 com a base
completa. Usamos a máscara pronta do desafio, sem dilatar, e o custo em nódulos inalcançáveis
está medido no registro, com intervalo de confiança. Descartamos dilatar, porque os raios que a
literatura publica não vêm com métrica que os justifique e dilatar aumenta a região de busca e
portanto o falso positivo, que é o eixo da FROC.

**0003, um paciente aparece em duas dobras.** Em aberto, e é a única. O `config.yaml` afirmava
que cada `seriesuid` é um paciente, e isso é falso: o LUNA16 identifica o exame e não diz quem é
o paciente. Extraímos o mapa uma vez do metadata do LIDC e deu 888 exames para 887 pacientes. O
`LIDC-IDRI-0332` tem duas séries, uma no subset 2 e outra no subset 6, e como os subsets são as
dobras, ele cai em treino e em teste nas duas rodadas em que o subset de teste é o 2 ou o 6. O
efeito numérico é desprezível, um paciente em 887, e o de banca não é, porque a seção 3.1 do
enunciado nomeia esse erro por escrito. As duas saídas estão no registro, e a escolha não foi
feita porque a divisão ainda não existe em código.

**0004, espaçamento alvo de 1 mm.** Fechada em 08/09, atualizada em 10/09. O registro existe
para desfazer uma herança: o valor ficou oito dias no `config.yaml` antes de existir script que
o medisse. A tabela que compara oito espaçamentos por contraste, por nódulos que não cabem no
recorte e por custo em voxels está no registro, e sai de
`scripts/06_escolher_espacamento.py`. Mantivemos 1,0 mm, e declaramos no próprio registro que
1,25 mm não foi descartado por medição, e sim por dois motivos não estatísticos.

**0005, DVC para o pipeline e não para o dado.** Fechada em 07/09. Nada no enunciado exige
ferramenta de versionamento de dado: a lista da seção 3.3 é GitHub, Colab ou Kaggle, Trello,
Drive e `requirements.txt`. Adotamos o DVC por conta própria, porque nada no repositório gravava
de onde o resultado veio. O `dvc.yaml` declara cada estágio com o script, os módulos que ele
importa, o arquivo que lê e as chaves do `config.yaml` que usa, e o `dvc.lock` guarda o hash
disso a cada execução. O dado fica de fora: a base bruta está num HD que é de leitura, e os
volumes pré-processados entram como `cache: false`, o que faz o DVC guardar o hash e não o
conteúdo.

**0006, a normalização entra no volume salvo.** Fechada em 08/09. A dúvida não era escrever a
função, era onde ela roda, porque isso muda o tipo do arquivo em disco. A suspeita de que
guardar float quadruplicaria o disco estava errada, e a medição que mostra isso está no
registro. Ligar a normalização quebrou em silêncio o painel direito da figura de antes e depois,
que virou um retângulo cinza chapado sem levantar erro nenhum, e a primeira versão da função
promovia o volume a float de 64 bits e dobrava o arquivo do mesmo jeito silencioso. Os dois
casos viraram teste em `testes/test_figuras.py` e `testes/test_preprocessamento.py`.

## Como o projeto virou reprodutível

Em 02/09 e 03/09 a árvore mudou de forma, adotando a estrutura que o feedback do professor
sugeriu: `codigo/pi3` virou `src/` com submódulos em inglês, `documentacao/` virou `docs/`, as
pastas vazias saíram e os marcadores viraram README onde a pasta explica algo. Foi um commit que
só move e renomeia, para o diff seguinte voltar a mostrar trabalho. Essa mudança não tem registro
de decisão, e este documento é o único lugar onde ela está escrita.

Quatro coisas seguram a reprodutibilidade, e nenhuma é opinião.

O `configuracao/config.yaml` é o único lugar com caminho e parâmetro numérico. Em 09/09 tiramos
a chave `usar_mascara_do_desafio`, que era parâmetro declarado que nenhum código lia, e pior,
quem pusesse `false` continuaria com a máscara aplicada sem aviso. Em 14/09 corrigimos a
`divisao.chave`, que dizia `seriesuid` embaixo de um comentário dizendo que a divisão é por
paciente, e movemos para o config o último caminho absoluto que ainda estava escrito dentro de
um script.

A semente é fixa em todo script, por `config.fixar_semente()`, que fixa `random`, `numpy` e
`torch`.

Os testes prendem o que não pode quebrar em silêncio. Os que mais importam são os da conversão
de coordenada, que rodam sobre exames reais nos dois extremos de espaçamento em z mais um exame
de direção invertida, e os que verificam que a ordem das etapas do pré-processamento não mudou.

E todo número reportado vai com intervalo de confiança de 95% por bootstrap, com o número de
reamostras declarado no `config.yaml`.

## A auditoria de 09/09

Um bloco de sete commits sem funcionalidade nova, só consertando o que já estava escrito.

As datas do registro estavam erradas em três lugares. Dois trechos diziam o que fazer a seguir
dentro de documento de registro, e saíram, ficando a medição que os sustentava. Dois testes não
pegavam o que a docstring deles prometia: o de vazamento fora do pulmão passava mesmo com a
ordem das etapas trocada, porque o interior do pulmão sintético era -1000 uniforme junto à
borda, e o das máscaras largas comparava só a contagem, então uma máscara saindo e outra
entrando mantinha o total em 37 e passava calado. O DVC apagava as figuras versionadas antes de
rodar o estágio, o que com saída `cache: false` é destrutivo, e reproduzimos isso com o HD
desconectado: o script saiu com código zero e deixou quatro figuras apagadas na árvore. E a
tabela que sustenta a escolha da lista de candidatos não tinha script atrás dela, era contagem
de terminal, então escrevemos o script e a tabela voltou idêntica.

## Transformação: a lista de candidatos

O desafio entrega duas listas de candidatos, e a escolha muda o teto do que dá para alcançar.
Medimos as duas contra os 1.186 nódulos em 03/09, contando à mão, e refizemos em 09/09 com
`scripts/08_comparar_candidatos.py`, com resultado idêntico nas seis colunas. Adotamos o
`candidates_V2`, que alcança 98,3% dos nódulos contra 94,4% da lista antiga. A tabela completa,
o critério de acerto e o custo em pontos a mais estão em `docs/criterios_inclusao_luna16.md`.

Vinte nódulos ficam sem candidato nenhum mesmo no V2, e isso é teto que nenhum modelo recupera
enquanto a lista for essa.

Adotamos também o critério de inclusão do desafio inteiro, sem acrescentar filtro nosso, porque
todo trabalho que publica número no LUNA16 mede sobre exatamente esses 888 exames e esses 1.186
nódulos. Os quatro casos de fronteira estão medidos e escritos no mesmo arquivo, e um deles
mudou o código: dois exames têm espaçamento em z maior que 2,5 mm por um bit de float32, e as
comparações com o limite passaram a usar tolerância em vez de igualdade.

## Transformação: o que veio por branch

Em 10/09 integramos o recorte dos cubos em 3D e o cubo passando de 32 para 34 voxels, e em 13/09
a geração de candidatos por blob detection. Os dois merges preservaram o commit de cada autor na
história.

O recorte trata a borda intersectando a caixa pedida com o volume e preenchendo o resto com
zero, porque cortar por fatiamento direto devolveria um pedaço vazio sem erro nenhum. O cubo de
34 zera a perda a 1 mm: com 32, o nódulo de 32,27 mm não cabia, e com 34 nenhum dos 1.186 fica
de fora. A medição das duas opções lado a lado está na atualização de 10/09 de
`docs/decisoes/0004`, e refiz o pipeline inteiro com o recorte novo.

Onde os dois trabalhos se encontraram, a reconciliação ficou com o que já estava integrado ao
pipeline, aos testes e à decisão registrada. No caso da normalização, comparei as duas versões
voxel a voxel e a maior diferença foi de 5,96e-08, um bit de float de 32 bits, então as duas
valiam o mesmo e o critério não foi qualidade, foi o estado da `main`. O notebook e as figuras
que vieram no branch ficaram de fora porque tinham sido gerados com a lista de candidatos
antiga, que o projeto já não usava desde 07/09.

A geração de candidatos é blob detection 3D por Laplacian of Gaussian sobre os volumes já
pré-processados. O sigma vira raio multiplicando por raiz de três, que é a fórmula do LoG em três
dimensões, e o índice de voxel vira coordenada de mundo pela geometria do próprio arquivo. O
método, os parâmetros e a medição estão em `docs/04-deteccao-de-candidatos.md`.

Conferi a geometria no dado real antes de integrar, porque o módulo novo abre um segundo caminho
de conversão entre milímetro e voxel, independente do que já existia em
`src/preprocessing/coordenadas.py`. Os dois concordam, e isso virou teste em
`testes/test_blobs.py`, que roda sobre três exames reais: os dois extremos de espaçamento em z e
um de direção invertida.

## O que a geração de candidatos entrega hoje

A medição de 13/09/2026, em 8 exames, está em `docs/04-deteccao-de-candidatos.md` com o comando
ao lado. Ela diz duas coisas. A cobertura dos nódulos daquela amostra é total, e a lista sai com
16 vezes mais pontos por exame que o `candidates_V2`.

O diagnóstico de por que ela sai larga, que é a escala em que os blobs aparecem e a resposta da
parede da máscara de pulmão, foi levantado em 13/09 mas ainda não tem script versionado, então
não entra como medição do projeto enquanto não tiver. A calibração dos parâmetros é a etapa
seguinte da Transformação.

## A limpeza de 14/09

O cache do DVC guardava uma segunda cópia inteira dos 888 volumes, resto de uma rodada anterior
à declaração `cache: false`. Antes de liberar, conferimos a integridade da cópia de trabalho
contra o `dvc.lock`, comparando contagem de arquivos e tamanho total, e usamos `dvc gc
--all-commits`, que preserva os objetos ainda em uso, em vez de apagar a pasta. Saiu também uma
pasta `src/pi3` que só guardava bytecode do layout de antes de 02/09.

Na mesma varredura corrigimos o que os documentos afirmavam e não era mais verdade. Os números
que envelheceram foram o tempo do pré-processamento, que estava como a rodada de 08/09 em quatro
arquivos quando a rodada que está em disco é a de 10/09, a contagem de testes, a contagem de
estágios do DVC e a mediana de fatias. Dois eram erro de fato e não de envelhecimento: a decisão
0003 dizia que o paciente repetido cai em treino e em teste em oito das dez rodadas, quando por
enumeração são duas, e o `docs/criterios_inclusao_luna16.md` dizia que o espaçamento de
2.500000238418579 era a representação de 2,5 em float32, quando é o float seguinte a ele. O
README foi atualizado no que descrevia um estado do projeto que já tinha passado, e a receita de
reprodução ganhou os três scripts que faltavam.

## O que está em aberto

O tratamento do paciente que aparece em duas dobras, que é a decisão 0003. Ele segue sem escolha
porque a divisão entre treino, validação e teste não existe nem em código nem em disco, e é ela
que a seção 3.1 do enunciado cobra por paciente.

O valor de preenchimento de fora do pulmão, que é -1000 HU no nosso pipeline e cinza médio na
linhagem grt123, sem medição que compare os dois. Vira experimento quando houver modelo.

O recorte dos cubos ao redor de cada candidato tem código e teste e nunca rodou na base.

O baseline não existe. Ele é o classificador de redução de falsos positivos sobre a lista de
candidatos, que a seção 4.3 do enunciado descreve, e não existe nem para a lista pronta do
desafio nem para a lista que geramos. Com ele não existem as features de intensidade, o modelo
treinado e a avaliação FROC. O script oficial de avaliação do desafio está em Python 2 e não foi
portado.

A rodada da geração própria de candidatos nos 888 exames não aconteceu, e os parâmetros do blob
detection continuam sendo os de partida, sem calibração medida.

Os estágios do DVC não cobrem os dois últimos scripts, o de recorte e o de detecção.

Não há remote de DVC, então `dvc push` e `dvc pull` não funcionam para o resto do grupo, porque
a base foi baixada por conta própria em cada máquina.

Nenhum modelo treinado, e a tabela de `modelos/README.md` está vazia.

A pergunta de pesquisa não está escrita. O documento de revisão de literatura também não existe,
e o que já foi lido e usado está dentro da decisão 0002, que cita nove referências, três delas
de 2020 em diante.
