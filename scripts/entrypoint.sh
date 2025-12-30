#!/bin/bash
# Entrypoint para containers Julia
# Valida RUN_MODE e executa o serviço apropriado

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Julia Entrypoint ===${NC}"
echo "RUN_MODE: ${RUN_MODE:-not set}"
echo "APP_ENV: ${APP_ENV:-not set}"

# Validar RUN_MODE obrigatório
if [ -z "$RUN_MODE" ]; then
    echo -e "${RED}ERROR: RUN_MODE environment variable is required!${NC}"
    echo ""
    echo "Valid values:"
    echo "  - api       : Run FastAPI server (uvicorn)"
    echo "  - worker    : Run ARQ worker (fila consumer)"
    echo "  - scheduler : Run APScheduler (cron jobs)"
    echo ""
    echo "Example: RUN_MODE=api"
    exit 1
fi

# Validar APP_ENV obrigatório em produção
if [ "$APP_ENV" = "production" ] && [ -z "$SUPABASE_PROJECT_REF" ]; then
    echo -e "${YELLOW}WARNING: SUPABASE_PROJECT_REF not set in production. Hard guard disabled.${NC}"
fi

# Executar baseado no RUN_MODE
case "$RUN_MODE" in
    api)
        echo -e "${GREEN}Starting API server...${NC}"
        exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
        ;;
    worker)
        echo -e "${GREEN}Starting worker...${NC}"
        exec python -m app.workers.fila_worker
        ;;
    scheduler)
        echo -e "${GREEN}Starting scheduler...${NC}"
        exec python -m app.workers.scheduler
        ;;
    *)
        echo -e "${RED}ERROR: Invalid RUN_MODE: $RUN_MODE${NC}"
        echo ""
        echo "Valid values: api, worker, scheduler"
        exit 1
        ;;
esac
