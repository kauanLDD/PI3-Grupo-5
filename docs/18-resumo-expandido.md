# Resumo expandido, rascunho de 04/11/2026

Texto do resumo expandido (cartão S4 | T18). Todos os números de desempenho saem do avaliador
oficial do LUNA16; a fonte de cada um está nos comentários `<!-- -->` e na seção "Conferência" no
fim, que não entra no documento final. O modelo de formatação (fonte, margens, seções) ainda não
chegou; quando chegar, este texto é encaixado nele e cortado até quatro páginas.

---

## Detecção de nódulos pulmonares no LUNA16: rede convolucional 3D contra baseline de Random Forest, avaliados com o programa oficial do desafio

Kauan Felipe Nascimento da Silva, Náthaly Alessandra Batistella, Arthur Nicolas Oliveira,
Samuel Gonçalves Malta, Gabriel Schraider da Silveira, Lucas Gabriel Teixeira da Silva

Projeto Integrador de Extensão III, Inteligência Artificial, Biopark, 2026/2

### Resumo

A detecção de nódulos pulmonares em tomografia computadorizada exige alta sensibilidade com
poucos alarmes falsos por exame. Este trabalho compara um baseline de Random Forest sobre
estatísticas de intensidade com uma rede convolucional 3D na redução de falsos positivos da lista
oficial de candidatos do LUNA16 (888 exames, 1.186 nódulos). Os volumes foram janelados entre
−1000 e 400 HU, reamostrados para 1 mm isotrópico, escolha apoiada na comparação medida de oito
espaçamentos, e restritos à máscara de pulmão. A divisão foi feita por paciente: treino nos
subsets 0 a 6, validação no 7 e teste no 8 e no 9. As configurações foram escolhidas na
validação, e cada modelo congelado foi avaliado uma única vez no teste com o programa oficial do
desafio e intervalo de confiança de 95% por bootstrap. No teste (176 exames, 223 nódulos), a rede
obteve CPM de 0,724 (IC95% 0,670 a 0,778) e sensibilidade de 0,883 a 4 falsos positivos por exame
(0,843 a 0,929), acima da meta de 0,80. O Random Forest obteve CPM de 0,420 (0,349 a 0,490) e
0,520 a 4 falsos positivos, abaixo da meta de 0,70.

**Palavras-chave:** nódulo pulmonar; tomografia computadorizada; LUNA16; FROC; rede
convolucional 3D.

### 1. Introdução

O câncer de pulmão é a principal causa de morte por câncer no mundo, e a sobrevida depende de o
nódulo ser encontrado cedo. Em tomografia de tórax, o problema é achar estruturas de 3 a 30 mm em
volumes de centenas de fatias, sem encher o exame de alarmes: um detector com mil marcas por
exame não serve ao radiologista. Por isso a métrica não é a acurácia, mas a curva FROC, que
relaciona a sensibilidade à média de falsos positivos por exame. No nosso conjunto, só 0,21% dos
candidatos são nódulo, e responder sempre "não é nódulo" acertaria 99,79%.

O desafio LUNA16 (Setio et al., 2017) padronizou essa avaliação: 888 exames do LIDC-IDRI (Armato
et al., 2011), uma lista oficial de candidatos e um programa que calcula a FROC e o CPM, a média
da sensibilidade em 0,125, 0,25, 0,5, 1, 2, 4 e 8 falsos positivos por exame. Este trabalho trata
da etapa de redução de falsos positivos: dado um candidato, decidir se é nódulo. A pergunta é se
uma rede convolucional 3D supera um classificador simples sobre estatísticas de intensidade, com
as metas definidas no início do projeto: sensibilidade de 0,70 a 4 falsos positivos por exame
para o baseline e de 0,80 para a rede. O trabalho segue as etapas do KDD (Fayyad et al., 1996).

### 2. Materiais e métodos

**Dados.** O LUNA16 tem 888 exames e 1.186 nódulos de 3 mm ou mais, marcados por pelo menos três
de quatro radiologistas. Usamos a lista de candidatos V2 do desafio, com 754.975 candidatos, que
alcança 1.166 dos 1.186 nódulos; os outros 20 não têm candidato e nenhum classificador os
recupera. Seguindo o protocolo oficial, 35.192 achados excluídos pelo desafio (lesões que não
atingiram o consenso) não contam nem como acerto nem como falso positivo.

