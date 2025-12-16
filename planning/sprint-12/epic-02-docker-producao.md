# Epic 02: Docker Producao

## Objetivo

Ajustar configuracoes Docker para ambiente de producao, incluindo secrets, volumes persistentes e docker-compose otimizado.

---

## Stories

| ID | Story | Status |
|----|-------|--------|
| S12.E2.1 | Criar docker-compose.prod.yml | 🔴 |
| S12.E2.2 | Configurar secrets e variaveis | 🔴 |
| S12.E2.3 | Setup volumes persistentes | 🔴 |
| S12.E2.4 | Build e primeiro deploy | 🔴 |

---

## S12.E2.1 - Criar docker-compose.prod.yml

### Objetivo
Criar versao otimizada do docker-compose para producao, removendo servicos desnecessarios e ajustando configuracoes.

### Contexto
O docker-compose.yml atual inclui servicos de desenvolvimento (pgadmin, n8n). Em producao, queremos apenas o essencial e com configuracoes de seguranca.

### Pre-requisitos
- Epic 01 completo

### Tarefas

1. **Criar docker-compose.prod.yml**
```bash
cd /opt/julia
nano docker-compose.prod.yml
```

2. **Conteudo do docker-compose.prod.yml**
```yaml
# docker-compose.prod.yml - Configuracao de Producao
# Uso: docker compose -f docker-compose.prod.yml up -d

services:
  # =========================================
  # INFRAESTRUTURA
  # =========================================

  redis:
    image: redis:7-alpine
    container_name: julia-redis
    restart: always
    command: >
      redis-server
      --port 6379
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - julia-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # =========================================
  # EVOLUTION API (WhatsApp)
  # =========================================

  evolution-api:
    image: atendai/evolution-api:latest
    container_name: julia-evolution
    restart: always
    env_file:
      - .env
    environment:
      - SERVER_URL=https://${DOMAIN}/evolution
      - CORS_ORIGIN=*
      - CORS_METHODS=GET,POST,PUT,DELETE
      - CORS_CREDENTIALS=true
      - LOG_LEVEL=ERROR
      - DEL_INSTANCE=false
      - CONFIG_SESSION_PHONE_CLIENT=Julia
      - CONFIG_SESSION_PHONE_NAME=Chrome
      - QRCODE_LIMIT=30
      - AUTHENTICATION_TYPE=apikey
      - AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY}
      - AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true
    volumes:
      - evolution_instances:/evolution/instances
      - evolution_store:/evolution/store
    networks:
      - julia-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # =========================================
  # CHATWOOT (Supervisao)
  # =========================================

  chatwoot-base: &chatwoot-base
    image: chatwoot/chatwoot:latest
    env_file: .env
    environment:
      - RAILS_ENV=production
      - NODE_ENV=production
      - INSTALLATION_ENV=docker
      - SECRET_KEY_BASE=${SECRET_KEY_BASE}
      - FRONTEND_URL=https://${DOMAIN}/chatwoot
      - REDIS_URL=redis://redis:6379
      - POSTGRES_HOST=${POSTGRES_HOST:-postgres}
      - POSTGRES_PORT=${POSTGRES_PORT:-5432}
      - POSTGRES_DATABASE=${POSTGRES_DATABASE:-chatwoot}
      - POSTGRES_USERNAME=${POSTGRES_USERNAME:-postgres}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - chatwoot_storage:/app/storage
    networks:
      - julia-net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  chatwoot:
    <<: *chatwoot-base
    container_name: julia-chatwoot
    depends_on:
      redis:
        condition: service_healthy
    entrypoint: docker/entrypoints/rails.sh
    command: ["bundle", "exec", "rails", "s", "-p", "3000", "-b", "0.0.0.0"]
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/v1/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  chatwoot-sidekiq:
    <<: *chatwoot-base
    container_name: julia-chatwoot-sidekiq
    depends_on:
      - chatwoot
    command: ["bundle", "exec", "sidekiq", "-C", "config/sidekiq.yml"]
    restart: always

  # =========================================
  # AGENTE JULIA
  # =========================================

  julia-api:
    build:
      context: .
      dockerfile: Dockerfile
    image: julia-api:latest
    container_name: julia-api
    restart: always
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - REDIS_URL=redis://redis:6379/0
      - EVOLUTION_API_URL=http://evolution-api:8080
      - CHATWOOT_URL=http://chatwoot:3000
      - JULIA_API_URL=http://julia-api:8000
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - julia-net
    volumes:
      - julia_logs:/app/logs
      - ./credentials:/app/credentials:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  julia-worker:
    build:
      context: .
      dockerfile: Dockerfile
    image: julia-api:latest
    container_name: julia-worker
    restart: always
    command: ["python", "-m", "app.workers", "fila"]
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis:6379/0
      - EVOLUTION_API_URL=http://evolution-api:8080
    depends_on:
      julia-api:
        condition: service_healthy
    networks:
      - julia-net
    volumes:
      - julia_logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  julia-scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    image: julia-api:latest
    container_name: julia-scheduler
    restart: always
    command: ["python", "-m", "app.workers", "scheduler"]
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - JULIA_API_URL=http://julia-api:8000
    depends_on:
      julia-api:
        condition: service_healthy
    networks:
      - julia-net
    volumes:
      - julia_logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # =========================================
  # WATCHTOWER (Auto-update containers)
  # =========================================

  watchtower:
    image: containrrr/watchtower
    container_name: julia-watchtower
    restart: always
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_POLL_INTERVAL=86400  # 24 horas
      - WATCHTOWER_INCLUDE_STOPPED=false
      - WATCHTOWER_NOTIFICATIONS=slack
      - WATCHTOWER_NOTIFICATION_SLACK_HOOK_URL=${SLACK_WEBHOOK_URL}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - julia-net
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

# =========================================
# VOLUMES PERSISTENTES
# =========================================

volumes:
  redis_data:
    name: julia-redis-data
  evolution_instances:
    name: julia-evolution-instances
  evolution_store:
    name: julia-evolution-store
  chatwoot_storage:
    name: julia-chatwoot-storage
  julia_logs:
    name: julia-logs

# =========================================
# REDE
# =========================================

networks:
  julia-net:
    name: julia-network
    driver: bridge
```

