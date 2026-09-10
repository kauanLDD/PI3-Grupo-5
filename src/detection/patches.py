"""Extracao de cubos 3D a partir de volumes em ordem z, y, x."""

import numpy as np


def extrair_patch(volume, centro_xyz, tamanho_xyz, preenchimento=0.0):
    """Devolve um patch de tamanho fixo, preenchido fora dos limites do volume."""
    if volume.ndim != 3:
        raise ValueError("volume precisa ter tres dimensoes: z, y, x")

    tamanho_xyz = np.asarray(tamanho_xyz, dtype=int)
    if (tamanho_xyz <= 0).any():
        raise ValueError("cada dimensao do patch precisa ser positiva")

    inicio_xyz = np.asarray(centro_xyz, dtype=int) - tamanho_xyz // 2
    fim_xyz = inicio_xyz + tamanho_xyz
    inicio_zyx = inicio_xyz[::-1]
    fim_zyx = fim_xyz[::-1]
    tamanho_zyx = tuple(tamanho_xyz[::-1])

    patch = np.full(tamanho_zyx, preenchimento, dtype=volume.dtype)
    origem = np.maximum(inicio_zyx, 0)
    limite = np.minimum(fim_zyx, volume.shape)
    if (limite <= origem).any():
        return patch

    destino_inicio = origem - inicio_zyx
    destino_limite = destino_inicio + (limite - origem)
    origem_fatias = tuple(slice(a, b) for a, b in zip(origem, limite))
    destino_fatias = tuple(slice(a, b) for a, b in zip(destino_inicio, destino_limite))
    patch[destino_fatias] = volume[origem_fatias]
    return patch
