# Epic 05: Deploy Automatizado

## Objetivo

Criar scripts e processos para deploy seguro, rapido e com capacidade de rollback.

---

## Stories

| ID | Story | Status |
|----|-------|--------|
| S12.E5.1 | Script de deploy | 🔴 |
| S12.E5.2 | Script de rollback | 🔴 |
| S12.E5.3 | Backup automatico | 🔴 |
| S12.E5.4 | Runbook de operacoes | 🔴 |

---

## S12.E5.1 - Script de Deploy

### Objetivo
Criar script que automatiza o processo de deploy com zero downtime.

### Contexto
O script deve fazer pull do codigo, rebuild das imagens e restart dos containers de forma segura.

### Pre-requisitos
- Epic 04 completo

### Tarefas

1. **Criar script de deploy**
```bash
cat > /opt/julia/scripts/deploy.sh << 'EOF'
#!/bin/bash
set -e

# =============================================
# Script de Deploy - Agente Julia
# =============================================
# Uso: ./deploy.sh [--skip-backup] [--force]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/var/log/julia-deploy.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funcoes auxiliares
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    notify_slack "❌ Deploy FALHOU: $1"
    exit 1
}

notify_slack() {
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$1\"}" \
            "$SLACK_WEBHOOK" > /dev/null
    fi
}

# Parse argumentos
SKIP_BACKUP=false
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-backup) SKIP_BACKUP=true; shift ;;
        --force) FORCE=true; shift ;;
        *) error "Argumento desconhecido: $1" ;;
    esac
done

# Inicio
log "========================================="
log "Iniciando deploy do Agente Julia"
log "========================================="
notify_slack "🚀 Iniciando deploy do Agente Julia..."

cd "$PROJECT_DIR"

# 1. Verificar se ha mudancas locais
if [ "$FORCE" = false ]; then
    if [ -n "$(git status --porcelain)" ]; then
        error "Ha mudancas locais nao commitadas. Use --force para ignorar."
    fi
fi

# 2. Backup antes do deploy
if [ "$SKIP_BACKUP" = false ]; then
    log "Executando backup pre-deploy..."
    if [ -f "$SCRIPT_DIR/backup-volumes.sh" ]; then
        "$SCRIPT_DIR/backup-volumes.sh" || warn "Backup falhou, continuando..."
    fi
fi

# 3. Salvar versao atual para rollback
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "$CURRENT_COMMIT" > "$PROJECT_DIR/.last-deploy-commit"
log "Versao atual: $CURRENT_COMMIT"

# 4. Pull das mudancas
log "Baixando ultimas mudancas..."
git fetch origin
git pull origin main || error "Falha no git pull"

NEW_COMMIT=$(git rev-parse HEAD)
if [ "$CURRENT_COMMIT" = "$NEW_COMMIT" ]; then
    log "Nenhuma mudanca detectada. Forcando rebuild mesmo assim..."
fi

# 5. Build das imagens
log "Buildando imagens Docker..."
docker compose -f "$COMPOSE_FILE" build --no-cache julia-api || error "Falha no build"

# 6. Parar worker e scheduler primeiro (evita jobs em andamento)
log "Parando workers..."
docker compose -f "$COMPOSE_FILE" stop julia-worker julia-scheduler || true

# 7. Aguardar jobs em andamento
log "Aguardando 10 segundos para jobs finalizarem..."
sleep 10

# 8. Deploy rolling da API
log "Atualizando Julia API..."
docker compose -f "$COMPOSE_FILE" up -d --no-deps julia-api || error "Falha ao atualizar julia-api"

# 9. Aguardar API ficar healthy
log "Aguardando Julia API ficar healthy..."
MAX_WAIT=60
WAIT_COUNT=0
until docker compose -f "$COMPOSE_FILE" ps julia-api | grep -q "healthy"; do
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -gt $MAX_WAIT ]; then
        error "Julia API nao ficou healthy em ${MAX_WAIT}s. Iniciando rollback..."
    fi
    echo -n "."
    sleep 1
done
echo ""
log "Julia API esta healthy!"

# 10. Reiniciar workers
log "Reiniciando workers..."
docker compose -f "$COMPOSE_FILE" up -d julia-worker julia-scheduler

# 11. Verificacao final
log "Verificando saude dos servicos..."
sleep 5

HEALTH=$(curl -sf http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "FALHA")
if [ "$HEALTH" != "healthy" ]; then
    error "Health check falhou apos deploy!"
fi

# 12. Limpar imagens antigas
log "Limpando imagens antigas..."
docker image prune -f > /dev/null

# Sucesso
log "========================================="
log "Deploy concluido com sucesso!"
log "Commit: $NEW_COMMIT"
log "========================================="
notify_slack "✅ Deploy concluido com sucesso! Commit: ${NEW_COMMIT:0:8}"
EOF

chmod +x /opt/julia/scripts/deploy.sh
```