### Como Testar
```bash
# Validar sintaxe do arquivo
docker compose -f docker-compose.prod.yml config

# Deve mostrar a configuracao expandida sem erros
```

### DoD
- [ ] Arquivo docker-compose.prod.yml criado
- [ ] Sintaxe validada sem erros
- [ ] Servicos de dev removidos (pgadmin, n8n)
- [ ] Health checks configurados
- [ ] Logging limitado em todos os servicos
- [ ] Restart policies definidas

---

## S12.E2.2 - Configurar Secrets e Variaveis

### Objetivo
Configurar todas as variaveis de ambiente necessarias para producao de forma segura.

### Contexto
O arquivo .env contem segredos sensiveis. Deve ter permissoes restritas e nunca ser commitado.

### Pre-requisitos
- S12.E2.1 completo

### Tarefas

1. **Criar .env de producao completo**
```bash
cd /opt/julia
nano .env
```

2. **Template do .env de producao**
```bash
# ==============================================
# PRODUCAO - Agente Julia
# ==============================================

# ----------------------------------------------
# APP
# ----------------------------------------------
APP_NAME=Agente Julia
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Dominio (usado pelo Nginx e Evolution)
DOMAIN=julia.seudominio.com.br

# ----------------------------------------------
# SUPABASE
# ----------------------------------------------
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ----------------------------------------------
# ANTHROPIC
# ----------------------------------------------
ANTHROPIC_API_KEY=sk-ant-api03-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# ----------------------------------------------
# VOYAGE AI
# ----------------------------------------------
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=voyage-3.5-lite

# ----------------------------------------------
# EVOLUTION API
# ----------------------------------------------
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=SUA_API_KEY_EVOLUTION
EVOLUTION_INSTANCE=Revoluna

# ----------------------------------------------
# CHATWOOT
# ----------------------------------------------
CHATWOOT_URL=http://chatwoot:3000
CHATWOOT_API_KEY=SUA_API_KEY_CHATWOOT
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# Para Docker interno
SECRET_KEY_BASE=gere_uma_chave_secreta_longa_aqui_minimo_64_chars
POSTGRES_HOST=SEU_HOST_POSTGRES_EXTERNO
POSTGRES_PORT=5432
POSTGRES_DATABASE=chatwoot_production
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=SENHA_FORTE_AQUI

# ----------------------------------------------
# SLACK
# ----------------------------------------------
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
SLACK_CHANNEL=#julia-producao
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...

# ----------------------------------------------
# REDIS (interno Docker)
# ----------------------------------------------
REDIS_URL=redis://redis:6379/0

# ----------------------------------------------
# RATE LIMITING
# ----------------------------------------------
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# ----------------------------------------------
# GOOGLE DOCS
# ----------------------------------------------
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-sa.json
GOOGLE_BRIEFINGS_FOLDER_ID=ID_DA_PASTA_BRIEFINGS

# ----------------------------------------------
# EMPRESA
# ----------------------------------------------
NOME_EMPRESA=Revoluna
GESTOR_WHATSAPP=5511999999999

# ----------------------------------------------
# JULIA API (interno)
# ----------------------------------------------
JULIA_API_URL=http://julia-api:8000
```

