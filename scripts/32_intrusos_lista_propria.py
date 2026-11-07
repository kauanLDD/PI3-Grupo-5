"""Quais candidatos da nossa lista recebem nota acima dos nódulos verdadeiros, e o que eles têm em comum.

Lê as notas que o script 31 gravou na validação, sem pontuar nada de novo. Intruso de um nódulo é
todo falso positivo do mesmo exame com nota maior que a do melhor acerto daquele nódulo; um falso
positivo conta uma vez só, mesmo que passe na frente de dois nódulos.
"""

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import candidatos as det
from experimentos import erros


def script_29():
    arquivo = Path(__file__).resolve().parent / "29_analisar_erros_cnn.py"
    spec = importlib.util.spec_from_file_location("analisar_erros", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def melhor_acerto(nodulos, marcas):
    """Nota do melhor candidato dentro do raio de cada nódulo e a distância dele ao centro, em mm.

    NaN quando nenhum candidato cai dentro do raio.
    """
    por_exame = dict(tuple(marcas.groupby("seriesuid")))
    notas, distancias = [], []
    for _, n in nodulos.iterrows():
        exame = por_exame.get(n.seriesuid)
        pontos = exame[det.COLUNAS].to_numpy(float) if exame is not None else np.zeros((0, 3))
        dentro = erros.dentro(pontos, n)
        if not dentro.any():
            notas.append(np.nan)
            distancias.append(np.nan)
            continue
        i = int(np.argmax(np.where(dentro, exame.probability.to_numpy(), -np.inf)))
        notas.append(float(exame.probability.iloc[i]))
        distancias.append(float(np.linalg.norm(pontos[i] - [n.coordX, n.coordY, n.coordZ])))
    return np.array(notas), np.array(distancias)


def marcar_intrusos(marcas, nodulos):
    """Cada falso positivo vira intruso se passa na frente de ao menos um nódulo do exame."""
    corte = nodulos.dropna(subset=["melhor_acerto"]).groupby("seriesuid").melhor_acerto.min()
    limite = marcas.seriesuid.map(corte)
    return (marcas.rotulo == det.FALSO_POSITIVO) & (marcas.probability > limite)


def intrusos_por_nodulo(marcas, nodulos):
    falsos = marcas[marcas.rotulo == det.FALSO_POSITIVO]
    por_exame = {uid: g.probability.to_numpy() for uid, g in falsos.groupby("seriesuid")}
    return [int((por_exame.get(n.seriesuid, np.array([])) > n.melhor_acerto).sum())
            if pd.notna(n.melhor_acerto) else np.nan for _, n in nodulos.iterrows()]


def rotular(marcas, nodulos, excluidas):
    marcas = marcas.reset_index(drop=True)
    marcas["rotulo"] = det.rotular(marcas, nodulos, excluidas)
    return marcas


def contar(grupos, coluna, cortes, unidade, abaixo=None, vazio=None):
    """Contagem e proporção por faixa; `abaixo` nomeia a faixa negativa e `vazio` a dos NaN."""
    limites = [*cortes, np.inf]
    nomes = [f"{a} a {b} {unidade}" for a, b in zip(cortes, cortes[1:])] + [f"acima de {cortes[-1]} {unidade}"]
    if abaixo:
        limites, nomes = [-np.inf, *limites], [abaixo, *nomes]
    linhas = []
    for grupo, tabela in grupos.items():
        if tabela[coluna].isna().all():
            continue
        faixa = pd.cut(tabela[coluna], limites, right=False, labels=nomes)
        contagem = faixa.value_counts().reindex(nomes, fill_value=0)
        if vazio:
            contagem[vazio] = int(tabela[coluna].isna().sum())
        for nome, n in contagem.items():
            linhas.append({"medida": coluna, "faixa": nome, "grupo": grupo, "n": int(n),
                           "proporcao": round(n / len(tabela), 3)})
    return linhas


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    c, p = cfg["caminhos"], cfg["intrusos"]
    saida, completa = c["intrusos_lista_propria"], c["intrusos_lista_propria_completa"]
    if saida.exists() or completa.exists():
        raise ValueError(f"preserve a análise anterior e apague-a à mão: {saida} / {completa}")
    analise = script_29()

    divisao = pd.read_csv(c["divisao"])
    uids = sorted(divisao.loc[divisao.particao.eq(cfg["lista_propria"]["particao"]), "seriesuid"])
    anotacoes = pd.read_csv(c["luna16_anotacoes"])
    excluidas = pd.read_csv(c["luna16_anotacoes_excluidas"])
    nodulos = anotacoes[anotacoes.seriesuid.isin(uids)].reset_index(drop=True)
    excluidas = excluidas[excluidas.seriesuid.isin(uids)]

    propria = rotular(pd.read_csv(config.RAIZ / p["probabilidades"]), nodulos, excluidas)
    v2 = rotular(pd.read_csv(config.RAIZ / p["probabilidades_v2"]), nodulos, excluidas)
    for nome, marcas in (("própria", propria), ("V2", v2)):
        if sorted(marcas.seriesuid.unique()) != uids:
            raise ValueError(f"lista {nome}: exames diferentes dos {len(uids)} da validação")
    print(f"exames lidos {len(uids)}, com erro 0, descartados 0; marcas: própria {len(propria)}, V2 {len(v2)}")
    print("rótulos da própria:", propria.rotulo.value_counts().to_dict())

    resumo = {"exames": len(uids), "nodulos": len(nodulos), "listas": {}}
    grupos = {}
    for nome, marcas in (("propria", propria), ("v2", v2)):
        nodulos[f"melhor_acerto_{nome}"], nodulos[f"melhor_acerto_centro_mm_{nome}"] = melhor_acerto(nodulos, marcas)
        com_nome = nodulos.assign(melhor_acerto=nodulos[f"melhor_acerto_{nome}"])
        nodulos[f"intrusos_{nome}"] = intrusos_por_nodulo(marcas, com_nome)
        marcas["intruso"] = marcar_intrusos(marcas, com_nome)
        topo = erros.marcas_por_exame(marcas)
        resumo["listas"][nome] = {
            "marcas": len(marcas), "acertos": int((marcas.rotulo == det.ACERTO).sum()),
            "falsos_positivos": int((marcas.rotulo == det.FALSO_POSITIVO).sum()),
            "intrusos": int(marcas.intruso.sum()),
            "exames_com_intruso": int(marcas.loc[marcas.intruso, "seriesuid"].nunique()),
            "nodulos_sem_candidato": int(nodulos[f"melhor_acerto_{nome}"].isna().sum()),
            "nodulos_com_intruso": int((nodulos[f"intrusos_{nome}"] > 0).sum()),
            "intrusos_por_nodulo_mediana": float(np.nanmedian(nodulos[f"intrusos_{nome}"])),
            "falsos_positivos_nas_100": int((topo.rotulo == det.FALSO_POSITIVO).sum()),
            "intrusos_nas_100": int(topo.intruso.sum()),
            "acertos_nas_100": int((topo.rotulo == det.ACERTO).sum())}
        grupos[f"intrusos_{nome}"] = marcas[marcas.intruso].copy()
        # Acrescentado depois da primeira execução: um nódulo sozinho gerou 79% dos intrusos da
        # nossa lista, quase todos fora das 100 marcas que o avaliador guarda.
        grupos[f"intrusos_nas_100_{nome}"] = topo[topo.intruso].copy()
    print(json.dumps(resumo["listas"], indent=2))

    grupos["acertos_propria"] = propria[propria.rotulo == det.ACERTO].copy()
    comuns = propria[(propria.rotulo == det.FALSO_POSITIVO) & ~propria.intruso]
    grupos["comuns_propria"] = comuns.sample(p["amostra_falsos_positivos"], random_state=cfg["seed"]).copy()
    for g in grupos.values():
        if "raio" not in g:
            g["raio"] = np.nan

    lidas, sem_mascara = 0, []
    limite_borda = cfg["analise_erros"]["distancia_borda_maxima"]
    for tabela in grupos.values():
        tabela["distancia_borda_mm"] = np.nan
        tabela["nodulo_mais_proximo_mm"], _ = analise.mais_proximo(tabela, nodulos)
    for uid in uids:
        if not (c["luna16_mascaras"] / f"{uid}.mhd").exists():
            sem_mascara.append(uid)
            continue
        for tabela in grupos.values():
            linhas = tabela.index[tabela.seriesuid == uid]
            if len(linhas):
                pontos = tabela.loc[linhas, det.COLUNAS].to_numpy(float)
                tabela.loc[linhas, "distancia_borda_mm"] = analise.distancia_da_borda(
                    uid, pontos, c["luna16_mascaras"], limite_borda)
        lidas += 1
    print(f"máscaras lidas {lidas}; sem máscara {len(sem_mascara)}")

    linhas = (contar(grupos, "raio", p["faixas_raio"], "mm")
              + contar(grupos, "distancia_borda_mm", p["faixas_borda"], "mm", abaixo="fora do pulmão")
              + contar(grupos, "nodulo_mais_proximo_mm", p["faixas_distancia_nodulo"], "mm",
                       vazio="exame sem nódulo"))
    tabela = pd.DataFrame(linhas)
    largura = tabela.pivot_table(index=["medida", "faixa"], columns="grupo", values=["n", "proporcao"],
                                 sort=False)
    largura.columns = [f"{grupo}_{valor}" for valor, grupo in largura.columns]
    ordem = [f"{g}_{v}" for g in grupos for v in ("n", "proporcao") if f"{g}_{v}" in largura.columns]
    largura = largura[ordem].reset_index()

    completa.mkdir(parents=True)
    saida.mkdir(parents=True)
    for nome, g in grupos.items():
        g.to_csv(completa / f"{nome}.csv", index=False)
    nodulos.to_csv(saida / "nodulos.csv", index=False)
    largura.to_csv(saida / "intrusos_por_faixa.csv", index=False)
    resumo["grupos"] = {nome: {"n": len(g), "nota_mediana": round(float(g.probability.median()), 4),
                               "raio_mediana": None if g.raio.isna().all() else float(g.raio.median()),
                               "borda_mediana_mm": round(float(g.distancia_borda_mm.median()), 2),
                               "nodulo_mais_proximo_mediana_mm": round(float(g.nodulo_mais_proximo_mm.median()), 2)}
                        for nome, g in grupos.items()}
    resumo["mascaras_lidas"], resumo["sem_mascara"] = lidas, sem_mascara
    resumo["acrescentado_depois_da_primeira_execucao"] = [
        "grupos intrusos_nas_100", "melhor_acerto_centro_mm por nódulo", "intrusos_por_exame",
        "nodulo_dentro_do_cubo"]
    # Metade do lado do cubo que a rede vê (32 voxels de 1 mm): o nódulo aparece dentro do recorte.
    meio_cubo = cfg["cnn"]["patch_size"] / 2
    resumo["nodulo_dentro_do_cubo"] = {
        nome: {"ate_mm": meio_cubo, "n": int((g.nodulo_mais_proximo_mm <= meio_cubo).sum()), "de": len(g),
               "nota_0_9_ou_mais": int(((g.nodulo_mais_proximo_mm <= meio_cubo) & (g.probability >= 0.9)).sum()),
               "de_nota_0_9_ou_mais": int((g.probability >= 0.9).sum())}
        for nome, g in grupos.items()}
    resumo["intrusos_por_exame"] = {nome: grupos[f"intrusos_{nome}"].seriesuid.value_counts().head(5).tolist()
                                    for nome in ("propria", "v2")}
    resumo["amostra_comuns"] = {"n": p["amostra_falsos_positivos"], "semente": cfg["seed"], "de": len(comuns)}

    topo = grupos["intrusos_propria"].sort_values("probability", ascending=False).head(p["intrusos_figura"])
    topo = topo.reset_index(drop=True)
    topo["legenda"] = [f"#{i + 1}, nota {analise.virgula(f.probability, 3)}, borda "
                       f"{analise.virgula(f.distancia_borda_mm, 0)} mm, nódulo a "
                       f"{analise.virgula(f.nodulo_mais_proximo_mm, 0)} mm" for i, f in topo.iterrows()]
    a = cfg["analise_erros"]
    resumo["figuras"] = analise.galerias(topo, c["volumes"], a["recorte_figura"], p["intrusos_figura"],
                                         "Intrusos de maior nota na nossa lista, validação (cruz: centro da marca)",
                                         saida / "intrusos")
    (saida / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumo["grupos"], indent=2, ensure_ascii=False))
    print(json.dumps(resumo["nodulo_dentro_do_cubo"], indent=2))
    print(largura.to_string(index=False))


if __name__ == "__main__":
    main()