2. **Testar script de deploy**
```bash
# Dry run (apenas verificar)
cd /opt/julia
git status  # Verificar se esta limpo

# Executar deploy
./scripts/deploy.sh
```

### Como Testar
```bash
# Verificar script
cat /opt/julia/scripts/deploy.sh | head -50

# Executar deploy real
cd /opt/julia
./scripts/deploy.sh

# Verificar logs
tail -50 /var/log/julia-deploy.log
```

### DoD
- [ ] Script deploy.sh criado
- [ ] Script executavel
- [ ] Deploy funciona sem erros
- [ ] Notificacao Slack enviada
- [ ] Log de deploy criado
- [ ] Health check pos-deploy passa

---

## S12.E5.2 - Script de Rollback

### Objetivo
Criar script para reverter rapidamente para versao anterior em caso de problemas.

### Contexto
Rollback e critico para minimizar downtime quando um deploy da problema.

### Pre-requisitos
- S12.E5.1 completo

### Tarefas

1. **Criar script de rollback**
```bash
cat > /opt/julia/scripts/rollback.sh << 'EOF'
#!/bin/bash
set -e

# =============================================
# Script de Rollback - Agente Julia
# =============================================
# Uso: ./rollback.sh [commit-hash]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/var/log/julia-deploy.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

notify_slack() {
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$1\"}" \
            "$SLACK_WEBHOOK" > /dev/null
    fi
}

cd "$PROJECT_DIR"

# Determinar commit para rollback
if [ -n "$1" ]; then
    TARGET_COMMIT="$1"
elif [ -f ".last-deploy-commit" ]; then
    TARGET_COMMIT=$(cat .last-deploy-commit)
else
    error "Nenhum commit especificado e .last-deploy-commit nao existe"
fi

CURRENT_COMMIT=$(git rev-parse HEAD)

log "========================================="
log "Iniciando ROLLBACK do Agente Julia"
log "========================================="
log "De: $CURRENT_COMMIT"
log "Para: $TARGET_COMMIT"
notify_slack "⚠️ Iniciando ROLLBACK do Agente Julia para ${TARGET_COMMIT:0:8}..."

# Confirmar
read -p "Confirmar rollback? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Rollback cancelado pelo usuario"
    exit 0
fi

# 1. Checkout do commit anterior
log "Revertendo codigo..."
git checkout "$TARGET_COMMIT" || error "Falha ao checkout $TARGET_COMMIT"

# 2. Rebuild
log "Rebuildando imagens..."
docker compose -f "$COMPOSE_FILE" build julia-api || error "Falha no build"

# 3. Parar workers
log "Parando workers..."
docker compose -f "$COMPOSE_FILE" stop julia-worker julia-scheduler || true
sleep 5

# 4. Atualizar API
log "Atualizando Julia API..."
docker compose -f "$COMPOSE_FILE" up -d --no-deps julia-api

# 5. Aguardar healthy
log "Aguardando Julia API..."
MAX_WAIT=60
WAIT_COUNT=0
until docker compose -f "$COMPOSE_FILE" ps julia-api | grep -q "healthy"; do
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -gt $MAX_WAIT ]; then
        error "API nao ficou healthy. Rollback pode ter falhado!"
    fi
    sleep 1
done

# 6. Reiniciar workers
log "Reiniciando workers..."
docker compose -f "$COMPOSE_FILE" up -d julia-worker julia-scheduler

# 7. Verificar saude
sleep 5
HEALTH=$(curl -sf http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "FALHA")
if [ "$HEALTH" != "healthy" ]; then
    error "Health check falhou apos rollback!"
fi

log "========================================="
log "ROLLBACK concluido com sucesso!"
log "Agora em: $TARGET_COMMIT"
log "========================================="
notify_slack "✅ ROLLBACK concluido! Agora em: ${TARGET_COMMIT:0:8}"

# Voltar para main (detached HEAD)
log "ATENCAO: Voce esta em detached HEAD. Para voltar: git checkout main"
EOF

chmod +x /opt/julia/scripts/rollback.sh
```

