"""Média das sementes, pareamento só por exames e regra da supressão com raio maior."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def carregar():
    arquivo = Path(__file__).resolve().parents[1] / "scripts" / "34_supressao_lista_propria.py"
    spec = importlib.util.spec_from_file_location("supressao_lista_propria", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def notas(probabilidades, ordem=(0, 1)):
    pontos = pd.DataFrame({"seriesuid": ["a", "b"], "coordX": [1.0, 2.0], "coordY": [0.0, 0.0],
                           "coordZ": [0.0, 0.0], "probability": probabilidades})
    return pontos.iloc[list(ordem)]


def test_media_das_sementes_alinha_os_pontos_antes_de_tirar_a_media():
    media = carregar().media_das_sementes({42: notas([0.2, 0.8]), 43: notas([0.4, 0.6], ordem=(1, 0))})
    assert media.set_index("seriesuid").probability.to_dict() == pytest.approx({"a": 0.3, "b": 0.7})


def test_media_das_sementes_recusa_pontos_diferentes():
    outra = notas([0.4, 0.6]).assign(coordX=[1.0, 9.0])
    with pytest.raises(ValueError, match="pontos diferentes"):
        carregar().media_das_sementes({42: notas([0.2, 0.8]), 43: outra})


def protocolo(**mudanca):
    return {"exames": ["a", "b"], "protocolo": {"seed": 42, "bootstrap": 1000, "confianca": 0.95,
                                                "max_marcas_por_exame": 100, **mudanca}}


def test_pareamento_aceita_marcas_diferentes_mas_nao_outro_protocolo():
    modulo = carregar()
    modulo.conferir_exames(protocolo(), protocolo())
    with pytest.raises(ValueError, match="seed"):
        modulo.conferir_exames(protocolo(), protocolo(seed=7))
    with pytest.raises(ValueError, match="exames"):
        modulo.conferir_exames(protocolo(), {**protocolo(), "exames": ["a"]})


def tabelas(raio_10, raio_16, media, pares_10, pares_16, pares_media):
    linhas = [{"variante": "lista_inteira", "semente": s, "cpm": 0.50} for s in (42, 43, 44)]
    linhas += [{"variante": "raio_10", "semente": s, "cpm": c} for s, c in zip((42, 43, 44), raio_10)]
    linhas += [{"variante": "raio_16", "semente": s, "cpm": c} for s, c in zip((42, 43, 44), raio_16)]
    linhas.append({"variante": "media_sementes", "semente": "42, 43 e 44", "cpm": media})
    pares = [{"variante": v, "semente": s, "diferenca_cpm": d}
             for v, ds in (("raio_10", pares_10), ("raio_16", pares_16), ("media_sementes", pares_media))
             for s, d in zip((42, 43, 44), ds)]
    return pd.DataFrame(linhas), pd.DataFrame(pares)


def test_fica_a_supressao_de_maior_media_entre_as_que_passam():
    tabela, pares = tabelas((0.55,) * 3, (0.60,) * 3, 0.52, (0.05,) * 3, (0.10,) * 3, (0.01,) * 3)
    regra = carregar().aplicar_regra(tabela, pares, 0.50)
    assert regra["supressao_adotada"] == "raio_16"
    assert regra["media_sementes"]["passou"]


def test_uma_pareada_negativa_reprova_a_supressao_mesmo_com_media_maior():
    tabela, pares = tabelas((0.55,) * 3, (0.70,) * 3, 0.49, (0.05,) * 3, (0.2, 0.2, -0.01), (0.01,) * 3)
    regra = carregar().aplicar_regra(tabela, pares, 0.50)
    assert regra["supressao_adotada"] == "raio_10"
    assert not regra["supressao"]["raio_16"]["passou"]
    assert not regra["media_sementes"]["passou"]


def test_nenhuma_supressao_passa_abaixo_da_lista_inteira():
    tabela, pares = tabelas((0.45,) * 3, (0.48,) * 3, 0.52, (0.01,) * 3, (0.01,) * 3, (0.01,) * 3)
    assert carregar().aplicar_regra(tabela, pares, 0.50)["supressao_adotada"] is None