3. **Gerar SECRET_KEY_BASE**
```bash
openssl rand -hex 64
```

4. **Proteger o arquivo**
```bash
chmod 600 .env
chown deploy:deploy .env
```

5. **Verificar permissoes**
```bash
ls -la .env
# Deve mostrar: -rw------- 1 deploy deploy ...
```

### Como Testar
```bash
# Verificar se todas as variaveis estao definidas
grep -E "^[A-Z].*=" .env | wc -l
# Deve mostrar ~30+ linhas

# Verificar se nao ha valores em branco criticos
grep -E "^(ANTHROPIC_API_KEY|SUPABASE_URL|SUPABASE_SERVICE_KEY)=" .env
```

### DoD
- [ ] .env criado com todos os valores de producao
- [ ] SECRET_KEY_BASE gerado e unico
- [ ] Permissao 600 no arquivo .env
- [ ] Todas as API keys preenchidas
- [ ] URLs internas do Docker configuradas
- [ ] Nenhuma senha padrao ou placeholder

---

## S12.E2.3 - Setup Volumes Persistentes

### Objetivo
Garantir que dados persistentes estao em volumes adequados e seguros.

### Contexto
Volumes Docker garantem que dados sobrevivam a restarts e atualizacoes de containers.

### Pre-requisitos
- S12.E2.2 completo

### Tarefas

1. **Criar diretorio para backups**
```bash
sudo mkdir -p /opt/backups/julia
sudo chown deploy:deploy /opt/backups/julia
```

2. **Verificar volumes definidos**
```bash
# Os volumes sao criados automaticamente pelo docker compose
# Mas podemos pre-criar para verificar
docker volume create julia-redis-data
docker volume create julia-evolution-instances
docker volume create julia-evolution-store
docker volume create julia-chatwoot-storage
docker volume create julia-logs
```

3. **Criar script de backup de volumes**
```bash
cat > /opt/julia/scripts/backup-volumes.sh << 'EOF'
#!/bin/bash
# Backup de volumes Docker para Agente Julia

BACKUP_DIR="/opt/backups/julia"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Iniciando backup dos volumes..."

# Backup Redis
docker run --rm \
  -v julia-redis-data:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/redis_${DATE}.tar.gz -C /data .

# Backup Evolution
docker run --rm \
  -v julia-evolution-instances:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/evolution_instances_${DATE}.tar.gz -C /data .

docker run --rm \
  -v julia-evolution-store:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/evolution_store_${DATE}.tar.gz -C /data .

# Backup Chatwoot storage
docker run --rm \
  -v julia-chatwoot-storage:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/chatwoot_storage_${DATE}.tar.gz -C /data .

# Backup logs (opcional)
docker run --rm \
  -v julia-logs:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/julia_logs_${DATE}.tar.gz -C /data .

# Limpar backups antigos (manter ultimos 7 dias)
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete

echo "Backup concluido em ${BACKUP_DIR}"
ls -lh ${BACKUP_DIR}/*.tar.gz | tail -10
EOF

chmod +x /opt/julia/scripts/backup-volumes.sh
```

4. **Criar diretorio de scripts**
```bash
mkdir -p /opt/julia/scripts
```

### Como Testar
```bash
# Listar volumes criados
docker volume ls | grep julia

# Verificar script de backup
cat /opt/julia/scripts/backup-volumes.sh
ls -la /opt/julia/scripts/
```