2. **Criar script para listar deploys anteriores**
```bash
cat > /opt/julia/scripts/list-deploys.sh << 'EOF'
#!/bin/bash
# Lista os ultimos 10 deploys

echo "Ultimos 10 commits (possiveis pontos de rollback):"
echo "=================================================="
git log --oneline -10
echo ""
echo "Ultimo deploy registrado:"
if [ -f ".last-deploy-commit" ]; then
    cat .last-deploy-commit
else
    echo "Nenhum registro encontrado"
fi
EOF

chmod +x /opt/julia/scripts/list-deploys.sh
```

### Como Testar
```bash
# Listar commits disponiveis
./scripts/list-deploys.sh

# Testar rollback (apenas se necessario)
# ./scripts/rollback.sh <commit-hash>
```

### DoD
- [ ] Script rollback.sh criado
- [ ] Script executavel
- [ ] Confirmacao antes de executar
- [ ] Notificacao Slack enviada
- [ ] Script list-deploys.sh criado
- [ ] Rollback testado (dry-run ou real)

---

## S12.E5.3 - Backup Automatico

### Objetivo
Configurar backups automaticos diarios dos volumes e banco de dados.

### Contexto
Backups sao essenciais para disaster recovery. Vamos fazer backup diario e manter 7 dias.

### Pre-requisitos
- S12.E5.2 completo

### Tarefas

1. **Melhorar script de backup**
```bash
cat > /opt/julia/scripts/backup-full.sh << 'EOF'
#!/bin/bash
set -e

# =============================================
# Backup Completo - Agente Julia
# =============================================

BACKUP_DIR="/opt/backups/julia"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7
LOG_FILE="/var/log/julia-backup.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

notify_slack() {
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$1\"}" \
            "$SLACK_WEBHOOK" > /dev/null
    fi
}

# Criar diretorio se nao existir
mkdir -p "$BACKUP_DIR"

log "Iniciando backup completo..."

# 1. Backup dos volumes Docker
log "Backupando volumes..."

# Redis
docker run --rm \
    -v julia-redis-data:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/redis_${DATE}.tar.gz" -C /data . 2>/dev/null || log "WARN: Falha backup Redis"

# Evolution instances
docker run --rm \
    -v julia-evolution-instances:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/evolution_instances_${DATE}.tar.gz" -C /data . 2>/dev/null || log "WARN: Falha backup Evolution instances"

# Evolution store
docker run --rm \
    -v julia-evolution-store:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/evolution_store_${DATE}.tar.gz" -C /data . 2>/dev/null || log "WARN: Falha backup Evolution store"

# Chatwoot storage
docker run --rm \
    -v julia-chatwoot-storage:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/chatwoot_storage_${DATE}.tar.gz" -C /data . 2>/dev/null || log "WARN: Falha backup Chatwoot"

# Prometheus data
docker run --rm \
    -v julia-prometheus-data:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/prometheus_${DATE}.tar.gz" -C /data . 2>/dev/null || log "WARN: Falha backup Prometheus"

# Grafana data
docker run --rm \
    -v julia-grafana-data:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/grafana_${DATE}.tar.gz" -C /data . 2>/dev/null || log "WARN: Falha backup Grafana"

# 2. Backup do .env (sem segredos em texto claro - apenas referencia)
log "Backupando configuracoes..."
cp /opt/julia/.env "$BACKUP_DIR/env_${DATE}.bak"
chmod 600 "$BACKUP_DIR/env_${DATE}.bak"

# 3. Backup do codigo (git bundle)
log "Criando git bundle..."
cd /opt/julia
git bundle create "$BACKUP_DIR/repo_${DATE}.bundle" --all 2>/dev/null || log "WARN: Falha git bundle"

# 4. Limpar backups antigos
log "Removendo backups com mais de ${RETENTION_DAYS} dias..."
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.bak" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.bundle" -mtime +$RETENTION_DAYS -delete

# 5. Calcular tamanho total
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log "Backup concluido!"
log "Tamanho total: $TOTAL_SIZE"
log "Arquivos:"
ls -lh "$BACKUP_DIR"/*_${DATE}* 2>/dev/null || true

notify_slack "💾 Backup diario concluido. Tamanho: $TOTAL_SIZE"
EOF

chmod +x /opt/julia/scripts/backup-full.sh
```

2. **Configurar cron para backup diario**
```bash
# Backup diario as 3h da manha
(crontab -l 2>/dev/null | grep -v "backup-full.sh"; echo "0 3 * * * /opt/julia/scripts/backup-full.sh >> /var/log/julia-backup.log 2>&1") | crontab -
```

