"""Divisão por paciente. Ver decisão 0003."""

import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset import divisao

# Medido em 30/08/2026: este é o único paciente com mais de uma série.
EXCECAO_CONHECIDA = "LIDC-IDRI-0332"


def tabela_de_pacientes():
    caminho = config.carregar()["caminhos"]["intermediario"] / "pacientes.csv"
    if not caminho.exists():
        pytest.skip("rode antes o scripts/01_pacientes.py")

    import pandas as pd

    return pd.read_csv(caminho)


def test_todo_exame_tem_paciente():
    d = tabela_de_pacientes()
    assert d.paciente.notna().all(), f"{int(d.paciente.isna().sum())} exames sem paciente"


def test_a_tabela_cobre_o_desafio_inteiro():
    d = tabela_de_pacientes()
    assert len(d) == 888, f"a tabela tem {len(d)} exames"
    assert d.paciente.nunique() == 887, f"{d.paciente.nunique()} pacientes distintos"


def test_so_um_paciente_aparece_em_mais_de_uma_dobra():
    """Falha se aparecer vazamento novo, ou se a exceção conhecida sumir sem registro."""
    d = tabela_de_pacientes()
    dobras = d.groupby("paciente").subset.nunique()
    espalhados = set(dobras[dobras > 1].index)

    assert espalhados == {EXCECAO_CONHECIDA}, (
        f"pacientes em mais de uma dobra: {sorted(espalhados)}. A decisão 0003 precisa ser remedida."
    )


def test_a_excecao_esta_nos_subsets_2_e_6():
    d = tabela_de_pacientes()
    subsets = sorted(d[d.paciente == EXCECAO_CONHECIDA].subset)
    assert subsets == [2, 6], f"{EXCECAO_CONHECIDA} mudou de dobra: agora está em {subsets}"


def test_divisao_mantem_as_duas_series_do_paciente_na_mesma_parte():
    pacientes = pd.DataFrame({
        "seriesuid": ["a", "b", "c", "d"],
        "paciente": ["repetido", "repetido", "validacao", "teste"],
        "subset": [2, 6, 7, 8],
    })
    plano = {"treino": [2, 6], "validacao": [7], "teste": [8]}

    resultado = divisao.criar(pacientes, plano)

    assert set(resultado.loc[resultado.paciente == "repetido", "particao"]) == {"treino"}


def test_divisao_recusa_paciente_em_partes_diferentes():
    pacientes = pd.DataFrame({
        "seriesuid": ["a", "b", "c"],
        "paciente": ["repetido", "repetido", "teste"],
        "subset": [2, 7, 8],
    })
    plano = {"treino": [2], "validacao": [7], "teste": [8]}

    with pytest.raises(ValueError, match="paciente presente"):
        divisao.criar(pacientes, plano)


def test_divisao_recusa_subset_repetido():
    pacientes = pd.DataFrame({
        "seriesuid": ["a", "b", "c"],
        "paciente": ["a", "b", "c"],
        "subset": [0, 1, 2],
    })
    plano = {"treino": [0, 1], "validacao": [1], "teste": [2]}

    with pytest.raises(ValueError, match="mais de uma partição"):
        divisao.criar(pacientes, plano)


def test_plano_do_projeto_cobre_a_base_sem_vazamento():
    pacientes = tabela_de_pacientes()
    cfg = config.carregar()

    resultado = divisao.criar(pacientes, cfg["divisao"]["particoes"])
    resumo = divisao.resumir(resultado)

    assert resumo.to_dict("index") == {
        "treino": {"exames": 623, "pacientes": 622},
        "validacao": {"exames": 89, "pacientes": 89},
        "teste": {"exames": 176, "pacientes": 176},
    }
