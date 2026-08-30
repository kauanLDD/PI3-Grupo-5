"""Conversão entre milímetro e índice de voxel."""

import sys
from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
from pi3 import config
from pi3.dados import volumes
from pi3.preprocessamento import coordenadas

RAI = [1, 0, 0, 0, 1, 0, 0, 0, 1]
LPI = [-1, 0, 0, 0, -1, 0, 0, 0, 1]
ESPACAMENTO = [0.5, 0.5, 2.0]


def ingenua(mundo, origem, espacamento):
    """A fórmula sem direção."""
    return (np.asarray(mundo, float) - np.asarray(origem, float)) / np.asarray(espacamento, float)


def test_geometria_fixa_rai():
    indice = coordenadas.mundo_para_indice([-90, -40, -180], [-100, -50, -200], ESPACAMENTO, RAI)
    assert np.allclose(indice, [20, 20, 10])


def test_geometria_fixa_lpi():
    indice = coordenadas.mundo_para_indice([90, 40, -180], [100, 50, -200], ESPACAMENTO, LPI)
    assert np.allclose(indice, [20, 20, 10])


def test_ingenua_acerta_no_rai_e_erra_no_lpi():
    origem_rai, origem_lpi = [-100, -50, -200], [100, 50, -200]
    assert np.allclose(ingenua([-90, -40, -180], origem_rai, ESPACAMENTO), [20, 20, 10])
    assert np.allclose(ingenua([90, 40, -180], origem_lpi, ESPACAMENTO), [-20, -20, 10])


def test_dentro_do_volume():
    assert coordenadas.dentro_do_volume([0, 511, 120], [512, 512, 121])
    assert not coordenadas.dentro_do_volume([-1, 100, 50], [512, 512, 121])
    assert not coordenadas.dentro_do_volume([100, 100, 121], [512, 512, 121])


def volumes_de_teste():
    """Extremos de espaçamento em z, mais um volume de direção invertida."""
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
        caminho = volumes.caminho_do_volume(
            cfg["caminhos"]["luna16"], linha.seriesuid, cfg["selecao"]["subsets"]
        )
        if caminho:
            saida.append(pytest.param(linha, caminho, id=f"z{linha.espacamento_z:.3f}"))
    return saida


com_volume = pytest.mark.parametrize("linha,caminho", volumes_de_teste())


@com_volume
def test_ida_e_volta(linha, caminho):
    origem, espacamento, direcao = coordenadas.geometria(linha)
    mundo = [-50.0, 30.0, origem[2] + 40.0]

    indice = coordenadas.mundo_para_indice(mundo, origem, espacamento, direcao)
    volta = coordenadas.indice_para_mundo(indice, origem, espacamento, direcao)
    assert np.allclose(volta, mundo)


def geometria_do_arquivo(caminho):
    """Imagem 1x1x1 com a geometria do .mhd."""
    leitor = sitk.ImageFileReader()
    leitor.SetFileName(str(caminho))
    leitor.ReadImageInformation()

    imagem = sitk.Image(1, 1, 1, sitk.sitkUInt8)
    imagem.SetOrigin(leitor.GetOrigin())
    imagem.SetSpacing(leitor.GetSpacing())
    imagem.SetDirection(leitor.GetDirection())
    return imagem


@com_volume
def test_concorda_com_simpleitk(linha, caminho):
    origem, espacamento, direcao = coordenadas.geometria(linha)
    centro = coordenadas.indice_para_mundo(
        [d / 2 for d in (linha.dim_x, linha.dim_y, linha.dim_z)], origem, espacamento, direcao
    )

    nosso = coordenadas.mundo_para_indice(centro, origem, espacamento, direcao)
    deles = geometria_do_arquivo(caminho).TransformPhysicalPointToContinuousIndex(
        [float(v) for v in centro]
    )
    assert np.allclose(nosso, deles)
