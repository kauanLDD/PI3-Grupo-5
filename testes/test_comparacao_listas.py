"""A comparação entre a lista própria e o V2 na mesma base (S4-T11)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import candidatos as det
from detection import comparacao


def pontos(*linhas):
    return pd.DataFrame([{"seriesuid": u, "coordX": x, "coordY": y, "coordZ": z}
                         for u, x, y, z in linhas])


def nodulos(*linhas):
    return pd.DataFrame([{"seriesuid": u, "coordX": x, "coordY": 0.0, "coordZ": 0.0,
                          "diameter_mm": d} for u, x, d in linhas])


def test_conferencia_conta_o_que_fica_fora_do_inventario():
    lista = pontos(("a", 0, 0, 0), ("a", 1, 0, 0), ("x", 0, 0, 0))
    entrada = comparacao.conferir_entrada(lista, {"a", "b"})
    assert entrada == {"pontos_lidos": 3, "pontos_fora_do_inventario": 1, "exames": 2,
                       "exames_com_candidato": 1, "exames_sem_candidato": 1}


def test_conferencia_recusa_coordenada_ausente():
    """Ponto sem coordenada não alcança nada e baixaria a cobertura sem aviso."""
    lista = pontos(("a", np.nan, 0, 0))
    with pytest.raises(ValueError, match="coordenada"):
        comparacao.conferir_entrada(lista, {"a"})


def test_conferencia_recusa_lista_sem_coluna_de_coordenada():
    with pytest.raises(ValueError, match="coordZ"):
        comparacao.conferir_entrada(pontos(("a", 0, 0, 0)).drop(columns="coordZ"), {"a"})


def test_exame_sem_candidato_entra_no_denominador():
    """Três exames e quatro pontos dão 4/3 por exame, e não 4/2."""
    lista = pontos(("a", 0, 0, 0), ("a", 1, 0, 0), ("a", 2, 0, 0), ("b", 0, 0, 0))
    contagem = comparacao.candidatos_por_exame(lista, {"a", "b", "c"})
    assert contagem.to_dict() == {"a": 3, "b": 1, "c": 0}
    assert contagem.mean() == pytest.approx(4 / 3)


def test_ponto_de_exame_fora_do_inventario_nao_entra_na_conta():
    lista = pontos(("a", 0, 0, 0), ("x", 0, 0, 0))
    assert comparacao.candidatos_por_exame(lista, {"a"}).sum() == 1


def test_resumo_junta_quantidade_e_cobertura():
    referencia = nodulos(("a", 0.0, 10.0), ("b", 0.0, 10.0))
    lista = pontos(("a", 1, 0, 0), ("a", 50, 0, 0), ("c", 0, 0, 0))
    alcance = det.alcancados(referencia, lista)
    linha = comparacao.resumir("teste", lista, {"a", "b", "c"}, referencia, alcance,
                               reamostras=100, confianca=0.95, semente=42)
    assert (linha["pontos"], linha["exames"], linha["minimo_por_exame"]) == (3, 3, 0)
    assert linha["por_exame"] == pytest.approx(1.0)
    assert (linha["alcancados"], linha["nodulos"], linha["cobertura"]) == (1, 2, 0.5)


def test_cruzamento_separa_o_que_cada_lista_alcanca_sozinha():
    propria = np.array([True, True, False, False, True])
    v2 = np.array([True, False, True, False, True])
    assert comparacao.cruzar(propria, v2) == {"nodulos": 5, "ambas": 2, "so_a": 1, "so_b": 1,
                                              "nenhuma": 1, "uniao": 4}


def test_mesma_cobertura_nao_quer_dizer_os_mesmos_nodulos():
    """As duas alcançam um de dois, e a união alcança os dois."""
    resultado = comparacao.cruzar([True, False], [False, True])
    assert resultado["ambas"] == 0
    assert resultado["uniao"] == 2


def test_cruzamento_recusa_alcances_de_tamanhos_diferentes():
    """Tamanho diferente é sinal de nódulos diferentes, e a comparação perde o sentido."""
    with pytest.raises(ValueError, match="mesmos nódulos"):
        comparacao.cruzar([True, False], [True])
