# Calibração exploratória do LoG

Protocolo registrado em 20/09/2026, antes da comparação, por
`.venv/bin/python scripts/12_calibrar_detector.py --preparar`.

Comparamos quatro configurações em uma amostra fixa. A configuração `inicial` reproduz
os parâmetros de partida no ambiente atual. As outras elevam o limiar para 0,15 ou 0,20,
ou ampliam a escala máxima para sigma 9 com limiar 0,15. A grade está em
`configuracao/config.yaml`, seção `calibracao_log`. Os parâmetros usados pelo script de
produção, em `deteccao.blob_log`, permanecem separados desta grade.

## Separação dos pacientes

Para este experimento, usamos os subsets 0 a 6 para desenvolvimento, o 7 para validação
e os subsets 8 e 9 como teste reservado. São 623 exames de 622 pacientes no desenvolvimento,
89 exames de 89 pacientes na validação e 176 exames de 176 pacientes no teste.
O manifesto `dados/intermediario/calibracao_log/divisao.csv` registra as 888 séries.

As duas séries do paciente descrito na decisão 0003 permanecem no desenvolvimento,
nos subsets originais 2 e 6. Nenhum paciente atravessa partições nesta separação.
Esta é uma separação fixa para o experimento, não uma execução da validação cruzada
nas dez dobras. Em 28/09/2026, essa separação passou a ser a divisão fixa dos modelos,
conforme `docs/decisoes/0003-um-paciente-em-duas-dobras.md`.

Sorteamos, com semente 42, dois exames com nódulo e um sem nódulo de cada subset de
desenvolvimento. A comparação usa 21 exames com 23 nódulos de referência. Para a
validação, sorteamos oito exames com nódulo e quatro sem nódulo, totalizando 12 exames
com 11 nódulos. `amostra.csv` registra a seleção antes de executar o detector.
Os exames de teste não entram nessa amostra nem na escolha de parâmetros.

## Regra de escolha

Escolhemos a configuração com menos candidatos que preserve todos os nódulos alcançados
pela configuração inicial no desenvolvimento. Manter apenas a mesma quantidade de
nódulos não basta: perder um nódulo e encontrar outro reprova esse critério.
Sem redução de candidatos, conservamos a configuração inicial.

Congelamos a escolha em `escolha_desenvolvimento.json` antes de abrir os volumes de
validação. Comparamos apenas essa configuração e a inicial na validação. Registramos
se a redução se manteve sem perder acertos, sem tentar outros parâmetros após observar
a validação. Uma configuração com falhas ou exames faltando não pode vencer.

## Medições e limites

Registramos candidatos por exame, cobertura dos nódulos de referência e tempo de execução.
Cada nódulo conta uma única vez para a cobertura, pelo critério já implementado em
`src/detection/candidatos.py`. A conversão de coordenadas usa a geometria do volume
pré-processado em `src/detection/blobs.py`.

Os intervalos de confiança de 95% usam 1.000 reamostras de pacientes. As séries de um
mesmo paciente permanecem juntas em cada reamostra. Exames sem nódulos entram na média
de candidatos. As quantidades absolutas são contagens da amostra, não estimativas
do total de candidatos na base inteira.

A amostra é pequena e estratificada pela presença de nódulo. A cobertura e a média
de candidatos descrevem essa amostra; não são estimativas finais sobre os 888 exames.
Os intervalos de desenvolvimento não corrigem o viés de escolher a melhor configuração
no mesmo conjunto. A validação é a conferência separada dessa escolha.

Candidatos por exame não são falsos positivos por exame. Esta rodada não calcula FROC,
não trata as anotações excluídas da avaliação oficial e não verifica a meta de 4 FP/exame.
Uma cobertura de 100% numa amostra pequena também não demonstra sensibilidade de 100%
no teste.

A inspeção dos diâmetros das anotações ligadas a `amostra.csv` em 20/09/2026 encontrou
mínimo de 4,11 mm no desenvolvimento e 4,96 mm na validação. Não há nódulos de 3 a 4 mm
nesta amostra. A medição foi feita juntando `annotations.csv` com `amostra.csv` por
`seriesuid` e calculando o mínimo de `diameter_mm` em cada partição. Essa faixa menor
permanece sem verificação nesta calibração.

