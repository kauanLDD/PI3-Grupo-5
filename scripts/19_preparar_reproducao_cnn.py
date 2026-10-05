"""Copia a população técnica congelada; não altera nem reprocessa o dataset."""

import argparse
import json
from pathlib import Path
import shutil
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from experimentos.cnn import conferir_divisao


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="raiz externa do LUNA16")
    parser.add_argument("--saida", type=Path, default=config.RAIZ / "dados/processado/cnn_reproducao")
    args = parser.parse_args()
    base, destino = args.dataset.resolve(), args.saida.resolve()
    tabela = config.RAIZ / "configuracao/cnn_reproducao_exames.csv"
    exames = pd.read_csv(tabela)
    conferir_divisao(exames)
    fontes = {"divisao.csv": tabela, "annotations.csv": base / "annotations.csv",
              "annotations_excluded.csv": base / "evaluationScript/evaluationScript/annotations/annotations_excluded.csv",
              "candidates_V2.csv": base / "candidates_V2/candidates_V2.csv"}
    for uid in exames.seriesuid:
        fontes[f"patches/{uid}.npz"] = base / "processado/patches" / f"{uid}.npz"
    for caminho in fontes.values():
        if not caminho.is_file():
            raise FileNotFoundError(caminho)
    # Pastas existentes são preservadas; evitar misturar versões silenciosamente.
    if destino.exists():
        raise ValueError(f"pasta já existe; use as entradas existentes ou escolha outra --saida: {destino}")
    for nome, origem in fontes.items():
        alvo = destino / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, alvo)
    (destino / "selecao.json").write_text(json.dumps({
        "escopo": "reproducao_tecnica_6_exames", "origem": str(base),
        "regra_original": "dois menores NPZ com anotacao por subset 0/7/8, antes de ver escores",
        "populacao_congelada": str(tabela.relative_to(config.RAIZ)),
        "identidade_paciente": "aliases por exame, restritos a subsets sem repeticao conforme decisao 0003",
    }, indent=2), encoding="utf-8")
    print(destino)


if __name__ == "__main__":
    main()
