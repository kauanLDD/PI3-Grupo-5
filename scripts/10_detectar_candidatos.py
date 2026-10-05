"""Geração de candidatos por blob detection 3D, o produto central do grupo (Sprint 3).

Faz as duas partes do card em sequência:

1. Roda num exame só, com nódulo grande e conhecido, e desenha o resultado numa figura para
   olhar antes de soltar nos 888 (passos 1 a 4 do card).
2. Roda nos 888 exames pré-processados e grava `candidatos.csv`, e mede quantos dos 1.186
   nódulos anotados os candidatos alcançam, pelo critério de `src/detection/candidatos.py`
   (passo 5, e os dois últimos itens do checklist).

A segunda parte é a do card S4-T10. Ela é retomável: cada exame grava o próprio arquivo em
`rodada_deteccao`, e rodar de novo pula os prontos e tenta de novo os que falharam. A pasta
guarda os parâmetros com que nasceu e recusa continuar com outros. No fim grava a situação de
cada exame, a cobertura com intervalo de confiança e a troca entre cobertura e quantidade de
candidatos. Cobertura aqui é teto de sensibilidade da lista, não é FROC.

Recebe opcionalmente quantos exames rodar no passo 2, para medir o custo antes de soltar os 888.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import blobs
from detection import candidatos as det
from detection import rodada
from visualization import fatias

cfg = config.carregar()
config.fixar_semente()

parametros = cfg["deteccao"]["blob_log"]
pasta_volumes = cfg["caminhos"]["volumes"]

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
disponiveis = {p.stem for p in pasta_volumes.glob("*.mha")}
no_inventario = len(inventario)
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

# Confirmar a configuração antes de rodar: a pasta guarda os parâmetros com que nasceu, e
# continuar com outros misturaria duas buscas na mesma lista.
pasta_rodada = cfg["caminhos"]["rodada_deteccao"]
try:
    retomando = rodada.preparar_pasta(pasta_rodada, parametros)
except ValueError as erro:
    sys.exit(str(erro))

faltam = rodada.pendentes(pasta_rodada, lote.seriesuid)
print(f"parâmetros da rodada: {', '.join(f'{k}={v}' for k, v in parametros.items())}")
print(f"{pasta_rodada}: {'retomando' if retomando else 'rodada nova'}, "
      f"{len(lote) - len(faltam)} de {len(lote)} exames já prontos, {len(faltam)} por fazer\n")

comeco = time.time()
for n, uid in enumerate(faltam, 1):
    t = time.time()
    try:
        imagem, volume = carregar(uid)
        candidatos_exame, _ = detectar_exame(uid, imagem, volume)
    except (OSError, RuntimeError, ValueError) as erro:
        rodada.registrar(pasta_rodada, uid, rodada.FALHA, segundos=time.time() - t,
                         erro=f"{type(erro).__name__}: {str(erro).splitlines()[0]}")
    else:
        rodada.gravar_exame(pasta_rodada, uid, candidatos_exame)
        status = rodada.CONCLUIDO if len(candidatos_exame) else rodada.SEM_CANDIDATO
        rodada.registrar(pasta_rodada, uid, status, len(candidatos_exame), time.time() - t)

    if n % 25 == 0 or n == len(faltam):
        passado = time.time() - comeco
        print(f"{n}/{len(faltam)}  {passado:.0f}s, faltam uns {passado / n * (len(faltam) - n):.0f}s")

# Registrar exames concluídos, falhas e exames sem candidato.
situacao = rodada.situacao(pasta_rodada, lote.seriesuid)
situacao = situacao.merge(lote[["seriesuid", "subset"]], on="seriesuid")
destino_situacao = cfg["caminhos"]["situacao_deteccao"]
situacao.to_csv(destino_situacao, index=False)

contagem = situacao.status.value_counts()
processados = situacao[situacao.status.isin([rodada.CONCLUIDO, rodada.SEM_CANDIDATO])]
print(f"\n{len(lote)} exames na lista: "
      + ", ".join(f"{contagem.get(s, 0)} {s}" for s in
                  [rodada.CONCLUIDO, rodada.SEM_CANDIDATO, rodada.FALHA, rodada.PENDENTE]))
print(destino_situacao)

candidatos_proprios = rodada.juntar(pasta_rodada, lote.seriesuid, blobs.COLUNAS)
destino = cfg["caminhos"]["candidatos_proprios"]
candidatos_proprios.to_csv(destino, index=False)

# Média de candidatos por exame. O denominador são os exames que rodaram, incluindo os que não
# deram candidato nenhum, porque esses contam na média de falso positivo da FROC depois.
por_exame = processados.candidatos
print(f"\n{len(candidatos_proprios)} candidatos em {len(processados)} exames processados")
if len(processados):
    print(f"por exame: média {por_exame.mean():.0f}, mediana {por_exame.median():.0f}, "
          f"de {por_exame.min()} a {por_exame.max()}")
    tempos = processados.segundos.dropna()
    if len(tempos):
        print(f"tempo por exame: média {tempos.mean():.1f}s, total {tempos.sum() / 3600:.1f} h")
print(destino)

# Fração de nódulos encontrados, só sobre os exames que rodaram: exame com falha não teve busca,
# e contar os nódulos dele como perdidos misturaria falha de execução com falha do método.
reamostras = cfg["avaliacao"]["bootstrap_reamostras"]
confianca = cfg["avaliacao"]["intervalo_confianca"]
semente = cfg["seed"]
exames_medidos = set(processados.seriesuid)
nodulos_medidos = nodulos[nodulos.seriesuid.isin(exames_medidos)]


def medir(nome, filtro, lista):
    alcancado = det.alcancados(nodulos_medidos, lista)
    medida = det.cobertura(nodulos_medidos, alcancado, reamostras, confianca, semente)
    return {"lista": nome, "filtro": filtro, "exames": len(exames_medidos),
            "pontos": len(lista), "por_exame": len(lista) / max(1, len(exames_medidos)),
            **medida}


propria = medir("candidatos.csv (próprio)", "nenhum", candidatos_proprios)
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
