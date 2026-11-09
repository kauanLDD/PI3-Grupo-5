"""Quais nódulos a supressão suave tirou das 100 marcas de cada exame no teste, e quem os rebaixou.

Descreve o que o script 37 já gravou no terceiro uso do teste (decisão 0013): não pontua, não
avalia e não ajusta raio nem forma da supressão. Compara os nódulos sem marca das avaliações sem e
com supressão, refaz a supressão suave dos exames afetados registrando cada rebaixamento, confere que
a repetição dá as mesmas 100 marcas gravadas, e diz se o vizinho que rebaixou cada nódulo é outro
nódulo anotado, um achado excluído ou um falso alarme.
"""

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import candidatos as det
from experimentos import erros

SEM_MARCA = ["seriesuid", "id", "coordX", "coordY", "coordZ", "diameter_mm", "escore"]
OUTRO_NODULO, EXCLUIDA, FALSO_ALARME = "outro_nodulo", "achado_excluido", "falso_alarme"


def ler_sem_marca(pasta):
    """Os nódulos que o avaliador oficial não achou entre as marcas, um por linha."""
    return pd.read_csv(Path(pasta) / "nodulesWithoutCandidate_predicoes.txt", header=None, names=SEM_MARCA)


def so_em(a, b):
    """Linhas de a que não estão em b, pelo exame e pelo centro do nódulo."""
    chave = ["seriesuid", "coordX", "coordY", "coordZ", "diameter_mm"]
    juntos = a.merge(b[chave].drop_duplicates(), on=chave, how="left", indicator=True)
    return juntos.loc[juntos._merge.eq("left_only"), a.columns].reset_index(drop=True)


def rastrear_suave(exame, raio_mm, forma, marcas, sigma):
    """A `det.suprimir_suave` de um exame, guardando a nota final de cada ponto e quem a rebaixou.

    Devolve as posições escolhidas, na ordem, a nota de todos os pontos ao fim das `marcas` escolhas
    e, para cada escolha, os vizinhos rebaixados e o fator aplicado. O teste confere que as escolhas
    e as notas são as mesmas da função original.
    """
    pontos = exame[det.COLUNAS].to_numpy(float)
    notas = exame.probability.to_numpy(float).copy()
    arvore = cKDTree(pontos)
    livre = np.ones(len(exame), dtype=bool)
    escolhidas, rebaixos = [], []
    for _ in range(min(marcas, len(exame))):
        i = int(np.argmax(np.where(livre, notas, -np.inf)))
        escolhidas.append(i)
        livre[i] = False
        vizinhos = np.array([j for j in arvore.query_ball_point(pontos[i], r=raio_mm) if livre[j]], dtype=int)
        fator = np.ones(0)
        if len(vizinhos):
            sobreposicao = 1 - np.linalg.norm(pontos[vizinhos] - pontos[i], axis=1) / raio_mm
            fator = np.exp(-sobreposicao ** 2 / sigma) if forma == "gaussiana" else 1 - sobreposicao
            notas[vizinhos] *= fator
        rebaixos.append((i, vizinhos, fator))
    return escolhidas, notas, rebaixos


def tipo_do_ponto(ponto, nodulos, excluidas):
    """Outro nódulo anotado, achado excluído ou falso alarme, pela regra do avaliador oficial."""
    xyz = np.asarray(ponto, float)[None, :]
    for _, nodulo in nodulos.iterrows():
        if erros.dentro(xyz, nodulo)[0]:
            return OUTRO_NODULO, nodulo
    for _, achado in excluidas.iterrows():
        if erros.dentro(xyz, achado)[0]:
            return EXCLUIDA, achado
    return FALSO_ALARME, None


