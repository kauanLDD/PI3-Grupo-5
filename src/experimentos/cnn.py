"""CNN3D extraída da pesquisa; treino amostrado e inferência completa por exame."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from detection.procedencia_recortes import assinatura
from torch import nn
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler


class CNN3D(nn.Module):
    """Mesma arquitetura e nomes de pesos de curvafroc_pesquisa.ipynb."""

    def __init__(self, dropout_rate=0.3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv3d(1, 16, 3, padding=1), nn.BatchNorm3d(16),
            nn.ReLU(inplace=True), nn.MaxPool3d(2),
            nn.Conv3d(16, 32, 3, padding=1), nn.BatchNorm3d(32),
            nn.ReLU(inplace=True), nn.MaxPool3d(2),
            nn.Conv3d(32, 64, 3, padding=1), nn.BatchNorm3d(64),
            nn.ReLU(inplace=True), nn.MaxPool3d(2), nn.AdaptiveAvgPool3d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Dropout(dropout_rate), nn.Linear(64, 32),
            nn.ReLU(inplace=True), nn.Linear(32, 2),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


def fixar_determinismo(semente, threads, device="cpu"):
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.set_num_threads(threads)
    torch.manual_seed(semente)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(semente)
    # Decisão 0007: na GPU o modo determinístico avisa em vez de interromper.
    torch.use_deterministic_algorithms(True, warn_only=device == "cuda")
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def conferir_divisao(tabela):
    colunas = {"seriesuid", "paciente", "subset", "particao"}
    if not colunas.issubset(tabela.columns) or tabela[list(colunas)].isna().any().any():
        raise ValueError("divisao precisa de seriesuid, paciente, subset e particao sem vazios")
    if tabela.seriesuid.duplicated().any():
        raise ValueError("exame duplicado na divisao")
    if not {"treino", "validacao"}.issubset(set(tabela.particao)) or not set(tabela.particao).issubset({"treino", "validacao", "teste"}):
        raise ValueError("divisao precisa conter treino e validacao, com teste opcional")
    if tabela.groupby("paciente").particao.nunique().gt(1).any():
        raise ValueError("paciente compartilhado entre particoes")


def ler_exame(pasta, uid, candidatos, tamanho):
    esperado = candidatos.loc[candidatos.seriesuid.eq(uid)]
    if esperado.empty:
        raise ValueError(f"exame sem candidatos: {uid}")
    with np.load(Path(pasta) / f"{uid}.npz", allow_pickle=False) as dados:
        if not np.array_equal(dados["candidate_id"], esperado.index.to_numpy()):
            raise ValueError(f"candidate_id diverge da lista V2: {uid}")
        for nome in ("coordX", "coordY", "coordZ"):
            if not np.array_equal(dados[nome], esperado[nome].to_numpy(dtype=np.float32)):
                raise ValueError(f"{nome} diverge da lista V2: {uid}")
        if not np.array_equal(dados["classe_luna16"], esperado["class"].to_numpy()):
            raise ValueError(f"classes divergem da lista V2: {uid}")
        cubos = dados["patches"]
        if (cubos.shape != (len(esperado), 34, 34, 34) or cubos.dtype != np.float32
                or not np.isfinite(cubos).all() or cubos.min() < 0 or cubos.max() > 1):
            raise ValueError(f"recortes invalidos: {uid}")
    if tamanho not in (32, 34):
        raise ValueError("entrada da CNN precisa ser 32 ou 34 voxels")
    margem = (34 - tamanho) // 2
    # Centro 17 do recorte original passa a 16 no cubo de 32.
    cubos = cubos[:, margem:margem+tamanho, margem:margem+tamanho, margem:margem+tamanho]
    return np.ascontiguousarray(cubos), esperado


def selecionar_treino(candidatos, divisao, proporcao, semente):
    uids = divisao.loc[divisao.particao.eq("treino"), "seriesuid"]
    dados = candidatos.loc[candidatos.seriesuid.isin(uids)]
    positivos = dados.loc[dados["class"].eq(1)]
    negativos = dados.loc[dados["class"].eq(0)]
    if positivos.empty or negativos.empty:
        raise ValueError("treino precisa das duas classes")
    negativos = negativos.sample(n=min(len(negativos), len(positivos) * proporcao),
                                 random_state=semente)
    selecionados = pd.concat([positivos, negativos]).sort_index()
    selecionados = selecionados.copy()
    selecionados.insert(0, "candidate_id", selecionados.index)
    return selecionados


def aumentar(cubos, gerador):
    """Espelha cada cubo ao acaso nos três eixos e gira o lote em múltiplos de 90 graus no plano axial."""
    for eixo in (2, 3, 4):
        espelhar = torch.rand(len(cubos), generator=gerador, device=cubos.device) < 0.5
        cubos = torch.where(espelhar[:, None, None, None, None], cubos.flip(eixo), cubos)
    voltas = int(torch.randint(4, (1,), generator=gerador, device=cubos.device))
    return torch.rot90(cubos, voltas, dims=(3, 4))


def treinar(candidatos, divisao, pasta, parametros, semente, device, registrar):
    selecionados = selecionar_treino(candidatos, divisao, parametros["negativos_por_positivo"], semente)
    blocos, rotulos = [], []
    for uid in sorted(selecionados.seriesuid.unique()):
        cubos, grupo = ler_exame(pasta, uid, candidatos, parametros["patch_size"])
        mascara = grupo.index.isin(selecionados.index)
        blocos.append(cubos[mascara])
        rotulos.append(grupo.loc[mascara, "class"].to_numpy(dtype=np.int64))
    x = torch.from_numpy(np.concatenate(blocos)).unsqueeze(1)
    y = torch.from_numpy(np.concatenate(rotulos))
    contagem = np.bincount(y.numpy(), minlength=2)
    gerador = torch.Generator().manual_seed(semente)
    sampler = WeightedRandomSampler(1.0 / contagem[y.numpy()], len(y), replacement=True,
                                    generator=gerador)
    loader = DataLoader(TensorDataset(x, y), batch_size=parametros["batch_size"],
                        sampler=sampler, num_workers=0, generator=gerador)
    modelo = CNN3D(parametros["dropout_rate"]).to(device)
    otimizador = torch.optim.Adam(modelo.parameters(), lr=parametros["learning_rate"],
                                 weight_decay=parametros["weight_decay"])
    criterio = nn.CrossEntropyLoss()
    gerador_aumento = None
    if parametros.get("aumento", False):
        gerador_aumento = torch.Generator(device=device).manual_seed(semente)
    historico = []
    for epoca in range(1, parametros["epochs"] + 1):
        modelo.train()
        perda, total = 0.0, 0
        for cubos, classes in loader:
            cubos, classes = cubos.to(device), classes.to(device)
            if gerador_aumento is not None:
                cubos = aumentar(cubos, gerador_aumento)
            otimizador.zero_grad()
            logits = modelo(cubos)
            loss = criterio(logits, classes)
            loss.backward()
            otimizador.step()
            perda += loss.item() * len(classes)
            total += len(classes)
        linha = {"epoch": epoca, "train_loss": perda / total}
        historico.append(linha)
        registrar(linha)
    return modelo, selecionados, pd.DataFrame(historico)


def prever(modelo, candidatos, divisao, particao, pasta, parametros, device):
    modelo.eval()
    saidas = []
    for uid in sorted(divisao.loc[divisao.particao.eq(particao), "seriesuid"]):
        cubos, grupo = ler_exame(pasta, uid, candidatos, parametros["patch_size"])
        probabilidades = pontuar(modelo, cubos, parametros["batch_size"], device)
        saida = grupo[["seriesuid", "coordX", "coordY", "coordZ", "class"]].copy()
        saida.insert(0, "candidate_id", grupo.index)
        saida["probability"] = probabilidades
        saidas.append(saida)
    resultado = pd.concat(saidas).reset_index(drop=True)
    if not np.isfinite(resultado.probability).all() or not resultado.probability.between(0, 1).all():
        raise ValueError("probabilidades invalidas")
    return resultado


def pontuar(modelo, cubos, lote, device):
    """Probabilidade de nódulo de cada cubo, com o modelo em modo de avaliação."""
    modelo.eval()
    probabilidades = []
    with torch.inference_mode():
        for inicio in range(0, len(cubos), lote):
            parte = torch.from_numpy(cubos[inicio:inicio+lote]).unsqueeze(1)
            logits = modelo(parte.to(device))
            probabilidades.extend(torch.softmax(logits, dim=1)[:, 1].cpu().numpy())
    return probabilidades


def hash_pesos(modelo):
    resumo = hashlib.sha256()
    for nome, tensor in sorted(modelo.state_dict().items()):
        resumo.update(nome.encode())
        resumo.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return resumo.hexdigest()


def conferir_origem(pasta, volumes, exames):
    for uid in exames:
        with np.load(Path(pasta) / f"{uid}.npz", allow_pickle=False) as dados:
            if "procedencia" not in dados:
                raise ValueError(f"recortes sem procedencia: {uid}; execute a extracao atualizada")
            if json.loads(str(dados["procedencia"])) != assinatura(Path(volumes) / f"{uid}.mha", (34, 34, 34)):
                raise ValueError(f"recortes desatualizados: {uid}; execute a extracao novamente")
