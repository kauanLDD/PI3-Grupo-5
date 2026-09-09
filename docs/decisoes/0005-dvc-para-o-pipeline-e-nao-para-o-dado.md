# 0005: usamos o DVC para o pipeline e não para guardar o dado

**Estado:** decidido
**Data:** 07/09/2026

## Contexto

Até aqui a rastreabilidade do projeto era git mais disciplina de escrita. O `.gitignore` corta
dado e peso, o `config.yaml` é o único lugar com caminho e parâmetro, a semente é fixada por
`config.fixar_semente()`, os scripts são numerados na ordem de execução, e todo número em
documento vem com o script e a data que mediu.

Isso funciona e é honesto, mas é manual. **Nenhum script grava de onde veio o resultado.** Se
alguém mudar o espaçamento alvo no `config.yaml` e rodar de novo, nada no repositório detecta que
as figuras passaram a sair de outro parâmetro. A ligação entre código e resultado existe porque
uma pessoa reescreve o documento quando o número muda.

A aula 05 de MLOps, dada em 26/08, apresentou o DVC como resposta a exatamente esse problema. O
enunciado do PIEX3 não exige ferramenta de versionamento de dados: a seção 3.3 lista GitHub,
Colab ou Kaggle, Trello, Drive e `requirements.txt`, e a seção 5.5 define reprodutibilidade como
semente fixa, `requirements.txt`, README com instruções e código no GitHub. O feedback do
Checkpoint 1 pede "salvar com estrutura versionada e commitar o script no GitHub", sem nomear
ferramenta.

Ou seja, ninguém nos obriga. Adotamos porque o buraco descrito acima é real.

## A decisão

Usamos o DVC para **declarar o pipeline**, não para guardar o dado.

Entra no git: `dvc.yaml` com os cinco estágios, `dvc.lock` com o hash de cada entrada, parâmetro
e saída, e `.dvc/config`. O cache fica em `.dvc/cache`, no disco interno, fora do git. Não
configuramos remote.

As figuras são declaradas com `cache: false`. Elas continuam versionadas no git, porque a mesma
imagem vai para o Sprint Review e depois para o paper. O DVC guarda o hash, o git guarda o
arquivo.

Os parâmetros são lidos direto do `configuracao/config.yaml`, e não de um `params.yaml` novo na
raiz. Declaramos por chave, então `seed`, `selecao.subsets` e o bloco `pre_processamento` entram
no lock, e os caminhos ficam de fora de propósito: eles mudam de máquina para máquina e cada um
do grupo aponta para onde a base está na dele.

## Por que não guardar o dado

Medido em 07/09/2026 com `du -sh` e com `git ls-files | xargs stat`:

| | |
|---|---|
| Base bruta em `luna/archive` | 112 GB |
| O que o pipeline já escreveu em `dados/` | 60 MB |
| O que o git versiona hoje | 49 arquivos, 1,3 MB |

A base bruta não cabe e nem deveria entrar. Ela é pública, vem do Zenodo, tem md5 conferido
contra os arquivos oficiais, e o HD onde ela vive é de leitura por regra nossa. O `dvc add`
faz o oposto: move o arquivo para o cache e deixa um link no lugar.

Guardar a saída também não fecha. Os 888 volumes pré-processados dariam cerca de 5,9 GiB, que é
o tamanho de um volume em inteiro de 16 bits vezes 888. Os recortes dos 754.975 candidatos dariam
de 23 a 92 GiB, que é o número de candidatos vezes um cubo de 32 voxels de aresta, a 1 byte e a 4
bytes por voxel. Isso é aritmética, não medição de arquivo que exista.

Duas ressalvas sobre esses dois números, que ficaram desatualizados no mesmo dia. A decisão 0006
passou a gravar o volume normalizado em float de 32 bits, e o que ficou em disco são 8,6 GiB e não
5,9. A decisão 0004 mostrou que o recorte precisa ter 34 voxels de aresta e não 32, o que leva a
estimativa dos recortes para 28 a 111 GiB. O argumento não muda com isso: em qualquer das
versões não temos onde pôr. Não temos onde pôr: o GitHub e o Drive gratuitos ficam ordens de grandeza abaixo disso, e
esses limites são os que as duas empresas publicam, não algo que tenhamos conferido nesta data.

## O que fica de fora do grafo, e por quê

**A base bruta não é dependência de estágio nenhum.** O lock não detectaria a base mudar. Aceitamos
porque já conferimos o md5 dos três CSV contra os oficiais do desafio e a lista de exames em disco
contra o `seriesuids.csv`, e porque o HD é de leitura.

**O `01_pacientes.py` não é estágio.** Ele lê o metadata do LIDC-IDRI, que saiu do projeto na
decisão 0001. Se virasse estágio, `dvc repro` tentaria reexecutá-lo e quebraria em qualquer
máquina sem o LIDC. O `pacientes.csv` é artefato produzido uma vez.

**Não há remote.** `dvc push` e `dvc pull` não funcionam para o grupo hoje. Cada um baixou a base
do Zenodo por conta própria e ninguém além de uma máquina tem os 112 GB. Fica em aberto.

## O que descartamos

**Git LFS.** Resolve arquivo grande no git e não resolve a pergunta que temos, que é qual código e
qual parâmetro produziram qual resultado.

**`dvc add` na base bruta.** Criaria uma segunda cópia por hash dos 112 GB e exigiria escrever no
HD, o que a regra do projeto proíbe.

**Um `params.yaml` na raiz, do jeito que o laboratório da aula fez.** Seria uma segunda camada de
configuração em cima do `config.yaml`, que já é o único lugar de parâmetro.