3. **Criar script de restore**
```bash
cat > /opt/julia/scripts/restore.sh << 'EOF'
#!/bin/bash
set -e

# =============================================
# Restore de Backup - Agente Julia
# =============================================
# Uso: ./restore.sh <data> [volume]
# Exemplo: ./restore.sh 20241215_030000 redis

BACKUP_DIR="/opt/backups/julia"

if [ -z "$1" ]; then
    echo "Uso: $0 <data> [volume]"
    echo "Datas disponiveis:"
    ls "$BACKUP_DIR"/*.tar.gz 2>/dev/null | sed 's/.*_//' | sed 's/.tar.gz//' | sort -u
    exit 1
fi

DATE=$1
VOLUME=${2:-"all"}

echo "ATENCAO: Isso vai SOBRESCREVER os dados atuais!"
read -p "Continuar? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

restore_volume() {
    local name=$1
    local file="$BACKUP_DIR/${name}_${DATE}.tar.gz"

    if [ ! -f "$file" ]; then
        echo "Arquivo nao encontrado: $file"
        return 1
    fi

    echo "Restaurando $name..."
    docker run --rm \
        -v "julia-${name}:/data" \
        -v "$BACKUP_DIR":/backup \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/${name}_${DATE}.tar.gz -C /data"
    echo "$name restaurado!"
}

if [ "$VOLUME" = "all" ]; then
    restore_volume "redis-data"
    restore_volume "evolution-instances"
    restore_volume "evolution-store"
    restore_volume "chatwoot-storage"
    echo "Todos os volumes restaurados. Reinicie os containers!"
else
    restore_volume "$VOLUME"
fi
EOF

chmod +x /opt/julia/scripts/restore.sh
```

4. **Testar backup**
```bash
# Executar backup manualmente
./scripts/backup-full.sh

# Verificar arquivos criados
ls -lh /opt/backups/julia/
```

### Como Testar
```bash
# Verificar cron configurado
crontab -l | grep backup

# Executar backup manual
/opt/julia/scripts/backup-full.sh

# Verificar backups
ls -lh /opt/backups/julia/

# Verificar log
tail -20 /var/log/julia-backup.log
```

### DoD
- [ ] Script backup-full.sh criado
- [ ] Script restore.sh criado
- [ ] Cron configurado para 3h diario
- [ ] Backup testado manualmente
- [ ] Retencao de 7 dias funcionando
- [ ] Notificacao Slack de backup

---

## S12.E5.4 - Runbook de Operacoes

### Objetivo
Documentar procedimentos operacionais para manutencao e troubleshooting.

### Contexto
Runbook e um documento vivo com todos os comandos e procedimentos para operar o sistema.

### Pre-requisitos
- S12.E5.3 completo

### Tarefas

1. **Criar RUNBOOK.md**
```bash
cat > /opt/julia/RUNBOOK.md << 'EOF'
# Runbook - Agente Julia em Producao

## Informacoes do Ambiente

| Item | Valor |
|------|-------|
| Servidor | julia.seudominio.com.br |
| IP | XXX.XXX.XXX.XXX |
| Usuario SSH | deploy |
| Diretorio | /opt/julia |
| Compose File | docker-compose.prod.yml |

---

## Comandos Rapidos

### Status dos Servicos
```bash
cd /opt/julia
docker compose -f docker-compose.prod.yml ps
```

### Ver Logs
```bash
# Todos os servicos
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Servico especifico
docker compose -f docker-compose.prod.yml logs -f julia-api
docker compose -f docker-compose.prod.yml logs -f julia-worker
docker compose -f docker-compose.prod.yml logs -f evolution-api
```

### Reiniciar Servico
```bash
docker compose -f docker-compose.prod.yml restart julia-api
docker compose -f docker-compose.prod.yml restart julia-worker
```

### Parar Tudo
```bash
docker compose -f docker-compose.prod.yml down
```

### Iniciar Tudo
```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## Procedimentos

### Deploy de Nova Versao
```bash
cd /opt/julia
./scripts/deploy.sh
```

### Rollback
```bash
# Listar versoes disponiveis
./scripts/list-deploys.sh

# Rollback para commit especifico
./scripts/rollback.sh <commit-hash>
```

### Backup Manual
```bash
./scripts/backup-full.sh
```

### Restore de Backup
```bash
# Listar backups disponiveis
ls /opt/backups/julia/

# Restaurar todos os volumes
./scripts/restore.sh 20241215_030000

# Reiniciar apos restore
docker compose -f docker-compose.prod.yml restart
```

---

## Troubleshooting

### Container reiniciando em loop
```bash
# Ver logs do container
docker compose -f docker-compose.prod.yml logs julia-api --tail=100

# Causas comuns:
# 1. Variavel de ambiente faltando no .env
# 2. Servico dependente nao esta rodando
# 3. Erro de codigo

# Verificar .env
cat .env | grep -E "^[A-Z]"
```