def analisar_nodulo(nodulo, exame, escolhidas, notas_finais, rebaixos, nodulos_exame, excluidas_exame):
    """Uma linha da tabela: o ponto do nódulo, as notas antes e depois, e o vizinho que mais rebaixou."""
    pontos = exame[det.COLUNAS].to_numpy(float)
    originais = exame.probability.to_numpy(float)
    centro = nodulo[det.COLUNAS].to_numpy(float)
    distancia = np.linalg.norm(pontos - centro, axis=1)
    perto = int(np.argmin(distancia))
    dentro = np.flatnonzero(erros.dentro(pontos, nodulo))
    if not len(dentro):
        raise ValueError(f"nenhum ponto da lista dentro do nódulo {nodulo.seriesuid} {centro}")
    # O ponto que contava como acerto sem a supressão: o de maior nota dentro do raio.
    alvo = int(dentro[np.argmax(originais[dentro])])
    if alvo in escolhidas:
        raise ValueError("o ponto do nódulo foi escolhido pela supressão; o nódulo não estaria perdido")
    golpes = [(i, float(f[np.flatnonzero(v == alvo)[0]])) for i, v, f in rebaixos if np.any(v == alvo)]
    if not golpes:
        raise ValueError("ponto do nódulo perdido sem nenhum rebaixamento")
    vizinho, fator = min(golpes, key=lambda g: g[1])
    tipo, achado = tipo_do_ponto(pontos[vizinho], nodulos_exame, excluidas_exame)
    corte = notas_finais[escolhidas[-1]] if len(escolhidas) else np.nan
    return {
        "seriesuid": nodulo.seriesuid, "coordX": nodulo.coordX, "coordY": nodulo.coordY, "coordZ": nodulo.coordZ,
        "diametro_mm": nodulo.diameter_mm,
        "ponto_mais_perto_mm": float(distancia[perto]), "nota_ponto_mais_perto": float(originais[perto]),
        "pontos_dentro_do_raio": len(dentro), "distancia_ponto_nodulo_mm": float(distancia[alvo]),
        "nota_antes": float(originais[alvo]), "nota_depois": float(notas_finais[alvo]),
        "nota_da_100a_marca": float(corte), "rebaixamentos": len(golpes),
        "fator_total": float(np.prod([f for _, f in golpes])),
        "vizinho_coordX": pontos[vizinho, 0], "vizinho_coordY": pontos[vizinho, 1],
        "vizinho_coordZ": pontos[vizinho, 2], "nota_vizinho": float(originais[vizinho]),
        "ordem_do_vizinho": escolhidas.index(vizinho) + 1, "fator_do_vizinho": fator,
        "distancia_vizinho_mm": float(np.linalg.norm(pontos[vizinho] - pontos[alvo])),
        "distancia_vizinho_centro_mm": float(np.linalg.norm(pontos[vizinho] - centro)),
        "tipo_vizinho": tipo,
        "diametro_do_outro_nodulo_mm": float(achado.diameter_mm) if tipo == OUTRO_NODULO else np.nan,
    }


def conferir_marcas(exame, escolhidas, notas_finais, gravadas):
    """A repetição tem de dar as mesmas marcas e notas que o script 37 entregou ao avaliador."""
    nossas = exame.iloc[escolhidas][det.COLUNAS].assign(probability=notas_finais[escolhidas])
    chave = det.COLUNAS
    a = nossas.sort_values(chave).reset_index(drop=True)
    b = gravadas[chave + ["probability"]].sort_values(chave).reset_index(drop=True)
    if len(a) != len(b) or not np.allclose(a.to_numpy(float), b.to_numpy(float), rtol=0, atol=1e-6):
        raise ValueError(f"a supressão repetida difere das marcas gravadas em {exame.seriesuid.iloc[0]}")


def escolher_casos(tabela, quantos):
    """Metade dos casos com vizinho nódulo e metade com falso alarme, os de maior diâmetro primeiro."""
    ordem = tabela.sort_values(["diametro_mm", "seriesuid"], ascending=[False, True])
    metade = quantos // 2
    grupos = [ordem[ordem.tipo_vizinho.eq(OUTRO_NODULO)], ordem[ordem.tipo_vizinho.ne(OUTRO_NODULO)]]
    casos = pd.concat([grupos[0].head(metade), grupos[1].head(quantos - metade)])
    resto = ordem.drop(casos.index)
    return pd.concat([casos, resto.head(quantos - len(casos))])


