# Guia de Deploy - Agente Júlia

## Pré-requisitos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **4GB RAM** mínimo (8GB recomendado)
- **20GB disco** livre
- **Portas disponíveis**: 8000, 3000, 8080, 6379, 5432, 4000, 5678

---

## Deploy Local (Desenvolvimento)

### 1. Clonar Repositório

```bash
git clone <repository-url>
cd whatsapp-api
```

### 2. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Evolution API
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=xxx

# Chatwoot
CHATWOOT_URL=http://chatwoot:3000
CHATWOOT_API_KEY=xxx

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Redis (já configurado no docker-compose)
REDIS_URL=redis://redis:6379/0
```

### 3. Subir Serviços

```bash
# Build e iniciar todos os serviços
docker compose up -d --build

# Verificar status
docker compose ps

# Ver logs
docker compose logs -f julia-api
```

### 4. Verificar Saúde

```bash
# Health check da API
curl http://localhost:8000/health

# Verificar todos os serviços
docker compose ps
```

---

## Deploy Produção

### 1. Preparar Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
```

### 2. Configurar Firewall

```bash
# Permitir portas necessárias
sudo ufw allow 8000/tcp   # API Júlia
sudo ufw allow 3000/tcp   # Chatwoot
sudo ufw allow 8080/tcp   # Evolution API
sudo ufw enable
```

### 3. Deploy da Aplicação

```bash
# Clonar repositório
git clone <repository-url>
cd whatsapp-api

# Configurar .env (usar secrets seguros)
nano .env

# Subir serviços
docker compose up -d --build

# Verificar logs
docker compose logs -f
```

### 4. Configurar Nginx (Recomendado)

```nginx
# /etc/nginx/sites-available/julia
server {
    listen 80;
    server_name api.julia.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/julia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Configurar SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.julia.com
```

---

## Estrutura de Serviços

```
docker-compose.yml
├── julia-api          (FastAPI - porta 8000)
├── julia-worker       (Worker de fila)
├── julia-scheduler    (Jobs agendados)
├── redis              (Cache - porta 6379)
├── evolution-api      (WhatsApp - porta 8080)
├── chatwoot           (Atendimento - porta 3000)
└── postgres           (Banco - porta 5432, opcional)
```

---

## Comandos Úteis

### Gerenciamento de Containers

```bash
# Iniciar todos os serviços
docker compose up -d

# Parar todos os serviços
docker compose down

# Reiniciar um serviço específico
docker compose restart julia-api

# Ver logs de um serviço
docker compose logs -f julia-api

# Ver logs de todos os serviços
docker compose logs -f

# Ver status
docker compose ps

# Rebuild após mudanças
docker compose up -d --build
```

### Logs

```bash
# Logs da API
docker compose logs -f julia-api

# Logs do worker
docker compose logs -f julia-worker

# Logs do scheduler
docker compose logs -f julia-scheduler

# Últimas 100 linhas
docker compose logs --tail=100 julia-api
```

### Executar Comandos

```bash
# Entrar no container
docker compose exec julia-api bash

# Executar script Python
docker compose exec julia-api python scripts/check_env.py

# Executar testes
docker compose exec julia-api pytest
```

### Backup

```bash
# Backup do Redis
docker compose exec redis redis-cli SAVE
docker compose cp redis:/data/dump.rdb ./backup/

# Backup de volumes
docker run --rm -v whatsapp-api_evolution_redis:/data -v $(pwd):/backup \
  alpine tar czf /backup/redis-backup.tar.gz /data
```

---

## Monitoramento

### Health Checks

```bash
# API
curl http://localhost:8000/health

# Métricas
curl http://localhost:8000/admin/metricas/health

# Performance
curl http://localhost:8000/admin/metricas/performance
```

### Verificar Serviços

```bash
# Status dos containers
docker compose ps

# Uso de recursos
docker stats

# Espaço em disco
docker system df
```

---

## Troubleshooting

### Container não inicia

