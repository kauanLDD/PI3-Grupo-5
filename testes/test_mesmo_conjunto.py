"""Contagens por conjunto e comparação das listas da rede e do Random Forest (T21)."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]


def carregar():
    arquivo = RAIZ / "scripts" / "38_conferir_mesmo_conjunto.py"
    spec = importlib.util.spec_from_file_location("conferir_mesmo_conjunto", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def divisao():
    return pd.DataFrame({"seriesuid": ["a", "b", "c", "d"], "paciente": ["p1", "p1", "p2", "p3"],
                         "subset": [0, 1, 7, 8], "particao": ["treino", "treino", "validacao", "teste"]})


def test_acha_paciente_em_dois_conjuntos():
    tabela = divisao().assign(paciente=["p1", "p2", "p1", "p3"])
    assert carregar().pacientes_em_mais_de_um_conjunto(tabela) == ["p1"]


def test_paciente_com_duas_series_no_mesmo_conjunto_nao_e_vazamento():
    assert carregar().pacientes_em_mais_de_um_conjunto(divisao()) == []


def test_contar_separa_positivos_e_conta_pacientes():
    marcas = pd.DataFrame({"seriesuid": ["a", "a", "b"], "class": [1, 0, 0]})
    linha = carregar().contar(marcas, divisao(), "treino", "rede", "-")
    assert (linha["exames"], linha["pacientes"], linha["candidatos"], linha["positivos"], linha["negativos"]) == \
        (2, 1, 3, 1, 2)


def test_contar_sem_rotulo_nao_inventa_positivos():
    linha = carregar().contar(pd.DataFrame({"seriesuid": ["d"]}), divisao(), "teste", "rede", "-")
    assert linha["positivos"] is None and linha["negativos"] is None


def test_contar_recusa_exame_de_outra_particao():
    with pytest.raises(ValueError, match="fora da partição"):
        carregar().contar(pd.DataFrame({"seriesuid": ["a", "c"]}), divisao(), "validacao", "rede", "-")


def test_comparar_pontos_conta_os_dois_lados():
    a = pd.DataFrame({"candidate_id": [1, 2, 3]})
    b = pd.DataFrame({"candidate_id": [2, 3, 4, 5]})
    assert carregar().comparar_pontos(a, b, ["candidate_id"]) == \
        {"so_na_rede": 1, "so_no_random_forest": 2, "nos_dois": 2}


def test_comparar_pontos_recusa_ponto_repetido():
    a = pd.DataFrame({"candidate_id": [1, 1]})
    with pytest.raises(ValueError, match="repetido"):
        carregar().comparar_pontos(a, a, ["candidate_id"])


def test_divisao_versionada_nao_poe_paciente_em_dois_conjuntos():
    """Roda sem a base: a divisão congelada junto da rede escolhida está no git."""
    tabela = pd.read_csv(RAIZ / "modelos" / "cnn_lr_3e-4" / "divisao.csv")
    assert carregar().pacientes_em_mais_de_um_conjunto(tabela) == []
    assert not tabela.seriesuid.duplicated().any()
    resumo = carregar().resumir_divisao(tabela).set_index("conjunto")[["exames", "pacientes"]]
    assert resumo.to_dict("index") == {"treino": {"exames": 623, "pacientes": 622},
                                       "validacao": {"exames": 89, "pacientes": 89},
                                       "teste": {"exames": 176, "pacientes": 176}}
