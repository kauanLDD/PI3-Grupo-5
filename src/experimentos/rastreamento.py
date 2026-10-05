"""Rastreia execuções locais e a procedência dos arquivos usados."""

from contextlib import contextmanager
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import config


def sha256(caminho):
    resumo = hashlib.sha256()
    with Path(caminho).open("rb") as arquivo:
        while bloco := arquivo.read(1024 * 1024):
            resumo.update(bloco)
    return resumo.hexdigest()


def uri_local(cfg):
    banco = cfg["caminhos"]["mlflow_banco"].resolve()
    banco.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{banco.as_posix()}"


def cliente_local(cfg):
    os.environ["MLFLOW_ENABLE_TELEMETRY"] = "false"
    from mlflow import MlflowClient
    return MlflowClient(tracking_uri=uri_local(cfg))


def arquivos_codigo():
    arquivos = set()
    for pasta in ("src", "scripts"):
        arquivos.update((config.RAIZ / pasta).rglob("*.py"))
    arquivos.update((config.RAIZ / "configuracao").glob("*.yaml"))
    for nome in ("dvc.yaml", "dvc.lock", "requirements.txt", "requirements-rastreamento.lock.txt"):
        caminho = config.RAIZ / nome
        if caminho.exists():
            arquivos.add(caminho)
    return sorted(arquivos)


@contextmanager
def iniciar(cfg, nome, tipo, parametros, entradas):
    cliente = cliente_local(cfg)
    experimento = cliente.get_experiment_by_name(cfg["rastreamento"]["experimento"])
    if experimento is None:
        artefatos = cfg["caminhos"]["mlflow_artefatos"].resolve()
        artefatos.mkdir(parents=True, exist_ok=True)
        experimento_id = cliente.create_experiment(
            cfg["rastreamento"]["experimento"], artifact_location=artefatos.as_uri()
        )
    else:
        experimento_id = experimento.experiment_id

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=config.RAIZ, text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=config.RAIZ, text=True
    )
    run = cliente.create_run(experimento_id, tags={
        "mlflow.runName": nome, "tipo": tipo, "git_commit_base": commit,
        "git_com_alteracoes": str(bool(status.strip())).lower(),
        "origem": "local", "teste_utilizado": "false",
    })
    run_id = run.info.run_id
    try:
        for chave, valor in parametros.items():
            cliente.log_param(run_id, chave, valor)
        with TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            manifesto = {
                "git_commit_base": commit,
                "git_status": status,
                "entradas": {
                    nome: {"sha256": sha256(caminho), "bytes": Path(caminho).stat().st_size}
                    for nome, caminho in entradas.items()
                },
                "codigo": {
                    str(p.relative_to(config.RAIZ)): sha256(p) for p in arquivos_codigo()
                },
            }
            (pasta / "procedencia.json").write_text(json.dumps(manifesto, indent=2))
            (pasta / "ambiente.txt").write_text("\n".join(sorted(
                f"{d.metadata['Name']}=={d.version}" for d in distributions()
            )) + "\n")
            with ZipFile(pasta / "codigo.zip", "w") as pacote:
                for caminho in arquivos_codigo():
                    pacote.write(caminho, str(caminho.relative_to(config.RAIZ)))
            cliente.log_artifacts(run_id, str(pasta), artifact_path="procedencia")
        yield cliente, run_id
    except BaseException:
        cliente.set_terminated(run_id, status="FAILED")
        raise
    else:
        cliente.set_terminated(run_id, status="FINISHED")
