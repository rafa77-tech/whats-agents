# Epic 04: Monitoramento

## Objetivo

Implementar sistema de monitoramento para acompanhar saude dos servicos, metricas de negocio e receber alertas de problemas.

---

## Stories

| ID | Story | Status |
|----|-------|--------|
| S12.E4.1 | Setup Prometheus + Node Exporter | 🔴 |
| S12.E4.2 | Setup Grafana | 🔴 |
| S12.E4.3 | Dashboards e metricas | 🔴 |
| S12.E4.4 | Alertas via Slack | 🔴 |

---

## S12.E4.1 - Setup Prometheus + Node Exporter

### Objetivo
Configurar Prometheus para coletar metricas de todos os servicos e do servidor.

### Contexto
Prometheus e o padrao de mercado para coleta de metricas. Node Exporter coleta metricas do sistema (CPU, memoria, disco).

### Pre-requisitos
- Epic 03 completo

### Tarefas

1. **Adicionar servicos de monitoramento ao docker-compose**
```bash
cd /opt/julia
nano docker-compose.prod.yml
```

2. **Adicionar bloco de monitoramento**
```yaml
  # =========================================
  # MONITORAMENTO
  # =========================================

  prometheus:
    image: prom/prometheus:latest
    container_name: julia-prometheus
    restart: always
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus_data:/prometheus
    networks:
      - julia-net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  node-exporter:
    image: prom/node-exporter:latest
    container_name: julia-node-exporter
    restart: always
    command:
      - '--path.rootfs=/host'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /:/host:ro,rslave
    networks:
      - julia-net
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: julia-cadvisor
    restart: always
    privileged: true
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    networks:
      - julia-net
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  alertmanager:
    image: prom/alertmanager:latest
    container_name: julia-alertmanager
    restart: always
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    networks:
      - julia-net
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"
```

3. **Adicionar volumes**
```yaml
volumes:
  # ... volumes existentes ...
  prometheus_data:
    name: julia-prometheus-data
  alertmanager_data:
    name: julia-alertmanager-data
  grafana_data:
    name: julia-grafana-data
```

4. **Criar diretorio de monitoramento**
```bash
mkdir -p /opt/julia/monitoring
```

5. **Criar prometheus.yml**
```bash
cat > /opt/julia/monitoring/prometheus.yml << 'EOF'
# Prometheus configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - /etc/prometheus/alerts.yml

scrape_configs:
  # Prometheus auto-monitoramento
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter - metricas do host
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  # cAdvisor - metricas de containers
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # Julia API
  - job_name: 'julia-api'
    metrics_path: /metrics
    static_configs:
      - targets: ['julia-api:8000']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF
```

6. **Criar alerts.yml**
```bash
cat > /opt/julia/monitoring/alerts.yml << 'EOF'
groups:
  - name: julia-alerts
    rules:
      # Container down
      - alert: ContainerDown
        expr: absent(container_last_seen{name=~"julia.*"})
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.name }} esta down"
          description: "Container nao esta respondendo ha mais de 1 minuto"

      # Alta utilizacao de CPU
      - alert: HighCpuUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alta utilizacao de CPU"
          description: "CPU acima de 80% por mais de 5 minutos"

      # Alta utilizacao de memoria
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alta utilizacao de memoria"
          description: "Memoria acima de 85% por mais de 5 minutos"

      # Disco quase cheio
      - alert: DiskSpaceLow
        expr: (1 - (node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes{fstype!="tmpfs"})) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Disco quase cheio"
          description: "Disco com mais de 85% de uso"

      # Julia API nao respondendo
      - alert: JuliaApiDown
        expr: up{job="julia-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Julia API esta down"
          description: "Julia API nao esta respondendo ao health check"

      # Alta latencia Julia API
      - alert: JuliaApiHighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="julia-api"}[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alta latencia na Julia API"
          description: "95% das requisicoes demorando mais de 5 segundos"

      # Container reiniciando muito
      - alert: ContainerRestarting
        expr: increase(container_restart_count{name=~"julia.*"}[1h]) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container reiniciando frequentemente"
          description: "Container {{ $labels.name }} reiniciou mais de 3 vezes na ultima hora"
EOF
```

