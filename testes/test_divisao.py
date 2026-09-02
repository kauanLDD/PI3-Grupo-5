"""Divisão por paciente. Ver decisão 0003."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
from pi3 import config

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