**Pré-processamento.** Os valores foram limitados à janela de −1000 a 400 HU, que mantém 98,3%
dos voxels do pulmão numa amostra de 30 exames, antes da reamostragem, para que o osso não vaze
para o pulmão na interpolação. Depois veio a reamostragem, a máscara de pulmão do desafio sem
dilatação e a normalização para o intervalo [0, 1].

**Escolha do espaçamento.** Os exames têm espaçamento entre fatias de 0,45 a 2,5 mm. Sem
reamostrar, um nódulo de 6 mm ocupa treze fatias num exame e duas em outro, e o modelo aprenderia
a espessura de corte em vez do nódulo. O enunciado manda reamostrar, mas não diz para quanto, e
o valor de 1 mm estava na configuração desde o início sem medição. Por isso comparamos oito alvos,
de 0,5 a 2,0 mm, em três critérios: o contraste do nódulo com o tecido em volta (diferença entre
as medianas de HU, em 39 nódulos estratificados por diâmetro, com IC95% por bootstrap), quantos
dos 1.186 nódulos deixam de caber no recorte e o custo em voxels. Abaixo de 1 mm o contraste não
melhora: os intervalos de 0,5 a 1,0 mm se sobrepõem (245 HU, IC95% 192 a 282, a 1,0 mm), e 0,5 mm
custa oito vezes mais voxels e deixa 94 nódulos maiores que o recorte de 34 voxels. Acima de 1 mm
o contraste cai, e a 2,0 mm o intervalo (94 a 165 HU) já não toca o de 1,0 mm. A 1,0 mm nenhum
nódulo fica fora do recorte. A medição não separa 1,0 de 1,25 mm (180 HU, IC95% 130 a 242), que
custaria metade dos voxels; mantivemos 1,0 mm por ser o valor usado na literatura do LUNA16, o que
evita uma diferença de método sem ganho medido.

**Divisão por paciente.** Os 888 exames são de 887 pacientes: um paciente tem duas séries em
subsets diferentes, e ambas ficaram no treino. O treino usa os subsets 0 a 6 (623 exames), a
validação o subset 7 (89 exames, 111 nódulos) e o teste os subsets 8 e 9 (176 exames, 223
nódulos). Os scripts recusam rodar se um paciente aparecer em duas partições.

**Recortes.** Para cada candidato, um cubo de 34 voxels (34 mm) centrado nele: 754.975 recortes,
sem falhas, cada um com o hash do volume de origem.

**Baseline.** Random Forest de 200 árvores com as estatísticas pedidas no enunciado (média, desvio
padrão, curtose, mínimo, máximo e percentis 25 e 75). Calculadas sobre o cubo inteiro, deram CPM
de 0,003 na validação: o nódulo típico tem 6,4 mm e se dilui no cubo de 34 mm. Antes de corrigir,
testamos e descartamos quatro causas de erro de pipeline (dados diferentes dos da rede, rótulo
deslocado, coluna de probabilidade invertida e conjuntos de candidatos diferentes). A versão final
calcula as mesmas sete estatísticas em três cubos concêntricos de 8, 16 e 34 voxels.

**Rede convolucional 3D.** Três blocos convolucionais 3D (16, 32 e 64 canais, com normalização em
lote, ReLU e max pooling), média global, dropout de 0,3 e duas camadas densas, sobre o cubo
central de 32 voxels. Treino com Adam e entropia cruzada, com todos os 1.098 positivos de treino
e lotes equilibrados por amostragem ponderada.

**Protocolo.** As regras foram fixadas antes dos experimentos: uma mudança por vez sobre a melhor
versão anterior, no máximo cinco variantes, todas comparadas só na validação, com diferença
pareada e IC95%. A configuração escolhida (40 épocas, 20 negativos por positivo, aumento de dados,
learning rate de 0,0003) foi congelada, com o hash dos pesos registrado, antes de abrir o teste.
O teste foi usado duas vezes, cada uma para um único modelo já congelado: a rede em 13/10/2026 e
o Random Forest em 26/10/2026, este só para a comparação. Nenhum resultado do teste voltou para
escolher configuração.

**Avaliação.** Usamos o programa oficial do LUNA16 (`noduleCADEvaluationLUNA16.py`), convertido de
Python 2 para Python 3 só na sintaxe, com no máximo 100 marcas por exame, os achados excluídos e
1.000 reamostras de bootstrap por exame para o IC95%. Antes de usá-lo, conferimos a conversão
contra a saída de exemplo distribuída com o desafio: os sete pontos da FROC e o CPM são iguais.

