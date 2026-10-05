"""Registro real em SQLite temporário, com sucesso e falha de execução."""

import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from experimentos import rastreamento


def configuracao(tmp_path):
    return {
        "caminhos": {
            "mlflow_banco": tmp_path / "mlflow.db",
            "mlflow_artefatos": tmp_path / "artefatos",
        },
        "rastreamento": {"experimento": "teste"},
    }


def test_registra_parametros_metricas_hash_e_codigo(tmp_path):
    cfg = configuracao(tmp_path)
    entrada = tmp_path / "entrada.csv"
    entrada.write_text("classe\n1\n")
    with rastreamento.iniciar(cfg, "verificacao", "teste", {"seed": 42}, {"dados": entrada}) as (cliente, run_id):
        cliente.log_metric(run_id, "linhas", 1)
    run = cliente.get_run(run_id)
    assert run.info.status == "FINISHED"
    assert run.data.params["seed"] == "42"
    assert run.data.metrics["linhas"] == 1
    assert run.data.tags["tipo"] == "teste"
    assert run.data.tags["git_com_alteracoes"] in {"true", "false"}
    manifesto = cliente.download_artifacts(run_id, "procedencia/procedencia.json", str(tmp_path))
    assert json.loads(Path(manifesto).read_text())["entradas"]["dados"]["sha256"] == rastreamento.sha256(entrada)
    codigo = cliente.download_artifacts(run_id, "procedencia/codigo.zip", str(tmp_path))
    with ZipFile(codigo) as pacote:
        assert "src/experimentos/rastreamento.py" in pacote.namelist()
        assert not any(p.startswith(("dados/", "tmp/", "_local/")) for p in pacote.namelist())


def test_excecao_marca_execucao_como_falha(tmp_path):
    cfg = configuracao(tmp_path)
    with pytest.raises(ValueError, match="erro esperado"):
        with rastreamento.iniciar(cfg, "falha", "teste", {}, {}) as (cliente, run_id):
            raise ValueError("erro esperado")
    assert cliente.get_run(run_id).info.status == "FAILED"
