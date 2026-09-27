#!/bin/bash

echo "Demarrage de Career Intelligence AI..."

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd ~/career-intelligence-ai
source .venv/bin/activate

cd backend
uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload &
FASTAPI_PID=$!
echo "FastAPI demarre (PID: $FASTAPI_PID)"

sleep 3

nvm use 22

cd ~/career-intelligence-ai
n8n start &
N8N_PID=$!
echo "n8n demarre (PID: $N8N_PID)"

echo ""
echo "Tout est lance !"
echo "FastAPI : http://127.0.0.1:8000"
echo "n8n     : http://localhost:5678"
echo ""
echo "Pour tout arreter, ferme cette fenetre ou appuie sur Ctrl+C"

wait
