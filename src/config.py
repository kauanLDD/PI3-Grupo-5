"""Lê configuracao/config.yaml e fixa a semente."""

import os
import random
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO = RAIZ / "configuracao" / "config.yaml"


def carregar(caminho=None):
    """Devolve os `caminhos` como Path absoluto: relativo no yaml é relativo à raiz do repo."""
    with open(caminho or CAMINHO, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    caminhos = {}
    for chave, valor in cfg["caminhos"].items():
        caminho = Path(valor)
        # Caminho absoluto fica como está: no Windows a base pode viver em outro disco.
        caminhos[chave] = caminho if caminho.is_absolute() else RAIZ / caminho
    cfg["caminhos"] = caminhos
    return cfg


def fixar_semente(semente=None):
    """Fixa random, numpy e torch. Chamar no início de todo script e notebook."""
    if semente is None:
        semente = carregar()["seed"]

    random.seed(semente)
    os.environ["PYTHONHASHSEED"] = str(semente)

    try:
        import numpy as np
        np.random.seed(semente)
    except ImportError:
        pass

    try:
        import torch
        torch.manual_seed(semente)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(semente)
    except ImportError:
        pass

    return semente
