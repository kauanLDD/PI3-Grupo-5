"""Escolha do corte ilustrativo da evidência de normalização."""

import importlib.util
from pathlib import Path

import numpy as np

CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "11_evidencia_normalizacao.py"
spec = importlib.util.spec_from_file_location("evidencia_normalizacao", CAMINHO)
evidencia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidencia)


def test_escolhe_maior_area_pulmonar_na_metade_central():
    volume = np.zeros((12, 6, 8), dtype=np.int16)
    volume[0] = -700  # Área maior, mas fora da metade central.
    volume[4, :2, :2] = -700
    volume[7, :3, :3] = -700
    volume[5] = -400  # O limite superior não pertence à faixa.
    volume[6] = -1000  # Nem o limite inferior.
    assert evidencia.escolher_corte(volume, (-1000, -400)) == 7


def test_sem_voxel_na_faixa_pulmonar_usa_o_meio():
    volume = np.zeros((12, 6, 8), dtype=np.int16)
    assert evidencia.escolher_corte(volume, (-1000, -400)) == 6
