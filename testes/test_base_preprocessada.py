"""A rodada do pré-processamento na base completa. Ver docs/03-pre-processamento.md."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config

# Medido em 07/09/2026: a máscara do desafio vaza para o ar em volta do paciente nestes exames.
MASCARAS_LARGAS = 37
LIMITE_LITROS = 8.0


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
    largas = int((d.litros > LIMITE_LITROS).sum())
    assert largas == MASCARAS_LARGAS, (
        f"{largas} exames com máscara acima de {LIMITE_LITROS} L, e o registro fala em "
        f"{MASCARAS_LARGAS}. O documento de pré-processamento precisa ser remedido."
    )
