"""Onde a rede escolhida erra no teste: nódulos perdidos por tamanho e falsos positivos de maior escore.

Lê as previsões que o avaliador oficial já recebeu, sem prever nem avaliar o teste de novo. Antes
de qualquer tabela, confere que o casamento repetido aqui dá os mesmos totais e os mesmos sete
pontos que o programa oficial gravou.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.stats import fisher_exact, mannwhitneyu
import SimpleITK as sitk

import config
from experimentos import erros
from preprocessing.coordenadas import mundo_para_indice
from visualization.fatias import tres_planos

PONTOS = [0.125, 0.25, 0.5, 1, 2, 4, 8]
NOMES_DOS_TIPOS = {"ao_lado_de_nodulo": "ao lado de um nódulo",
                   "sobre_lesao_grande_ou_irregular": "sobre lesão grande ou irregular",
                   "opacidade_arredondada_isolada": "opacidade arredondada isolada",
                   "vaso": "vaso", "parede_do_pulmao": "parede do pulmão", "outra": "outra"}
TOTAIS_OFICIAIS = {"True positives": "acerto", "False positives": "falso_positivo",
                   "Ignored candidates on excluded nodules": "excluida"}


def ler_avaliacao(pasta: Path, anotacoes, excluidas):
    previsoes = pd.read_csv(pasta / "predicoes.csv")
    exames = (pasta / "seriesuids.csv").read_text(encoding="utf-8").split()
    nodulos = anotacoes[anotacoes.seriesuid.isin(exames)]
    marcas, nodulos = erros.casar(erros.marcas_por_exame(previsoes),
                                  nodulos, excluidas[excluidas.seriesuid.isin(exames)])
    return previsoes, exames, marcas, nodulos


def conferir(pasta: Path, marcas, nodulos, exames):
    """Para se o casamento daqui não reproduz o CADAnalysis.txt e os sete pontos oficiais."""
    oficiais = {}
    for linha in (pasta / "CADAnalysis.txt").read_text(encoding="utf-8").splitlines():
        chave, _, valor = linha.strip().partition(":")
        if chave in TOTAIS_OFICIAIS:
            oficiais[chave] = int(valor)
    # Uma marca que acerta o nódulo conta uma vez como TP; as outras sobre ele são as duplas.
    nossos = {"True positives": int(nodulos.escore.notna().sum()),
              "False positives": int((marcas.tipo == "falso_positivo").sum()),
              "Ignored candidates on excluded nodules": int((marcas.tipo == "excluida").sum())}
    if nossos != oficiais:
        raise ValueError(f"{pasta}: casamento diferente do oficial: {nossos} contra {oficiais}")
    curva = erros.froc(marcas, nodulos, len(exames))
    nossos_pontos = np.interp(PONTOS, curva.fp_por_exame, curva.sensibilidade)
    oficiais_pontos = pd.read_csv(pasta / "pontos_operacao.csv").sensibilidade.to_numpy()
    if not np.allclose(nossos_pontos, oficiais_pontos, atol=1e-6):
        raise ValueError(f"{pasta}: FROC diferente da oficial: {nossos_pontos} contra {oficiais_pontos}")
    return {"totais": nossos, "sete_pontos": [round(float(v), 6) for v in nossos_pontos]}


def faixas(diametros, cortes):
    limites = [*cortes, np.inf]
    rotulos = [f"{a} a {b} mm" for a, b in zip(cortes, cortes[1:])] + [f"acima de {cortes[-1]} mm"]
    return pd.cut(diametros, limites, right=False, labels=rotulos)


def distancia_da_borda(uid, pontos, mascaras: Path, limite: float):
    """Distância em mm até fora da máscara de pulmão: positiva dentro, negativa fora."""
    mascara = sitk.ReadImage(str(mascaras / f"{uid}.mhd"))
    # Mesmo critério do pré-processamento (decisão 0002): tudo acima de zero é pulmão.
    pulmao = sitk.GetArrayFromImage(mascara) > 0
    passo = np.array(mascara.GetSpacing()[::-1])
    geometria = (mascara.GetOrigin(), mascara.GetSpacing(), mascara.GetDirection())
    meia = np.ceil(limite / passo).astype(int)
    distancias = []
    for ponto in pontos:
        centro = np.clip(np.round(mundo_para_indice(ponto, *geometria)).astype(int)[::-1], 0,
                         np.array(pulmao.shape) - 1)
        inicio = np.maximum(centro - meia, 0)
        caixa = pulmao[tuple(slice(a, b) for a, b in zip(inicio, centro + meia + 1))]
        local = tuple(centro - inicio)
        sinal = 1.0 if caixa[local] else -1.0
        alvo = caixa if caixa[local] else ~caixa
        if alvo.all():
            distancias.append(sinal * limite)
            continue
        distancia = ndimage.distance_transform_edt(alvo, sampling=passo)[local]
        distancias.append(sinal * min(float(distancia), limite))
    return distancias


def posicao_no_exame(nodulos, marcas):
    """1 quando a melhor marca do nódulo é a de maior escore do exame."""
    posicoes = []
    for _, n in nodulos.iterrows():
        escores = marcas.loc[marcas.seriesuid == n.seriesuid, "probability"]
        posicoes.append(int((escores > n.escore).sum()) + 1 if pd.notna(n.escore) else np.nan)
    return posicoes


def melhor_da_lista(nodulos, previsoes):
    """Maior escore entre todos os candidatos V2 dentro do raio, sem o limite de 100 marcas."""
    melhores = []
    for _, n in nodulos.iterrows():
        exame = previsoes[previsoes.seriesuid == n.seriesuid]
        dentro = erros.dentro(exame[["coordX", "coordY", "coordZ"]].to_numpy(), n)
        melhores.append(float(exame.probability[dentro].max()) if dentro.any() else np.nan)
    return melhores


def mais_proximo(marcas, achados):
    """Distância de cada marca ao achado mais próximo do mesmo exame, em mm e em raios."""
    mm, raios = [], []
    for _, m in marcas.iterrows():
        do_exame = achados[achados.seriesuid == m.seriesuid]
        if do_exame.empty:
            mm.append(np.nan)
            raios.append(np.nan)
            continue
        d = np.sqrt(((do_exame[["coordX", "coordY", "coordZ"]].to_numpy()
                      - m[["coordX", "coordY", "coordZ"]].to_numpy(float)) ** 2).sum(axis=1))
        i = int(np.argmin(d))
        diametro = do_exame.diameter_mm.iloc[i]
        mm.append(float(d[i]))
        raios.append(float(d[i] / (diametro / 2)) if diametro > 0 else np.nan)
    return mm, raios


def galerias(casos, volumes: Path, lado: int, por_figura: int, titulo: str, prefixo: Path):
    """Figuras com até `por_figura` casos, dois por linha, cada um nos três planos."""
    arquivos = []
    for pagina, inicio in enumerate(range(0, len(casos), por_figura), start=1):
        lote = casos.iloc[inicio:inicio + por_figura]
        linhas = int(np.ceil(len(lote) / 2))
        figura, eixos = plt.subplots(linhas, 6, figsize=(13, 2.5 * linhas), squeeze=False)
        for eixo in eixos.ravel():
            eixo.axis("off")
        for k, (_, caso) in enumerate(lote.iterrows()):
            imagem = sitk.ReadImage(str(volumes / f"{caso.seriesuid}.mha"))
            volume = sitk.GetArrayFromImage(imagem)
            centro = mundo_para_indice((caso.coordX, caso.coordY, caso.coordZ), imagem.GetOrigin(),
                                       imagem.GetSpacing(), imagem.GetDirection())[::-1]
            raio = caso.diameter_mm / 2 / imagem.GetSpacing()[0] if "diameter_mm" in caso else None
            trio = eixos[k // 2, 3 * (k % 2):3 * (k % 2) + 3]
            for eixo in trio:
                eixo.axis("on")
            tres_planos(trio, volume, centro, lado // 2, raio)
            trio[0].set_title(caso.legenda, fontsize=8, loc="left")
            if k < 2:
                for eixo, nome in zip(trio[1:], ("coronal", "sagital")):
                    eixo.set_title(nome, fontsize=8)
        unica = len(casos) <= por_figura
        figura.suptitle(titulo if unica else f"{titulo} ({pagina})", fontsize=10, x=0.01, ha="left")
        figura.tight_layout()
        sufixo = "" if unica else f"_{pagina}"
        destino = prefixo.with_name(f"{prefixo.name}{sufixo}.png")
        figura.savefig(destino, dpi=130)
        plt.close(figura)
        arquivos.append(destino.name)
    return arquivos


def perto_da_parede(nodulos, falsos, limite_mm):
    """Perdidos contra achados perto da borda, e quanto os falsos positivos de topo encostam em nódulo."""
    perto = nodulos.distancia_borda_mm <= limite_mm
    perdido = ~nodulos.achado_4fp
    tabela = [[int((perto & perdido).sum()), int((~perto & perdido).sum())],
              [int((perto & ~perdido).sum()), int((~perto & ~perdido).sum())]]
    razao, p_fisher = fisher_exact(tabela)
    vizinhanca = {}
    for quantos in (24, 100, len(falsos)):
        topo = falsos.head(quantos)
        vizinhanca[str(quantos)] = {
            "a_menos_de_20_mm_de_nodulo": round(float((topo.nodulo_mais_proximo_mm < 20).mean()), 3),
            "a_menos_de_3_raios_de_nodulo": round(float((topo.nodulo_mais_proximo_raios < 3).mean()), 3),
            f"a_{limite_mm}_mm_ou_menos_da_borda": round(float((topo.distancia_borda_mm <= limite_mm).mean()), 3)}
    return {"tabela_perto_longe_por_perdido_achado": tabela, "razao_de_chances": round(float(razao), 3),
            "p_fisher": round(float(p_fisher), 4),
            "p_mann_whitney_distancia": round(float(mannwhitneyu(nodulos.distancia_borda_mm[perdido],
                                                                  nodulos.distancia_borda_mm[~perdido]).pvalue), 4),
            "mediana_borda_mm": {"perdidos": round(float(nodulos.distancia_borda_mm[perdido].median()), 1),
                                 "achados": round(float(nodulos.distancia_borda_mm[~perdido].median()), 1)},
            "falsos_positivos_perto_de_nodulo": vizinhanca}


def por_tipo(classificacao: Path, falsos):
    """Junta a classificação visual aos falsos positivos e conta por tipo."""
    tipos = pd.read_csv(classificacao)
    topo = falsos.head(len(tipos))
    mesmos = (tipos.seriesuid.to_numpy() == topo.seriesuid.to_numpy()).all() and np.allclose(
        tipos[["coordX", "coordY", "coordZ"]].to_numpy(), topo[["coordX", "coordY", "coordZ"]].to_numpy())
    if not mesmos:
        raise ValueError(f"{classificacao} não corresponde aos {len(tipos)} falsos positivos de maior escore")
    topo = topo.assign(tipo=tipos.tipo.to_numpy(), observacao=tipos.observacao.fillna("").to_numpy())
    contagem = topo.groupby("tipo").agg(
        falsos_positivos=("tipo", "size"),
        nodulo_mais_proximo_mediana_mm=("nodulo_mais_proximo_mm", "median"),
        borda_mediana_mm=("distancia_borda_mm", "median")).sort_values("falsos_positivos", ascending=False)
    contagem.insert(1, "fracao", (contagem.falsos_positivos / len(topo)).round(3))
    return topo, contagem.round({"nodulo_mais_proximo_mediana_mm": 1, "borda_mediana_mm": 1})


def virgula(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",")


def main():
    config.fixar_semente()
    cfg = config.carregar()
    c, p = cfg["caminhos"], cfg["analise_erros"]
    saida = c["analise_erros_cnn"]
    saida.mkdir(parents=True, exist_ok=True)
    anotacoes = pd.read_csv(c["luna16_anotacoes"])
    excluidas = pd.read_csv(c["luna16_anotacoes_excluidas"])

    pasta = config.RAIZ / p["avaliacao"]
    previsoes, exames, marcas, nodulos = ler_avaliacao(pasta, anotacoes, excluidas)
    conferencia = {"cnn": conferir(pasta, marcas, nodulos, exames)}
    print(f"casamento igual ao oficial: {conferencia['cnn']['totais']}")

    limiares = {fp: erros.limiar(marcas, fp, len(exames)) for fp in p["fp_por_exame"]}
    for fp, valor in limiares.items():
        nodulos[f"achado_{fp}fp"] = nodulos.escore >= valor
    nodulos["faixa"] = faixas(nodulos.diameter_mm, p["faixas_diametro"])
    nodulos["posicao_no_exame"] = posicao_no_exame(nodulos, marcas)
    nodulos["melhor_escore_lista_v2"] = melhor_da_lista(nodulos, previsoes)

    pasta_rf = config.RAIZ / p["comparar_com"]
    _, exames_rf, marcas_rf, nodulos_rf = ler_avaliacao(pasta_rf, anotacoes, excluidas)
    if sorted(exames_rf) != sorted(exames):
        raise ValueError("as duas avaliações precisam ser dos mesmos exames")
    conferencia["random_forest"] = conferir(pasta_rf, marcas_rf, nodulos_rf, exames_rf)
    limiar_rf = erros.limiar(marcas_rf, 4, len(exames))
    nodulos["achado_rf_4fp"] = (nodulos_rf.escore >= limiar_rf).to_numpy()

    corte = limiares[max(limiares)]
    falsos = marcas[(marcas.tipo == "falso_positivo") & (marcas.probability >= corte)]
    falsos = falsos.sort_values("probability", ascending=False).reset_index(drop=True)
    falsos["nodulo_mais_proximo_mm"], falsos["nodulo_mais_proximo_raios"] = mais_proximo(falsos, nodulos)
    falsos["excluida_mais_proxima_mm"], _ = mais_proximo(
        falsos, excluidas[excluidas.seriesuid.isin(exames)].assign(diameter_mm=lambda d: d.diameter_mm.clip(lower=0)))

    nodulos["distancia_borda_mm"] = np.nan
    falsos["distancia_borda_mm"] = np.nan
    lidos, sem_mascara = 0, []
    for uid in sorted(set(nodulos.seriesuid) | set(falsos.seriesuid)):
        if not (c["luna16_mascaras"] / f"{uid}.mhd").exists():
            sem_mascara.append(uid)
            continue
        for tabela in (nodulos, falsos):
            linhas = tabela.index[tabela.seriesuid == uid]
            if len(linhas):
                pontos = tabela.loc[linhas, ["coordX", "coordY", "coordZ"]].to_numpy(float)
                tabela.loc[linhas, "distancia_borda_mm"] = distancia_da_borda(uid, pontos, c["luna16_mascaras"],
                                                                         p["distancia_borda_maxima"])
        lidos += 1
    print(f"máscaras lidas: {lidos}; sem máscara: {len(sem_mascara)}")

    por_tamanho = nodulos.groupby("faixa", observed=False).agg(
        nodulos=("seriesuid", "size"), sem_marca_nas_100=("escore", lambda e: int(e.isna().sum())),
        **{f"achados_{fp}fp": (f"achado_{fp}fp", "sum") for fp in p["fp_por_exame"]})
    for fp in p["fp_por_exame"]:
        por_tamanho[f"sensibilidade_{fp}fp"] = (por_tamanho[f"achados_{fp}fp"] / por_tamanho.nodulos).round(3)
    por_tamanho.loc["total"] = por_tamanho.sum(numeric_only=True)
    for fp in p["fp_por_exame"]:
        por_tamanho.loc["total", f"sensibilidade_{fp}fp"] = round(
            por_tamanho.loc["total", f"achados_{fp}fp"] / por_tamanho.loc["total", "nodulos"], 3)
    por_tamanho.to_csv(saida / "por_tamanho.csv")

    nodulos.to_csv(saida / "nodulos.csv", index=False)
    falsos.to_csv(saida / "falsos_positivos_4fp.csv", index=False)
    por_exame = falsos.groupby("seriesuid").size().sort_values(ascending=False)
    por_exame.rename("falsos_positivos").to_csv(saida / "falsos_positivos_por_exame.csv")

    perdidos = nodulos[~nodulos.achado_4fp].sort_values("diameter_mm").copy()
    perdidos["legenda"] = [
        f"{virgula(n.diameter_mm, 1)} mm, " + (f"escore {virgula(n.escore)}, {int(n.posicao_no_exame)}º do exame"
                                              if pd.notna(n.escore) else "sem marca nas 100")
        for _, n in perdidos.iterrows()]
    topo = falsos.head(p["falsos_positivos_figura"]).copy()
    topo["legenda"] = [f"#{i + 1}, escore {virgula(f.probability, 3)}, borda {virgula(f.distancia_borda_mm, 0)} mm"
                       for i, f in topo.iterrows()]
    figuras = {
        "perdidos": galerias(perdidos, c["volumes"], p["recorte_figura"], p["casos_por_figura"],
                             "Nódulos perdidos a 4 FP por exame, do menor para o maior (verde: diâmetro anotado)",
                             saida / "perdidos"),
        "falsos_positivos": galerias(topo, c["volumes"], p["recorte_figura"],
                                     p["casos_por_figura"],
                                     "Falsos positivos de maior escore (cruz: centro da marca)",
                                     saida / "falsos_positivos")}

    tipos, contagem = por_tipo(c["classificacao_falsos_positivos"], falsos)
    contagem.to_csv(saida / "falsos_positivos_por_tipo.csv")
    tipos.to_csv(saida / "falsos_positivos_classificados.csv", index=False)
    figuras["por_tipo"] = []
    for tipo, grupo in tipos.groupby("tipo"):
        exemplos = grupo.head(p["exemplos_por_tipo"]).copy()
        exemplos["legenda"] = [f"#{i + 1}, escore {virgula(f.probability, 3)}" for i, f in exemplos.iterrows()]
        figuras["por_tipo"] += galerias(exemplos, c["volumes"], p["recorte_figura"], p["exemplos_por_tipo"],
                                        f"Falsos positivos, tipo {NOMES_DOS_TIPOS[tipo]}: "
                                        f"{len(grupo)} dos {len(tipos)} de maior escore",
                                        saida / f"tipo_{tipo}")
    print(contagem.to_string())

    resumo = {"avaliacao": p["avaliacao"], "exames": len(exames), "nodulos": len(nodulos),
              "conferencia_com_o_oficial": conferencia,
              "limiares": {f"{fp}fp": v for fp, v in limiares.items()}, "limiar_rf_4fp": limiar_rf,
              "achados": {f"{fp}fp": int(nodulos[f"achado_{fp}fp"].sum()) for fp in p["fp_por_exame"]},
              "perdidos_4fp": len(perdidos), "sem_marca_nas_100": int(nodulos.escore.isna().sum()),
              "sem_candidato_v2_no_raio": int(nodulos.melhor_escore_lista_v2.isna().sum()),
              "perdidos_pela_cnn_achados_pelo_rf_4fp": int((~nodulos.achado_4fp & nodulos.achado_rf_4fp).sum()),
              "falsos_positivos_4fp": len(falsos), "exames_com_falso_positivo_4fp": int(len(por_exame)),
              "parede_e_vizinhanca": perto_da_parede(nodulos, falsos, p["perto_da_borda"]),
              "falsos_positivos_por_tipo": contagem.falsos_positivos.to_dict(),
              "mascaras_lidas": lidos, "sem_mascara": sem_mascara, "figuras": figuras}
    (saida / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(por_tamanho.to_string())
    print(f"falsos positivos a 4 FP: {len(falsos)} em {len(por_exame)} exames")


if __name__ == "__main__":
    main()
