# 0004 - Execução local, com o treino numa GPU de notebook

Status: Aceito
Data: 2026-11-24

Contexto
O sistema não atende usuário pela internet (ADR 0001), então não precisa de hospedagem. Precisava
de uma máquina que guardasse a base e treinasse a rede 3D em tempo útil. Em 12/10/2026 medimos um
lote de treino da rede em 480 a 530 ms na CPU e em 21,8 a 23,1 ms numa RTX 4050 Laptop de 6 GB
(`scripts/21_medir_velocidade_cnn.py`, decisão 0007 do PI3).

Decisão
Rodamos tudo localmente. O treino usa a RTX 4050 de um integrante, com PyTorch para CUDA no ambiente
`.venv-cnn-gpu`. O painel do MLflow abre só na própria máquina, em `http://127.0.0.1:5000`. O
código fica no GitHub; a base, num HD externo e no Drive do grupo.

Consequências
Melhora: não há custo de nuvem, e o treino da rede leva minutos em vez de horas.
Piora: o treino depende da máquina de uma pessoa. Na GPU o resultado é reprodutível só em parte,
porque algumas operações do PyTorch não têm versão determinística; o treino avisa em vez de parar
(decisão 0007 do PI3).
