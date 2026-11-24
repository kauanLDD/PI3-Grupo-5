# Requisitos

O sistema é um pipeline em lote: recebe tomografias de tórax do LUNA16 e devolve, para cada exame,
os pontos suspeitos de nódulo com uma nota. Os requisitos abaixo descrevem o que está implementado
e foi medido. Os itens do levantamento de 15/08/2026 que dependem de um aplicativo (tela, login,
histórico) ficam no fim, com prioridade baixa e marcados como não implementados.

## Funcionais

| Código | Requisito | Prioridade | Onde |
|---|---|---|---|
| RF-01 | Ler os 888 exames do LUNA16 em MetaImage e gravar um inventário com origem, espaçamento e tamanho de cada um | Alta | `scripts/02_inventario_volumes.py` |
| RF-02 | Converter coordenada de mundo em milímetro para índice de voxel e de volta | Alta | `src/preprocessing/coordenadas.py`, `testes/test_coordenadas.py` |
| RF-03 | Pré-processar cada exame: janela de HU, reamostragem para 1 mm, máscara de pulmão e normalização [0, 1] | Alta | `scripts/07_preprocessar_base.py` |
| RF-04 | Gerar uma lista própria de candidatos por blob detection 3D (LoG) | Alta | `scripts/10_detectar_candidatos.py` |
| RF-05 | Dividir os exames em treino, validação e teste por paciente | Alta | `scripts/13_criar_divisao.py` |
| RF-06 | Recortar um cubo 3D em volta de cada candidato | Alta | `dvc repro patches` |
| RF-07 | Dar uma nota a cada candidato com uma rede neural 3D | Alta | `scripts/18_treinar_cnn.py` |
| RF-08 | Dar uma nota a cada candidato com um Random Forest, como modelo de comparação | Média | `scripts/25_treinar_random_forest_centro.py` |
| RF-09 | Rebaixar candidatos vizinhos a até 16 mm de um candidato de nota maior | Média | `scripts/36_supressao_suave.py` |
| RF-10 | Avaliar as notas com o programa oficial do LUNA16: curva FROC, CPM e sensibilidade a 1 e 4 falsos positivos por exame | Alta | `src/experimentos/avaliacao_oficial.py` |
| RF-11 | Registrar cada treino com parâmetros, semente, hash dos dados e métricas | Média | MLflow, `scripts/16_abrir_mlflow.py` |
| RF-12 | Gerar figuras dos nódulos perdidos e dos falsos positivos | Média | `scripts/29_analisar_erros_cnn.py` |
| RF-13 | Juntar a nota de duas redes pela média | Baixa | `scripts/40_combinar_redes.py` |
| RF-14 | Mostrar ao médico a fatia com o nódulo marcado (não implementado) | Baixa | |
| RF-15 | Ter uma interface com login do médico e histórico de exames (não implementado) | Baixa | |

## Não funcionais

| Código | Requisito | Prioridade |
|---|---|---|
| RNF-01 | Achar pelo menos 80% dos nódulos com até 4 falsos positivos por exame (meta do enunciado, seção 7.6) | Alta |
| RNF-02 | Todo resultado com intervalo de confiança de 95% por bootstrap, com pelo menos 500 reamostras (usamos 1.000) | Alta |
| RNF-03 | Semente fixa (42) em todo script, para o mesmo comando dar o mesmo resultado | Alta |
| RNF-04 | Treinar a rede numa GPU de 6 GB de memória (RTX 4050 Laptop) | Média |
| RNF-05 | 100% dos testes automáticos passando antes de cada merge na main | Alta |
| RNF-06 | Nenhum caminho de arquivo escrito no código: 100% dos caminhos em `configuracao/config.yaml` | Média |
| RNF-07 | Nenhum dado, imagem médica ou dado de paciente no repositório (0 arquivos) | Alta |

## De domínio

| Código | Regra | Prioridade |
|---|---|---|
| RD-01 | A divisão é por paciente. Fatias ou candidatos do mesmo exame nunca ficam em dois conjuntos | Alta |
| RD-02 | O teste só avalia modelo congelado. Cada uso do teste é declarado (foram três: decisões 0008, 0009 e 0013) | Alta |
| RD-03 | Nódulo é o achado de pelo menos 3 mm marcado por pelo menos três dos quatro radiologistas (critério do LUNA16) | Alta |
| RD-04 | Candidato em cima de um achado excluído pelo LUNA16 não conta como falso positivo | Alta |
| RD-05 | Acurácia e AUC-ROC não são usadas: os positivos são 0,2062% dos candidatos | Alta |
| RD-06 | O sistema só aponta candidatos. Não classifica benigno contra maligno e não serve para decisão clínica | Alta |
| RD-07 | O avaliador oficial considera no máximo 100 marcas por exame | Média |
