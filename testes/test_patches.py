"""Recortes 3D para candidatos."""

import sys
from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import patches, recorte


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


def imagem_com_ponto(espacamento, origem, indice_xyz):
    volume = np.zeros((40, 50, 60), dtype=np.float32)
    volume[indice_xyz[::-1]] = 1.0
    imagem = sitk.GetImageFromArray(volume)
    imagem.SetSpacing(espacamento)
    imagem.SetOrigin(origem)
    return imagem, volume


@pytest.mark.parametrize("espacamento, origem", [((1.0, 1.0, 1.0), (-150.0, -120.0, -300.0)),
                                                 ((0.7, 0.7, 2.5), (-180.5, -95.25, -410.0))])
def test_recorte_por_coordenada_de_mundo_centra_o_ponto(espacamento, origem):
    """Origem e espaçamento mudam de exame para exame; o centro do cubo tem de cair no mesmo voxel."""
    indice = (31, 22, 17)
    imagem, volume = imagem_com_ponto(espacamento, origem, indice)
    mundo = imagem.TransformIndexToPhysicalPoint(indice)
    cubo = recorte.recortar(imagem, volume, [mundo], (8, 8, 8))[0]
    assert cubo[4, 4, 4] == 1.0 and cubo.sum() == 1.0


def test_recorte_de_32_e_o_miolo_do_de_34():
    """A rede foi treinada no cubo de 34 cortado no centro; recortar 32 direto tem de dar o mesmo."""
    gerador = np.random.default_rng(0)
    volume = gerador.random((40, 50, 60), dtype=np.float32)
    imagem = sitk.GetImageFromArray(volume)
    ponto = [imagem.TransformIndexToPhysicalPoint((30, 25, 20))]
    grande = recorte.recortar(imagem, volume, ponto, (34, 34, 34))[0]
    assert np.array_equal(recorte.recortar(imagem, volume, ponto, (32, 32, 32))[0], grande[1:33, 1:33, 1:33])


def test_recorte_recusa_ponto_fora_do_volume():
    imagem, volume = imagem_com_ponto((1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (1, 1, 1))
    with pytest.raises(ValueError):
        recorte.recortar(imagem, volume, [(-5.0, 0.0, 0.0)], (4, 4, 4))
