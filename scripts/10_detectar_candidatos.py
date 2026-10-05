"""Geração de candidatos por blob detection 3D, o produto central do grupo (Sprint 3).

Faz as duas partes do card em sequência:

1. Roda num exame só, com nódulo grande e conhecido, e desenha o resultado numa figura para
   olhar antes de soltar nos 888 (passos 1 a 4 do card).
2. Roda nos 888 exames pré-processados e grava `candidatos.csv`, e mede quantos dos 1.186
   nódulos anotados os candidatos alcançam, pelo critério de `src/detection/candidatos.py`
   (passo 5, e os dois últimos itens do checklist).

Recebe opcionalmente quantos exames rodar no passo 2, para medir o custo antes de soltar os 888.
Guarda uma saída atômica por exame para permitir retomada e monta o CSV final somente quando
todo o lote termina.
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import blobs, rodada
from detection import candidatos as det
from visualization import fatias

cfg = config.carregar()
config.fixar_semente()

parametros = cfg["deteccao"]["blob_log"]
trabalhadores = cfg["deteccao"]["trabalhadores"]
pasta_volumes = cfg["caminhos"]["volumes"]

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
disponiveis = {p.stem for p in pasta_volumes.glob("*.mha")}
no_inventario = len(inventario)
ausentes = inventario[~inventario.seriesuid.isin(disponiveis)]
if not ausentes.empty:
    raise ValueError(f"{len(ausentes)} volumes ausentes; a rodada completa nao pode continuar")
inventario = inventario[inventario.seriesuid.isin(disponiveis)]
print(f"{no_inventario} exames no inventário, {len(inventario)} com volume pré-processado em disco, "
      f"{no_inventario - len(inventario)} sem")
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


def detectar_exame(seriesuid: str, imagem, volume):
    """Devolve o par (candidatos em mm, blobs crus em voxel)."""
    achados = blobs.detectar(volume, **parametros)
    return blobs.candidatos_do_exame(seriesuid, imagem, achados), achados


def chave_da_execucao():
    origem = Path(blobs.__file__)
    h = hashlib.sha256()
    h.update(origem.read_bytes())
    h.update(json.dumps(parametros, sort_keys=True).encode())
    relatorio = cfg["caminhos"]["intermediario"] / "preprocessamento.csv"
    if relatorio.exists():
        h.update(relatorio.read_bytes())
    return h.hexdigest()[:12]


def processar_exame(tarefa):
    seriesuid, caminho_volume, destino, parametros_exame = tarefa
    destino = Path(destino)
    try:
        if destino.exists():
            candidatos = rodada.ler_exame(destino, seriesuid)
            return seriesuid, len(candidatos), None, True
        imagem = sitk.ReadImage(caminho_volume)
        volume = sitk.GetArrayFromImage(imagem)
        achados = blobs.detectar(volume, **parametros_exame)
        candidatos = blobs.candidatos_do_exame(seriesuid, imagem, achados)
        temporario = destino.with_suffix(".tmp")
        candidatos.to_csv(temporario, index=False)
        temporario.replace(destino)
        return seriesuid, len(candidatos), None, False
    except (OSError, RuntimeError, ValueError, MemoryError) as erro:
        return seriesuid, 0, f"{type(erro).__name__}: {erro}", False


def juntar_resultados(lote, pasta, destino):
    temporario = destino.with_suffix(".tmp")
    escreveu_cabecalho = False
    with open(temporario, "wb") as saida:
        for uid in lote.seriesuid:
            origem = pasta / f"{uid}.csv"
            if not origem.exists():
                continue
            with open(origem, "rb") as entrada:
                if escreveu_cabecalho:
                    entrada.readline()
                else:
                    escreveu_cabecalho = True
                while bloco := entrada.read(1024 * 1024):
                    saida.write(bloco)
    if not escreveu_cabecalho:
        pd.DataFrame(columns=blobs.COLUNAS).to_csv(temporario, index=False)
    temporario.replace(destino)


def medir_cobertura(lote, pasta, nodulos_do_lote):
    alcancados = 0
    pontos = 0
    por_uid = {uid: grupo for uid, grupo in nodulos_do_lote.groupby("seriesuid")}
    for uid in lote.seriesuid:
        caminho = pasta / f"{uid}.csv"
        if not caminho.exists():
            continue
        candidatos = pd.read_csv(caminho)
        pontos += len(candidatos)
        nodulos_exame = por_uid.get(uid)
        if nodulos_exame is not None:
            alcancados += int(det.alcancados(nodulos_exame, candidatos).sum())
    return pontos, alcancados


candidatos_do_inventario = nodulos.merge(inventario, on="seriesuid")
if candidatos_do_inventario.empty:
    sys.exit(
        "nenhum dos exames com volume pré-processado tem nódulo anotado, "
        "e a demonstração precisa de um para validar a geometria"
    )

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

limite = int(sys.argv[1]) if len(sys.argv) > 1 else None
lote = inventario if not limite else inventario.groupby("subset", group_keys=False).head(
    max(1, limite // 10)
).head(limite)

chave = chave_da_execucao()
pasta_execucao = cfg["caminhos"]["intermediario"] / "deteccao_log" / chave / "por_exame"
pasta_execucao.mkdir(parents=True, exist_ok=True)

falhas = []
concluidos = 0
comeco = time.time()
tarefas = [
    (
        linha.seriesuid,
        str(pasta_volumes / f"{linha.seriesuid}.mha"),
        str(pasta_execucao / f"{linha.seriesuid}.csv"),
        parametros,
    )
    for linha in lote.itertuples()
]

with ProcessPoolExecutor(max_workers=trabalhadores) as executor:
    futuros = [executor.submit(processar_exame, tarefa) for tarefa in tarefas]
    for futuro in as_completed(futuros):
        uid, _, erro, _ = futuro.result()
        concluidos += 1
        if erro:
            falhas.append({"seriesuid": uid, "erro": erro})
        if concluidos % 25 == 0 or concluidos == len(lote):
            print(f"{concluidos}/{len(lote)}  {time.time() - comeco:.0f}s")

destino = cfg["caminhos"]["candidatos_proprios"]
destino.parent.mkdir(parents=True, exist_ok=True)

destino_falhas = cfg["caminhos"]["intermediario"] / "falhas_deteccao.csv"
pd.DataFrame(falhas, columns=["seriesuid", "erro"]).to_csv(destino_falhas, index=False)
for falha in falhas:
    rodada.registrar(pasta_execucao, falha["seriesuid"], rodada.FALHA, erro=falha["erro"])
if falhas:
    raise RuntimeError(f"{len(falhas)} exames com erro; saidas finais anteriores preservadas")
rodada.situacao(pasta_execucao, lote.seriesuid).to_csv(cfg["caminhos"]["situacao_deteccao"], index=False)
juntar_resultados(lote, pasta_execucao, destino)

print(f"\n{len(lote)} exames na lista, {len(lote) - len(falhas)} processados, {len(falhas)} com erro")
nodulos_do_lote = nodulos[nodulos.seriesuid.isin(lote.seriesuid)]
pontos, alcancados = medir_cobertura(lote, pasta_execucao, nodulos_do_lote)
print(f"{pontos} candidatos no total, "
      f"{pontos / max(1, len(lote) - len(falhas)):.0f} por exame")
print(destino)

teto = alcancados / len(nodulos_do_lote) if len(nodulos_do_lote) else float("nan")

tabela = pd.DataFrame([{
    "lista": "candidatos.csv (próprio)",
    "pontos": pontos,
    "por_exame": pontos / max(1, len(lote) - len(falhas)),
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


# Relatorios de cobertura da rodada completa, sem selecionar parametros pelo teste.
candidatos_proprios = pd.read_csv(destino)
exames_medidos = set(lote.seriesuid)
reamostras = cfg["avaliacao"]["bootstrap_reamostras"]
confianca = cfg["avaliacao"]["intervalo_confianca"]
semente = cfg["seed"]
def medir(nome, filtro, lista):
    alcancado = det.alcancados(nodulos_do_lote, lista)
    medida = det.cobertura(nodulos_do_lote, alcancado, reamostras, confianca, semente)
    return {"lista": nome, "filtro": filtro, "exames": len(exames_medidos),
            "pontos": len(lista), "por_exame": len(lista) / max(1, len(exames_medidos)),
            **medida}


propria = medir("candidatos.csv (próprio)", "nenhum", candidatos_proprios)
propria["teto"] = propria["cobertura"]
pd.DataFrame([propria]).to_csv(cfg["caminhos"]["cobertura_candidatos_proprios"], index=False)

print(f"\n{propria['alcancados']} de {propria['nodulos']} nódulos alcançados nos "
      f"{propria['exames']} exames processados: {propria['cobertura']:.1%}, "
      f"IC {confianca:.0%} de {propria['ic_inferior']:.1%} a {propria['ic_superior']:.1%} "
      f"({reamostras} reamostras por exame)")
print("é teto de sensibilidade da lista, não ponto da curva FROC")
print(cfg["caminhos"]["cobertura_candidatos_proprios"])

# A troca entre cobertura e quantidade de candidatos. Dentro da nossa lista, cortar as escalas
# menores do blob_log é o jeito de ter menos pontos sem rodar de novo; ao lado, as duas listas
# prontas do desafio, medidas sobre os mesmos exames.
linhas = [propria]
for raio_minimo in sorted(candidatos_proprios.raio.round(3).unique())[1:]:
    filtrada = candidatos_proprios[candidatos_proprios.raio.round(3) >= raio_minimo]
    linhas.append(medir("candidatos.csv (próprio)", f"raio >= {raio_minimo:.2f} mm", filtrada))

for nome, caminho in [("candidates.csv", cfg["caminhos"]["luna16_candidatos_original"]),
                      ("candidates_V2.csv", cfg["caminhos"]["luna16_candidatos"])]:
    if not caminho.exists():
        print(f"\n{caminho} não existe, a troca sai sem {nome}")
        continue
    lista = pd.read_csv(caminho)
    linhas.append(medir(nome, "nenhum", lista[lista.seriesuid.isin(exames_medidos)]))

troca = pd.DataFrame(linhas)
destino_troca = cfg["caminhos"]["troca_cobertura_candidatos"]
troca.to_csv(destino_troca, index=False)

print(f"\n{'lista':>24} {'filtro':>18} {'por exame':>10} {'alcançados':>14} {'cobertura':>10}")
print("-" * 82)
for linha in troca.itertuples():
    print(f"{linha.lista:>24} {linha.filtro:>18} {linha.por_exame:10.0f} "
          f"{linha.alcancados:6d} de {linha.nodulos:<5d} {linha.cobertura:9.1%}")
print(destino_troca)
