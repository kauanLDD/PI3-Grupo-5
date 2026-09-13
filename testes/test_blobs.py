"""Blob detection 3D por Laplacian of Gaussian."""

import sys
from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import blobs


def volume_com_blob(shape=(40, 40, 40), centro=(20, 20, 20), sigma=2.0, pico=1.0):
    """Volume sintético com um único blob gaussiano, em (z, y, x)."""
    zz, yy, xx = np.indices(shape)
    d2 = (zz - centro[0]) ** 2 + (yy - centro[1]) ** 2 + (xx - centro[2]) ** 2
    return (pico * np.exp(-d2 / (2 * sigma ** 2))).astype(np.float32)


def imagem_de_teste(origem=(0.0, 0.0, 0.0), espacamento=(1.0, 1.0, 1.0)):
    """Imagem 1x1x1 só para carregar a geometria, como em test_coordenadas.py."""
    imagem = sitk.Image(1, 1, 1, sitk.sitkUInt8)
    imagem.SetOrigin(origem)
    imagem.SetSpacing(espacamento)
    return imagem


def test_detectar_acha_o_blob_sintetico():
    volume = volume_com_blob()
    achados = blobs.detectar(volume, min_sigma=1, max_sigma=5, num_sigma=5, threshold=0.1)

    assert len(achados) == 1
    z, y, x, _ = achados[0]
    assert np.allclose([z, y, x], [20, 20, 20], atol=1.0)


def test_detectar_com_threshold_alto_nao_acha_nada():
    volume = volume_com_blob(pico=0.3)
    achados = blobs.detectar(volume, min_sigma=1, max_sigma=5, num_sigma=5, threshold=0.9)
    assert len(achados) == 0


def test_detectar_recusa_volume_que_nao_e_3d():
    with pytest.raises(ValueError):
        blobs.detectar(np.zeros((10, 10)))


def test_raio_mm_usa_sqrt_de_tres():
    # LoG: o raio do blob é sigma * sqrt(3) em 3D. Sigma 2 em voxel de 1 mm dá raio ~3,46 mm.
    assert blobs.raio_mm(2.0, espacamento_mm=1.0) == pytest.approx(2.0 * np.sqrt(3))


def test_raio_mm_escala_com_o_espacamento():
    assert blobs.raio_mm(2.0, espacamento_mm=0.5) == pytest.approx(1.0 * np.sqrt(3))


def test_candidatos_do_exame_converte_indice_para_mundo():
    imagem = imagem_de_teste(origem=(-100.0, -50.0, -200.0), espacamento=(2.0, 2.0, 2.0))
    achados = np.array([[10.0, 20.0, 30.0, 1.5]])  # z, y, x, sigma

    candidatos = blobs.candidatos_do_exame("exame-a", imagem, achados)

    assert list(candidatos.columns) == blobs.COLUNAS
    assert len(candidatos) == 1
    linha = candidatos.iloc[0]
    assert linha.seriesuid == "exame-a"
    # mundo = origem + indice * espacamento, com direção identidade.
    assert linha.coordX == pytest.approx(-100.0 + 30 * 2.0)
    assert linha.coordY == pytest.approx(-50.0 + 20 * 2.0)
    assert linha.coordZ == pytest.approx(-200.0 + 10 * 2.0)
    assert linha.raio == pytest.approx(blobs.raio_mm(1.5, 2.0))


def test_candidatos_do_exame_sem_blob_devolve_tabela_vazia():
    imagem = imagem_de_teste()
    candidatos = blobs.candidatos_do_exame("exame-b", imagem, np.empty((0, 4)))
    assert candidatos.empty
    assert list(candidatos.columns) == blobs.COLUNAS
