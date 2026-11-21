"""Junta pares de redes pela média das notas e avalia cada par uma vez na validação (T26)."""

import json
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

import config
from experimentos import avaliacao_oficial

CHAVE = ["candidate_id", "seriesuid", "coordX", "coordY", "coordZ", "class"]


def ler_notas(pasta):
    recibo = json.loads((pasta / "execucao.json").read_text(encoding="utf-8"))
    if recibo["teste_utilizado"]:
        raise ValueError(f"{pasta.name} foi avaliada no teste; a combinação usa só validação")
    return pd.read_csv(pasta / "probabilidades_validacao.csv"), recibo["run_id"]


def combinar(cfg, nome, pastas):
    caminhos, avaliacao = cfg["caminhos"], cfg["avaliacao"]
    notas, runs = zip(*(ler_notas(p) for p in pastas))
    juntas = notas[0][CHAVE].copy()
    for pasta, tabela in zip(pastas, notas):
        # Mesma lista e mesma ordem nas duas redes, senão a média mistura candidatos diferentes.
        if not tabela[CHAVE].equals(notas[0][CHAVE]):
            raise ValueError(f"{pasta.name} tem candidatos diferentes da primeira rede")
        juntas[pasta.name] = tabela.probability.to_numpy()
    juntas["probability"] = juntas[[p.name for p in pastas]].mean(axis=1)

    divisao = pd.read_csv(caminhos["divisao"])
    exames = divisao.loc[divisao.particao.eq("validacao"), "seriesuid"].tolist()
    print(f"{len(juntas)} candidatos de {juntas.seriesuid.nunique()} exames; "
          f"validação tem {len(exames)} exames", flush=True)

    completa, destino = caminhos["combinacao_redes_completa"] / nome, caminhos["combinacao_redes"] / nome
    metricas = avaliacao_oficial.avaliar(
        juntas, exames, caminhos["luna16_anotacoes"], caminhos["luna16_anotacoes_excluidas"],
        completa / "avaliacao_validacao", cfg["seed"], avaliacao["bootstrap_reamostras"],
        avaliacao["intervalo_confianca"])
    juntas.to_csv(completa / "probabilidades_validacao.csv", index=False)
    # As 75 mil notas ficam fora do git; o resumo que o documento cita fica em relatorios.
    destino.mkdir(parents=True, exist_ok=True)
    for nome in ("avaliacao.json", "pontos_operacao.csv", "froc_predicoes.png", "cpm_bootstrap.csv"):
        shutil.copy(completa / "avaliacao_validacao" / nome, destino / nome)
    recibo = {"regra": "media_simples", "redes": [p.name for p in pastas], "runs": list(runs),
              "teste_utilizado": False, "metricas": metricas}
    (destino / "combinacao.json").write_text(json.dumps(recibo, indent=2, ensure_ascii=False), encoding="utf-8")
    return metricas


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    linhas = []
    for nome, pastas in cfg["combinacao_redes"]["pares"].items():
        m = combinar(cfg, nome, [config.RAIZ / p for p in pastas])
        linhas.append({"par": nome, "cpm": m["cpm"], "cpm_ic_inferior": m["cpm_ic_inferior"],
                       "cpm_ic_superior": m["cpm_ic_superior"], "sens_1": m["sensibilidade_1fp"],
                       "sens_4": m["sensibilidade_4fp"]})
    tabela = pd.DataFrame(linhas)
    tabela.to_csv(cfg["caminhos"]["combinacao_redes"] / "pares.csv", index=False)
    print(tabela.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
