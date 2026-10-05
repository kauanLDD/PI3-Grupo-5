"""Amostragem por paciente e comparação pareada do gerador de candidatos."""

import numpy as np
import pandas as pd


def separar(pacientes, plano):
    if pacientes.seriesuid.duplicated().any() or pacientes.paciente.isna().any():
        raise ValueError("mapa de pacientes incompleto ou com exames repetidos")
    grupos = {}
    for fase in ("desenvolvimento", "validacao", "teste"):
        for subset in plano[fase]:
            if subset in grupos:
                raise ValueError("subset em mais de uma partição")
            grupos[subset] = fase
    tabela = pacientes.copy()
    tabela["particao"] = tabela.subset.map(grupos)
    if tabela.particao.isna().any():
        raise ValueError("exames sem partição")
    if (tabela.groupby("paciente").particao.nunique() > 1).any():
        raise ValueError("paciente presente em mais de uma partição")
    return tabela


def amostrar(tabela, anotacoes, positivos, negativos, seed):
    tabela = tabela.sort_values("seriesuid").copy()
    contagem = anotacoes.groupby("seriesuid").size()
    tabela["nodulos"] = tabela.seriesuid.map(contagem).fillna(0).astype(int)
    partes = []
    for tem_nodulo, quantidade in ((True, positivos), (False, negativos)):
        grupo = tabela[(tabela.nodulos > 0) == tem_nodulo]
        if len(grupo) < quantidade:
            raise ValueError("exames insuficientes para a amostra predefinida")
        partes.append(grupo.sample(n=quantidade, random_state=seed))
    return pd.concat(partes).sort_values("seriesuid").reset_index(drop=True)


def escolher(resultados, cobertura):
    """Menos candidatos, preservando cada nódulo alcançado pela configuração inicial."""
    referencia = resultados[resultados.configuracao == "inicial"]
    ids = set(referencia.seriesuid)
    if referencia.erro.ne("").any():
        raise ValueError("a referência contém falhas")
    acertos = cobertura[cobertura.configuracao == "inicial"].set_index("nodulo_id").alcancado
    elegiveis = []
    for nome, grupo in resultados.groupby("configuracao"):
        if set(grupo.seriesuid) != ids or grupo.erro.ne("").any():
            continue
        atual = cobertura[cobertura.configuracao == nome].set_index("nodulo_id").alcancado
        if set(atual.index) != set(acertos.index):
            continue
        if not (acertos & ~atual.reindex(acertos.index)).any():
            elegiveis.append((int(grupo.candidatos.sum()), nome))
    if not elegiveis:
        raise ValueError("nenhuma configuração com comparação completa")
    menor, nome = min(elegiveis)
    return nome if menor < referencia.candidatos.sum() else "inicial"


def resumir(resultados, reamostras, confianca, seed):
    """IC por bootstrap de pacientes, incluindo exames sem nódulos na média de candidatos."""
    linhas = []
    for (fase, nome), grupo in resultados.groupby(["particao", "configuracao"]):
        if grupo.erro.ne("").any():
            continue
        pacientes = grupo.groupby("paciente").agg(
            candidatos=("candidatos", "sum"), alcancados=("alcancados", "sum"),
            nodulos=("nodulos", "sum"), exames=("seriesuid", "size"),
        )
        valores = pacientes.to_numpy(float)
        rng = np.random.default_rng(seed)
        sorteios = valores[rng.integers(len(valores), size=(reamostras, len(valores)))].sum(axis=1)
        quantis = [(1 - confianca) / 2, (1 + confianca) / 2]
        ic_pontos = np.quantile(sorteios[:, 0] / sorteios[:, 3], quantis)
        validos = sorteios[:, 2] > 0
        ic_cobertura = np.quantile(sorteios[validos, 1] / sorteios[validos, 2], quantis) if validos.any() else [np.nan, np.nan]
        linhas.append({
            "particao": fase, "configuracao": nome, "exames": len(grupo),
            "pacientes": len(pacientes), "candidatos": int(grupo.candidatos.sum()),
            "por_exame": float(grupo.candidatos.mean()),
            "por_exame_ic_inf": ic_pontos[0], "por_exame_ic_sup": ic_pontos[1],
            "alcancados": int(grupo.alcancados.sum()), "nodulos": int(grupo.nodulos.sum()),
            "cobertura": grupo.alcancados.sum() / grupo.nodulos.sum() if grupo.nodulos.sum() else np.nan,
            "cobertura_ic_inf": ic_cobertura[0], "cobertura_ic_sup": ic_cobertura[1],
            "segundos": float(grupo.segundos.sum()),
        })
    return pd.DataFrame(linhas)
