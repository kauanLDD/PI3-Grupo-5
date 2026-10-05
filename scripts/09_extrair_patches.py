"""Extrai e verifica cubos 3D da lista V2, um NPZ por exame.

Arquivos validos sao reaproveitados; arquivos incompletos sao recriados.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from zipfile import BadZipFile

import numpy as np
import pandas as pd
import SimpleITK as sitk
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import patches


def argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seriesuid", help="extrai somente este exame")
    parser.add_argument("--candidatos", type=Path, help="caminho do candidates_V2.csv")
    parser.add_argument("--volumes", type=Path, help="pasta dos volumes pre-processados .mha")
    parser.add_argument("--saida", type=Path, help="pasta de saida dos .npz")
    return parser.parse_args()


def metadados(grupo):
    return {
        "candidate_id": grupo.index.to_numpy(dtype=np.int64),
        "coordX": grupo.coordX.to_numpy(dtype=np.float32),
        "coordY": grupo.coordY.to_numpy(dtype=np.float32),
        "coordZ": grupo.coordZ.to_numpy(dtype=np.float32),
        "classe_luna16": grupo["class"].to_numpy(dtype=np.int8),
    }


def validar_arquivo(caminho, grupo, tamanho):
    """Confere tamanho, faixa, coordenadas, classes e IDs contra a lista V2."""
    with np.load(caminho, allow_pickle=False) as dados:
        if set(dados.files) != {"patches", *metadados(grupo)}:
            raise ValueError("campos do NPZ inesperados")
        cubos = dados["patches"]
        if cubos.shape != (len(grupo), *tamanho[::-1]):
            raise ValueError(f"formato incorreto: {cubos.shape}")
        if cubos.dtype != np.float32 or not np.isfinite(cubos).all():
            raise ValueError("cubos nao sao float32 finitos")
        if cubos.size and (cubos.min() < 0 or cubos.max() > 1):
            raise ValueError("voxels fora de [0, 1]")
        for nome, valores in metadados(grupo).items():
            if not np.array_equal(dados[nome], valores):
                raise ValueError(f"{nome} diverge da lista V2")
    return caminho.stat().st_size


def extrair(imagem, grupo, tamanho):
    volume = sitk.GetArrayFromImage(imagem)
    if not np.isfinite(volume).all() or volume.min() < 0 or volume.max() > 1:
        raise ValueError("volume pre-processado fora de [0, 1]")
    recortes = np.empty((len(grupo), *tamanho[::-1]), dtype=np.float32)
    for i, candidato in enumerate(grupo.itertuples()):
        centro = imagem.TransformPhysicalPointToIndex(
            (float(candidato.coordX), float(candidato.coordY), float(candidato.coordZ))
        )
        if any(indice < 0 or indice >= limite
               for indice, limite in zip(centro, imagem.GetSize())):
            raise ValueError(f"candidate_id={candidato.Index}: centro {centro} fora do volume")
        recortes[i] = patches.extrair_patch(volume, centro, tamanho)
        if recortes[i, tamanho[2] // 2, tamanho[1] // 2, tamanho[0] // 2] != volume[centro[::-1]]:
            raise ValueError(f"candidate_id={candidato.Index}: centro do cubo divergente")
    return recortes


def salvar(destino, grupo, recortes, tamanho):
    temporario = destino.with_name(f"{destino.stem}.tmp{destino.suffix}")
    try:
        with open(temporario, "wb") as arquivo:
            np.savez_compressed(arquivo, patches=recortes, **metadados(grupo))
        bytes_gravados = validar_arquivo(temporario, grupo, tamanho)
        temporario.replace(destino)
        return bytes_gravados
    finally:
        temporario.unlink(missing_ok=True)


def main():
    args = argumentos()
    cfg = config.carregar()
    tamanho = tuple(cfg["candidatos"]["patch"])
    if tamanho != (34, 34, 34):
        sys.exit(f"esperado cubo 34 x 34 x 34; configurado {tamanho}")
    caminho_v2 = args.candidatos or cfg["caminhos"]["luna16_candidatos"]
    volumes = args.volumes or cfg["caminhos"]["volumes"]
    saida = args.saida or cfg["caminhos"]["processado"] / "patches"
    if not caminho_v2.is_file():
        sys.exit(f"lista V2 nao encontrada: {caminho_v2}")
    if not volumes.is_dir():
        sys.exit(f"pasta dos volumes nao encontrada: {volumes}")

    candidatos = pd.read_csv(caminho_v2)
    ausentes = {"seriesuid", "coordX", "coordY", "coordZ", "class"} - set(candidatos.columns)
    if ausentes:
        sys.exit(f"colunas ausentes na lista V2: {sorted(ausentes)}")
    if candidatos[["seriesuid", "coordX", "coordY", "coordZ", "class"]].isna().any().any():
        sys.exit("lista V2 contem campos vazios")
    if not np.isfinite(candidatos[["coordX", "coordY", "coordZ"]].to_numpy(dtype=float)).all():
        sys.exit("lista V2 contem coordenadas nao finitas")
    if not candidatos["class"].isin([0, 1]).all():
        sys.exit("lista V2 contem classe diferente de 0 ou 1")
    if args.seriesuid:
        candidatos = candidatos[candidatos.seriesuid == args.seriesuid]
        if candidatos.empty:
            sys.exit(f"nenhum candidato encontrado para {args.seriesuid}")
    elif candidatos.seriesuid.nunique() != 888:
        sys.exit(f"esperados 888 exames; encontrados {candidatos.seriesuid.nunique()}")

    saida.mkdir(parents=True, exist_ok=True)
    inicio = time.perf_counter()
    contagem = {"criado": 0, "existente": 0, "recriado": 0, "falhou": 0}
    falhas = []
    recortes_validos = 0
    bytes_validos = 0
    for seriesuid, grupo in tqdm(candidatos.groupby("seriesuid"), desc="Extraindo patches",
                                 unit="exame"):
        destino = saida / f"{seriesuid}.npz"
        ja_existe = destino.exists()
        if ja_existe:
            try:
                tamanho_arquivo = validar_arquivo(destino, grupo, tamanho)
                contagem["existente"] += 1
                recortes_validos += len(grupo)
                bytes_validos += tamanho_arquivo
                continue
            except (OSError, ValueError, KeyError, EOFError, RuntimeError, BadZipFile) as erro:
                tqdm.write(f"{seriesuid}: arquivo existente invalido ({erro}); recriando")
        try:
            caminho = volumes / f"{seriesuid}.mha"
            if not caminho.is_file():
                raise FileNotFoundError(f"volume pre-processado nao encontrado: {caminho}")
            imagem = sitk.ReadImage(str(caminho))
            recortes = extrair(imagem, grupo, tamanho)
            tamanho_arquivo = salvar(destino, grupo, recortes, tamanho)
            contagem["recriado" if ja_existe else "criado"] += 1
            recortes_validos += len(grupo)
            bytes_validos += tamanho_arquivo
        except (OSError, RuntimeError, ValueError, KeyError, EOFError, BadZipFile) as erro:
            contagem["falhou"] += 1
            falhas.append({"seriesuid": seriesuid, "erro": f"{type(erro).__name__}: {erro}"})

    sufixo = f"_{args.seriesuid}" if args.seriesuid else ""
    relatorios = cfg["caminhos"]["intermediario"]
    relatorios.mkdir(parents=True, exist_ok=True)
    falhas_csv = relatorios / f"falhas_patches{sufixo}.csv"
    pd.DataFrame(falhas, columns=["seriesuid", "erro"]).to_csv(falhas_csv, index=False)
    arquivos_na_pasta = [
        caminho for caminho in saida.glob("*.npz") if not caminho.name.endswith(".tmp.npz")
    ]
    uids_esperados = set(candidatos.seriesuid)
    arquivos_extras = sorted(
        caminho.stem for caminho in arquivos_na_pasta if caminho.stem not in uids_esperados
    )
    resumo = {
        "exames_esperados": candidatos.seriesuid.nunique(),
        "recortes_esperados": len(candidatos),
        "arquivos_validos": sum(contagem[k] for k in ("criado", "existente", "recriado")),
        "arquivos_npz_na_pasta": len(arquivos_na_pasta),
        "arquivos_extras": arquivos_extras,
        "recortes_validos": recortes_validos,
        "segundos_da_rodada": round(time.perf_counter() - inicio, 2),
        "bytes_arquivos_validos": bytes_validos,
        "bytes_npz_na_pasta": sum(caminho.stat().st_size for caminho in arquivos_na_pasta),
        **contagem,
    }
    resumo_json = relatorios / f"resumo_patches{sufixo}.json"
    resumo_json.write_text(json.dumps(resumo, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resumo, indent=2))
    print(f"Arquivos: {saida}\nFalhas: {falhas_csv}\nResumo: {resumo_json}")
    if (resumo["arquivos_validos"] != resumo["exames_esperados"]
            or recortes_validos != len(candidatos)
            or (not args.seriesuid and arquivos_extras)):
        sys.exit(1)


if __name__ == "__main__":
    main()
