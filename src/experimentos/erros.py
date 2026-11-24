"""Separa as marcas de um modelo em acerto, falso positivo e ignorada, nódulo a nódulo.

Repete o casamento do `noduleCADEvaluationLUNA16.py`, que só grava os totais. Precisamos saber
qual nódulo foi perdido e qual marca é falso positivo para olhar a imagem de cada um.
"""

import numpy as np
import pandas as pd

# O programa oficial troca diâmetro negativo, que aparece nas excluídas, por 10 mm.
DIAMETRO_DESCONHECIDO = 10.0


def marcas_por_exame(previsoes: pd.DataFrame, maximo: int = 100) -> pd.DataFrame:
    """As marcas que o avaliador guarda: só as de escore estritamente maior que o 101º do exame."""
    partes = []
    for _, exame in previsoes.groupby("seriesuid", sort=False):
        if len(exame) > maximo:
            corte = np.sort(exame.probability.to_numpy())[::-1][maximo]
            exame = exame[exame.probability > corte].head(maximo)
        partes.append(exame)
    return pd.concat(partes)


def casar(marcas: pd.DataFrame, nodulos: pd.DataFrame, excluidas: pd.DataFrame):
    """Devolve as marcas com `tipo` e `nodulo`, e os nódulos com o maior escore que os alcançou."""
    marcas = marcas.reset_index(drop=True).assign(tipo="falso_positivo", nodulo=-1)
    nodulos = nodulos.reset_index(drop=True).assign(escore=np.nan, marcas=0)
    for uid, indices in marcas.groupby("seriesuid").groups.items():
        xyz = marcas.loc[indices, ["coordX", "coordY", "coordZ"]].to_numpy()
        for i, nodulo in nodulos[nodulos.seriesuid == uid].iterrows():
            perto = dentro(xyz, nodulo)
            if perto.any():
                alvo = indices[perto]
                marcas.loc[alvo, ["tipo", "nodulo"]] = ["acerto", i]
                nodulos.loc[i, ["escore", "marcas"]] = [marcas.loc[alvo, "probability"].max(), len(alvo)]
        livres = marcas.loc[indices, "tipo"] == "falso_positivo"
        for _, achado in excluidas[excluidas.seriesuid == uid].iterrows():
            alvo = indices[dentro(xyz, achado) & livres.to_numpy()]
            marcas.loc[alvo, "tipo"] = "excluida"
    return marcas, nodulos


def dentro(xyz: np.ndarray, achado) -> np.ndarray:
    diametro = achado.diameter_mm if achado.diameter_mm >= 0 else DIAMETRO_DESCONHECIDO
    centro = np.array([achado.coordX, achado.coordY, achado.coordZ], float)
    return ((xyz - centro) ** 2).sum(axis=1) < (diametro / 2) ** 2


def froc(marcas: pd.DataFrame, nodulos: pd.DataFrame, exames: int) -> pd.DataFrame:
    """FP por exame e sensibilidade em cada limiar dado pelos escores das marcas."""
    falsos = np.sort(marcas.loc[marcas.tipo == "falso_positivo", "probability"].to_numpy())
    acertos = np.sort(nodulos.escore.dropna().to_numpy())
    limiares = np.unique(np.concatenate([falsos, acertos]))[::-1]
    fp = len(falsos) - np.searchsorted(falsos, limiares, side="left")
    tp = len(acertos) - np.searchsorted(acertos, limiares, side="left")
    return pd.DataFrame({"limiar": limiares, "fp_por_exame": fp / exames, "sensibilidade": tp / len(nodulos)})


def limiar(marcas: pd.DataFrame, fp_por_exame: float, exames: int) -> float:
    """Menor escore que ainda deixa no máximo `fp_por_exame` falsos positivos por exame."""
    falsos = np.sort(marcas.loc[marcas.tipo == "falso_positivo", "probability"].to_numpy())[::-1]
    permitidos = int(np.floor(fp_por_exame * exames))
    if permitidos >= len(falsos):
        return float(falsos[-1])
    # Escore do primeiro falso positivo que passaria da conta, com um passo acima para excluí-lo.
    return float(np.nextafter(falsos[permitidos], np.inf))
