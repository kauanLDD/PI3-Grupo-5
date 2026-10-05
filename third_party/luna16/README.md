# Avaliador LUNA16

Os quatro arquivos Python são cópias sem alterações do pacote `evaluationScript`
distribuído com o LUNA16, obtidas em 05/10/2026 de
`G:/Meu Drive/PI3-Grupo-5/Dataset/evaluationScript/evaluationScript`.
Referência: [avaliação do desafio](https://luna16.grand-challenge.org/Evaluation/).
As tabelas de anotações continuam fora do Git.

`src/experimentos/avaliacao_oficial.py` cria uma cópia temporária para Python 3:

- `print` e `iteritems` passam à sintaxe atual.
- CSV é aberto em texto, com `newline=""`.
- Matplotlib usa `base`, `visible` e `bbox_inches=None`.
- Sem nenhum positivo detectado, o TPR `NaN` devolvido pelo sklearn passa a
  sensibilidade zero: nenhum acerto dividido pelo total de nódulos anotados.
  A mesma correção se aplica às reamostras de bootstrap sem acertos.

As distâncias físicas, as marcações excluídas, o limite oficial de
100 marcas por exame e o bootstrap permanecem no programa original.
Cada avaliação grava os SHA-256 dos arquivos originais e das cópias adaptadas,
semente, configuração e log de execução em `avaliacao.json` e `avaliador.log`.

Os `.py` originais usam Python 2; execute-os pelo adaptador, não diretamente.