## Resultado

As 108 execuções terminaram sem falhas: quatro configurações em 21 exames de
desenvolvimento e duas configurações em 12 exames de validação. Os arquivos
`resultados_por_exame.csv`, `falhas_desenvolvimento.csv` e `falhas_validacao.csv`
registram essa contagem.

| Partição | Configuração | Candidatos por exame, IC 95% | Redução | Cobertura, IC 95% | Tempo por exame |
|---|---|---:|---:|---:|---:|
| Desenvolvimento | sigma 1 a 5, limiar 0,10 | 14.923,3, 13.324,2 a 16.700,4 | referência | 23/23, 100%, 100% a 100% | 27,4 s |
| Desenvolvimento | sigma 1 a 5, limiar 0,15 | 9.331,2, 8.362,4 a 10.431,2 | 37,5% | 23/23, 100%, 100% a 100% | 25,4 s |
| Desenvolvimento | sigma 1 a 9, limiar 0,15 | 9.284,3, 8.300,0 a 10.370,5 | 37,8% | 23/23, 100%, 100% a 100% | 60,5 s |
| Desenvolvimento | sigma 1 a 5, limiar 0,20 | 4.645,0, 3.999,9 a 5.309,6 | 68,9% | 23/23, 100%, 100% a 100% | 24,4 s |
| Validação | sigma 1 a 5, limiar 0,10 | 16.258,8, 14.731,6 a 17.718,9 | referência | 11/11, 100%, 100% a 100% | 26,4 s |
| Validação | sigma 1 a 5, limiar 0,20 | 5.354,2, 4.440,6 a 6.366,0 | 67,1% | 10/11, 90,9%, 72,7% a 100% | 24,1 s |

No desenvolvimento, o limiar 0,20 reduziu a contagem de 313.390 para 97.544 candidatos
e preservou os 23 nódulos, por isso foi a configuração congelada para a validação. Na
validação, a contagem caiu de 195.105 para 64.250, mas a cobertura passou de 11 para 10
nódulos. O nódulo perdido tem o identificador 505 em `cobertura_por_nodulo.csv`, pertence
ao exame `1.3.6.1.4.1.14519.5.2.1.6279.6001.219618492426142913407827034169` e media
4,96 mm na conferência de 20/09/2026. Era o menor nódulo da validação.

O critério definido antes da comparação reprova o limiar 0,20 porque ele perdeu um
nódulo que a configuração inicial alcançava. Mantivemos `threshold: 0.1` em
`deteccao.blob_log`. O conjunto de teste continuou reservado e não ajustamos outra
configuração depois de observar a validação.

## Reprodução

```
.venv/bin/python -m pytest testes/test_calibracao.py testes/test_blobs.py testes/test_candidatos.py testes/test_divisao.py -q
.venv/bin/python scripts/12_calibrar_detector.py --preparar
.venv/bin/python -u scripts/12_calibrar_detector.py
```

As saídas ficam em `dados/intermediario/calibracao_log/`, fora do Git. O script preserva
`dados/intermediario/candidatos.csv` e o relatório da rodada anterior.
Cada comparação concluída ganha um JSON por exame e configuração, permitindo retomada.
O protocolo inclui hashes dos volumes selecionados, das anotações, do mapa de pacientes
e do código, além das versões das bibliotecas. A retomada recusa entradas ou protocolo
diferentes dos registrados.

`resultados_por_exame.csv` e `cobertura_por_nodulo.csv` guardam as medições individuais.
`resumo.csv` contém a agregação e os intervalos de confiança.
`conclusao.json` registra a configuração escolhida no desenvolvimento e o resultado
da conferência na validação. Os arquivos `falhas_desenvolvimento.csv` e
`falhas_validacao.csv` registram erros de execução. Os parâmetros de produção não são
alterados automaticamente pelo experimento.