def desenhar(casos, volumes, lado_mm, saida):
    """Corte axial no z do nódulo: o nódulo circulado em verde e o vizinho que o rebaixou em vermelho."""
    figura, eixos = plt.subplots(1, len(casos), figsize=(4 * len(casos), 5), squeeze=False,
                                layout="constrained")
    for eixo, (_, caso) in zip(eixos[0], casos.iterrows()):
        imagem = sitk.ReadImage(str(Path(volumes) / f"{caso.seriesuid}.mha"))
        volume = sitk.GetArrayFromImage(imagem)
        espacamento = np.array(imagem.GetSpacing())
        x, y, z = imagem.TransformPhysicalPointToIndex((caso.coordX, caso.coordY, caso.coordZ))
        vx, vy, vz = imagem.TransformPhysicalPointToIndex((caso.vizinho_coordX, caso.vizinho_coordY,
                                                          caso.vizinho_coordZ))
        meio = lado_mm / 2 / espacamento[0]
        cx, cy = (x + vx) / 2, (y + vy) / 2
        eixo.imshow(volume[z], cmap="gray", vmin=0, vmax=1)
        eixo.add_patch(plt.Circle((x, y), caso.diametro_mm / 2 / espacamento[0], fill=False, color="lime",
                                  linewidth=1.4))
        eixo.plot(vx, vy, marker="x", color="red", markersize=9, mew=2)
        eixo.set_xlim(cx - meio, cx + meio)
        eixo.set_ylim(cy + meio, cy - meio)
        eixo.set_xticks([])
        eixo.set_yticks([])
        rotulo = {OUTRO_NODULO: "outro nódulo", EXCLUIDA: "achado excluído", FALSO_ALARME: "falso alarme"}
        eixo.set_title(f"nódulo {caso.diametro_mm:.1f} mm, nota {caso.nota_antes:.2f} → {caso.nota_depois:.2f}\n"
                       f"vizinho: {rotulo[caso.tipo_vizinho]}, nota {caso.nota_vizinho:.2f}, "
                       f"{caso.distancia_vizinho_mm:.1f} mm\n"
                       f"{caso.seriesuid[-6:]}, fatia {z}, vizinho na fatia {vz}", fontsize=8)
    figura.suptitle("Teste, nossa lista: nódulos que a supressão suave a 16 mm tirou das 100 marcas\n"
                    "verde = nódulo anotado, vermelho = marca mantida que mais rebaixou a nota dele", fontsize=10)
    figura.savefig(saida, dpi=150, bbox_inches="tight")
    plt.close(figura)


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, fase, suave = cfg["caminhos"], cfg["supressao_perdidos"], cfg["supressao_suave"]
    forma = cfg["teste_supressao"]["forma"]
    completa, saida = caminhos["teste_supressao_completa"], caminhos["supressao_perdidos"]

    sem, com = ler_sem_marca(completa / "propria"), ler_sem_marca(completa / "propria_suave")
    perdidos = so_em(com, sem)
    recuperados = so_em(sem, com)
    print(f"sem marca: {len(sem)} sem supressão, {len(com)} com supressão; só com supressão {len(perdidos)}, "
          f"só sem supressão {len(recuperados)}", flush=True)
    if len(perdidos) != fase["perdidos_esperados"]:
        print(f"atenção: o docs/19, seção 11, implica {fase['perdidos_esperados']} perdidos só com a supressão",
              flush=True)

    uids = set(perdidos.seriesuid)
    notas = pd.concat([c[c.seriesuid.isin(uids)] for c in
                       pd.read_csv(completa / "probabilidades.csv", chunksize=2_000_000)], ignore_index=True)
    gravadas = pd.read_csv(completa / "propria_suave" / "predicoes.csv")
    nodulos = pd.read_csv(caminhos["luna16_anotacoes"])
    excluidas = pd.read_csv(caminhos["luna16_anotacoes_excluidas"])

    linhas = []
    for uid, exame in notas.groupby("seriesuid", sort=True):
        escolhidas, finais, rebaixos = rastrear_suave(exame, float(suave["raio_mm"]), forma,
                                                      suave["marcas_por_exame"], suave["sigma"])
        conferir_marcas(exame, escolhidas, finais, gravadas[gravadas.seriesuid.eq(uid)])
        for _, nodulo in perdidos[perdidos.seriesuid.eq(uid)].iterrows():
            linhas.append(analisar_nodulo(nodulo, exame, escolhidas, finais, rebaixos,
                                          nodulos[nodulos.seriesuid.eq(uid)], excluidas[excluidas.seriesuid.eq(uid)]))
    tabela = pd.DataFrame(linhas).sort_values(["tipo_vizinho", "diametro_mm"], ascending=[False, False])
    por_causa = (tabela.groupby("tipo_vizinho")
                 .agg(nodulos=("seriesuid", "size"), exames=("seriesuid", "nunique"),
                      diametro_mediano_mm=("diametro_mm", "median"),
                      distancia_mediana_vizinho_mm=("distancia_vizinho_mm", "median"))
                 .reindex([OUTRO_NODULO, EXCLUIDA, FALSO_ALARME]).fillna({"nodulos": 0, "exames": 0})
                 .astype({"nodulos": int, "exames": int}).reset_index())

    saida.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(saida / "nodulos.csv", index=False)
    por_causa.to_csv(saida / "por_causa.csv", index=False)
    casos = escolher_casos(tabela, fase["casos_figura"])
    desenhar(casos, caminhos["volumes"], fase["lado_figura_mm"], saida / "casos.png")
    (saida / "resumo.json").write_text(json.dumps({
        "conjunto": "teste", "decisao": "0013", "teste_reavaliado": False, "forma": forma,
        "raio_mm": suave["raio_mm"], "sem_marca_sem_supressao": len(sem), "sem_marca_com_supressao": len(com),
        "perdidos_so_com_supressao": len(perdidos), "perdidos_so_sem_supressao": len(recuperados),
        "exames_refeitos": len(uids), "supressao_repetida_confere": True,
        "por_causa": dict(zip(por_causa.tipo_vizinho, por_causa.nodulos)),
        "casos_figura": casos.seriesuid.tolist()}, indent=2, ensure_ascii=False), encoding="utf-8")
    colunas = ["seriesuid", "diametro_mm", "nota_antes", "nota_depois", "nota_da_100a_marca", "tipo_vizinho",
               "nota_vizinho", "distancia_vizinho_mm", "rebaixamentos"]
    print(tabela[colunas].assign(seriesuid=tabela.seriesuid.str[-6:]).round(3).to_string(index=False), flush=True)
    print(por_causa.round(2).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
