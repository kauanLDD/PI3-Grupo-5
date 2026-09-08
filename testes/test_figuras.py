"""A figura de antes e depois desenha dois volumes em escalas diferentes."""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visualization import fatias

HU = (-1000, 400)


def par_de_volumes():
    """O mesmo conteúdo em HU e normalizado, que é o que o pré-processamento devolve."""
    rng = np.random.default_rng(42)
    arr = rng.normal(-500, 300, (8, 40, 40)).astype(np.int16)
    bruto = sitk.GetImageFromArray(arr)
    normalizado = sitk.GetImageFromArray(((arr - HU[0]) / (HU[1] - HU[0])).astype(np.float32))
    for imagem in (bruto, normalizado):
        imagem.SetSpacing((1.0, 1.0, 1.0))
    return bruto, normalizado


def maior_mancha_chapada(caminho: Path) -> float:
    """Fração da metade direita coberta pelo cinza mais repetido. Painel apagado passa de 50%."""
    imagem = plt.imread(caminho)[:, :, 0]
    metade = (imagem[:, imagem.shape[1] // 2:] * 255).astype(np.uint8)
    return float(np.bincount(metade.ravel()).max()) / metade.size


def desenhar(faixas, saida: Path) -> Path:
    bruto, normalizado = par_de_volumes()
    fatias.antes_e_depois(bruto, normalizado, (20.0, 20.0, 4.0), 3.0, faixas, "", saida)
    return saida


def test_o_painel_de_depois_mostra_o_volume_normalizado(tmp_path):
    assert maior_mancha_chapada(desenhar((HU, (0, 1)), tmp_path / "certo.png")) < 0.5


def test_desenhar_o_normalizado_com_a_janela_de_hu_apaga_o_painel(tmp_path):
    """Sem este teste, passar a janela errada gera figura chapada e o pipeline não acusa.

    Foi o que aconteceu em 07/09/2026, quando a normalização entrou: o volume passou a sair em
    [0, 1] e a figura continuou desenhando com vmin de -1000, virando um retângulo cinza.
    """
    assert maior_mancha_chapada(desenhar((HU, HU), tmp_path / "errado.png")) > 0.5
