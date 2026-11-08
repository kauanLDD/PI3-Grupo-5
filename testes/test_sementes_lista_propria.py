"""Regra da Fase 4: média na nossa lista, pareadas positivas nas três sementes e limite de queda na V2."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def carregar():
    arquivo = Path(__file__).resolve().parents[1] / "scripts" / "33_sementes_lista_propria.py"
    spec = importlib.util.spec_from_file_location("sementes_lista_propria", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def tabelas(propria_nova, v2_nova, pares_propria):
    linhas = []
    for semente, (p, v) in zip((42, 43, 44), zip(propria_nova, v2_nova)):
        linhas += [{"rede": "uniforme", "semente": semente, "lista": "propria", "cpm": p},
                   {"rede": "uniforme", "semente": semente, "lista": "v2", "cpm": v},
                   {"rede": "antiga", "semente": semente, "lista": "propria", "cpm": 0.47},
                   {"rede": "antiga", "semente": semente, "lista": "v2", "cpm": 0.78}]
    pares = pd.DataFrame({"semente": [42, 43, 44], "lista": "propria", "diferenca_cpm": pares_propria})
    return pd.DataFrame(linhas), pares


@pytest.mark.parametrize("propria, v2, pares, confirmada", [
    ((0.52, 0.51, 0.53), (0.77, 0.78, 0.76), (0.05, 0.04, 0.06), True),
    ((0.52, 0.51, 0.53), (0.77, 0.78, 0.76), (0.05, -0.01, 0.06), False),
    ((0.52, 0.51, 0.53), (0.74, 0.75, 0.73), (0.05, 0.04, 0.06), False),
    ((0.46, 0.46, 0.46), (0.78, 0.78, 0.78), (0.01, 0.01, 0.01), False),
])
def test_regra_exige_as_duas_condicoes(propria, v2, pares, confirmada):
    tabela, diferencas = tabelas(propria, v2, pares)
    assert carregar().aplicar_regra(tabela, diferencas, 0.022)["confirmada"] is confirmada


def test_queda_exatamente_no_limite_ainda_passa():
    tabela, diferencas = tabelas((0.52, 0.52, 0.52), (0.758, 0.758, 0.758), (0.05, 0.05, 0.05))
    regra = carregar().aplicar_regra(tabela, diferencas, 0.022)
    assert regra["queda_media_cpm_v2"] == pytest.approx(0.022)
    assert regra["condicao_2_v2_dentro_do_limite"]
