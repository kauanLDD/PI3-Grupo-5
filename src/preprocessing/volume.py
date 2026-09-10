"""Janela de HU, reamostragem isotrópica e aplicação da máscara de pulmão."""

import SimpleITK as sitk


def janela(imagem, hu_min: int, hu_max: int):
    return sitk.Clamp(imagem, sitk.sitkInt16, hu_min, hu_max)


def normalizar(imagem, hu_min: int, hu_max: int):
    """Mapeia a janela HU fixa para o intervalo [0, 1]."""
    escala = hu_max - hu_min
    if escala <= 0:
        raise ValueError("hu_max precisa ser maior que hu_min")
    imagem_float = sitk.Cast(imagem, sitk.sitkFloat32)
    return sitk.Clamp((imagem_float - hu_min) / escala, sitk.sitkFloat32, 0.0, 1.0)


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
    # Decisão 0002: `> 0` em vez de `== 3 ou == 4`, que recupera três nódulos.
    return sitk.Cast(mascara > 0, sitk.sitkUInt8)


def aplicar_mascara(volume, mascara, fora: float):
    return sitk.Mask(volume, mascara, outsideValue=fora)


def preprocessar(volume, mascara, hu, alvo, normalizar_0_a_1=True):
    """Janela, reamostragem e máscara. Devolve o volume e a máscara reamostrada."""
    volume_iso = reamostrar(janela(volume, *hu), alvo, sitk.sitkLinear, fundo=hu[0])
    mascara_iso = reamostrar(binarizar(mascara), alvo, sitk.sitkNearestNeighbor, fundo=0)
    if normalizar_0_a_1:
        volume_iso = normalizar(volume_iso, *hu)
        fora = 0.0
    else:
        fora = hu[0]
    return aplicar_mascara(volume_iso, mascara_iso, fora=fora), mascara_iso
