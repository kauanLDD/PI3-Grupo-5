"""A rodada do pré-processamento na base completa. Ver docs/03-pre-processamento.md."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config

LIMITE_LITROS = 8.0

# Medido em 08/09/2026: a máscara do desafio vaza para o ar em volta do paciente nestes exames,
# marcando mais de 8 litros de pulmão. Guardados pelos oito últimos dígitos, que são únicos entre
# os 888. Comparar o conjunto e não a contagem: troca de um por outro mantém o total em 37.
MASCARAS_LARGAS = {
    "03668137", "05017227", "06266464", "09623059", "10079250", "13903329",
    "14831537", "20209778", "20864961", "33453512", "36913951", "39120843",
    "39595820", "40048766", "40311282", "40828684", "42462394", "42618641",
    "47301883", "50180824", "50909530", "51154201", "51367533", "53159586",
    "54756843", "54875981", "57657094", "62251777", "63560826", "64161877",
    "66711534", "70295147", "75453085", "81016103", "84187602", "85874395",
    "95118048",
}


def relatorio():
    caminho = config.carregar()["caminhos"]["intermediario"] / "preprocessamento.csv"
    if not caminho.exists():
        pytest.skip("rode antes o scripts/07_preprocessar_base.py")

    import pandas as pd

    d = pd.read_csv(caminho)
    # O volume reamostrado é isotrópico de 1 mm, então voxel e mm3 são a mesma contagem.
    d["litros"] = d.pulmao_fracao * d.dim_x * d.dim_y * d.dim_z / 1e6
    return d


def test_a_rodada_cobre_os_888_exames():
    d = relatorio()
    assert len(d) == 888, f"o relatório tem {len(d)} exames"
    assert d.seriesuid.nunique() == 888, "há exame repetido no relatório"


def test_as_dez_dobras_estao_inteiras():
    """As dobras são os subsets do desafio, com 89 exames cada até a oitava e 88 nas duas últimas."""
    d = relatorio()
    assert d.subset.value_counts().sort_index().tolist() == [89] * 8 + [88] * 2


def test_nenhum_exame_ficou_sem_pulmao():
    """Fração zero significa máscara que apagou o volume inteiro, e o recorte sairia vazio."""
    d = relatorio()
    vazios = d[d.pulmao_fracao <= 0].seriesuid.tolist()
    assert not vazios, f"exames sem nenhum voxel de pulmão: {vazios}"


def test_o_pulmao_mediano_e_fisiologico():
    d = relatorio()
    assert 3.0 < d.litros.median() < 7.0, f"mediana de {d.litros.median():.2f} L"


def test_as_mascaras_largas_continuam_sendo_as_mesmas():
    """Falha se aparecer máscara larga nova, ou se as conhecidas sumirem sem registro."""
    d = relatorio()
    agora = set(d[d.litros > LIMITE_LITROS].seriesuid.str[-8:])
    entraram = sorted(agora - MASCARAS_LARGAS)
    sairam = sorted(MASCARAS_LARGAS - agora)

    assert not entraram and not sairam, (
        f"a lista de máscaras acima de {LIMITE_LITROS} L mudou. Entraram: {entraram}. "
        f"Saíram: {sairam}. O documento de pré-processamento precisa ser remedido."
    )
