"""Pre-processa todos os volumes LUNA16 de forma retomavel."""

import sys
from pathlib import Path

import pandas as pd
import SimpleITK as sitk
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset import volumes
from preprocessing import volume as pre

cfg = config.carregar()
config.fixar_semente()

hu = (cfg["pre_processamento"]["hu_min"], cfg["pre_processamento"]["hu_max"])
alvo = cfg["pre_processamento"]["espacamento_alvo"]
normalizar_0_a_1 = cfg["pre_processamento"]["normalizar_0_a_1"]
inventario = cfg["caminhos"]["intermediario"] / "inventario_volumes.csv"
saida = cfg["caminhos"]["processado"] / "volumes"


def salvar(imagem, destino):
    temporario = destino.with_name(f"{destino.stem}.tmp{destino.suffix}")
    escritor = sitk.ImageFileWriter()
    escritor.SetFileName(str(temporario))
    escritor.UseCompressionOn()
    escritor.Execute(imagem)
    temporario.replace(destino)


def ja_processado(destino):
    if not destino.exists():
        return False
    if not normalizar_0_a_1:
        return True

    leitor = sitk.ImageFileReader()
    leitor.SetFileName(str(destino))
    try:
        leitor.ReadImageInformation()
        return (
            leitor.HasMetaDataKey("pi3_normalizado_0_a_1")
            and leitor.GetMetaData("pi3_normalizado_0_a_1") == "true"
        )
    except RuntimeError:
        return False


def processar(linha):
    destino = saida / f"{linha.seriesuid}.mha"
    if ja_processado(destino):
        return "existente", None

    origem = volumes.caminho_do_volume(
        cfg["caminhos"]["luna16"], linha.seriesuid, cfg["selecao"]["subsets"]
    )
    mascara = cfg["caminhos"]["luna16_mascaras"] / f"{linha.seriesuid}.mhd"
    if origem is None:
        return "falhou", "volume nao encontrado"
    if not mascara.exists():
        return "falhou", "mascara nao encontrada"

    try:
        volume, _ = pre.preprocessar(
            sitk.ReadImage(str(origem)),
            sitk.ReadImage(str(mascara)),
            hu,
            alvo,
            normalizar_0_a_1=normalizar_0_a_1,
        )
        volume.SetMetaData("pi3_normalizado_0_a_1", str(normalizar_0_a_1).lower())
        salvar(volume, destino)
    except (OSError, RuntimeError) as erro:
        return "falhou", f"{type(erro).__name__}: {erro}"
    return "criado", None


if not inventario.exists():
    sys.exit(f"rode antes o 02_inventario_volumes.py: {inventario} não existe")

saida.mkdir(parents=True, exist_ok=True)
falhas = []
contagem = {"criado": 0, "existente": 0, "falhou": 0}
for linha in tqdm(pd.read_csv(inventario).itertuples(), desc="Pre-processando", unit="volume"):
    status, erro = processar(linha)
    contagem[status] += 1
    if erro:
        falhas.append({"seriesuid": linha.seriesuid, "erro": erro})

relatorio = cfg["caminhos"]["intermediario"] / "falhas_preprocessamento.csv"
relatorio.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(falhas, columns=["seriesuid", "erro"]).to_csv(relatorio, index=False)

print(f"{contagem['criado']} criados, {contagem['existente']} ja existentes, {contagem['falhou']} falharam")
print(saida)
print(relatorio)
