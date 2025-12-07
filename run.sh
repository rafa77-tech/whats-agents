#!/bin/bash
# Script para rodar a aplicação

# Carregar variáveis de ambiente
set -a
source .env
set +a

# Rodar com uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
