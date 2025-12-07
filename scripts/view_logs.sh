#!/bin/bash
#
# Script para visualizar logs dos serviços Júlia
#
# Uso:
#   ./scripts/view_logs.sh          # Todos os serviços
#   ./scripts/view_logs.sh api      # Apenas API
#   ./scripts/view_logs.sh worker   # Apenas Worker
#   ./scripts/view_logs.sh scheduler # Apenas Scheduler
#   ./scripts/view_logs.sh all      # Todos (incluindo redis, evolution)

set -e

TAIL_LINES=${TAIL_LINES:-100}

show_help() {
    echo "Visualizador de logs - Agente Júlia"
    echo ""
    echo "Uso: $0 [serviço] [opções]"
    echo ""
    echo "Serviços:"
    echo "  api         Logs da API FastAPI"
    echo "  worker      Logs do worker de fila"
    echo "  scheduler   Logs do scheduler"
    echo "  julia       Todos os serviços Júlia (padrão)"
    echo "  all         Todos os serviços (inclui redis, evolution, chatwoot)"
    echo ""
    echo "Opções:"
    echo "  -f, --follow    Seguir logs em tempo real (padrão)"
    echo "  -n, --lines N   Número de linhas iniciais (padrão: 100)"
    echo "  --no-follow     Mostrar logs e sair"
    echo "  -h, --help      Mostrar esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0                    # Logs de todos os serviços Júlia"
    echo "  $0 api -n 50          # Últimas 50 linhas da API"
    echo "  $0 all --no-follow    # Todos os logs, sem seguir"
}

# Parse argumentos
SERVICE="julia"
FOLLOW="-f"

while [[ $# -gt 0 ]]; do
    case $1 in
        api|worker|scheduler|julia|all)
            SERVICE="$1"
            shift
            ;;
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        --no-follow)
            FOLLOW=""
            shift
            ;;
        -n|--lines)
            TAIL_LINES="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Definir serviços baseado na seleção
case $SERVICE in
    api)
        SERVICES="julia-api"
        ;;
    worker)
        SERVICES="julia-worker"
        ;;
    scheduler)
        SERVICES="julia-scheduler"
        ;;
    julia)
        SERVICES="julia-api julia-worker julia-scheduler"
        ;;
    all)
        SERVICES="julia-api julia-worker julia-scheduler redis evolution-api chatwoot"
        ;;
esac

echo "📋 Visualizando logs de: $SERVICES"
echo "📊 Últimas $TAIL_LINES linhas"
echo "---"

# Executar docker compose logs
docker compose logs --tail="$TAIL_LINES" $FOLLOW $SERVICES
