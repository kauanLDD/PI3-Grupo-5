"""Leitura de cabeçalho .mhd. Roda sem o HD ligado."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
from pi3.dados import volumes

CABECALHO = """ObjectType = Image
NDims = 3
TransformMatrix = 1 0 0 0 1 0 0 0 1
Offset = -198.10000600000001 -195 -335.209991
AnatomicalOrientation = RAI
ElementSpacing = 0.7617189884185791 0.7617189884185791 2.5
DimSize = 512 512 121
ElementType = MET_SHORT
ElementDataFile = volume.raw
"""


def test_campos_do_texto(tmp_path):
    mhd = tmp_path / "volume.mhd"
    mhd.write_text(CABECALHO, encoding="utf-8")

    campos = volumes.campos_do_texto(mhd)
    assert campos["DimSize"] == "512 512 121"
    assert campos["AnatomicalOrientation"] == "RAI"
    assert campos["ElementType"] == "MET_SHORT"


def test_identidade_aceita_ruido_de_float32():
    # É o que o .mhd traz no lugar de 1 em parte dos volumes do desafio.
    assert volumes.e_identidade((1, 0, 0, 0, 1, 0, 0, 0, 0.99999999999999989))


def test_identidade_recusa_direcao_invertida():
    # Os 11 volumes LPI do LUNA16 trazem esta matriz, e nela x e y saem espelhados.
    assert not volumes.e_identidade((-1, 0, 0, 0, -1, 0, 0, 0, 1))


def test_confere_aceita_o_que_bate():
    volumes.confere({"DimSize": (512, 512, 121)}, {"DimSize": "512 512 121"}, "volume.mhd")


def test_confere_estoura_quando_diverge():
    with pytest.raises(ValueError, match="DimSize"):
        volumes.confere({"DimSize": (512, 512, 120)}, {"DimSize": "512 512 121"}, "volume.mhd")


def test_pasta_do_subset_repete_o_nome():
    assert volumes.pasta_do_subset(Path("/luna"), 3) == Path("/luna/subset3/subset3")


def test_por_eixo():
    assert volumes.por_eixo("dim", (512, 512, 121)) == {"dim_x": 512, "dim_y": 512, "dim_z": 121}