7. **Criar alertmanager.yml**
```bash
cat > /opt/julia/monitoring/alertmanager.yml << 'EOF'
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'slack-notifications'

  routes:
    - match:
        severity: critical
      receiver: 'slack-critical'
      repeat_interval: 1h

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'SLACK_WEBHOOK_URL_AQUI'
        channel: '#julia-alertas'
        title: '{{ .Status | toUpper }}: {{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
        send_resolved: true

  - name: 'slack-critical'
    slack_configs:
      - api_url: 'SLACK_WEBHOOK_URL_AQUI'
        channel: '#julia-alertas'
        title: '🚨 CRITICO: {{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
EOF
```

8. **Atualizar alertmanager.yml com webhook do Slack**
```bash
sed -i 's|SLACK_WEBHOOK_URL_AQUI|SEU_WEBHOOK_SLACK_REAL|g' /opt/julia/monitoring/alertmanager.yml
```

9. **Subir servicos de monitoramento**
```bash
docker compose -f docker-compose.prod.yml up -d prometheus node-exporter cadvisor alertmanager
```

### Como Testar
```bash
# Verificar containers
docker compose -f docker-compose.prod.yml ps | grep -E "prometheus|node|cadvisor|alert"

# Testar Prometheus (internamente)
curl http://localhost:9090/-/healthy

# Verificar targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'
```

### DoD
- [ ] Prometheus rodando
- [ ] Node Exporter rodando
- [ ] cAdvisor rodando
- [ ] Alertmanager rodando
- [ ] prometheus.yml configurado
- [ ] alerts.yml com alertas basicos
- [ ] alertmanager.yml com webhook Slack

---

## S12.E4.2 - Setup Grafana

### Objetivo
Configurar Grafana para visualizacao de metricas com dashboards.

### Contexto
Grafana conecta ao Prometheus e permite criar dashboards bonitos e uteis.

### Pre-requisitos
- S12.E4.1 completo

### Tarefas