```bash
# Ver logs de erro
docker compose logs julia-api

# Verificar variáveis de ambiente
docker compose exec julia-api env | grep SUPABASE

# Verificar conectividade
docker compose exec julia-api ping redis
```

### API não responde

```bash
# Verificar se está rodando
docker compose ps julia-api

# Verificar logs
docker compose logs -f julia-api

# Testar health check
curl http://localhost:8000/health

# Reiniciar
docker compose restart julia-api
```

### Worker não processa fila

```bash
# Verificar logs
docker compose logs -f julia-worker

# Verificar conexão Redis
docker compose exec julia-worker python -c "import redis; r=redis.Redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Reiniciar worker
docker compose restart julia-worker
```

### Scheduler não executa jobs

```bash
# Verificar logs
docker compose logs -f julia-scheduler

# Verificar conectividade com API
docker compose exec julia-scheduler curl http://julia-api:8000/health

# Verificar variável JULIA_API_URL
docker compose exec julia-scheduler env | grep JULIA_API_URL
```

### Redis não conecta

```bash
# Verificar se está rodando
docker compose ps redis

# Testar conexão
docker compose exec redis redis-cli ping

# Ver logs
docker compose logs redis
```

---

## Atualização

### Atualizar Código

```bash
# Pull do repositório
git pull

# Rebuild e restart
docker compose up -d --build

# Verificar logs
docker compose logs -f
```

### Atualizar Imagens

```bash
# Pull de imagens atualizadas
docker compose pull

# Rebuild aplicação
docker compose build --no-cache julia-api

# Restart
docker compose up -d
```

---

## Segurança

### Checklist

- [ ] `.env` não versionado (no .gitignore)
- [ ] Secrets em variáveis de ambiente
- [ ] Firewall configurado
- [ ] SSL/TLS habilitado
- [ ] Logs não expõem secrets
- [ ] Containers rodam como usuário não-root
- [ ] Volumes com permissões corretas

### Boas Práticas

1. **Nunca commitar `.env`**
2. **Usar secrets management** (Vault, AWS Secrets Manager)
3. **Rotacionar credenciais** regularmente
4. **Monitorar logs** para tentativas de acesso
5. **Manter imagens atualizadas** (security patches)

---

## Escalabilidade

### Escalar Workers

```yaml
# docker-compose.yml
julia-worker:
  deploy:
    replicas: 3
```

```bash
docker compose up -d --scale julia-worker=3
```

### Escalar API

```yaml
# docker-compose.yml
julia-api:
  deploy:
    replicas: 2
```

```bash
docker compose up -d --scale julia-api=2
```

**Nota**: Para escalabilidade avançada, considere Kubernetes.

---

## Backup e Recuperação

### Backup Automático

```bash
# Criar script de backup
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/$DATE"
mkdir -p $BACKUP_DIR

# Backup Redis
docker compose exec -T redis redis-cli SAVE
docker compose cp redis:/data/dump.rdb $BACKUP_DIR/

# Backup volumes
docker run --rm -v whatsapp-api_evolution_redis:/data \
  -v $(pwd)/$BACKUP_DIR:/backup alpine \
  tar czf /backup/redis.tar.gz /data

echo "Backup criado em $BACKUP_DIR"
EOF

chmod +x backup.sh

# Adicionar ao cron (diário às 2h)
crontab -e
# 0 2 * * * /path/to/backup.sh
```

### Recuperação

```bash
# Restaurar Redis
docker compose cp ./backup/dump.rdb redis:/data/
docker compose restart redis
```

---

## Próximos Passos

1. **CI/CD**: Configurar GitHub Actions
2. **Monitoring**: Integrar Prometheus/Grafana
3. **Logging**: Centralizar com ELK/Loki
4. **Kubernetes**: Migrar para K8s para escalabilidade
5. **Multi-region**: Deploy em múltiplas regiões

---

## Suporte

Para problemas ou dúvidas:
- Verificar logs: `docker compose logs -f`
- Consultar runbook: `docs/RUNBOOK.md`
- Verificar health: `curl http://localhost:8000/admin/metricas/health`

