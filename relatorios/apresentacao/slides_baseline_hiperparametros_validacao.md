# Conteúdo de três slides

Fonte de cada número: `docs/14-baseline-literatura-sementes-e-teste-rf.md`. Onde está escrito
**pendente**, o número ainda não existe e não pode ir para o slide como resultado.

---

## Slide 1 — Baseline e referências da literatura

**Baseline:** o ponto de partida que um método novo precisa superar, medido do mesmo jeito.

| Referência | O que fez | CPM |
|---|---|---:|
| Li et al., 2025 (Sci. Rep.) | Detector 3D com atenção + redução de FP | 0,929 |
| Zheng et al., 2022 (Diagnostics) | Detector 3D multiescala + redução de FP | 0,906 |
| Desafio LUNA16, trilha de redução de FP (Setio et al., 2017) | CNNs sobre a mesma lista de candidatos | 0,758 a 0,908 |

> Protocolos diferentes: os artigos geram os próprios candidatos e fazem 10 dobras sobre os 888
> exames; nós classificamos a lista V2 e medimos num teste fixo de 176 exames.

**Nosso baseline:** Random Forest centro — CPM 0,420 no teste (0,409 na validação). Nossa CNN: CPM
0,724 no teste. Gráfico das duas no teste: `relatorios/experimentos/comparacao_teste/froc.png`.

**Nossas metas** (sensibilidade a 4 FP por exame, não CPM): baseline ≥ 70% · CNN ≥ 80%.

*Fala sugerida:* "Os artigos mostram onde está o estado da arte, mas não são uma régua direta: o
mais parecido com o nosso protocolo é a trilha de redução de falsos positivos do próprio
desafio. As metas são em sensibilidade a 4 falsos positivos, um ponto da curva, e não em CPM."

Referências: Li et al. (2025), DOI 10.1038/s41598-025-97187-w, confirmado pelo PDF; Zheng et al.
(2022), DOI 10.3390/diagnostics12112660; Setio et al. (2017), DOI 10.1016/j.media.2017.06.015.

---

## Slide 2 — Hiperparâmetros da CNN

Configuração `cnn_lr_3e-4` (run `2f8b0a3c`, `modelos/cnn_lr_3e-4/execucao.json` e
`src/experimentos/cnn.py`):

| | |
|---|---|
| Arquitetura | CNN 3D: 3 blocos conv 3×3×3 (16, 32, 64 filtros) + BatchNorm + ReLU + max pooling; pooling global; dropout 0,3; densas 64→32→2 |
| Entrada | cubo de 32×32×32 voxels de 1 mm, HU −1000 a 400 normalizado para [0, 1], com máscara de pulmão |
| Otimizador | Adam, learning rate 0,0003 constante, weight decay 0,00001 |
| Batch / épocas | 32 / 40; checkpoint da época 40, sem early stopping |
| Perda | entropia cruzada, 2 classes |
| Desbalanceamento | todos os positivos + 20 negativos por positivo (23.058 candidatos); sampler com peso inverso à frequência |
| Aumento de dados | espelhamento aleatório nos 3 eixos + rotação de 90° no plano axial |
| Semente / hardware | 42 / RTX 4050, determinismo parcial na GPU |

*Fala sugerida:* "A rede é pequena de propósito. Os três ganhos que mais pesaram foram mais
épocas, mais negativos por positivo e o learning rate de 0,0003, cada um testado só na validação."

Nenhum valor desta tabela está "não documentado": todos estão no run e no código. Valores
padrão do PyTorch (betas do Adam 0,9 e 0,999; inicialização dos pesos) não foram alterados.

---

## Slide 3 — Validação com múltiplas sementes

**Testamos a mesma configuração com diferentes sementes para verificar se o desempenho observado
depende excessivamente de uma única inicialização.**

| Semente | CPM na validação |
|---:|---:|
| Semente | CPM na validação | IC95% | Sensibilidade a 4 FP |
|---:|---:|---|---:|
| 42 (original, a que foi ao teste) | 0,752 | 0,681 a 0,819 | 0,883 |
| 43 | 0,790 | 0,725 a 0,862 | 0,901 |
| 44 | 0,790 | 0,728 a 0,858 | 0,892 |
| Média ± desvio padrão | 0,777 ± 0,022 | | 0,892 ± 0,009 |
| Mínimo / máximo | 0,752 / 0,790 | | 0,883 / 0,901 |

Gráfico: `relatorios/experimentos/sementes_cnn/cpm_por_semente.png`.

**Conclusão sobre estabilidade:** a diferença entre sementes (0,039) é bem menor que o IC95% de
cada uma (cerca de 0,14). A semente congelada, 42, foi a menor das três, então o resultado não
veio de uma inicialização de sorte. As novas sementes não foram ao teste.

Nota para quem apresentar: 43 e 44 dão o mesmo CPM por coincidência. As redes são diferentes e
acertam nódulos diferentes em cada ponto, mas a soma dos sete pontos deu igual (seção 4 do
docs/14).

*Fala sugerida:* "O intervalo de confiança mede a incerteza por termos poucos exames; a variação
entre sementes mede a incerteza de treinar de novo. São duas perguntas diferentes."
