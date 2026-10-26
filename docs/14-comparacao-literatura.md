# Comparação com a literatura, 26/10/2026

Pedido do professor no feedback da Sprint 4 (orientação 7): uma baseline da literatura para
dizer se o CPM de 0,724 no teste (`docs/12-avaliacao-final-teste.md`) é bom.

Os números abaixo foram copiados das tabelas dos artigos originais, não de tabelas de terceiros.

## Tabela

| Trabalho | Base | Lista de candidatos | Divisão dos dados | Métrica | Valor |
|---|---|---|---|---|---|
| Li et al. 2025, Sci. Rep. 15:12313 | LUNA16, 888 exames, 1.186 nódulos | Própria: RPN 3D multiescala com atenção | 10 dobras pelos subsets oficiais | CPM | 0,929 |
| Zheng et al. 2022, Diagnostics 12(11):2660 (TSND) | LUNA16, 888 exames, 1.186 nódulos | Própria: MSFD-Net, cerca de 7,5 candidatos por exame, mais uma rede de redução de FP | 10 dobras pelos subsets oficiais | CPM | 0,906 |
| Setio et al. 2017, Med. Image Anal. 42:1-13, desafio LUNA16, trilha de redução de FP, 1º lugar (CUMedVis) | LUNA16, 888 exames, 1.186 nódulos | Oficial V2: 754.975 candidatos, alcança 1.166 nódulos | 10 dobras pelos subsets oficiais | CPM | 0,908 |
| Idem, outros sistemas da mesma trilha | Idem | Oficial V2 | 10 dobras | CPM | JackFPR 0,872; DIAG_CONVNET 0,854; CADIMI 0,783; ZNET 0,758 |
| Dou et al. 2017, IEEE TBME 64(7), doi 10.1109/TBME.2016.2613502 | LUNA16, 888 exames, 1.186 nódulos | Oficial V1: 551.065 candidatos, alcança 1.120 nódulos | 10 dobras pelos subsets oficiais | CPM | 0,827 |
| **Grupo 5, CNN `cnn_lr_3e-4`** | LUNA16, teste com 176 exames e 223 nódulos | Oficial V2; 218 dos 223 nódulos com candidato | Treino subsets 0 a 6, validação 7, teste 8 e 9, uma única avaliação | CPM (IC95%) | **0,724 (0,670 a 0,778)** |

O que cada coluna "lista de candidatos" quer dizer:

- **Própria**: o artigo mede o sistema completo. Ele gera os candidatos e depois os pontua.
  Com poucos candidatos por exame, há pouca chance de falso positivo.
- **Oficial**: o trabalho só classifica uma lista entregue pelo desafio, como nós. O teto de
  sensibilidade é a cobertura da lista: 1.166/1.186 = 0,983 no V2 e 1.120/1.186 = 0,944 no V1.
  No nosso teste, 218/223 = 0,978.

## Curva FROC ponto a ponto

Sensibilidade em cada taxa de FP por exame:

| Trabalho | Lista | 0,125 | 0,25 | 0,5 | 1 | 2 | 4 | 8 | CPM |
|---|---|---|---|---|---|---|---|---|---|
| Li et al. 2025 | Própria | 0,773 | 0,888 | 0,945 | 0,971 | 0,977 | 0,977 | 0,977 | 0,929 |
| Zheng et al. 2022 | Própria | 0,771 | 0,849 | 0,905 | 0,940 | 0,957 | 0,960 | 0,960 | 0,906 |
| CUMedVis (desafio) | V2 | 0,677 | 0,834 | 0,927 | 0,972 | 0,981 | 0,983 | 0,983 | 0,908 |
| DIAG_CONVNET (desafio) | V2 | 0,669 | 0,760 | 0,831 | 0,892 | 0,923 | 0,945 | 0,960 | 0,854 |
| ZNET (desafio) | V2 | 0,511 | 0,630 | 0,720 | 0,793 | 0,850 | 0,884 | 0,915 | 0,758 |
| Dou et al. 2017 | V1 | 0,677 | 0,737 | 0,815 | 0,848 | 0,879 | 0,907 | 0,922 | 0,827 |
| **Grupo 5** | V2 | 0,457 | 0,574 | 0,641 | 0,735 | 0,852 | 0,883 | 0,924 | 0,724 |

