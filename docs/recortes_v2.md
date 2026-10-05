# Recortes 3D da lista V2

Rodada concluída em 01/10/2026 no Windows, usando os volumes pré-processados
que já estavam em `G:\Meu Drive\PI3-Grupo-5\Dataset\processado\volumes`.
Os 888 nomes dos volumes correspondem aos 888 `seriesuid` do
`candidates_V2.csv`; não foi necessário repetir o pré-processamento.

| Medida | Resultado |
|---|---:|
| Exames na V2 | 888 |
| Pontos na V2 | 754.975 |
| Arquivos `.npz` válidos | 888 |
| Cubos `34 × 34 × 34` válidos | 754.975 |
| Criados no lote completo | 887 |
| Reaproveitado do teste com `--seriesuid` | 1 |
| Falhas | 0 |
| Tempo do lote completo | 7.958,47 s (2 h 12 min 38 s) |
| Tempo do teste de um exame | 7,89 s |
| Espaço dos arquivos `.npz` | 39.861.743.501 bytes (37,12 GiB) |

O exame de teste tinha 1.068 pontos. O lote completo reutilizou seu `.npz`.
Os 7.958,47 s são o tempo da execução completa, incluindo a conferência
desse arquivo existente; o teste anterior foi uma execução separada.

O script conferiu, para cada arquivo, a quantidade de cubos, o formato
`(N, 34, 34, 34)`, `float32` finito em `[0, 1]`, os IDs, as coordenadas
físicas e as classes contra as linhas correspondentes da V2. Na geração,
conferiu também que o voxel central corresponde ao ponto físico transformado
em índice do volume. Uma segunda contagem da pasta confirmou 888 arquivos,
39.861.743.501 bytes e nenhum `.tmp.npz` restante.

Arquivos produzidos:

- Recortes: `G:\Meu Drive\PI3-Grupo-5\Dataset\processado\patches`
- Resumo: `dados/intermediario/resumo_patches.json`
- Falhas: `dados/intermediario/falhas_patches.csv` (somente cabeçalho)

O `config.yaml` salvo neste checkout ainda aponta para o caminho Linux de
outro integrante. Nesta rodada, os caminhos do Windows foram passados por
`--candidatos`, `--volumes` e `--saida`. Reexecutar o mesmo comando
revalida os arquivos existentes e retoma qualquer exame faltante:

```powershell
python scripts/09_extrair_patches.py `
  --candidatos "G:\Meu Drive\PI3-Grupo-5\Dataset\candidates_V2\candidates_V2.csv" `
  --volumes "G:\Meu Drive\PI3-Grupo-5\Dataset\processado\volumes" `
  --saida "G:\Meu Drive\PI3-Grupo-5\Dataset\processado\patches"
```
