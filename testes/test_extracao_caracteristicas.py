"""Seleção da partição e retomada após falhas de leitura."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import SimpleITK as sitk

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/14_extrair_caracteristicas.py"
spec = importlib.util.spec_from_file_location("extracao", SCRIPT)
extracao = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extracao)


def grupo():
    return pd.DataFrame([{
        "candidate_id": 42, "seriesuid": "serie", "paciente": "p1",
        "subset": 7, "particao": "validacao", "coordX": 2.,
        "coordY": 2., "coordZ": 2., "class": 1,
    }])


def test_selecao_preserva_id_original_e_exclui_treino_e_teste(tmp_path):
    candidatos = pd.DataFrame({
        "seriesuid": ["treino", "validacao", "teste"],
        "coordX": [0., 1., 2.], "coordY": [0., 1., 2.],
        "coordZ": [0., 1., 2.], "class": [0, 1, 0],
    })
    divisao = pd.DataFrame({
        "seriesuid": candidatos.seriesuid, "paciente": ["a", "b", "c"],
        "subset": [0, 7, 8], "particao": ["treino", "validacao", "teste"],
    })
    caminho = tmp_path / "candidatos.csv"
    candidatos.to_csv(caminho, index=False)
    resultado, total = extracao.carregar_candidatos(caminho, divisao, "validacao")
    assert total == 3
    assert resultado.candidate_id.tolist() == [1]
    assert resultado["class"].tolist() == [1]
    with pytest.raises(ValueError, match="particao permitida"):
        extracao.carregar_candidatos(caminho, divisao, "teste")
    divisao.loc[1, "paciente"] = "a"
    with pytest.raises(ValueError, match="paciente presente"):
        extracao.carregar_candidatos(caminho, divisao, "validacao")


def test_falha_de_leitura_e_tentada_novamente(tmp_path, monkeypatch):
    volume = tmp_path / "volume.mha"
    destino = tmp_path / "features.csv"
    auditoria = tmp_path / "auditoria.csv"
    tarefa = ("serie", grupo(), str(volume), str(destino), str(auditoria), [3, 3, 3])
    primeira = extracao.processar_exame(tarefa)
    assert primeira[3] is not None
    assert not extracao.cache_valido(destino, auditoria, grupo())

    sitk.WriteImage(sitk.GetImageFromArray(np.ones((5, 5, 5), dtype=np.float32)), str(volume))
    segunda = extracao.processar_exame(tarefa)
    assert segunda == ("serie", 1, 0, None, False)

    def leitura_proibida(*args):
        pytest.fail("cache valido nao deve reabrir volume")
    monkeypatch.setattr(extracao.sitk, "ReadImage", leitura_proibida)
    terceira = extracao.processar_exame(tarefa)
    assert terceira == ("serie", 1, 0, None, True)

    tabela = pd.read_csv(destino)
    tabela.loc[0, "candidate_id"] = 99
    tabela.to_csv(destino, index=False)
    assert not extracao.cache_valido(destino, auditoria, grupo())
    with pytest.raises(RuntimeError, match="identificadores produzidos"):
        extracao.validar_resultado(grupo(), destino, auditoria)


def test_cache_incompleto_e_recusado(tmp_path):
    destino = tmp_path / "features.csv"
    auditoria = tmp_path / "auditoria.csv"
    pd.DataFrame({"candidate_id": [42]}).to_csv(destino, index=False)
    assert not extracao.cache_valido(destino, auditoria, grupo())
