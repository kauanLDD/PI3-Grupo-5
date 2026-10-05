"""Proteções contra vazamento e perda de nódulos durante a calibração."""

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import calibracao


def test_separacao_recusa_paciente_entre_desenvolvimento_e_validacao():
    pacientes = pd.DataFrame({"seriesuid": ["a", "b"], "paciente": ["p", "p"], "subset": [0, 1]})
    with pytest.raises(ValueError, match="paciente presente"):
        calibracao.separar(pacientes, {"desenvolvimento": [0], "validacao": [1], "teste": [2]})


def test_separacao_preserva_duas_series_na_mesma_particao():
    pacientes = pd.DataFrame({"seriesuid": ["a", "b", "c"], "paciente": ["p", "p", "q"], "subset": [2, 6, 8]})
    resultado = calibracao.separar(pacientes, {"desenvolvimento": [2, 6], "validacao": [7], "teste": [8]})
    assert resultado.particao.tolist() == ["desenvolvimento", "desenvolvimento", "teste"]


def test_amostra_e_reprodutivel_e_inclui_exames_sem_nodulo():
    tabela = pd.DataFrame({"seriesuid": ["a", "b", "c", "d"]})
    anotacoes = pd.DataFrame({"seriesuid": ["a", "a", "b"]})
    primeira = calibracao.amostrar(tabela, anotacoes, 1, 1, 42)
    segunda = calibracao.amostrar(tabela.iloc[::-1], anotacoes, 1, 1, 42)
    pd.testing.assert_frame_equal(primeira, segunda)
    assert (primeira.nodulos == 0).sum() == 1


def tabela_resultados():
    return pd.DataFrame([
        {"seriesuid": uid, "paciente": uid, "particao": "desenvolvimento", "configuracao": nome,
         "candidatos": n, "alcancados": 1 if uid == "a" else 0, "nodulos": 2 if uid == "a" else 0,
         "segundos": 1.0, "erro": ""}
        for nome, n in [("inicial", 100), ("menor", 20)] for uid in ["a", "b"]
    ])


def tabela_cobertura(trocar=False):
    return pd.DataFrame([
        {"configuracao": nome, "nodulo_id": i, "alcancado": acerto}
        for nome, valores in [("inicial", [True, False]), ("menor", [False, True] if trocar else [True, False])]
        for i, acerto in enumerate(valores)
    ])


def test_mesma_cobertura_com_nodulo_diferente_nao_basta():
    assert calibracao.escolher(tabela_resultados(), tabela_cobertura(trocar=True)) == "inicial"


def test_escolhe_reducao_que_preserva_os_mesmos_nodulos():
    assert calibracao.escolher(tabela_resultados(), tabela_cobertura()) == "menor"


def test_configuracao_com_exame_faltando_nao_pode_vencer():
    resultados = tabela_resultados().iloc[:-1]
    assert calibracao.escolher(resultados, tabela_cobertura()) == "inicial"


def test_configuracao_com_falha_nao_pode_vencer():
    resultados = tabela_resultados()
    resultados.loc[resultados.configuracao == "menor", "erro"] = "erro de leitura"
    assert calibracao.escolher(resultados, tabela_cobertura()) == "inicial"


def test_bootstrap_inclui_exame_negativo_e_agrega_por_paciente():
    resultados = tabela_resultados()
    resultados.loc[resultados.seriesuid == "b", "paciente"] = "a"
    resumo = calibracao.resumir(resultados, 1000, 0.95, 42).set_index("configuracao")
    assert resumo.loc["inicial", "pacientes"] == 1
    assert resumo.loc["inicial", "por_exame"] == 100
    assert resumo.loc["inicial", "cobertura"] == 0.5
    assert resumo.loc["inicial", "cobertura_ic_inf"] == 0.5
    assert resumo.loc["inicial", "cobertura_ic_sup"] == 0.5
