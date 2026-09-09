"""Casamento entre ponto candidato e nódulo anotado, pelo critério do desafio."""

import numpy as np
import pandas as pd

COLUNAS = ["coordX", "coordY", "coordZ"]


def alcancados(nodulos: pd.DataFrame, candidatos: pd.DataFrame) -> np.ndarray:
    """Quais nódulos têm ao menos um candidato dentro do raio deles.

    O critério é o da página de avaliação do LUNA16: acerto é candidato a menos de R do centro,
    com R igual ao diâmetro dividido por dois. Ver docs/decisoes/0002.
    """
    por_exame = {uid: g[COLUNAS].to_numpy(float) for uid, g in candidatos.groupby("seriesuid")}
    alcancado = np.zeros(len(nodulos), dtype=bool)

    for i, nodulo in enumerate(nodulos.itertuples()):
        pontos = por_exame.get(nodulo.seriesuid)
        if pontos is None:
            continue
        centro = np.array([nodulo.coordX, nodulo.coordY, nodulo.coordZ], float)
        raio = nodulo.diameter_mm / 2
        alcancado[i] = bool((((pontos - centro) ** 2).sum(axis=1) <= raio ** 2).any())

    return alcancado
