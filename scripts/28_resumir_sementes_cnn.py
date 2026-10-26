"""Junta na validação a rede escolhida treinada com três sementes: CPM, sete pontos, média, desvio, mínimo e máximo.

Não treina nem avalia: lê o execucao.json que o script 18 gravou em cada pasta. Recusa sementes
cuja configuração difira da original em qualquer coisa além da semente. Ver decisão 0010.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd

import config

PONTOS = [0.125, 0.25, 0.5, 1, 2, 4, 8]
# Chaves que mudam com a semente ou com a máquina e não fazem parte da configuração.
LIVRES = {"seed", "seed_avaliacao", "gpu", "torch", "determinismo"}


def pasta_da_semente(cfg, semente):
    variante = cfg["sementes_cnn"]["variante"]
    if semente == cfg["sementes_cnn"]["original"]:
        return config.RAIZ / f"modelos/cnn_{variante}"
    return config.RAIZ / f"modelos/cnn_{variante}_semente_{semente}"


def ler(pasta):
    recibo = json.loads((pasta / "execucao.json").read_text(encoding="utf-8"))
    historico = pd.read_csv(pasta / "historico.csv")
    return recibo, historico


def conferir_configuracao(recibos):
    referencia = recibos[0]
    base = {k: v for k, v in referencia["parametros"].items() if k not in LIVRES}
    sementes = [r["parametros"]["seed"] for r in recibos]
    if len(set(sementes)) != len(sementes):
        raise ValueError("sementes repetidas")
    for recibo in recibos[1:]:
        outro = {k: v for k, v in recibo["parametros"].items() if k not in LIVRES}
        diferentes = sorted(k for k in base.keys() | outro.keys() if base.get(k) != outro.get(k))
        if diferentes:
            raise ValueError(f"semente {recibo['parametros']['seed']} muda a configuracao em {diferentes}")
        if recibo["dados_sha256"] != referencia["dados_sha256"]:
            raise ValueError(f"semente {recibo['parametros']['seed']} usou outros dados")
        avaliacao = recibo["parametros"].get("seed_avaliacao", recibo["parametros"]["seed"])
        if avaliacao != referencia["parametros"]["seed"]:
            raise ValueError("bootstrap da avaliacao com semente diferente da original")
        if recibo["teste_utilizado"]:
            raise ValueError("as sementes sao medidas so na validacao")


def linha(recibo, historico):
    m = recibo["metricas"]
    saida = {"seed": recibo["parametros"]["seed"], "run_id": recibo["run_id"],
             "epoca_checkpoint": int(historico.epoch.max()),
             "loss_ultima_epoca": float(historico.train_loss.iloc[-1]),
             "cpm": m["validacao_cpm"], "cpm_ic_inferior": m["validacao_cpm_ic_inferior"],
             "cpm_ic_superior": m["validacao_cpm_ic_superior"]}
    for fp in PONTOS:
        saida[f"sens_{fp:g}"] = m[f"validacao_sensibilidade_{str(fp).replace('.', '_')}fp"]
    return saida


def estatisticas(tabela):
    cpm = tabela.cpm
    return {"sementes": int(len(cpm)), "cpm_medio": float(cpm.mean()),
            "cpm_desvio_padrao_amostral": float(cpm.std(ddof=1)),
            "cpm_minimo": float(cpm.min()), "cpm_maximo": float(cpm.max()),
            "cpm_amplitude": float(cpm.max() - cpm.min()),
            "sens_4_media": float(tabela["sens_4"].mean()),
            "sens_4_desvio_padrao_amostral": float(tabela["sens_4"].std(ddof=1))}


def desenhar(tabela, resumo, destino):
    figura, eixo = plt.subplots(figsize=(6.4, 3.6))
    posicoes = np.arange(len(tabela))
    eixo.axhspan(resumo["cpm_medio"] - resumo["cpm_desvio_padrao_amostral"],
                 resumo["cpm_medio"] + resumo["cpm_desvio_padrao_amostral"], color="#1764a8", alpha=0.10,
                 linewidth=0, label="média ± desvio padrão entre sementes")
    eixo.axhline(resumo["cpm_medio"], color="#1764a8", linewidth=1, linestyle="--")
    eixo.errorbar(posicoes, tabela.cpm, yerr=[tabela.cpm - tabela.cpm_ic_inferior, tabela.cpm_ic_superior - tabela.cpm],
                  fmt="o", color="#1764a8", markersize=8, capsize=4, markeredgecolor="white",
                  label="CPM de cada semente, IC95% do bootstrap por exame")
    for x, valor in zip(posicoes, tabela.cpm):
        eixo.annotate(f"{valor:.3f}".replace(".", ","), (x, valor), xytext=(10, -3),
                      textcoords="offset points", color="#1f1f1f", fontsize=9)
    eixo.set_xticks(posicoes, [f"semente {s}" for s in tabela.seed])
    eixo.set_xlim(-0.5, len(tabela) - 0.5)
    eixo.set_ylabel("CPM na validação")
    # Marcas de 0,05 em 0,05: com o passo automático de 0,025 e duas casas, 0,825 aparecia como 0,83.
    eixo.yaxis.set_major_locator(MultipleLocator(0.05))
    eixo.yaxis.set_major_formatter(lambda v, _: f"{v:.2f}".replace(".", ","))
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)
    eixo.grid(axis="y", alpha=0.25)
    eixo.legend(loc="lower right", fontsize=8, frameon=False)
    figura.tight_layout()
    figura.savefig(destino / "cpm_por_semente.png", dpi=200)
    plt.close(figura)


def main():
    cfg = config.carregar()
    sementes = [cfg["sementes_cnn"]["original"], *cfg["sementes_cnn"]["extras"]]
    pastas = [pasta_da_semente(cfg, s) for s in sementes]
    faltando = [str(p.relative_to(config.RAIZ)) for p in pastas if not (p / "execucao.json").is_file()]
    if faltando:
        raise FileNotFoundError(f"sementes ainda nao treinadas: {faltando}")
    lidos = [ler(p) for p in pastas]
    recibos = [r for r, _ in lidos]
    conferir_configuracao(recibos)
    if [r["parametros"]["seed"] for r in recibos] != sementes:
        raise ValueError("semente gravada difere da declarada em sementes_cnn")
    tabela = pd.DataFrame([linha(r, h) for r, h in lidos])
    resumo = estatisticas(tabela)
    destino = cfg["caminhos"]["sementes_cnn"]
    destino.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino / "sementes.csv", index=False)
    (destino / "resumo.json").write_text(json.dumps({
        "variante": cfg["sementes_cnn"]["variante"], "conjunto": "validacao", "teste_utilizado": False,
        "pastas": [str(p.relative_to(config.RAIZ)) for p in pastas], **resumo}, indent=2), encoding="utf-8")
    desenhar(tabela, resumo, destino)
    print(tabela.round(3).to_string(index=False), flush=True)
    print(json.dumps(resumo, indent=2), flush=True)


if __name__ == "__main__":
    main()