### 3. Resultados

A Figura 1 traz a curva FROC inteira dos dois modelos no teste, e a Tabela 1, os sete pontos.

**Figura 1.** Curva FROC no conjunto de teste (176 exames, 223 nódulos), pelo avaliador oficial
do LUNA16. Linha: curva completa. Pontos: os sete pontos oficiais, com IC95%. Faixa: IC95% do
bootstrap por exame (1.000 reamostras).
<!-- arquivo: relatorios/experimentos/comparacao_teste/froc.png -->

**Tabela 1.** Sensibilidade por taxa de falsos positivos por exame no teste, com IC95% no CPM e
nos pontos de 1 e 4.

| Modelo | 0,125 | 0,25 | 0,5 | 1 | 2 | 4 | 8 | CPM (IC95%) |
|---|---|---|---|---|---|---|---|---|
| CNN 3D | 0,457 | 0,574 | 0,641 | 0,735 (0,659 a 0,819) | 0,852 | 0,883 (0,843 a 0,929) | 0,924 | 0,724 (0,670 a 0,778) |
| Random Forest | 0,283 | 0,332 | 0,354 | 0,381 (0,314 a 0,460) | 0,480 | 0,520 (0,442 a 0,603) | 0,587 | 0,420 (0,349 a 0,490) |

A rede superou a meta de 0,80 a 4 falsos positivos por exame com o intervalo inteiro acima dela.
O Random Forest ficou abaixo da meta de 0,70, também com o intervalo inteiro abaixo. Como os dois
modelos foram avaliados com as mesmas reamostras, a diferença de CPM pode ser medida reamostra a
reamostra: 0,304 a favor da rede (IC95% 0,247 a 0,360).

Na validação, cada mudança da rede foi medida contra a anterior. As 40 épocas acrescentaram 0,255
de CPM (IC95% 0,173 a 0,322), os 20 negativos por positivo 0,171 (0,107 a 0,256) e o learning
rate maior 0,055 (0,014 a 0,085); o aumento de dados não se distinguiu de zero (0,003, IC95%
−0,054 a 0,055). O CPM de validação passou de 0,268 para 0,752. Repetido com as sementes 43 e 44,
o treino deu 0,790 nas duas, com desvio padrão de 0,022 entre as três. O CPM do teste ficou 0,028
abaixo do da validação.

### 4. Discussão

**Comparação com a literatura.** A comparação justa é com a trilha de redução de falsos positivos
do LUNA16, que usa a mesma lista V2 (Setio et al., 2017). Lá os CPMs vão de 0,758 (ZNET) a 0,908
(CUMedVis). O nosso 0,724 fica abaixo de todos, mas o ZNET cai dentro do nosso intervalo. Os
trabalhos com CPM acima de 0,90 que geram os próprios candidatos medem o sistema completo e não
são comparáveis diretamente. Os artigos reportam a média de dez dobras sem intervalo; nós
reportamos uma avaliação em dois subsets, com intervalo.

**Onde a rede perde.** A distância para o vencedor está nas taxas baixas de falso positivo: 0,457
a 0,125 FP por exame, contra 0,677. A 8 FP por exame ficamos em 0,924, perto dos sistemas do
desafio. A rede acha os nódulos, mas põe falsos positivos acima deles no ranking do exame: dos 26
nódulos perdidos a 4 FP, 21 receberam marca, e 18 dessas marcas tiveram escore de 0,80 ou mais.
A sensibilidade a 4 FP cai com o tamanho (0,804 entre 3 e 5 mm, 0,969 acima de 10 mm). Nódulos a
até 3 mm da parede do pulmão são 35% dos perdidos e 13% dos achados (teste exato de Fisher,
p = 0,007): os dois maiores perdidos tiveram parte cortada pela máscara sem dilatação. Entre os
50 falsos positivos de maior escore, o tipo mais frequente, na nossa leitura visual sem
radiologista, é a marca ao lado de um nódulo verdadeiro. Como hipótese não medida, os sistemas
melhores combinam várias escalas ou vistas e treinam em cerca de 800 exames, contra os nossos 623
e uma única escala.

**O baseline.** A queda de 0,003 para 0,409 de CPM na validação mostra que o problema do Random
Forest não era o classificador, mas onde as estatísticas eram medidas. Mesmo corrigido, ele não
atingiu a meta, e a rede o supera em todos os pontos da curva.

