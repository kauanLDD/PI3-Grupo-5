## PI3 Grupo 5: detecção de candidatos a nódulos pulmonares

 # A ideia
 
O câncer de pulmão mata mais que qualquer outro câncer, e o problema não é a falta de tratamento, é a demora do diagnóstico. 54% dos pacientes descobrem no estágio IV, quando cerca de 5% sobrevivem cinco anos; quem descobre no estágio I tem cerca de 70%. O sinal que apareceria cedo é o nódulo, uma estrutura de 3 a 30 mm dentro do pulmão, e ele passa batido com facilidade: um radiologista olha de 300 a 500 exames por dia, cada exame com 300 a 500 fatias, algo perto de 250 mil imagens por dia.


## Dataset

**LUNA16** (Lung Nodule Analysis 2016), derivado do LIDC-IDRI e já filtrado, com o
critério de inclusão e as dobras de validação definidos pelo próprio desafio.

| | |
|---|---|
| Exames no desafio | 888 |
| Exames em disco | 445, os subsets 0 a 4 |
| Nódulos anotados | 1.186 em 601 exames, dos quais 615 estão nos exames que temos |
| Candidatos | 551.065 com 1.351 positivos, ou 0,2452% |
| Formato | MetaImage (`.mhd` mais `.raw`), um par por exame |
| Espaçamento entre fatias | de 0,5 a 2,5 mm |
| Máscaras de pulmão | prontas, em `seg-lungs-LUNA16` |
| Avaliação | curva FROC, com o script oficial do desafio |

Os subsets 5 a 9 não foram baixados, e todo resultado nosso declara isso.

Números medidos em 26/08/2026 com `scripts/02_inventario_volumes.py` e leitura direta dos
CSVs do desafio.
