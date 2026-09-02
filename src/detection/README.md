# Detecção

Vazio de propósito. É aqui que entra a geração de candidatos a nódulo, que é o produto
central do grupo e a etapa de Transformação do KDD.

O que vai ficar aqui:

- geração de candidatos por blob detection 3D, ou por limiar adaptativo com componentes conexos
- recorte dos cubos ao redor de cada candidato
- redução de falsos positivos

Cada candidato precisa sair com coordenada e raio estimado, gravado em `candidatos.csv`,
e validado visualmente sobre os cortes.