### Julia API retornando 502
```bash
# Verificar se container esta rodando
docker compose -f docker-compose.prod.yml ps julia-api

# Verificar health
curl http://localhost:8000/health

# Ver logs
docker compose -f docker-compose.prod.yml logs julia-api --tail=50
```

### Evolution nao conecta WhatsApp
```bash
# Verificar status
curl http://localhost:8080/instance/connectionState/Revoluna

# Gerar novo QR Code
curl -X GET http://localhost:8080/instance/connect/Revoluna

# Ver logs
docker compose -f docker-compose.prod.yml logs evolution-api --tail=50
```

### Redis cheio / lento
```bash
# Ver uso de memoria
docker exec julia-redis redis-cli INFO memory | grep used_memory_human

# Limpar cache (CUIDADO!)
docker exec julia-redis redis-cli FLUSHDB
```

### Disco cheio
```bash
# Ver uso de disco
df -h

# Limpar logs antigos
sudo find /var/log -name "*.log" -mtime +7 -delete

# Limpar imagens Docker antigas
docker system prune -a --volumes
```

### Certificado SSL expirado
```bash
# Renovar certificado
sudo certbot renew

# Verificar validade
echo | openssl s_client -servername julia.seudominio.com.br -connect julia.seudominio.com.br:443 2>/dev/null | openssl x509 -noout -dates
```

---

## Monitoramento

### Dashboards
- Grafana: https://julia.seudominio.com.br/grafana
- Usuario: admin
- Senha: (ver .env GRAFANA_PASSWORD)

### Alertas
- Canal Slack: #julia-alertas
- Alertas criticos notificam imediatamente

### Health Checks
```bash
# Julia API
curl https://julia.seudominio.com.br/health

# Evolution
curl https://julia.seudominio.com.br/evolution/

# Prometheus
curl http://localhost:9090/-/healthy
```

---

## Contatos

| Funcao | Nome | Contato |
|--------|------|---------|
| DevOps | - | - |
| Backend | - | - |
| Gestor | - | - |

---

## Historico de Incidentes

| Data | Incidente | Resolucao |
|------|-----------|-----------|
| - | - | - |

EOF
```

2. **Criar scripts utilitarios finais**
```bash
# Script de status rapido
cat > /opt/julia/scripts/status.sh << 'EOF'
#!/bin/bash
echo "=== Status Julia Production ==="
echo ""
echo "Containers:"
docker compose -f /opt/julia/docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
echo ""
echo "Recursos:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "RAM: $(free -h | awk '/Mem:/ {print $3 "/" $2}')"
echo "Disco: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')"
echo ""
echo "Health Julia API:"
curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "FALHA"
EOF

chmod +x /opt/julia/scripts/status.sh
```

3. **Adicionar alias uteis**
```bash
cat >> ~/.bashrc << 'EOF'

# Aliases Julia
alias julia-logs="cd /opt/julia && docker compose -f docker-compose.prod.yml logs -f"
alias julia-status="/opt/julia/scripts/status.sh"
alias julia-deploy="/opt/julia/scripts/deploy.sh"
alias julia-restart="cd /opt/julia && docker compose -f docker-compose.prod.yml restart"
EOF

source ~/.bashrc
```

### Como Testar
```bash
# Testar script de status
/opt/julia/scripts/status.sh

# Testar aliases
julia-status
```

### DoD
- [ ] RUNBOOK.md criado
- [ ] Script status.sh criado
- [ ] Aliases configurados
- [ ] Documentacao de troubleshooting completa
- [ ] Procedimentos de deploy/rollback documentados
- [ ] Contatos preenchidos (ajustar)

---

## Resumo do Epic

| Story | Tempo Estimado | Complexidade |
|-------|----------------|--------------|
| S12.E5.1 | 45 min | Media |
| S12.E5.2 | 30 min | Media |
| S12.E5.3 | 30 min | Baixa |
| S12.E5.4 | 45 min | Baixa |
| **Total** | **~2.5h** | |

---

## Checklist Final da Sprint

Apos completar todos os epics, verificar:

- [ ] VPS provisionada e segura
- [ ] Docker e containers funcionando
- [ ] HTTPS com certificado valido
- [ ] Monitoramento ativo
- [ ] Alertas chegando no Slack
- [ ] Script de deploy funcionando
- [ ] Script de rollback testado
- [ ] Backups automaticos configurados
- [ ] Runbook documentado
- [ ] Equipe treinada nos procedimentos

**Parabens! O Agente Julia esta em producao!** 🎉
EOF
