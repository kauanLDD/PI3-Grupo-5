"""Executa o programa LUNA16 com adaptações de sintaxe para Python 3."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

import config
from experimentos.rastreamento import sha256

ORIGEM = config.RAIZ / "third_party/luna16"
FONTES = ("noduleCADEvaluationLUNA16.py", "NoduleFinding.py", "tools/csvTools.py", "tools/__init__.py")


def adaptar(nome, texto):
    if nome == "noduleCADEvaluationLUNA16.py":
        texto = re.sub(r"(?m)^(\s*)print (.+)$", r"\1print(\2)", texto)
        texto = texto.replace(".iteritems()", ".items()")
        texto = texto.replace("basex=2", "base=2")
        texto = texto.replace("plt.grid(b=True", "plt.grid(visible=True")
        texto = texto.replace("bbox_inches=0", "bbox_inches=None")
        # sklearn retorna TPR NaN quando não há positivos detectados.
        # O denominador oficial ainda inclui os nódulos sem candidato: sensibilidade = 0.
        texto = texto.replace(
            "sens = (tpr * numberOfDetectedLesions) / totalNumberOfLesions",
            "sens = np.zeros(len(tpr)) if numberOfDetectedLesions == 0 else (tpr * numberOfDetectedLesions) / totalNumberOfLesions",
        )
    if nome == "tools/csvTools.py":
        texto = texto.replace('open(filename, "wb")', 'open(filename, "w", newline="")')
        texto = texto.replace('open(filename, "rb")', 'open(filename, "r", newline="")')
    return texto


def avaliar(previsoes, exames, anotacoes, excluidas, destino, semente, bootstrap, confianca):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    uids = sorted(exames)
    if not uids or len(set(uids)) != len(uids) or set(previsoes.seriesuid) != set(uids):
        raise ValueError("previsoes precisam cobrir exatamente os exames da particao")
    if not np.isfinite(previsoes.probability).all() or not previsoes.probability.between(0, 1).all():
        raise ValueError("probabilidades invalidas")
    resultados = destino / "predicoes.csv"
    previsoes[["seriesuid", "coordX", "coordY", "coordZ", "probability"]].to_csv(resultados, index=False)
    series = destino / "seriesuids.csv"
    series.write_text("\n".join(uids) + "\n", encoding="utf-8")
    with TemporaryDirectory() as temporario:
        pasta = Path(temporario)
        hashes = {}
        for nome in FONTES:
            alvo = pasta / nome
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(adaptar(nome, (ORIGEM / nome).read_text(encoding="utf-8")), encoding="utf-8")
            hashes[nome] = {"original": sha256(ORIGEM / nome), "python3": sha256(alvo)}
        launcher = pasta / "executar.py"
        launcher.write_text(
            "import numpy as np\nimport noduleCADEvaluationLUNA16 as oficial\n"
            f"np.random.seed({semente})\n"
            f"oficial.bNumberOfBootstrapSamples = {bootstrap}\n"
            f"oficial.bConfidence = {confianca!r}\n"
            f"oficial.noduleCADEvaluation({str(anotacoes.resolve())!r}, {str(excluidas.resolve())!r}, "
            f"{str(series.resolve())!r}, {str(resultados.resolve())!r}, {str(destino.resolve())!r})\n",
            encoding="utf-8",
        )
        ambiente = {**os.environ, "MPLBACKEND": "Agg", "PYTHONHASHSEED": str(semente)}
        with (destino / "avaliador.log").open("w", encoding="utf-8") as log:
            processo = subprocess.run([sys.executable, str(launcher)], env=ambiente,
                                      stdout=log, stderr=subprocess.STDOUT)
        if processo.returncode:
            raise RuntimeError(f"avaliador oficial falhou; consulte {destino / 'avaliador.log'}")
    curva = pd.read_csv(destino / "froc_predicoes.txt", header=None,
                        names=["fp_por_exame", "sensibilidade", "limiar"])
    curva.to_csv(destino / "curva_froc_completa.csv", index=False)
    ic = pd.read_csv(destino / "froc_predicoes_bootstrapping.csv")
    if not np.isfinite(curva[["fp_por_exame", "sensibilidade"]]).all().all() or not np.isfinite(ic).all().all():
        raise ValueError("avaliador produziu FROC indefinida; não registrar métricas NaN")
    pontos = [0.125, 0.25, 0.5, 1, 2, 4, 8]
    sensibilidades = np.interp(pontos, curva.fp_por_exame, curva.sensibilidade)
    media = np.interp(pontos, ic.iloc[:, 0], ic.iloc[:, 1])
    inferior = np.interp(pontos, ic.iloc[:, 0], ic.iloc[:, 2])
    superior = np.interp(pontos, ic.iloc[:, 0], ic.iloc[:, 3])
    tabela = pd.DataFrame({"fp_por_exame": pontos, "sensibilidade": sensibilidades,
                          "bootstrap_media": media, "ic_inferior": inferior, "ic_superior": superior})
    tabela.to_csv(destino / "pontos_operacao.csv", index=False)
    metricas = {"cpm": float(np.mean(sensibilidades))}
    for fp, sens, baixo, alto in zip(pontos, sensibilidades, inferior, superior):
        chave = str(fp).replace(".", "_")
        metricas.update({f"sensibilidade_{chave}fp": float(sens),
                         f"sensibilidade_{chave}fp_ic_inferior": float(baixo),
                         f"sensibilidade_{chave}fp_ic_superior": float(alto)})
    protocolo = {"avaliador": "LUNA16 oficial", "max_marcas_por_exame": 100,
                 "bootstrap": bootstrap, "confianca": confianca, "seed": semente,
                 "exames": len(uids), "fontes": hashes, "metricas": metricas,
                 "curva_pontos": len(curva), "curva_bootstrap_pontos": len(ic),
                 "correcao_caso_de_borda": "TPR NaN sem positivos detectados passa a sensibilidade zero",
                 "cpm": "media das 7 sensibilidades da curva pontual; IC por ponto do bootstrap oficial"}
    (destino / "avaliacao.json").write_text(json.dumps(protocolo, indent=2), encoding="utf-8")
    return metricas
