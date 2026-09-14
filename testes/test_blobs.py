"""Blob detection 3D por Laplacian of Gaussian."""

import sys
from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import blobs
from preprocessing import coordenadas


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


def volumes_de_teste():
    """Exames reais, nos extremos de espaçamento em z do original, mais um de direção invertida.

    O recorte roda sobre o volume já reamostrado, que é sempre isotrópico de 1 mm, então o que
    muda de exame para exame aqui é a origem e a direção.
    """
    cfg = config.carregar()
    inventario = cfg["caminhos"]["intermediario"] / "inventario_volumes.csv"
    if not inventario.exists():
        return []

    import pandas as pd

    d = pd.read_csv(inventario)
    invertidos = d[~d.matriz_identidade]
    escolhidas = [d.loc[d.espacamento_z.idxmin()], d.loc[d.espacamento_z.idxmax()]]
    if len(invertidos):
        escolhidas.append(invertidos.iloc[0])

    saida = []
    for linha in escolhidas:
        caminho = cfg["caminhos"]["volumes"] / f"{linha.seriesuid}.mha"
        if caminho.exists():
            saida.append(pytest.param(linha.seriesuid, caminho, id=f"z{linha.espacamento_z:.3f}"))
    return saida


com_volume = pytest.mark.parametrize("seriesuid,caminho", volumes_de_teste())


def geometria_do_mha(caminho):
    """Imagem 1x1x1 com a geometria do arquivo, sem carregar os voxels."""
    leitor = sitk.ImageFileReader()
    leitor.SetFileName(str(caminho))
    leitor.ReadImageInformation()

    imagem = sitk.Image(1, 1, 1, sitk.sitkUInt8)
    imagem.SetOrigin(leitor.GetOrigin())
    imagem.SetSpacing(leitor.GetSpacing())
    imagem.SetDirection(leitor.GetDirection())
    return imagem


@com_volume
def test_candidatos_do_exame_concorda_com_a_formula_do_projeto(seriesuid, caminho):
    """blobs.py abre um segundo caminho de conversão, e ele tem que dar o mesmo que coordenadas.py.

    Sem isto, uma divergência entre os dois desloca o candidato sem levantar erro nenhum.
    """
    imagem = geometria_do_mha(caminho)
    origem, espacamento, direcao = imagem.GetOrigin(), imagem.GetSpacing(), imagem.GetDirection()
    achados = np.array([[10.0, 20.0, 30.0, 1.5], [0.0, 0.0, 0.0, 2.0], [7.0, 3.0, 11.0, 1.0]])

    candidatos = blobs.candidatos_do_exame(seriesuid, imagem, achados)

    for (z, y, x, _), linha in zip(achados, candidatos.itertuples()):
        esperado = coordenadas.indice_para_mundo([x, y, z], origem, espacamento, direcao)
        assert np.allclose([linha.coordX, linha.coordY, linha.coordZ], esperado)


def test_candidatos_do_exame_em_espacamento_nao_isotropico():
    """A conversão não pode assumir 1 mm nem um espaçamento só para os três eixos."""
    imagem = imagem_de_teste(origem=(10.0, -5.0, 2.0), espacamento=(0.5, 0.7, 2.5))
    achados = np.array([[4.0, 6.0, 8.0, 1.0]])  # z, y, x, sigma

    linha = blobs.candidatos_do_exame("exame-c", imagem, achados).iloc[0]

    assert linha.coordX == pytest.approx(10.0 + 8 * 0.5)
    assert linha.coordY == pytest.approx(-5.0 + 6 * 0.7)
    assert linha.coordZ == pytest.approx(2.0 + 4 * 2.5)