**Limitações.** O teste foi usado duas vezes, uma por modelo, e a comparação entre os dois é
descritiva. A configuração da rede foi escolhida entre cinco versões na mesma validação de 89
exames, e o número de validação tende a ser otimista. Os modelos usam a lista V2: a busca própria
de candidatos do grupo alcança 97,6% dos nódulos, mas ainda não passou por classificador. Na GPU,
o PyTorch não garante pesos idênticos entre execuções. Nenhum modelo deste trabalho é dispositivo
médico, e nenhum deve ser usado em decisão clínica.

### 5. Conclusão

A rede convolucional 3D atingiu a meta de sensibilidade a 4 falsos positivos por exame no
teste, e o baseline de Random Forest não atingiu a dele. A rede supera o baseline em toda a curva
FROC, com CPM 0,304 maior. A distância para os melhores sistemas do LUNA16 está nas taxas baixas
de falso positivo, e os próximos passos são recortes em mais de uma escala, máscara de pulmão
dilatada para os nódulos de parede e a classificação dos candidatos da busca própria. Código,
configuração e avaliações estão em https://github.com/kauanLDD/PI3-Grupo-5.

### Referências

ARMATO, S. G. et al. The Lung Image Database Consortium (LIDC) and Image Database Resource
Initiative (IDRI): a completed reference database of lung nodules on CT scans. **Medical
Physics**, v. 38, n. 2, p. 915-931, 2011.

DOU, Q. et al. Multilevel contextual 3-D CNNs for false positive reduction in pulmonary nodule
detection. **IEEE Transactions on Biomedical Engineering**, v. 64, n. 7, p. 1558-1567, 2017.

FAYYAD, U.; PIATETSKY-SHAPIRO, G.; SMYTH, P. From data mining to knowledge discovery in
databases. **AI Magazine**, v. 17, n. 3, p. 37-54, 1996.

SETIO, A. A. A. et al. Pulmonary nodule detection in CT images: false positive reduction using
multi-view convolutional networks. **IEEE Transactions on Medical Imaging**, v. 35, n. 5,
p. 1160-1169, 2016.

SETIO, A. A. A. et al. Validation, comparison, and combination of algorithms for automatic
detection of pulmonary nodules in computed tomography images: the LUNA16 challenge. **Medical
Image Analysis**, v. 42, p. 1-13, 2017.

---

## Conferência (não entra no documento final)

| Número no texto | Fonte |
|---|---|
| 0,21% de positivos, 99,79% de acurácia trivial | `docs/02-analise-exploratoria.md` |
| 754.975 candidatos, 1.166 nódulos alcançados, 35.192 excluídos | `docs/13-dossie-modelagem.md`, seção 3 |
| 98,3% dos voxels na janela | `docs/03-pre-processamento.md` |
| Oito espaçamentos, 245, 180 e 94 a 165 HU, 94 nódulos fora a 0,5 mm | `docs/decisoes/0004-espacamento-alvo-de-1-mm.md`, tabela e atualização de 10/09 |
| Divisão, 623, 89 e 176 exames, 111 e 223 nódulos | decisão 0003; `docs/13`, seção 5 |
| Diagnóstico do Random Forest, CPM 0,003 e 0,409 | `docs/10-comparacao-validacao.md`; `docs/13`, seções 9.3 e 9.6 |
| Variantes e diferenças pareadas da rede | `docs/11-experimentos-validacao.md`; `docs/13`, seção 9.5 |
| Congelamento e os dois usos do teste | decisões 0008 e 0009 |
| Pontos e IC da rede no teste | `modelos/cnn_lr_3e-4_teste_final/pontos_operacao.csv` e `avaliacao.json` |
| Pontos e IC do Random Forest no teste | `modelos/random_forest_centro_teste_final/pontos_operacao.csv` e `avaliacao.json` |
| Diferença de CPM de 0,304 (0,247 a 0,360) | `docs/14-baseline-literatura-sementes-e-teste-rf.md` |
| Sementes 43 e 44 | `relatorios/experimentos/sementes_cnn/resumo.json` |
| Conferência do avaliador contra o exemplo | `docs/17-avaliador-oficial-contra-o-do-grupo.md` |
| Literatura, 0,758 a 0,908, 0,677 a 0,125 FP | `docs/16-comparacao-literatura.md` |
| Erros: 26 perdidos, 21 com marca, parede, tipos de FP | `docs/15-analise-de-erros-cnn.md` |
| Figura 1 | `relatorios/experimentos/comparacao_teste/froc.png` |
