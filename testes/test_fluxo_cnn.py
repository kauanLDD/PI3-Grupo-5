"""Protege o conjunto de teste e o vínculo do checkpoint com a divisão."""

import argparse
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
import torch


def carregar(nome):
    arquivo = Path(__file__).resolve().parents[1] / "scripts" / nome
    spec = importlib.util.spec_from_file_location(nome, arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_treino_nao_exige_recortes_de_teste(tmp_path, monkeypatch):
    script = carregar("18_treinar_cnn.py")
    pd.DataFrame({"seriesuid": ["a", "b", "c"], "paciente": ["p1", "p2", "p3"],
                  "subset": [0, 7, 8], "particao": ["treino", "validacao", "teste"]}).to_csv(
                      tmp_path / "divisao.csv", index=False)
    pd.DataFrame({"seriesuid": ["a", "b", "c"], "coordX": [0., 0., 0.],
                  "coordY": [0., 0., 0.], "coordZ": [0., 0., 0.], "class": [1, 0, 1]}).to_csv(
                      tmp_path / "candidates_V2.csv", index=False)
    monkeypatch.setattr(script, "argumentos", lambda: argparse.Namespace(
        config=None, dados=tmp_path, saida=tmp_path / "modelo", reproduzir_de=None,
        variante=None, semente=None, lista_propria=None))
    monkeypatch.setattr(script.config, "carregar", lambda _: {
        "cnn": {"epochs": 1, "negativos_por_positivo": 1}, "caminhos": {"volumes": tmp_path},
    })
    def conferir(pasta, volumes, exames):
        assert list(exames) == ["a", "b"]
        raise RuntimeError("checagem de origem alcançada")
    monkeypatch.setattr(script.cnn, "conferir_origem", conferir)
    with pytest.raises(RuntimeError, match="checagem de origem"):
        script.main()


def test_avaliacao_final_recusa_mudar_a_divisao(tmp_path, monkeypatch):
    script = carregar("20_avaliar_teste_cnn.py")
    modelo = tmp_path / "modelo.pt"
    torch.save({"divisao_sha256": "outro-hash"}, modelo)
    divisao = tmp_path / "divisao.csv"
    divisao.write_text("seriesuid,paciente,subset,particao\na,p,8,teste\n")
    monkeypatch.setattr(script.config, "carregar", lambda: {"caminhos": {"divisao": divisao}})
    monkeypatch.setattr(script.sys, "argv", ["20", "--modelo", str(modelo),
                                           "--saida", str(tmp_path / "saida")])
    with pytest.raises(ValueError, match="entrada congelada"):
        script.main()


def test_semente_de_treino_e_opcional_e_inteira(monkeypatch, tmp_path):
    script = carregar("18_treinar_cnn.py")
    monkeypatch.setattr(script.sys, "argv", ["18", "--saida", str(tmp_path)])
    assert script.argumentos().semente is None
    monkeypatch.setattr(script.sys, "argv", ["18", "--saida", str(tmp_path), "--semente", "43"])
    assert script.argumentos().semente == 43


def test_variante_sobrescreve_cnn_e_recusa_chave_desconhecida():
    script = carregar("18_treinar_cnn.py")
    cfg = {"cnn": {"epochs": 15, "batch_size": 32},
           "experimentos_cnn": {"longa": {"epochs": 40, "aumento": True}, "errada": {"epoch": 40}}}
    assert script.aplicar_variante(cfg, None) == {"epochs": 15, "batch_size": 32}
    assert script.aplicar_variante(cfg, "longa") == {"epochs": 40, "batch_size": 32, "aumento": True}
    with pytest.raises(ValueError, match="desconhecidas"):
        script.aplicar_variante(cfg, "errada")
    with pytest.raises(ValueError, match="inexistente"):
        script.aplicar_variante(cfg, "outra")


@pytest.mark.parametrize("variante, lista, mensagem", [
    ("lr_3e-4", "inexistente", "variante inexistente"),
    ("aumento", "vizinhos", "usa --variante lr_3e-4"),
])
def test_lista_propria_recusa_variante_errada_antes_de_ler_dados(tmp_path, monkeypatch, variante, lista, mensagem):
    script = carregar("18_treinar_cnn.py")
    monkeypatch.setattr(script, "argumentos", lambda: argparse.Namespace(
        config=None, dados=None, saida=tmp_path / "modelo", reproduzir_de=None,
        variante=variante, semente=None, lista_propria=lista))
    monkeypatch.setattr(script.config, "carregar", lambda _: {
        "cnn": {"epochs": 1, "negativos_por_positivo": 1},
        "experimentos_cnn": {"lr_3e-4": {"epochs": 40}, "aumento": {"epochs": 40}},
        "treino_lista_propria": {"variante_rede": "lr_3e-4", "variantes": {"vizinhos": {}}},
        "caminhos": {}})
    with pytest.raises(ValueError, match=mensagem):
        script.main()
    assert not (tmp_path / "modelo").exists()
