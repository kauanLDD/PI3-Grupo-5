"""Geração de candidatos por blob detection 3D, o produto central do grupo (Sprint 3).

Faz as duas partes do card em sequência:

1. Roda num exame só, com nódulo grande e conhecido, e desenha o resultado numa figura para
   olhar antes de soltar nos 888 (passos 1 a 4 do card).
2. Roda nos 888 exames pré-processados e grava `candidatos.csv`, e mede quantos dos 1.186
   nódulos anotados os candidatos alcançam, pelo critério de `src/detection/candidatos.py`
   (passo 5, e os dois últimos itens do checklist).

Recebe opcionalmente quantos exames rodar no passo 2, para medir o custo antes de soltar os 888.
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import blobs
from detection import candidatos as det
from visualization import fatias

cfg = config.carregar()
config.fixar_semente()

parametros = cfg["deteccao"]["blob_log"]
pasta_volumes = cfg["caminhos"]["volumes"]

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
disponiveis = {p.stem for p in pasta_volumes.glob("*.mha")}
inventario = inventario[inventario.seriesuid.isin(disponiveis)]
if inventario.empty:
    sys.exit(
        f"nenhum volume pré-processado em {pasta_volumes}. "
        "Rode antes: python scripts/07_preprocessar_base.py"
    )

anotacoes = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"])
nodulos = anotacoes[anotacoes.seriesuid.isin(inventario.seriesuid)]


def carregar(seriesuid: str):
    imagem = sitk.ReadImage(str(pasta_volumes / f"{seriesuid}.mha"))
    return imagem, sitk.GetArrayFromImage(imagem)


def detectar_exame(seriesuid: str, imagem, volume) -> pd.DataFrame:
    achados = blobs.detectar(volume, **parametros)
    return blobs.candidatos_do_exame(seriesuid, imagem, achados), achados


# --- Passo 1 a 4: um exame só, com nódulo grande, para aprender e validar visualmente. ---

candidatos_do_inventario = nodulos.merge(inventario, on="seriesuid")
retos = candidatos_do_inventario[candidatos_do_inventario.matriz_identidade]
escolhido = (retos if not retos.empty else candidatos_do_inventario).nlargest(1, "diameter_mm").iloc[0]
uid_demo = escolhido.seriesuid

print(f"exame de demonstração: {uid_demo}")
print(f"nódulo de referência: {escolhido.diameter_mm:.1f} mm em "
      f"({escolhido.coordX:.1f}, {escolhido.coordY:.1f}, {escolhido.coordZ:.1f}) mm\n")

imagem_demo, volume_demo = carregar(uid_demo)
inicio = time.time()
candidatos_demo, achados_demo = detectar_exame(uid_demo, imagem_demo, volume_demo)
print(f"blob_log({', '.join(f'{k}={v}' for k, v in parametros.items())}) "
      f"achou {len(achados_demo)} blobs em {time.time() - inicio:.1f}s\n")

nodulos_demo = nodulos[nodulos.seriesuid == uid_demo].copy()
nodulos_demo["diameter_mm"] = nodulos_demo["diameter_mm"].astype(float)
alcancados_demo = det.alcancados(nodulos_demo, candidatos_demo)
print(f"neste exame: {int(alcancados_demo.sum())} de {len(nodulos_demo)} nódulos anotados "
      f"têm candidato em cima")

# Figura: a fatia do nódulo de referência, com os candidatos que caem perto dela.
indice_nodulo = imagem_demo.TransformPhysicalPointToContinuousIndex(
    (escolhido.coordX, escolhido.coordY, escolhido.coordZ)
)
espacamento = imagem_demo.GetSpacing()[0]
raio_nodulo_px = (escolhido.diameter_mm / 2) / espacamento

z_nodulo = indice_nodulo[2]
proximos = [
    (x, y, float(blobs.raio_mm(sigma, espacamento) / espacamento))
    for z, y, x, sigma in achados_demo
    if abs(z - z_nodulo) <= max(3.0, raio_nodulo_px)
]

figura = cfg["caminhos"]["figuras"] / "deteccao_candidatos.png"
fatias.fatia_com_candidatos(
    volume_demo, (0.0, 1.0), indice_nodulo, raio_nodulo_px, proximos,
    f"{uid_demo}\nnódulo de {escolhido.diameter_mm:.1f} mm, "
    f"{len(proximos)} candidato(s) perto da fatia", figura,
)
print(f"{figura}\n")

# --- Passo 5: os 888 exames, gravando candidatos.csv. ---

limite = int(sys.argv[1]) if len(sys.argv) > 1 else None
lote = inventario if not limite else inventario.groupby("subset", group_keys=False).head(
    max(1, limite // 10)
).head(limite)

resultados, falhas = [], []
comeco = time.time()
for n, linha in enumerate(lote.itertuples(), 1):
    uid = linha.seriesuid
    try:
        imagem, volume = carregar(uid)
        candidatos_exame, _ = detectar_exame(uid, imagem, volume)
        resultados.append(candidatos_exame)
    except (OSError, RuntimeError, ValueError) as erro:
        falhas.append({"seriesuid": uid, "erro": f"{type(erro).__name__}: {erro}"})

    if n % 25 == 0 or n == len(lote):
        print(f"{n}/{len(lote)}  {time.time() - comeco:.0f}s")

candidatos_proprios = pd.concat(resultados, ignore_index=True) if resultados else pd.DataFrame(
    columns=blobs.COLUNAS
)

destino = cfg["caminhos"]["candidatos_proprios"]
destino.parent.mkdir(parents=True, exist_ok=True)
candidatos_proprios.to_csv(destino, index=False)

destino_falhas = cfg["caminhos"]["intermediario"] / "falhas_deteccao.csv"
pd.DataFrame(falhas, columns=["seriesuid", "erro"]).to_csv(destino_falhas, index=False)

print(f"\n{len(lote)} exames na lista, {len(lote) - len(falhas)} processados, {len(falhas)} com erro")
print(f"{len(candidatos_proprios)} candidatos no total, "
      f"{len(candidatos_proprios) / max(1, len(lote) - len(falhas)):.0f} por exame")
print(destino)

# --- Medir a cobertura, e comparar com o teto das listas prontas do desafio. ---

nodulos_do_lote = nodulos[nodulos.seriesuid.isin(lote.seriesuid)]
alcancados = int(det.alcancados(nodulos_do_lote, candidatos_proprios).sum())
teto = alcancados / len(nodulos_do_lote) if len(nodulos_do_lote) else float("nan")

tabela = pd.DataFrame([{
    "lista": "candidatos.csv (próprio)",
    "pontos": len(candidatos_proprios),
    "por_exame": len(candidatos_proprios) / max(1, len(lote) - len(falhas)),
    "alcancados": alcancados,
    "nodulos": len(nodulos_do_lote),
    "teto": teto,
}])
destino_cobertura = cfg["caminhos"]["cobertura_candidatos_proprios"]
tabela.to_csv(destino_cobertura, index=False)

print(f"\n{alcancados} de {len(nodulos_do_lote)} nódulos alcançados ({teto:.1%} de teto)")
print(destino_cobertura)

comparacao = cfg["caminhos"]["intermediario"] / "comparacao_candidatos.csv"
if comparacao.exists():
    referencia = pd.read_csv(comparacao)
    print(f"\npara comparar, {comparacao.name} tem o teto das listas prontas do desafio:")
    for linha in referencia.itertuples():
        print(f"  {linha.lista:>18}  {linha.teto:6.1%}")
else:
    print(f"\nrode scripts/08_comparar_candidatos.py para ter o teto das listas prontas ao lado")
