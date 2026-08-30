"""Cabeçalho dos volumes .mhd do LUNA16, sem abrir o .raw."""

from pathlib import Path

import SimpleITK as sitk

IDENTIDADE = (1, 0, 0, 0, 1, 0, 0, 0, 1)

# Tolerância para o float32 do .mhd.
TOLERANCIA = 1e-6


def pasta_do_subset(raiz: Path, subset: int) -> Path:
    # O zip do Kaggle extrai com a pasta repetida.
    return raiz / f"subset{subset}" / f"subset{subset}"


def caminho_do_volume(raiz: Path, seriesuid: str, subsets) -> Path | None:
    for subset in subsets:
        mhd = pasta_do_subset(raiz, subset) / f"{seriesuid}.mhd"
        if mhd.exists():
            return mhd
    return None


def campos_do_texto(caminho: Path) -> dict[str, str]:
    campos = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if "=" in linha:
            chave, valor = linha.split("=", 1)
            campos[chave.strip()] = valor.strip()
    return campos


def e_identidade(direcao) -> bool:
    return all(abs(a - b) <= TOLERANCIA for a, b in zip(direcao, IDENTIDADE))


def proximos(lido, escrito: str) -> bool:
    do_texto = tuple(float(v) for v in escrito.split())
    return len(lido) == len(do_texto) and all(
        abs(a - b) <= TOLERANCIA * max(1.0, abs(b)) for a, b in zip(lido, do_texto)
    )


def confere(do_leitor: dict, texto: dict, arquivo: str):
    """Estoura se o SimpleITK e o cabeçalho de texto discordarem."""
    for campo, lido in do_leitor.items():
        if not proximos(lido, texto[campo]):
            raise ValueError(f"{arquivo}: {campo} é {texto[campo]!r} no arquivo e {lido} no SimpleITK")


def por_eixo(prefixo: str, valores) -> dict:
    return {f"{prefixo}_{eixo}": valor for eixo, valor in zip("xyz", valores)}


def ler_cabecalho(caminho: Path) -> dict:
    leitor = sitk.ImageFileReader()
    leitor.SetFileName(str(caminho))
    leitor.ReadImageInformation()

    origem = leitor.GetOrigin()
    espacamento = leitor.GetSpacing()
    dim = leitor.GetSize()
    direcao = leitor.GetDirection()
    texto = campos_do_texto(caminho)

    confere(
        {
            "Offset": origem,
            "ElementSpacing": espacamento,
            "DimSize": dim,
            "TransformMatrix": direcao,
        },
        texto,
        caminho.name,
    )

    raw = caminho.with_suffix(".raw")
    return {
        "seriesuid": caminho.stem,
        **por_eixo("origem", origem),
        **por_eixo("espacamento", espacamento),
        **por_eixo("dim", dim),
        "tipo_elemento": texto["ElementType"],
        "direcao": " ".join(f"{v:.6g}" for v in direcao),
        "matriz_identidade": e_identidade(direcao),
        "orientacao": texto.get("AnatomicalOrientation"),
        "extensao_z_mm": dim[2] * espacamento[2],
        "tamanho_raw_mb": round(raw.stat().st_size / 1e6, 1) if raw.exists() else None,
    }


def inventariar(pasta: Path, subset: int) -> tuple[list[dict], list[str]]:
    """Devolve as linhas lidas e os erros."""
    linhas, erros = [], []
    for mhd in sorted(pasta.glob("*.mhd")):
        try:
            registro = ler_cabecalho(mhd)
        except (RuntimeError, ValueError, KeyError) as e:
            erros.append(f"{mhd.name}: {type(e).__name__}: {e}")
            continue
        registro["subset"] = subset
        linhas.append(registro)
    return linhas, erros
