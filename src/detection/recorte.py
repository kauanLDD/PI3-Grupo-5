"""Cubos recortados na hora a partir de pontos em mm no mundo.

Fica fora de `patches.py` porque o hash daquele arquivo entra na procedência dos cubos em disco
(`procedencia_recortes.assinatura`): mudar o arquivo marcaria os 888 lotes como desatualizados.
"""

import numpy as np

from detection.patches import extrair_patch


def recortar(imagem, volume, pontos_xyz, tamanho_xyz):
    """Um cubo por ponto em mm no mundo, convertido pela origem, espaçamento e direção do exame.

    `imagem` é o SimpleITK.Image de onde `volume` saiu. Mesmo arredondamento do recorte da lista V2
    (`TransformPhysicalPointToIndex`), para os cubos das duas listas serem comparáveis.
    """
    recortes = np.empty((len(pontos_xyz), *tuple(tamanho_xyz)[::-1]), dtype=volume.dtype)
    for i, ponto in enumerate(pontos_xyz):
        centro = imagem.TransformPhysicalPointToIndex(tuple(float(v) for v in ponto))
        if any(c < 0 or c >= n for c, n in zip(centro, imagem.GetSize())):
            raise ValueError(f"ponto {i} fora do volume: índice {centro}")
        recortes[i] = extrair_patch(volume, centro, tamanho_xyz)
    return recortes
