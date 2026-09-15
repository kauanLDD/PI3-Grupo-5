# Normalização HU - Samuel Malta

## Objetivo

Padronizar as intensidades de um volume bruto de tomografia do dataset LUNA16,
aplicando uma janela de `-1000` a `400` Hounsfield Units e reescalando o
resultado para o intervalo `[0, 1]`.

## Exame utilizado

- `seriesuid`: `1.3.6.1.4.1.14519.5.2.1.6279.6001.979083010707182900091062408058`
- dimensões originais: `140 x 512 x 512` voxels em ordem z, y, x
- espaçamento original: `0,664 x 0,664 x 2,000 mm`
- intervalo original: `-3024` a `1651 HU`

## Método

1. Leitura do arquivo MetaImage com SimpleITK.
2. Conversão do volume para uma matriz NumPy em ponto flutuante de 32 bits.
3. Limitação das intensidades à janela pulmonar `[-1000, 400] HU`.
4. Normalização min-max pela expressão `(hu_limitado + 1000) / 1400`.
5. Verificação automática de valores não finitos e de valores fora de `[0, 1]`.
6. Geração de comparação visual e histogramas antes e depois do processamento.

## Resultado

Após o processamento, a intensidade mínima foi `0,000000` e a máxima foi
`1,000000`. A média do volume normalizado foi `0,408845`, com desvio padrão de
`0,331430`. A figura de evidência utiliza o corte axial 61.

O resultado confirma que valores extremos foram saturados nos limites da janela
e que todas as intensidades foram transformadas para a faixa esperada pelo
pipeline de pré-processamento.

## Execução

```bash
python scripts/11_normalizar_hu_samuel.py caminho/volume.mhd \
  --saida-imagem relatorios/figuras/normalizacao_hu_samuel.png \
  --saida-metricas relatorios/metricas/normalizacao_hu_samuel.csv
```

## Evidências

- código: `scripts/11_normalizar_hu_samuel.py`
- comparação visual: `relatorios/figuras/normalizacao_hu_samuel.png`
- métricas: `relatorios/metricas/normalizacao_hu_samuel.csv`

Esta atividade integra a etapa de pré-processamento do KDD e torna os exames
comparáveis antes da geração de candidatos a nódulos.
