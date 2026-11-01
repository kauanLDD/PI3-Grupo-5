"""Lê configuracao/config.yaml e fixa a semente."""

import os
import random
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO = RAIZ / "configuracao" / "config.yaml"
# Fora do git: cada máquina diz aqui onde está a base. Ver configuracao/caminhos.exemplo.yaml.
LOCAL = RAIZ / "configuracao" / "caminhos.local.yaml"


def carregar(caminho=None, local=LOCAL):
    """Devolve os `caminhos` como Path absoluto: relativo no yaml é relativo à raiz do repo."""
    with open(caminho or CAMINHO, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if Path(local).exists():
        with open(local, encoding="utf-8") as f:
            cfg["caminhos"] = trocar_caminhos(cfg["caminhos"], yaml.safe_load(f) or {})

    caminhos = {}
    for chave, valor in cfg["caminhos"].items():
        caminho = Path(valor)
        # Caminho absoluto fica como está: no Windows a base pode viver em outro disco.
        caminhos[chave] = caminho if caminho.is_absolute() else RAIZ / caminho
    cfg["caminhos"] = caminhos
    return cfg


def trocar_caminhos(caminhos: dict, trocas: dict) -> dict:
    """Aplica os caminhos desta máquina por cima dos do config.yaml.

    Trocar `luna16` troca também todo caminho que começa com a raiz antiga, porque a cópia do
    Drive repete a estrutura de pastas do HD. As outras chaves são trocadas uma a uma.
    """
    desconhecidas = set(trocas) - set(caminhos)
    if desconhecidas:
        raise KeyError(f"caminhos.local.yaml com chaves que o config.yaml não tem: {sorted(desconhecidas)}")
    novos = dict(caminhos)
    if "luna16" in trocas:
        antiga, nova = str(caminhos["luna16"]).rstrip("/"), str(trocas["luna16"]).rstrip("/\\")
        for chave, valor in caminhos.items():
            if str(valor) == antiga or str(valor).startswith(antiga + "/"):
                novos[chave] = nova + str(valor)[len(antiga):]
    novos.update({k: v for k, v in trocas.items() if k != "luna16"})
    return novos


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
