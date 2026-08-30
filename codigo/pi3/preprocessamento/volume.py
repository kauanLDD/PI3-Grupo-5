"""Janela de HU, reamostragem isotrópica e aplicação da máscara de pulmão."""

import SimpleITK as sitk


def janela(imagem, hu_min: int, hu_max: int):
    return sitk.Clamp(imagem, sitk.sitkInt16, hu_min, hu_max)


def dimensao_isotropica(imagem, alvo) -> list[int]:
    """Voxels necessários para cobrir a mesma extensão física no espaçamento alvo."""
    return [int(round(d * e / a)) for d, e, a in zip(imagem.GetSize(), imagem.GetSpacing(), alvo)]


def reamostrar(imagem, alvo, interpolador=sitk.sitkLinear, fundo: float = 0.0):
    """Reamostra para o espaçamento alvo, mantendo origem e direção."""
    return sitk.Resample(
        imagem,
        dimensao_isotropica(imagem, alvo),
        sitk.Transform(),
        interpolador,
        imagem.GetOrigin(),
        alvo,
        imagem.GetDirection(),
        fundo,
        imagem.GetPixelID(),
    )


def binarizar(mascara):
    # Decisão 0002: `> 0` em vez de `== 3 ou == 4`.
    return sitk.Cast(mascara > 0, sitk.sitkUInt8)


def aplicar_mascara(volume, mascara, fora: int):
    return sitk.Mask(volume, mascara, outsideValue=fora)


def preprocessar(volume, mascara, hu, alvo):
    """Janela, reamostragem e máscara. Devolve o volume e a máscara reamostrada."""
    volume_iso = reamostrar(janela(volume, *hu), alvo, sitk.sitkLinear, fundo=hu[0])
    mascara_iso = reamostrar(binarizar(mascara), alvo, sitk.sitkNearestNeighbor, fundo=0)
    return aplicar_mascara(volume_iso, mascara_iso, fora=hu[0]), mascara_iso
