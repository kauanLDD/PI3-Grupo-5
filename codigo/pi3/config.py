"""Lê configuracao/config.yaml e fixa a semente."""

import os
import random
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO = RAIZ / "configuracao" / "config.yaml"


def carregar(caminho=None):
    with open(caminho or CAMINHO, encoding="utf-8") as f:
        return yaml.safe_load(f)


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
