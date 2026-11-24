"""Geração de candidatos por blob detection 3D (Laplacian of Gaussian).

Nódulo é uma bolinha mais clara que o pulmão em volta. O skimage já implementa a busca por
bolinhas: `skimage.feature.blob_log` varre o volume em várias escalas de desvio padrão (sigma)
de um filtro gaussiano e aponta onde a resposta do Laplaciano é máxima. Cada blob sai como
`(z, y, x, sigma)`, em índice de voxel.
"""

import numpy as np
import pandas as pd
from skimage.feature import blob_log

COLUNAS = ["seriesuid", "coordX", "coordY", "coordZ", "raio"]

# Raio do blob = sigma * sqrt(ndim), como na documentação do skimage.feature.blob_log.
FATOR_RAIO_3D = np.sqrt(3)


def detectar(volume: np.ndarray, min_sigma=1.0, max_sigma=5.0, num_sigma=5,
             threshold=0.1) -> np.ndarray:
    """Roda blob_log 3D no volume (z, y, x) normalizado; cada linha é z, y, x e sigma, em voxel."""
    if volume.ndim != 3:
        raise ValueError("volume precisa ter tres dimensoes: z, y, x")

    return blob_log(volume, min_sigma=min_sigma, max_sigma=max_sigma,
                     num_sigma=num_sigma, threshold=threshold)


def raio_mm(sigma_voxel, espacamento_mm: float) -> np.ndarray:
    """Sigma do LoG, em voxel, vira raio estimado do nódulo, em mm."""
    return np.asarray(sigma_voxel, dtype=float) * espacamento_mm * FATOR_RAIO_3D


def candidatos_do_exame(seriesuid: str, imagem, blobs: np.ndarray) -> pd.DataFrame:
    """Converte blobs (z, y, x, sigma) em voxel para candidatos em mm, pela geometria do próprio `imagem`."""
    espacamento = imagem.GetSpacing()[0]  # isotrópico: um valor só vale para os três eixos.

    linhas = []
    for z, y, x, sigma in blobs:
        mundo = imagem.TransformContinuousIndexToPhysicalPoint((float(x), float(y), float(z)))
        linhas.append({
            "seriesuid": seriesuid,
            "coordX": mundo[0],
            "coordY": mundo[1],
            "coordZ": mundo[2],
            "raio": float(raio_mm(sigma, espacamento)),
        })

    return pd.DataFrame(linhas, columns=COLUNAS)
