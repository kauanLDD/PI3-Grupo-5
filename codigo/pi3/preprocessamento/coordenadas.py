"""Conversão entre coordenada de mundo em milímetro e índice de voxel.

Origem, espaçamento e direção mudam de exame para exame. Ignorar a direção espelha x e y
nos volumes LPI do desafio, sem levantar erro nenhum.
"""

import numpy as np


def geometria(linha):
    """Origem, espaçamento e direção de uma linha do inventário, em (x, y, z)."""
    return (
        [linha[f"origem_{eixo}"] for eixo in "xyz"],
        [linha[f"espacamento_{eixo}"] for eixo in "xyz"],
        [float(v) for v in linha["direcao"].split()],
    )


def mundo_para_indice(mundo, origem, espacamento, direcao) -> np.ndarray:
    """Índice contínuo. Quem precisa de voxel inteiro arredonda depois."""
    matriz = np.asarray(direcao, float).reshape(3, 3)
    deslocamento = np.asarray(mundo, float) - np.asarray(origem, float)
    # A direção é ortonormal, então a transposta é a inversa.
    return matriz.T @ deslocamento / np.asarray(espacamento, float)


def indice_para_mundo(indice, origem, espacamento, direcao) -> np.ndarray:
    matriz = np.asarray(direcao, float).reshape(3, 3)
    passo = np.asarray(indice, float) * np.asarray(espacamento, float)
    return matriz @ passo + np.asarray(origem, float)


def dentro_do_volume(indice, dimensao) -> bool:
    return all(0 <= i < d for i, d in zip(indice, dimensao))
