# Epic 03: SSL e Dominio

## Objetivo

Configurar dominio, Nginx como reverse proxy e certificado SSL para acesso seguro via HTTPS.

---

## Stories

| ID | Story | Status |
|----|-------|--------|
| S12.E3.1 | Configurar DNS do dominio | 🔴 |
| S12.E3.2 | Instalar e configurar Nginx | 🔴 |
| S12.E3.3 | Obter certificado SSL (Let's Encrypt) | 🔴 |
| S12.E3.4 | Testar acesso HTTPS end-to-end | 🔴 |

---

## S12.E3.1 - Configurar DNS do Dominio

### Objetivo
Apontar dominio/subdominio para o IP da VPS.

### Contexto
Voce pode usar um dominio proprio ou um subdominio. Recomendamos usar subdominio dedicado (ex: `julia.seudominio.com.br`).

### Pre-requisitos
- Epic 02 completo
- Dominio registrado
- Acesso ao painel DNS do dominio

### Tarefas

1. **Identificar IP da VPS**
```bash
# Na VPS
curl ifconfig.me
# Anote o IP publico
```

2. **Acessar painel DNS do dominio**
   - DigitalOcean: Networking > Domains
   - Cloudflare: DNS > Records
   - Registro.br: DNS > Editar zona
   - GoDaddy: DNS Management

3. **Criar registro A**
```
Tipo: A
Nome: julia (ou @ para dominio raiz)
Valor: SEU_IP_VPS
TTL: 3600 (ou automatico)
```

4. **Criar registro A para www (opcional)**
```
Tipo: A
Nome: www.julia
Valor: SEU_IP_VPS
TTL: 3600
```

5. **Aguardar propagacao DNS**
```bash
# Verificar se ja propagou (pode demorar ate 24h, geralmente 5-30 min)
dig julia.seudominio.com.br +short

# Ou usar servico online
# https://dnschecker.org/
```

### Como Testar
```bash
# Do seu computador local
ping julia.seudominio.com.br

# Deve retornar o IP da VPS
nslookup julia.seudominio.com.br

# Da VPS
curl -I http://julia.seudominio.com.br
# Pode dar timeout (Nginx ainda nao esta rodando) - OK
```

### DoD
- [ ] Registro A criado no DNS
- [ ] Dominio resolve para IP da VPS
- [ ] dig/nslookup retorna IP correto
- [ ] Propagacao DNS completa

---

## S12.E3.2 - Instalar e Configurar Nginx

### Objetivo
Instalar Nginx como reverse proxy para rotear trafego para os containers.

### Contexto
Nginx fica na frente de todos os servicos, roteando por path:
- `/` → Julia API
- `/evolution` → Evolution API
- `/chatwoot` → Chatwoot

### Pre-requisitos
- S12.E3.1 completo

### Tarefas

1. **Instalar Nginx**
```bash
sudo apt install nginx -y
```

2. **Remover configuracao padrao**
```bash
sudo rm /etc/nginx/sites-enabled/default
```

3. **Criar configuracao para Julia**
```bash
sudo nano /etc/nginx/sites-available/julia
```

4. **Conteudo da configuracao (HTTP inicial)**
```nginx
# /etc/nginx/sites-available/julia
# Configuracao HTTP (antes do SSL)

# Upstream definitions
upstream julia_api {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream evolution_api {
    server 127.0.0.1:8080;
    keepalive 32;
}

upstream chatwoot_app {
    server 127.0.0.1:3000;
    keepalive 32;
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 80;
    listen [::]:80;
    server_name julia.seudominio.com.br;  # ALTERAR!

    # Logs
    access_log /var/log/nginx/julia_access.log;
    error_log /var/log/nginx/julia_error.log;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Certbot challenge (para SSL depois)
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Julia API (raiz)
    location / {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://julia_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Webhook da Evolution (sem rate limit - precisa responder rapido)
    location /webhook/ {
        proxy_pass http://julia_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Evolution API
    location /evolution/ {
        rewrite ^/evolution/(.*) /$1 break;

        proxy_pass http://evolution_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Chatwoot
    location /chatwoot/ {
        rewrite ^/chatwoot/(.*) /$1 break;

        proxy_pass http://chatwoot_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }

    # Health check endpoint
    location /nginx-health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}
```

5. **Atualizar server_name com seu dominio**
```bash
sudo sed -i 's/julia.seudominio.com.br/SEU_DOMINIO_REAL/' /etc/nginx/sites-available/julia
```

6. **Criar diretorio para certbot**
```bash
sudo mkdir -p /var/www/certbot
```

7. **Habilitar site**
```bash
sudo ln -s /etc/nginx/sites-available/julia /etc/nginx/sites-enabled/
```

8. **Testar configuracao**
```bash
sudo nginx -t
```

9. **Reiniciar Nginx**
```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Como Testar
```bash
# Verificar Nginx rodando
sudo systemctl status nginx

# Testar health check
curl http://localhost/nginx-health

# Testar acesso externo (do seu computador)
curl http://julia.seudominio.com.br/health
```

### DoD
- [ ] Nginx instalado e rodando
- [ ] Configuracao /etc/nginx/sites-available/julia criada
- [ ] Site habilitado em sites-enabled
- [ ] nginx -t passa sem erros
- [ ] Health check respondendo
- [ ] Proxy para Julia API funcionando

---

## S12.E3.3 - Obter Certificado SSL (Let's Encrypt)

### Objetivo
Obter certificado SSL gratuito e configurar HTTPS automatico.

### Contexto
Let's Encrypt oferece certificados SSL gratuitos com renovacao automatica via Certbot.

### Pre-requisitos
- S12.E3.2 completo
- DNS ja propagado

### Tarefas

1. **Instalar Certbot**
```bash
sudo apt install certbot python3-certbot-nginx -y
```

2. **Obter certificado**
```bash
sudo certbot --nginx -d julia.seudominio.com.br
```

3. **Responder as perguntas**
   - Email: seu email (para avisos de expiracao)
   - Termos: Yes
   - Compartilhar email: No (opcional)
   - Redirect HTTP to HTTPS: 2 (Redirect)

4. **Verificar auto-renovacao**
```bash
sudo systemctl status certbot.timer

# Testar renovacao (dry-run)
sudo certbot renew --dry-run
```

5. **Verificar configuracao final do Nginx**
```bash
sudo cat /etc/nginx/sites-available/julia
# Certbot deve ter adicionado blocos SSL
```

6. **Configuracao SSL otimizada (opcional)**
```bash
# Adicionar parametros SSL mais seguros
sudo nano /etc/nginx/conf.d/ssl-params.conf
```

```nginx
# /etc/nginx/conf.d/ssl-params.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

# HSTS (15768000 segundos = 6 meses)
add_header Strict-Transport-Security "max-age=15768000; includeSubDomains" always;
```

7. **Recarregar Nginx**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Como Testar
```bash
# Testar HTTPS
curl -I https://julia.seudominio.com.br/health

# Verificar certificado
echo | openssl s_client -servername julia.seudominio.com.br -connect julia.seudominio.com.br:443 2>/dev/null | openssl x509 -noout -dates

# Testar redirect HTTP -> HTTPS
curl -I http://julia.seudominio.com.br
# Deve retornar 301 redirect para https://
```

### DoD
- [ ] Certbot instalado
- [ ] Certificado SSL obtido com sucesso
- [ ] HTTPS funcionando
- [ ] HTTP redireciona para HTTPS
- [ ] Auto-renovacao configurada (certbot.timer ativo)
- [ ] Dry-run da renovacao passa

---

## S12.E3.4 - Testar Acesso HTTPS End-to-End

### Objetivo
Validar que todos os servicos estao acessiveis via HTTPS e funcionando corretamente.

### Contexto
Este e o teste final de integracao - garantir que tudo funciona junto via HTTPS.

### Pre-requisitos
- S12.E3.3 completo

### Tarefas

1. **Testar Julia API**
```bash
# Health check
curl https://julia.seudominio.com.br/health

# Resposta esperada:
# {"status": "healthy", ...}
```

2. **Testar Evolution API**
```bash
# Status
curl https://julia.seudominio.com.br/evolution/

# Deve retornar info da Evolution API
```

3. **Testar Chatwoot (se configurado)**
```bash
# API status
curl https://julia.seudominio.com.br/chatwoot/api/v1/

# Acessar interface web
# Abrir no navegador: https://julia.seudominio.com.br/chatwoot/
```

4. **Testar webhook Evolution**
```bash
# Verificar se Evolution esta configurado para usar novo webhook
# No painel Evolution ou via API:
curl -X GET "https://julia.seudominio.com.br/evolution/webhook/find/Revoluna" \
  -H "apikey: SUA_API_KEY"

# Se nao estiver, configurar:
curl -X POST "https://julia.seudominio.com.br/evolution/webhook/set/Revoluna" \
  -H "apikey: SUA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "url": "https://julia.seudominio.com.br/webhook/evolution",
    "webhookByEvents": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

5. **Testar SSL Labs (qualidade do SSL)**
```bash
# Acessar: https://www.ssllabs.com/ssltest/
# Digitar seu dominio
# Objetivo: nota A ou A+
```

6. **Atualizar .env com novo dominio**
```bash
cd /opt/julia
nano .env

# Atualizar DOMAIN
DOMAIN=julia.seudominio.com.br

# Reiniciar containers
docker compose -f docker-compose.prod.yml restart
```

### Como Testar
```bash
# Checklist final
echo "=== Teste End-to-End ===" && \
curl -s https://julia.seudominio.com.br/health | jq . && \
curl -s https://julia.seudominio.com.br/evolution/ | head -5 && \
echo "Todos os testes passaram!"
```

### DoD
- [ ] Julia API acessivel via HTTPS
- [ ] Evolution API acessivel via /evolution/
- [ ] Chatwoot acessivel via /chatwoot/ (se aplicavel)
- [ ] Webhook Evolution configurado com URL HTTPS
- [ ] SSL Labs nota A ou superior
- [ ] HTTP redireciona para HTTPS
- [ ] Nenhum mixed content warning no navegador
- [ ] .env atualizado com DOMAIN correto

---

## Resumo do Epic

| Story | Tempo Estimado | Complexidade |
|-------|----------------|--------------|
| S12.E3.1 | 30 min | Baixa |
| S12.E3.2 | 45 min | Media |
| S12.E3.3 | 20 min | Baixa |
| S12.E3.4 | 30 min | Baixa |
| **Total** | **~2h** | |

## Troubleshooting

### Certificado nao emite
```bash
# Verificar se DNS esta apontando corretamente
dig julia.seudominio.com.br

# Verificar se porta 80 esta aberta
sudo ufw status

# Verificar se Nginx esta rodando
sudo systemctl status nginx
```

### 502 Bad Gateway
```bash
# Container nao esta rodando
docker compose -f docker-compose.prod.yml ps

# Verificar se upstream esta correto (porta)
curl http://localhost:8000/health
```

### Mixed Content Warnings
```bash
# Verificar se todas as URLs internas usam HTTPS
# Ou se proxy_set_header X-Forwarded-Proto esta configurado
```

## Proximo Epic

Apos completar este epic, prossiga para [Epic 04: Monitoramento](./epic-04-monitoramento.md)
