# Sistema final e tabela única de resultados

Tabela gerada em 24/11/2026 por `.venv/bin/python scripts/41_tabela_resultados.py`, que só lê os
resultados do avaliador oficial já gravados em disco (`config.yaml`, seção `tabela_resultados`). O
script não treina, não pontua e não abre o teste. Subsets 0 a 9 do LUNA16, divisão por paciente:
623 exames de treino, 89 de validação e 176 de teste.

## O sistema final

O sistema final é o que foi congelado e medido no teste pela decisão 0013: a rede `cnn_lr_3e-4`
(decisão 0008, semente 42) dá uma nota a cada candidato, e depois a supressão suave linear a 16 mm
rebaixa os vizinhos de um candidato de nota maior, com até 100 marcas por exame. Ele roda sobre
duas listas de candidatos:

- **Com a lista do desafio (V2):** CPM 0,758 (IC95% 0,709 a 0,806) no teste, sensibilidade de
  0,865 (0,817 a 0,913) a 4 falsos positivos por exame.
- **Com a nossa lista (LoG):** CPM 0,691 (IC95% 0,633 a 0,754) no teste, sensibilidade de 0,807
  (0,758 a 0,868) a 4 falsos positivos por exame. É a versão que não depende da lista pronta do
  desafio.

A distância entre as duas no teste é de -0,067 de CPM (IC95% pareado de -0,112 a -0,026), em
`relatorios/experimentos/teste_supressao/diferencas_pareadas.csv`. Sem a supressão, a distância era
de -0,235 (-0,271 a -0,196).

## Uso do teste

O teste foi aberto três vezes, cada uma com o modelo congelado antes de rodar:

1. Decisão 0008: a rede `cnn_lr_3e-4` na V2.
2. Decisão 0009: o Random Forest centro na V2, só para comparação com a rede.
3. Decisão 0013: a supressão suave a 16 mm nas duas listas.

Como o mesmo teste foi usado três vezes, as comparações feitas nele são descritivas. A escolha da
rede, da supressão e do raio foi feita só na validação.

## Tabela única

Todos os números são do programa oficial do LUNA16, com IC95% por bootstrap de 1.000 reamostras por
exame. "Sens. 1" e "Sens. 4" são a sensibilidade a 1 e a 4 falsos positivos por exame. A fonte de
cada linha está em `relatorios/experimentos/tabela_resultados/tabela.csv`, coluna `arquivo`.

| Modelo | Lista | Conjunto | CPM (IC95%) | Sens. 1 (IC95%) | Sens. 4 (IC95%) |
|---|---|---|---|---|---|
| CNN lr_3e-4 | V2 | validação | 0,752 (0,681 a 0,819) | 0,784 (0,699 a 0,870) | 0,883 (0,805 a 0,945) |
| CNN lr_3e-4, semente 43 | V2 | validação | 0,790 (0,725 a 0,862) | 0,829 (0,734 a 0,902) | 0,901 (0,831 a 0,953) |
| CNN lr_3e-4, semente 44 | V2 | validação | 0,790 (0,728 a 0,858) | 0,820 (0,750 a 0,902) | 0,892 (0,830 a 0,949) |
| Random Forest centro | V2 | validação | 0,409 (0,323 a 0,505) | 0,405 (0,291 a 0,519) | 0,559 (0,453 a 0,650) |
| CNN lr_3e-4 + supressão dura 16 mm | V2 | validação | 0,798 (0,716 a 0,871) | 0,802 | 0,865 |
| CNN lr_3e-4 | nossa (LoG) | validação | 0,465 (0,400 a 0,532) | 0,441 (0,359 a 0,537) | 0,712 (0,621 a 0,790) |
| CNN lr_3e-4 + supressão suave 16 mm | nossa (LoG) | validação | 0,745 (0,651 a 0,820) | 0,784 | 0,847 |
| CNN centro_16 | V2 | validação | 0,758 (0,680 a 0,823) | 0,802 (0,714 a 0,879) | 0,883 (0,816 a 0,950) |
| Média CNN lr_3e-4 e centro_16 | V2 | validação | 0,837 (0,769 a 0,898) | 0,874 (0,794 a 0,938) | 0,919 (0,864 a 0,967) |
| CNN lr_3e-4 | V2 | teste | 0,724 (0,670 a 0,778) | 0,735 (0,659 a 0,819) | 0,883 (0,843 a 0,929) |
| Random Forest centro | V2 | teste | 0,420 (0,349 a 0,490) | 0,381 (0,314 a 0,460) | 0,520 (0,442 a 0,603) |
| CNN lr_3e-4 + supressão suave 16 mm | V2 | teste | 0,758 (0,709 a 0,806) | 0,812 (0,756 a 0,861) | 0,865 (0,817 a 0,913) |
| CNN lr_3e-4 | nossa (LoG) | teste | 0,489 (0,438 a 0,546) | 0,480 (0,412 a 0,565) | 0,686 (0,623 a 0,758) |
| CNN lr_3e-4 + supressão suave 16 mm | nossa (LoG) | teste | 0,691 (0,633 a 0,754) | 0,717 (0,645 a 0,793) | 0,807 (0,758 a 0,868) |

Duas linhas da validação não têm o intervalo da sensibilidade, porque as tabelas de resumo de onde
elas saem (`supressao_v2/listas.csv` e `supressao_suave/validacao.csv`) só gravaram o intervalo do
CPM. A linha "supressão dura 16 mm" na V2 é a supressão medida antes da suave
(`scripts/35_supressao_v2.py`); a suave na V2 só foi medida no teste.

A média das duas redes (CPM 0,837) foi medida só na validação e não faz parte do sistema testado.
Duas redes de 32 com sementes diferentes, juntas pela mesma média, ficaram entre 0,790 e 0,806
(`docs/20-rede-centro-16.md`).

## Ressalva: só a rede teve ajuste

A rede passou por cinco versões na validação, uma mudança por vez (`docs/11-experimentos-validacao.md`),
e por três sementes (decisão 0010). O Random Forest centro usa os mesmos hiperparâmetros do Random
Forest v2, de 200 árvores (`config.yaml`, seção `random_forest`), e só mudou nas features. A
distância entre a rede e o Random Forest inclui essa diferença de ajuste.

## A FROC do grupo, como verificação

O grupo tem um cálculo próprio de FROC (`src/experimentos/froc_grupo.py`). Ele não entra na tabela
acima. Nas mesmas previsões, ele fica abaixo do oficial: CNN no teste 0,611 contra 0,724, CNN na
validação 0,630 contra 0,752, Random Forest centro na validação 0,351 contra 0,409
(`docs/17-avaliador-oficial-contra-o-do-grupo.md`). Serve só como conferência rápida.
