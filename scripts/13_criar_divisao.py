"""Grava a divisão fixa de treino, validação e teste por paciente."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset import divisao


def main():
    cfg = config.carregar()
    config.fixar_semente()

    origem = cfg["caminhos"]["intermediario"] / "pacientes.csv"
    if not origem.exists():
        sys.exit(f"rode antes o 01_pacientes.py: {origem} não existe")

    pacientes = pd.read_csv(origem)
    tabela = divisao.criar(pacientes, cfg["divisao"]["particoes"])
    destino = cfg["caminhos"]["divisao"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    tabela.to_csv(temporario, index=False)
    temporario.replace(destino)

    print(divisao.resumir(tabela).to_string())
    print("0 pacientes em mais de uma partição")
    print(destino)


if __name__ == "__main__":
    main()