Fontes: Li et al., tabela de comparação final; Zheng et al., tabela 6 do PDF; Setio et al.
2017, tabelas 2 e 3 (arXiv 1612.08012); Dou et al. 2017, tabela II; Grupo 5,
`modelos/cnn_lr_3e-4_teste_final/pontos_operacao.csv`.

## Leitura

**Comparação justa.** A linha que mede a mesma tarefa que nós é a da trilha de redução de FP do
desafio, que usa a mesma lista V2. Os dois artigos escolhidos como baseline, Li e Zheng, medem
outra tarefa: geram os próprios candidatos, com poucos candidatos por exame. Eles mostram aonde
a área chegou, mas não são a régua da nossa etapa.

**Onde ficamos.** Na mesma lista V2, o CPM de 0,724 fica abaixo de todos os sistemas da trilha
de redução de FP. O mais próximo é o ZNET, com 0,758, que cai dentro do nosso IC95% (0,670 a
0,778). Até o CADIMI, com 0,783, a distância é pequena. Do vencedor, CUMedVis com 0,908, nos
separam 0,18. Ficamos 0,10 abaixo de Dou et al. 2017, que usa a lista V1, com teto menor. Em
relação a Li e Zheng, ficamos cerca de 0,2 abaixo, mas a comparação não é direta.

**Onde está a diferença.** A distância vem quase toda das taxas baixas de FP. A 0,125 FP por
exame temos 0,457, contra 0,677 do CUMedVis. A 8 FP por exame temos 0,924, contra 0,960 do
DIAG_CONVNET e 0,915 do ZNET. Ou seja, a rede acha os nódulos, mas ainda coloca muitos falsos
positivos acima deles no topo do ranking de cada exame.

**Por quê, em hipóteses.** Não medimos estas causas; são as diferenças de método que os artigos
descrevem e nós não temos:

1. **Uma escala só.** Nossa CNN vê um cubo de 34 mm. Dou et al. juntam três redes com
   recortes de tamanhos diferentes. DIAG_CONVNET combina nove vistas 2D. Cada uma sozinha no
   artigo de Dou fica entre 0,46 e 0,55 a 0,125 FP; a fusão chega a 0,677.
2. **Menos dados de treino.** Com 10 dobras, cada modelo do artigo treina em 9 subsets, cerca de
   800 exames. Nós treinamos em 623, porque separamos validação e teste fixos.
3. **Redes pequenas e sem conjunto.** Três blocos convolucionais, um modelo, cinco variantes
   testadas (`docs/11-experimentos-validacao.md`).

**Cuidado com a comparação.** Os artigos reportam a média das 10 dobras sobre os 888 exames, sem
intervalo. Nós reportamos uma avaliação nos subsets 8 e 9, com IC95% de ±0,054. A diferença
para o ZNET não é distinguível pelo nosso intervalo; a diferença para o CUMedVis e para os
sistemas completos é.

**Meta do enunciado.** A meta para a CNN, 0,80 de sensibilidade a 4 FP por exame, foi atingida
no teste: 0,883 (IC95% de 0,843 a 0,929).

Uma observação: na tabela de comparação de Li et al., a linha "Zhu et al. [15]" traz os sete
pontos da fusão de Dou et al. 2017, cuja média é 0,827, mas com CPM 0,842. Por isso copiamos
os números dos artigos originais.

## Para o slide

> Na mesma lista V2 do desafio, nosso CPM de 0,724 fica abaixo dos sistemas da trilha de
> redução de FP do LUNA16 (0,758 a 0,908) e perto do último deles, o ZNET (0,758, dentro do nosso
> IC95%). Os artigos de 0,906 e 0,929 medem o sistema completo, com candidatos próprios, e não
> são comparáveis diretamente. A perda está nas taxas baixas de FP (0,457 a 0,125 FP contra
> 0,677 do vencedor): usamos uma única escala de recorte e uma rede pequena, enquanto os melhores
> combinam várias escalas ou vistas e treinam em cerca de 800 exames.