### DoD
- [ ] Diretorio /opt/backups/julia criado
- [ ] Volumes Docker criados
- [ ] Script de backup criado e executavel
- [ ] Diretorio scripts existe em /opt/julia

---

## S12.E2.4 - Build e Primeiro Deploy

### Objetivo
Fazer o build das imagens e subir todos os containers pela primeira vez.

### Contexto
Este e o momento da verdade - vamos subir toda a stack e verificar se tudo funciona junto.

### Pre-requisitos
- S12.E2.3 completo

### Tarefas

1. **Build das imagens Julia**
```bash
cd /opt/julia

# Build da imagem (pode demorar 2-3 min na primeira vez)
docker compose -f docker-compose.prod.yml build julia-api
```

2. **Subir servicos de infraestrutura primeiro**
```bash
# Redis primeiro (outros dependem dele)
docker compose -f docker-compose.prod.yml up -d redis

# Aguardar Redis ficar healthy
docker compose -f docker-compose.prod.yml ps redis
# Deve mostrar: healthy
```

3. **Subir Evolution API**
```bash
docker compose -f docker-compose.prod.yml up -d evolution-api

# Verificar logs
docker compose -f docker-compose.prod.yml logs -f evolution-api
# Ctrl+C para sair
```

4. **Subir Chatwoot (se usar)**
```bash
docker compose -f docker-compose.prod.yml up -d chatwoot chatwoot-sidekiq

# Primeira vez pode demorar (migrations)
docker compose -f docker-compose.prod.yml logs -f chatwoot
```

5. **Subir Julia API e workers**
```bash
docker compose -f docker-compose.prod.yml up -d julia-api julia-worker julia-scheduler

# Verificar health
docker compose -f docker-compose.prod.yml ps
```

6. **Subir Watchtower**
```bash
docker compose -f docker-compose.prod.yml up -d watchtower
```

7. **Verificar todos os containers**
```bash
docker compose -f docker-compose.prod.yml ps

# Todos devem estar "Up" e "healthy" ou "running"
```

8. **Testar endpoints internos**
```bash
# Julia API health
curl http://localhost:8000/health

# Evolution API
curl http://localhost:8080/

# Chatwoot (se subiu)
curl http://localhost:3000/api/v1/
```

### Como Testar
```bash
# Status de todos os containers
docker compose -f docker-compose.prod.yml ps

# Logs de erro (se houver)
docker compose -f docker-compose.prod.yml logs --tail=50 | grep -i error

# Health check manual
curl -s http://localhost:8000/health | jq .
```

### DoD
- [ ] Imagem julia-api buildada com sucesso
- [ ] Redis rodando e healthy
- [ ] Evolution API rodando
- [ ] Chatwoot rodando (se aplicavel)
- [ ] Julia API respondendo em /health
- [ ] Julia Worker rodando
- [ ] Julia Scheduler rodando
- [ ] Watchtower rodando
- [ ] Nenhum container em estado de restart loop
- [ ] Logs sem erros criticos

---

## Resumo do Epic

| Story | Tempo Estimado | Complexidade |
|-------|----------------|--------------|
| S12.E2.1 | 30 min | Media |
| S12.E2.2 | 30 min | Baixa |
| S12.E2.3 | 20 min | Baixa |
| S12.E2.4 | 60 min | Media |
| **Total** | **~2.5h** | |

## Troubleshooting Comum

### Container reiniciando em loop
```bash
# Ver logs do container especifico
docker compose -f docker-compose.prod.yml logs julia-api

# Causas comuns:
# - .env com variaveis faltando
# - Erro de conexao com Redis
# - Porta ja em uso
```

### Redis nao fica healthy
```bash
# Verificar se porta 6379 nao esta em uso
sudo netstat -tlnp | grep 6379

# Parar servico local se houver
sudo systemctl stop redis-server
```

### Erro de permissao nos volumes
```bash
# Verificar owner dos volumes
docker volume inspect julia-logs

# Se necessario, ajustar permissoes dentro do container
docker exec -it julia-api chown -R 1000:1000 /app/logs
```

## Proximo Epic

Apos completar este epic, prossiga para [Epic 03: SSL e Dominio](./epic-03-ssl-dominio.md)
