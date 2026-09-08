"""Pré-processa a base inteira e grava um volume por exame.

Recebe opcionalmente quantos exames processar, para medir o custo antes de soltar os 888.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset import volumes
from preprocessing import volume as pre

cfg = config.carregar()
config.fixar_semente()

hu = (cfg["pre_processamento"]["hu_min"], cfg["pre_processamento"]["hu_max"])
alvo = cfg["pre_processamento"]["espacamento_alvo"]
saida = cfg["caminhos"]["volumes"]
saida.mkdir(parents=True, exist_ok=True)

limite = int(sys.argv[1]) if len(sys.argv) > 1 else None
inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
if limite:
    # Amostra por subset em vez das primeiras linhas, para o tempo medido não vir de um subset só.
    inventario = inventario.groupby("subset", group_keys=False).head(max(1, limite // 10)).head(limite)

escritor = sitk.ImageFileWriter()
escritor.UseCompressionOn()

linhas, sem_volume, sem_mascara, com_erro = [], [], [], []
comeco = time.time()

for n, linha in enumerate(inventario.itertuples(), 1):
    uid = linha.seriesuid
    caminho = volumes.caminho_do_volume(cfg["caminhos"]["luna16"], uid, cfg["selecao"]["subsets"])
    mascara = cfg["caminhos"]["luna16_mascaras"] / f"{uid}.mhd"
    destino = saida / f"{uid}.mha"

    if caminho is None:
        sem_volume.append(uid)
        continue
    if not mascara.exists():
        sem_mascara.append(uid)
        continue

    t = time.time()
    try:
        processado, iso = pre.preprocessar(sitk.ReadImage(str(caminho)),
                                           sitk.ReadImage(str(mascara)), hu, alvo)
    except RuntimeError as erro:
        com_erro.append((uid, str(erro).splitlines()[0]))
        continue

    escritor.SetFileName(str(destino))
    escritor.Execute(processado)

    linhas.append({
        "seriesuid": uid,
        "subset": linha.subset,
        "dim_x": processado.GetSize()[0],
        "dim_y": processado.GetSize()[1],
        "dim_z": processado.GetSize()[2],
        "pulmao_fracao": float((sitk.GetArrayFromImage(iso) > 0).mean()),
        "mb": destino.stat().st_size / 1e6,
        "segundos": time.time() - t,
    })

    if n % 25 == 0 or n == len(inventario):
        print(f"{n}/{len(inventario)}  {time.time() - comeco:.0f}s")

relatorio = pd.DataFrame(linhas)
destino_csv = cfg["caminhos"]["intermediario"] / "preprocessamento.csv"
relatorio.to_csv(destino_csv, index=False)

print(f"\n{len(inventario)} exames na lista, {len(relatorio)} gravados")
print(f"  sem volume no disco: {len(sem_volume)}")
print(f"  sem máscara do desafio: {len(sem_mascara)}")
print(f"  erro na leitura ou no pré-processamento: {len(com_erro)}")
for uid, erro in com_erro:
    print(f"    {uid}  {erro}")

if not relatorio.empty:
    print(f"\ntempo por exame: mediana {relatorio.segundos.median():.1f}s, "
          f"de {relatorio.segundos.min():.1f} a {relatorio.segundos.max():.1f}")
    print(f"tamanho por exame: mediana {relatorio.mb.median():.1f} MB, "
          f"de {relatorio.mb.min():.1f} a {relatorio.mb.max():.1f}")
    print(f"total gravado: {relatorio.mb.sum() / 1000:.2f} GB")
    print(f"pulmão: mediana {relatorio.pulmao_fracao.median():.1%} do volume")
    print(f"\n{destino_csv}")
