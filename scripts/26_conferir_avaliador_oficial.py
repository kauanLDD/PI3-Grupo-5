"""Roda o exemplo do LUNA16 e compara a FROC oficial com a calculada pelo grupo no notebook.

1. Exemplo do pacote `evaluationScript`: com o limite de 100 marcas do programa distribuído e sem
   limite, para conferir a cópia Python 3 contra a saída que o pacote traz em exampleFiles/evaluation,
   gerada antes de o limite existir.
2. Previsões do projeto já avaliadas: reavalia com o oficial e confere contra o que está em modelos/.
3. Cálculo do grupo (src/experimentos/froc_grupo.py) nas mesmas previsões, lado a lado com o oficial.

Uso: python scripts/26_conferir_avaliador_oficial.py [--avaliador PASTA_evaluationScript]
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

import config
from detection.candidatos import ACERTO, rotular
from experimentos import avaliacao_oficial, froc_grupo
from experimentos.rastreamento import sha256

AVALIACOES = {
    "cnn_lr_3e-4_teste": "modelos/cnn_lr_3e-4_teste_final",
    "cnn_lr_3e-4_validacao": "modelos/cnn_lr_3e-4/avaliacao_validacao",
    "random_forest_centro_validacao": "modelos/random_forest_centro/avaliacao_validacao",
}
LINHAS_CONTAGEM = ("True positives", "False positives", "False negatives", "Total number of candidates",
                   "Total number of nodules", "Ignored candidates on excluded nodules",
                   "Ignored candidates which were double detections on a nodule")


def contagens(caminho):
    linhas = Path(caminho).read_text(encoding="utf-8").splitlines()
    return {r.split(":")[0].strip(): r.split(":")[1].strip() for r in linhas
            if r.strip().split(":")[0] in LINHAS_CONTAGEM}


def conferir_exemplo(pasta, intermediario, cfg, avaliacao):
    previsoes = pd.read_csv(pasta / "exampleFiles/submission/sampleSubmission.csv")
    exames = (pasta / "annotations/seriesuids.csv").read_text(encoding="utf-8").split()
    anotacoes, excluidas = pasta / "annotations/annotations.csv", pasta / "annotations/annotations_excluded.csv"
    esperado = pasta / "exampleFiles/evaluation"
    resultado = {}
    for nome, limite in (("com_limite_100", 100), ("sem_limite", -1)):
        destino = intermediario / f"exemplo_{nome}"
        metricas = avaliacao_oficial.avaliar(previsoes, exames, anotacoes, excluidas, destino, cfg["seed"],
                                             avaliacao["bootstrap_reamostras"],
                                             avaliacao["intervalo_confianca"], max_marcas=limite)
        resultado[nome] = {"metricas": metricas, "contagens": contagens(destino / "CADAnalysis.txt"),
                           "pontos": pd.read_csv(destino / "pontos_operacao.csv")}
    # A saída do pacote não tem limite; a curva não depende do sorteio, o bootstrap depende.
    obtida = np.loadtxt(intermediario / "exemplo_sem_limite/froc_predicoes.txt", delimiter=",")
    original = np.loadtxt(esperado / "froc_sampleSubmission.txt", delimiter=",")
    resultado["conferencia"] = {
        "contagens_iguais": contagens(esperado / "CADAnalysis.txt") == resultado["sem_limite"]["contagens"],
        "curva_mesmo_tamanho": obtida.shape == original.shape,
        "curva_maior_diferenca": float(np.abs(obtida - original).max()) if obtida.shape == original.shape else None,
    }
    curva = pd.DataFrame(original[:, :2], columns=["fp_por_exame", "sensibilidade"])
    pontos = list(froc_grupo.PONTOS)
    resultado["conferencia"]["cpm_saida_original"] = float(np.mean(np.interp(pontos, curva.fp_por_exame,
                                                                             curva.sensibilidade)))
    return resultado


def comparar(nome, origem, anotacoes, excluidas, intermediario, cfg, avaliacao):
    previsoes = pd.read_csv(origem / "predicoes.csv")
    exames = (origem / "seriesuids.csv").read_text(encoding="utf-8").split()
    destino = intermediario / nome
    oficial = avaliacao_oficial.avaliar(previsoes, exames, anotacoes, excluidas, destino, cfg["seed"],
                                        avaliacao["bootstrap_reamostras"], avaliacao["intervalo_confianca"])
    gravado = json.loads((origem / "avaliacao.json").read_text(encoding="utf-8"))["metricas"]
    reproduz = all(np.isclose(oficial[k], v, rtol=0, atol=1e-9) for k, v in gravado.items())

    nodulos, excluidos = pd.read_csv(anotacoes), pd.read_csv(excluidas)
    rotulos = rotular(previsoes, nodulos.loc[nodulos.seriesuid.isin(exames)],
                      excluidos.loc[excluidos.seriesuid.isin(exames)])
    y_true = (rotulos == ACERTO).astype(int)
    fps, sens = froc_grupo.compute_froc(y_true, previsoes.probability, n_scans=len(exames))
    cpm, por_ponto = froc_grupo.compute_cpm(fps, sens)
    boot = froc_grupo.bootstrap_froc_metrics(y_true, previsoes.probability, previsoes.seriesuid,
                                             avaliacao["bootstrap_reamostras"], cfg["seed"])
    cauda = (1 - avaliacao["intervalo_confianca"]) / 2
    pd.DataFrame({"fp_por_exame": fps, "sensibilidade": sens}).to_csv(destino / "curva_froc_grupo.csv", index=False)

    pontos = pd.read_csv(destino / "pontos_operacao.csv")
    tabela = pd.DataFrame({
        "modelo": nome, "fp_por_exame": list(froc_grupo.PONTOS) + ["CPM"],
        "oficial": list(pontos.sensibilidade) + [oficial["cpm"]],
        "oficial_ic_inferior": list(pontos.ic_inferior) + [oficial["cpm_ic_inferior"]],
        "oficial_ic_superior": list(pontos.ic_superior) + [oficial["cpm_ic_superior"]],
        "grupo": list(por_ponto.values()) + [cpm],
        "grupo_ic_inferior": list(np.quantile(boot["sensibilidades"], cauda, axis=0))
                             + [float(np.quantile(boot["cpm"], cauda))],
        "grupo_ic_superior": list(np.quantile(boot["sensibilidades"], 1 - cauda, axis=0))
                             + [float(np.quantile(boot["cpm"], 1 - cauda))],
    })
    tabela["diferenca"] = tabela.grupo - tabela.oficial
    contagem = pd.Series(rotulos).value_counts().to_dict()
    resumo = {"exames": len(exames), "previsoes": len(previsoes), "reproduz_resultado_gravado": bool(reproduz),
              "nodulos_anotados": int(nodulos.seriesuid.isin(exames).sum()),
              "candidatos_positivos_grupo": int(y_true.sum()), "rotulos": {k: int(v) for k, v in contagem.items()},
              "oficial": contagens(destino / "CADAnalysis.txt"), "reamostras_grupo_validas": len(boot["cpm"])}
    return tabela, resumo


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    parser = argparse.ArgumentParser()
    parser.add_argument("--avaliador", type=Path, default=cfg["caminhos"]["luna16_avaliacao"],
                        help="pasta evaluationScript do LUNA16, com annotations/ e exampleFiles/")
    pasta = parser.parse_args().avaliador
    avaliacao = cfg["avaliacao"]
    intermediario = cfg["caminhos"]["intermediario"] / "avaliador_oficial"
    saida = config.RAIZ / "relatorios/experimentos/avaliador_oficial"
    if intermediario.exists() or saida.exists():
        raise ValueError(f"preserve a conferência anterior e apague-a à mão: {intermediario} / {saida}")
    saida.mkdir(parents=True)
    anotacoes, excluidas = pasta / "annotations/annotations.csv", pasta / "annotations/annotations_excluded.csv"

    exemplo = conferir_exemplo(pasta, intermediario, cfg, avaliacao)
    for nome in ("com_limite_100", "sem_limite"):
        exemplo[nome]["pontos"].to_csv(saida / f"exemplo_{nome}_pontos_operacao.csv", index=False)
        exemplo[nome].pop("pontos")
        (saida / f"exemplo_{nome}_CADAnalysis.txt").write_text(
            (intermediario / f"exemplo_{nome}/CADAnalysis.txt").read_text(encoding="utf-8"), encoding="utf-8")

    tabelas, resumos = [], {}
    for nome, origem in AVALIACOES.items():
        tabela, resumos[nome] = comparar(nome, config.RAIZ / origem, anotacoes, excluidas,
                                         intermediario, cfg, avaliacao)
        tabelas.append(tabela)
        (intermediario / nome / "curva_froc_grupo.csv").replace(saida / f"{nome}_curva_froc_grupo.csv")
    pd.concat(tabelas).to_csv(saida / "oficial_vs_grupo.csv", index=False)

    registro = {"seed": cfg["seed"], "bootstrap": avaliacao["bootstrap_reamostras"],
                "confianca": avaliacao["intervalo_confianca"], "exemplo": exemplo, "previsoes": resumos,
                "entradas": {"annotations.csv": sha256(anotacoes), "annotations_excluded.csv": sha256(excluidas),
                             "sampleSubmission.csv": sha256(pasta / "exampleFiles/submission/sampleSubmission.csv")}}
    (saida / "conferencia.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(registro["exemplo"]["conferencia"], indent=2))
    print(pd.concat(tabelas).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
