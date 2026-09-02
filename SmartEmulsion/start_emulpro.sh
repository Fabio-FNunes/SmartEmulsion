#!/bin/bash

# Entrar na pasta onde este script está guardado
cd "$(dirname "$0")"

# Ativar o ambiente virtual (se o teu venv tiver outro nome, muda aqui)
source venv/bin/activate

# Iniciar a aplicação
python app.py