1. **Adicionar Grafana ao docker-compose**
```yaml
  grafana:
    image: grafana/grafana:latest
    container_name: julia-grafana
    restart: always
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://${DOMAIN}/grafana
      - GF_SERVER_SERVE_FROM_SUB_PATH=true
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    networks:
      - julia-net
    depends_on:
      - prometheus
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

2. **Adicionar GRAFANA_PASSWORD ao .env**
```bash
echo "GRAFANA_PASSWORD=$(openssl rand -base64 16)" >> /opt/julia/.env
```

3. **Criar estrutura de provisioning**
```bash
mkdir -p /opt/julia/monitoring/grafana/provisioning/datasources
mkdir -p /opt/julia/monitoring/grafana/provisioning/dashboards
```

4. **Criar datasource para Prometheus**
```bash
cat > /opt/julia/monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF
```

5. **Criar configuracao de dashboards**
```bash
cat > /opt/julia/monitoring/grafana/provisioning/dashboards/default.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: 'Julia'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboards/json
EOF
```

6. **Criar diretorio para dashboards JSON**
```bash
mkdir -p /opt/julia/monitoring/grafana/provisioning/dashboards/json
```

7. **Adicionar rota do Grafana no Nginx**
```bash
# Adicionar ao arquivo /etc/nginx/sites-available/julia
sudo nano /etc/nginx/sites-available/julia
```

```nginx
    # Grafana (adicionar antes do bloco de fechamento)
    location /grafana/ {
        proxy_pass http://127.0.0.1:3001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
```

8. **Atualizar docker-compose para expor Grafana na porta 3001**
```yaml
  grafana:
    # ... configuracao existente ...
    ports:
      - "127.0.0.1:3001:3000"  # Apenas localhost
```

9. **Reiniciar Nginx e subir Grafana**
```bash
sudo nginx -t && sudo systemctl reload nginx
docker compose -f docker-compose.prod.yml up -d grafana
```

### Como Testar
```bash
# Verificar Grafana rodando
docker compose -f docker-compose.prod.yml logs grafana | tail -20

# Testar acesso local
curl -s http://localhost:3001/api/health | jq .

# Testar via HTTPS (do navegador)
# Acessar: https://julia.seudominio.com.br/grafana
# Login: admin / (senha do .env GRAFANA_PASSWORD)
```

### DoD
- [ ] Grafana rodando
- [ ] Datasource Prometheus configurado
- [ ] Acesso via /grafana/ funcionando
- [ ] Login admin funcionando
- [ ] Senha forte configurada

---

## S12.E4.3 - Dashboards e Metricas

### Objetivo
Criar dashboards uteis para monitorar a saude do sistema.

### Contexto
Vamos usar dashboards pre-construidos da comunidade e customizar para Julia.

### Pre-requisitos
- S12.E4.2 completo

### Tarefas

1. **Importar Dashboard Node Exporter (ID: 1860)**
   - Acessar Grafana
   - Menu lateral > Dashboards > Import
   - ID: `1860`
   - Selecionar Prometheus como datasource
   - Import

2. **Importar Dashboard Docker (ID: 893)**
   - Menu lateral > Dashboards > Import
   - ID: `893`
   - Selecionar Prometheus como datasource
   - Import

3. **Criar Dashboard Julia customizado**
```bash
cat > /opt/julia/monitoring/grafana/provisioning/dashboards/json/julia-overview.json << 'EOF'
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "yellow", "value": 0},
              {"color": "red", "value": 0}
            ]
          },
          "unit": "short"
        }
      },
      "gridPos": {"h": 4, "w": 4, "x": 0, "y": 0},
      "id": 1,
      "options": {
        "colorMode": "value",
        "graphMode": "none",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        },
        "textMode": "auto"
      },
      "pluginVersion": "10.0.0",
      "targets": [
        {
          "expr": "count(container_last_seen{name=~\"julia.*\"})",
          "refId": "A"
        }
      ],
      "title": "Containers Julia Ativos",
      "type": "stat"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "mappings": [
            {"options": {"0": {"color": "red", "index": 0, "text": "DOWN"}}, "type": "value"},
            {"options": {"1": {"color": "green", "index": 1, "text": "UP"}}, "type": "value"}
          ],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "red", "value": null},
              {"color": "green", "value": 1}
            ]
          }
        }
      },
      "gridPos": {"h": 4, "w": 4, "x": 4, "y": 0},
      "id": 2,
      "options": {
        "colorMode": "value",
        "graphMode": "none",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        }
      },
      "targets": [
        {
          "expr": "up{job=\"julia-api\"}",
          "refId": "A"
        }
      ],
      "title": "Julia API Status",
      "type": "stat"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "palette-classic"},
          "unit": "percent"
        }
      },
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
      "id": 3,
      "options": {
        "legend": {"displayMode": "list", "placement": "bottom"},
        "tooltip": {"mode": "single"}
      },
      "targets": [
        {
          "expr": "100 - (avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
          "legendFormat": "CPU",
          "refId": "A"
        },
        {
          "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
          "legendFormat": "Memoria",
          "refId": "B"
        }
      ],
      "title": "Recursos do Sistema",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "palette-classic"},
          "unit": "bytes"
        }
      },
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
      "id": 4,
      "targets": [
        {
          "expr": "sum(container_memory_usage_bytes{name=~\"julia.*\"}) by (name)",
          "legendFormat": "{{name}}",
          "refId": "A"
        }
      ],
      "title": "Memoria por Container",
      "type": "timeseries"
    }
  ],
  "refresh": "30s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["julia"],
  "templating": {"list": []},
  "time": {"from": "now-1h", "to": "now"},
  "timepicker": {},
  "timezone": "browser",
  "title": "Julia Overview",
  "uid": "julia-overview",
  "version": 1
}
EOF
```

4. **Reiniciar Grafana para carregar dashboard**
```bash
docker compose -f docker-compose.prod.yml restart grafana
```

### Como Testar
```bash
# Acessar Grafana e verificar dashboards
# https://julia.seudominio.com.br/grafana

