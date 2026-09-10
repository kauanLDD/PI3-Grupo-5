"""Recortes 3D para candidatos."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import patches


def volume_de_teste():
    return np.arange(6 * 8 * 10, dtype=np.float32).reshape(6, 8, 10)


def test_patch_tem_o_tamanho_configurado():
    patch = patches.extrair_patch(volume_de_teste(), (5, 4, 3), (34, 34, 34))
    assert patch.shape == (34, 34, 34)


def test_centro_do_patch_corresponde_ao_candidato():
    volume = volume_de_teste()
    patch = patches.extrair_patch(volume, (5, 4, 3), (4, 4, 4))
    assert patch[2, 2, 2] == volume[3, 4, 5]


def test_patch_preenche_com_zero_fora_do_volume():
    volume = volume_de_teste() + 1
    patch = patches.extrair_patch(volume, (0, 0, 0), (4, 4, 4))
    assert (patch[:2] == 0).all()
    assert patch[2, 2, 2] == volume[0, 0, 0]
