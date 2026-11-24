# 0002 - Python 3.12 com PyTorch, scikit-learn e SimpleITK

Status: Aceito
Data: 2026-11-24

Contexto
Precisávamos ler volumes MetaImage (`.mhd` e `.raw`), processar imagem 3D, treinar uma rede neural
3D e um modelo simples de comparação, e rodar o avaliador oficial do LUNA16, que é escrito em
Python.

Decisão
Usamos Python 3.12. SimpleITK lê os volumes e guarda origem e espaçamento de cada exame.
scikit-image faz a busca de candidatos por LoG. PyTorch treina a rede 3D. scikit-learn treina o
Random Forest de comparação. pytest roda os testes. As versões exatas estão nos arquivos
`requirements-*.lock.txt`; o `requirements.txt` lista os pacotes sem versão.

Consequências
Melhora: o avaliador oficial roda no mesmo ambiente do resto, adaptado para Python 3 em
`src/experimentos/avaliacao_oficial.py`, e as bibliotecas cobrem todas as etapas sem código de
outra linguagem.
Piora: o PyTorch tem uma versão para CPU e outra para CUDA. Por isso o projeto usa três ambientes
(`.venv`, `.venv-cnn` e `.venv-cnn-gpu`), o que complica a instalação.