# Verificar:
# - Dashboard "Node Exporter Full" com metricas do host
# - Dashboard "Docker" com metricas de containers
# - Dashboard "Julia Overview" customizado
```

### DoD
- [ ] Dashboard Node Exporter importado
- [ ] Dashboard Docker importado
- [ ] Dashboard Julia Overview criado
- [ ] Metricas de CPU/memoria visíveis
- [ ] Status dos containers visivel
- [ ] Grafana atualizando em tempo real

---

## S12.E4.4 - Alertas via Slack

### Objetivo
Configurar alertas automaticos no Slack quando problemas ocorrerem.

### Contexto
Alertmanager envia notificacoes para Slack quando alertas sao disparados.

### Pre-requisitos
- S12.E4.3 completo
- Canal Slack para alertas criado

### Tarefas

1. **Criar canal no Slack**
   - Nome sugerido: `#julia-alertas`

2. **Verificar webhook configurado**
```bash
# O webhook ja deve estar em alertmanager.yml
grep "api_url" /opt/julia/monitoring/alertmanager.yml
```

3. **Testar alerta manualmente**
```bash
# Simular alerta de teste
curl -H "Content-Type: application/json" -d '[{
  "labels": {
    "alertname": "TesteManual",
    "severity": "warning"
  },
  "annotations": {
    "summary": "Teste de alerta Julia",
    "description": "Este e um teste do sistema de alertas. Se voce esta vendo isso, o sistema esta funcionando!"
  }
}]' http://localhost:9093/api/v1/alerts
```

4. **Verificar no Slack**
   - Mensagem deve aparecer no canal `#julia-alertas`

5. **Criar script de teste de saude**
```bash
cat > /opt/julia/scripts/health-check.sh << 'EOF'
#!/bin/bash
# Health check manual dos servicos Julia

echo "=== Julia Health Check ==="
echo ""

# Julia API
echo -n "Julia API: "
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "OK"
else
    echo "FALHA"
fi

# Redis
echo -n "Redis: "
if docker exec julia-redis redis-cli ping > /dev/null 2>&1; then
    echo "OK"
else
    echo "FALHA"
fi

# Evolution
echo -n "Evolution API: "
if curl -sf http://localhost:8080/ > /dev/null; then
    echo "OK"
else
    echo "FALHA"
fi

# Prometheus
echo -n "Prometheus: "
if curl -sf http://localhost:9090/-/healthy > /dev/null; then
    echo "OK"
else
    echo "FALHA"
fi

# Grafana
echo -n "Grafana: "
if curl -sf http://localhost:3001/api/health > /dev/null; then
    echo "OK"
else
    echo "FALHA"
fi

echo ""
echo "=== Fim do Health Check ==="
EOF

chmod +x /opt/julia/scripts/health-check.sh
```

6. **Adicionar cron para health check**
```bash
# Adicionar ao crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/julia/scripts/health-check.sh >> /var/log/julia-health.log 2>&1") | crontab -
```

### Como Testar
```bash
# Executar health check
/opt/julia/scripts/health-check.sh

# Verificar alertas ativos
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | .labels.alertname'

# Verificar se alerta de teste chegou no Slack
```

### DoD
- [ ] Canal Slack para alertas criado
- [ ] Webhook configurado no Alertmanager
- [ ] Alerta de teste enviado com sucesso
- [ ] Script de health check criado
- [ ] Cron configurado para health check periodico
- [ ] Alertas criticos notificam no Slack

---

## Resumo do Epic

| Story | Tempo Estimado | Complexidade |
|-------|----------------|--------------|
| S12.E4.1 | 45 min | Media |
| S12.E4.2 | 30 min | Baixa |
| S12.E4.3 | 45 min | Media |
| S12.E4.4 | 30 min | Baixa |
| **Total** | **~2.5h** | |

## Troubleshooting

### Prometheus nao coleta metricas
```bash
# Verificar targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Verificar se container expoe metricas
curl http://localhost:8000/metrics  # Julia API
```

### Grafana nao mostra dados
```bash
# Verificar datasource
curl -s http://localhost:3001/api/datasources | jq '.[].name'

# Testar query direto no Prometheus
curl 'http://localhost:9090/api/v1/query?query=up'
```

### Alertas nao chegam no Slack
```bash
# Verificar Alertmanager
curl http://localhost:9093/-/healthy

# Verificar configuracao
docker exec julia-alertmanager cat /etc/alertmanager/alertmanager.yml | grep -A5 slack
```

## Proximo Epic

Apos completar este epic, prossiga para [Epic 05: Deploy Automatizado](./epic-05-deploy-automatizado.md)
