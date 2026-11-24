# 0001 - Pipeline em lote de scripts, sem servidor e sem interface

Status: Aceito
Data: 2026-11-24

Contexto
O projeto é a etapa de detecção de candidatos a nódulo em tomografia, avaliada pela curva FROC do
LUNA16. O que precisa ser entregue é um resultado medido e reprodutível sobre 888 exames, não um
aplicativo para o médico. Cada etapa (pré-processamento, detecção, recorte, treino, avaliação)
demora de minutos a horas e grava arquivos que a etapa seguinte lê.

Decisão
Montamos o sistema como um pipeline em lote: scripts numerados em `scripts/`, na ordem de execução,
que importam a lógica de `src/`. O fluxo é: lista de candidatos (a V2 do desafio ou a nossa, por
LoG), recorte de um cubo 3D em volta de cada candidato, nota da rede 3D, supressão de vizinhos e
avaliação com o programa oficial do LUNA16. Os estágios principais estão declarados no `dvc.yaml`
(ADR 0003). Não há servidor, API nem tela.

Consequências
Melhora: cada etapa roda e é conferida sozinha, e um resultado pode ser refeito a partir dos
arquivos da etapa anterior sem repetir tudo.
Piora: quem usa precisa de terminal e Python. As funções de aplicativo do levantamento de
requisitos (RF-14 e RF-15 em `docs/requisitos.md`) ficam fora.
