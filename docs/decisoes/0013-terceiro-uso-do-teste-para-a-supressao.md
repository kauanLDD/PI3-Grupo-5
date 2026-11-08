# 0013: o terceiro uso do teste, para a supressão suave a 16 mm nas duas listas

**Estado:** decidido antes de rodar
**Data:** 08/11/2026

## Contexto

A rede `cnn_lr_3e-4` foi congelada e avaliada uma vez no teste com a V2 (decisão 0008), e o Random
Forest centro usou o teste uma segunda vez (decisão 0009). Depois disso escolhemos, só na validação,
o que fazer depois da rede: supressão de vizinhos a 16 mm (decisão 0012), na forma suave linear
(`docs/19`, seção 10). Nada desta escolha usou o teste.

## Decisão

**Usamos o teste uma terceira vez, uma só, para medir o processamento congelado nas duas listas.**
O que vai ao teste está fixado antes de rodar e não muda depois de ver o resultado:

- A rede `cnn_lr_3e-4` da decisão 0008, semente 42, sem treino novo.
- A nossa lista de candidatos (LoG) nos 176 exames de teste, pontuada por essa rede.
- A supressão suave linear a 16 mm, até 100 marcas por exame (`suprimir_suave`, `config.yaml`,
  seção `supressao_suave`).
- A mesma supressão nas notas que essa rede já deu à V2 do teste em 13/10/2026
  (`modelos/cnn_lr_3e-4_teste_final/predicoes.csv`).

A nossa lista é pontuada na GPU, o mesmo aparelho da validação em que escolhemos a supressão. As
notas da V2 no teste foram calculadas na CPU em 13/10/2026 (script 20) e não são refeitas. Entre os
dois aparelhos, a nota da rede muda até 1,5e-03 (medido em 08/11/2026 nos 3 exames de conferência);
por isso a conferência do recorte roda na CPU, contra as notas gravadas, com a mesma tolerância de
1e-05. Na primeira tentativa a conferência rodou na GPU e barrou o script antes de pontuar ou avaliar
qualquer coisa.

Reportamos as duas listas com e sem supressão, com IC95% por bootstrap, e as diferenças pareadas.

## Consequências

O resultado do teste não serve para escolher mais nada: nem raio, nem forma de supressão, nem
semente. Qualquer mudança depois disto volta para a validação, e o teste já usado fica declarado
como usado.
