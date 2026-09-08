"""Janela de HU, reamostragem isotrópica, máscara de pulmão e normalização."""

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
    # Decisão 0002: `> 0` em vez de `== 3 ou == 4`, que recupera três nódulos.
    return sitk.Cast(mascara > 0, sitk.sitkUInt8)


def aplicar_mascara(volume, mascara, fora: int):
    return sitk.Mask(volume, mascara, outsideValue=fora)


def normalizar(imagem, hu_min: int, hu_max: int):
    """Leva a janela de HU para [0, 1]. O fundo fora do pulmão, que é hu_min, vira 0."""
    # Multiplica pelo inverso: dividir por escalar promove o resultado a float de 64 bits.
    return (sitk.Cast(imagem, sitk.sitkFloat32) - hu_min) * (1.0 / (hu_max - hu_min))


def preprocessar(volume, mascara, hu, alvo):
    """Janela, reamostragem, máscara e normalização. Devolve o volume em [0, 1] e a máscara."""
    volume_iso = reamostrar(janela(volume, *hu), alvo, sitk.sitkLinear, fundo=hu[0])
    mascara_iso = reamostrar(binarizar(mascara), alvo, sitk.sitkNearestNeighbor, fundo=0)
    pulmao = aplicar_mascara(volume_iso, mascara_iso, fora=hu[0])
    return normalizar(pulmao, *hu), mascara_iso
