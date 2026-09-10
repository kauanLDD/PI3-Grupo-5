"""Extrai patches 3D dos candidatos em arquivos comprimidos por exame."""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import patches


def argumentos():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seriesuid", help="extrai somente os candidatos deste exame")
    return parser.parse_args()


def salvar(destino, grupo, recortes):
    temporario = destino.with_name(f"{destino.stem}.tmp{destino.suffix}")
    with open(temporario, "wb") as arquivo:
        np.savez_compressed(
            arquivo,
            patches=np.asarray(recortes, dtype=np.float32),
            candidate_id=grupo.index.to_numpy(dtype=np.int64),
            coordX=grupo.coordX.to_numpy(dtype=np.float32),
            coordY=grupo.coordY.to_numpy(dtype=np.float32),
            coordZ=grupo.coordZ.to_numpy(dtype=np.float32),
            classe_luna16=grupo["class"].to_numpy(dtype=np.int8),
        )
    temporario.replace(destino)


cfg = config.carregar()
config.fixar_semente()
args = argumentos()
tamanho = cfg["candidatos"]["patch"]
volumes = cfg["caminhos"]["processado"] / "volumes"
saida = cfg["caminhos"]["processado"] / "patches"
candidatos = pd.read_csv(cfg["caminhos"]["luna16_candidatos"])

if args.seriesuid:
    candidatos = candidatos[candidatos.seriesuid == args.seriesuid]
    if candidatos.empty:
        sys.exit(f"nenhum candidato encontrado para {args.seriesuid}")

saida.mkdir(parents=True, exist_ok=True)
falhas = []
contagem = {"criado": 0, "existente": 0, "falhou": 0}
for seriesuid, grupo in tqdm(candidatos.groupby("seriesuid"), desc="Extraindo patches", unit="exame"):
    destino = saida / f"{seriesuid}.npz"
    if destino.exists():
        contagem["existente"] += 1
        continue

    caminho = volumes / f"{seriesuid}.mha"
    if not caminho.exists():
        contagem["falhou"] += 1
        falhas.append({"seriesuid": seriesuid, "erro": "volume pre-processado nao encontrado"})
        continue

    try:
        imagem = sitk.ReadImage(str(caminho))
        volume = sitk.GetArrayFromImage(imagem)
        recortes = []
        for candidato in grupo.itertuples():
            centro = imagem.TransformPhysicalPointToIndex(
                (candidato.coordX, candidato.coordY, candidato.coordZ)
            )
            recortes.append(patches.extrair_patch(volume, centro, tamanho))
        salvar(destino, grupo, recortes)
        contagem["criado"] += 1
    except (OSError, RuntimeError, ValueError) as erro:
        contagem["falhou"] += 1
        falhas.append({"seriesuid": seriesuid, "erro": f"{type(erro).__name__}: {erro}"})

relatorio = cfg["caminhos"]["intermediario"] / "falhas_patches.csv"
relatorio.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(falhas, columns=["seriesuid", "erro"]).to_csv(relatorio, index=False)

print(f"{contagem['criado']} criados, {contagem['existente']} existentes, {contagem['falhou']} falharam")
print(saida)
print(relatorio)
