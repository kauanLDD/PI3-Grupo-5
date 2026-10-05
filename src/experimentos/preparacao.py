"""Confere features e rótulos contra a lista V2 e a divisão por paciente."""

import numpy as np
import pandas as pd

from detection.features import COLUNAS


def conferir(cfg):
    caminhos = cfg["caminhos"]
    divisao = pd.read_csv(caminhos["divisao"])
    if divisao.seriesuid.duplicated().any() or divisao.isna().any().any():
        raise ValueError("divisao incompleta ou com exames repetidos")
    if (divisao.groupby("paciente").particao.nunique() > 1).any():
        raise ValueError("paciente presente em mais de uma particao")
    candidatos = pd.read_csv(caminhos["luna16_candidatos"]).reset_index(names="candidate_id")
    candidatos = candidatos.merge(divisao, on="seriesuid", how="left", validate="many_to_one")
    if candidatos.particao.isna().any():
        raise ValueError("candidato sem particao")

    metricas = {}
    entradas = {"divisao": caminhos["divisao"], "candidatos_v2": caminhos["luna16_candidatos"]}
    for particao in ("treino", "validacao"):
        nomes = [f"caracteristicas_{particao}", f"auditoria_caracteristicas_{particao}",
                 f"falhas_caracteristicas_{particao}"]
        entradas.update({nome: caminhos[nome] for nome in nomes})
        f = pd.read_csv(caminhos[nomes[0]]).set_index("candidate_id").sort_index()
        a = pd.read_csv(caminhos[nomes[1]]).set_index("candidate_id").sort_index()
        esperado = candidatos[candidatos.particao == particao].set_index("candidate_id").sort_index()
        if not pd.read_csv(caminhos[nomes[2]]).empty:
            raise ValueError(f"{particao}: existem falhas de exame")
        if not f.index.is_unique or not a.index.is_unique:
            raise ValueError(f"{particao}: identificadores duplicados")
        if not f.index.equals(esperado.index) or not a.index.equals(esperado.index):
            raise ValueError(f"{particao}: identificadores nao coincidem com a lista V2")
        if not (a.status == "produzido").all():
            raise ValueError(f"{particao}: candidatos descartados precisam ser revisados")
        for campo in ["seriesuid", "paciente", "subset", "particao"]:
            if not f[campo].equals(esperado[campo]):
                raise ValueError(f"{particao}: {campo} desalinhado")
        if not np.array_equal(f.classe_luna16, esperado["class"]):
            raise ValueError(f"{particao}: rotulos desalinhados")
        coordenadas = ["coordX", "coordY", "coordZ"]
        if not np.allclose(f[coordenadas], esperado[coordenadas], rtol=0, atol=1e-10):
            raise ValueError(f"{particao}: coordenadas desalinhadas")
        if f.isna().any().any() or not np.isfinite(f[list(COLUNAS)]).all().all():
            raise ValueError(f"{particao}: valores ausentes ou infinitos")
        metricas.update({
            f"{particao}_candidatos": len(f), f"{particao}_exames": f.seriesuid.nunique(),
            f"{particao}_pacientes": f.paciente.nunique(),
            f"{particao}_positivos": int(f.classe_luna16.sum()),
            f"{particao}_negativos": int((f.classe_luna16 == 0).sum()),
            f"{particao}_descartados": 0,
        })
    return metricas, entradas
