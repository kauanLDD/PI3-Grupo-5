"""Prepara quatro exames de desenvolvimento para conferir o fluxo da CNN."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from experimentos.cnn import conferir_divisao


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    destino = args.saida.resolve()
    if destino.exists():
        raise ValueError("escolha uma pasta nova para a verificacao tecnica")
    escolhidos = pd.read_csv(config.RAIZ / "configuracao/cnn_reproducao_exames.csv")
    escolhidos = escolhidos.loc[escolhidos.particao.isin(["treino", "validacao"])]
    mapa = pd.read_csv(cfg["caminhos"]["divisao"])
    exames = mapa.loc[mapa.seriesuid.isin(escolhidos.seriesuid)]
    conferir_divisao(exames)
    if len(exames) != 4 or exames.particao.eq("teste").any():
        raise ValueError("amostra tecnica exige quatro exames de treino e validacao")
    fontes = {"annotations.csv": cfg["caminhos"]["luna16_anotacoes"],
              "annotations_excluded.csv": cfg["caminhos"]["luna16_anotacoes_excluidas"],
              "candidates_V2.csv": cfg["caminhos"]["luna16_candidatos"]}
    for origem in fontes.values():
        if not origem.is_file():
            raise FileNotFoundError(origem)
    destino.mkdir(parents=True)
    exames.to_csv(destino / "divisao.csv", index=False)
    for nome, origem in fontes.items():
        shutil.copy2(origem, destino / nome)
    for uid in exames.seriesuid:
        subprocess.run([sys.executable, str(config.RAIZ / "scripts/09_extrair_patches.py"),
                        "--seriesuid", uid, "--saida", str(destino / "patches")], check=True)
    (destino / "selecao.json").write_text(json.dumps({
        "escopo": "verificacao_tecnica_4_exames", "teste_utilizado": False,
        "identidade_paciente": "mapa real de divisao do projeto",
        "seriesuid": exames.seriesuid.tolist(),
    }, indent=2))


if __name__ == "__main__":
    main()
