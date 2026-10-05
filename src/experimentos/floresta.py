"""Treina o baseline com features de intensidade e preserva a identidade dos candidatos."""

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from detection.features import COLUNAS


def conferir_particao(dados, particao):
    if dados.empty or not dados.particao.eq(particao).all():
        raise ValueError(f"esperada somente a particao {particao}")
    if dados.candidate_id.duplicated().any() or dados.isna().any().any():
        raise ValueError("candidatos duplicados ou valores ausentes")
    if not dados.classe_luna16.isin([0, 1]).all():
        raise ValueError("rotulos devem ser 0 ou 1")
    if not np.isfinite(dados[list(COLUNAS)]).all().all():
        raise ValueError("features com valores infinitos")


def treinar(dados, parametros, semente):
    conferir_particao(dados, "treino")
    if dados.classe_luna16.nunique() != 2:
        raise ValueError("treino precisa das duas classes")
    modelo = RandomForestClassifier(random_state=semente, **parametros)
    modelo.fit(dados[list(COLUNAS)], dados.classe_luna16)
    return modelo


def prever_validacao(modelo, dados, treino):
    conferir_particao(dados, "validacao")
    for coluna in ("paciente", "seriesuid", "candidate_id"):
        if set(dados[coluna]) & set(treino[coluna]):
            raise ValueError(f"{coluna} compartilhado entre treino e validacao")
    positivos = np.flatnonzero(modelo.classes_ == 1)
    if len(positivos) != 1:
        raise ValueError("modelo sem classe positiva")
    saida = dados[["candidate_id", "seriesuid", "coordX", "coordY", "coordZ"]].copy()
    saida["probability"] = modelo.predict_proba(dados[list(COLUNAS)])[:, positivos[0]]
    if not np.isfinite(saida.probability).all() or not saida.probability.between(0, 1).all():
        raise ValueError("probabilidades invalidas")
    return saida
