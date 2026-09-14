# Detecção

Geração de candidatos a nódulo, o produto central do grupo e a etapa de Transformação do KDD.
Cada candidato sai com coordenada e raio estimado, gravado em `candidatos.csv`, e validado
visualmente sobre os cortes. Ver `docs/04-deteccao-de-candidatos.md`.

- `blobs.py`: geração por blob detection 3D (Laplacian of Gaussian, `skimage.feature.blob_log`),
  rodada por `scripts/10_detectar_candidatos.py`.
- `candidatos.py`: o critério de acerto do desafio, usado tanto para comparar as listas prontas
  (`scripts/08_comparar_candidatos.py`) quanto para medir a cobertura da lista própria.
- `patches.py`: recorte dos cubos ao redor de cada candidato.

O que ainda falta aqui: redução de falsos positivos.
