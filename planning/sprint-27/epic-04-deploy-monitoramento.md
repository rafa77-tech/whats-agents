# Epic 04: Deploy e Monitoramento

**Status:** Pendente
**Estimativa:** 3 horas
**Prioridade:** Alta
**Dependencia:** E03 (API de Ativacao)
**Responsavel:** Dev Junior

---

## Objetivo

Configurar deploy em producao com:
- Systemd para gerenciar servicos
- Nginx como proxy reverso
- SSL via Let's Encrypt
- Alertas no Slack

---

## Story 4.1: Criar Servico Systemd para API

### Objetivo
Configurar API para iniciar automaticamente e reiniciar em caso de falha.

### Passo a Passo

**1. Criar arquivo de servico**

```bash
sudo cat > /etc/systemd/system/chip-activator.service << 'EOF'
[Unit]
Description=Chip Activator API
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/chip-activator
Environment="PATH=/opt/chip-activator/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="ANDROID_HOME=/opt/android-sdk"
Environment="ANDROID_SDK_ROOT=/opt/android-sdk"
ExecStart=/opt/chip-activator/venv/bin/python -m api.main
Restart=always
RestartSec=10
StandardOutput=append:/var/log/chip-activator/api.log
StandardError=append:/var/log/chip-activator/api-error.log

# Limites de recursos
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
```

**NOTA:** Ajustar `User=ubuntu` para o usuario correto do VPS.

**2. Criar diretorio de logs**

```bash
sudo mkdir -p /var/log/chip-activator
sudo chown ubuntu:ubuntu /var/log/chip-activator
```

**3. Habilitar e iniciar servico**

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar inicio automatico
sudo systemctl enable chip-activator

# Iniciar servico
sudo systemctl start chip-activator

# Verificar status
sudo systemctl status chip-activator
```

**4. Testar reinicio automatico**

```bash
# Matar processo (deve reiniciar automaticamente)
sudo pkill -f "python -m api.main"

# Aguardar 15 segundos
sleep 15

# Verificar se reiniciou
sudo systemctl status chip-activator
# Deve mostrar "active (running)"
```

### DoD

- [ ] Servico chip-activator.service criado
- [ ] Inicia com o sistema
- [ ] Reinicia automaticamente em caso de falha

---

## Story 4.2: Criar Servico Systemd para Appium

### Objetivo
Appium tambem precisa rodar como servico.

### Passo a Passo

**1. Criar arquivo de servico**

```bash
sudo cat > /etc/systemd/system/appium.service << 'EOF'
[Unit]
Description=Appium Server
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
Environment="PATH=/usr/local/bin:/usr/bin"
Environment="ANDROID_HOME=/opt/android-sdk"
Environment="ANDROID_SDK_ROOT=/opt/android-sdk"
ExecStart=/usr/bin/appium --address 127.0.0.1 --port 4723 --relaxed-security
Restart=always
RestartSec=10
StandardOutput=append:/var/log/chip-activator/appium.log
StandardError=append:/var/log/chip-activator/appium-error.log

[Install]
WantedBy=multi-user.target
EOF
```

**2. Habilitar e iniciar**

```bash
sudo systemctl daemon-reload
sudo systemctl enable appium
sudo systemctl start appium
sudo systemctl status appium
```

**3. Verificar Appium**

```bash
curl http://127.0.0.1:4723/status
# Deve retornar JSON com status
```

### DoD

- [ ] Servico appium.service criado
- [ ] Appium inicia automaticamente

---

## Story 4.3: Configurar Nginx como Proxy Reverso

### Objetivo
Nginx vai receber requisicoes HTTPS e encaminhar para a API.

### Passo a Passo

**1. Instalar Nginx**

```bash
sudo apt update
sudo apt install -y nginx
```

**2. Criar configuracao do site**

```bash
sudo cat > /etc/nginx/sites-available/chip-activator << 'EOF'
server {
    listen 80;
    server_name _;

    # Redirect HTTP to HTTPS (depois de configurar SSL)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts maiores para ativacao (pode demorar)
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check sem proxy (direto do nginx)
    location /nginx-health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF
```

**3. Habilitar site**

```bash
# Criar link simbolico
sudo ln -sf /etc/nginx/sites-available/chip-activator /etc/nginx/sites-enabled/

# Remover site default
sudo rm -f /etc/nginx/sites-enabled/default

# Testar configuracao
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
```

**4. Testar acesso**

```bash
# Testar localmente
curl http://localhost/health

# Testar de fora (substituir IP)
curl http://IP_DO_VPS/health
```

### DoD

- [ ] Nginx instalado
- [ ] Proxy reverso configurado
- [ ] API acessivel via porta 80

---

## Story 4.4: Configurar SSL com Let's Encrypt

### Objetivo
Habilitar HTTPS gratuito com Certbot.

### Pre-requisitos

- Dominio apontando para o VPS (ou usar IP com self-signed)
- Porta 80 e 443 liberadas no firewall

### Passo a Passo (Com Dominio)

**1. Instalar Certbot**

```bash
sudo apt install -y certbot python3-certbot-nginx
```

**2. Obter certificado**

```bash
# Substituir SEU_DOMINIO pelo dominio real
sudo certbot --nginx -d SEU_DOMINIO.com
```

Seguir instrucoes interativas:
- Informar email
- Aceitar termos
- Escolher redirecionar HTTP para HTTPS (recomendado)

**3. Verificar renovacao automatica**

```bash
# Testar renovacao
sudo certbot renew --dry-run
```

### Passo a Passo (Sem Dominio - Self-Signed)

Se nao tiver dominio, usar certificado auto-assinado:

**1. Gerar certificado**

```bash
sudo mkdir -p /etc/nginx/ssl

sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out /etc/nginx/ssl/selfsigned.crt \
    -subj "/C=BR/ST=SP/L=SaoPaulo/O=Revoluna/CN=chip-activator"
```

**2. Atualizar Nginx**

```bash
sudo cat > /etc/nginx/sites-available/chip-activator << 'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /nginx-health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

sudo nginx -t
sudo systemctl restart nginx
```

**3. Testar HTTPS**

```bash
# Com certificado self-signed, precisa ignorar verificacao
curl -k https://IP_DO_VPS/health
```

### DoD

- [ ] SSL configurado (Let's Encrypt ou self-signed)
- [ ] HTTPS funcionando
- [ ] HTTP redireciona para HTTPS

---

## Story 4.5: Configurar Alertas Slack

### Objetivo
Enviar alertas para Slack quando houver falhas.

### Passo a Passo

**1. Criar webhook no Slack**

1. Acessar https://api.slack.com/apps
2. Criar novo app ou usar existente
3. Ir em "Incoming Webhooks"
4. Ativar e criar webhook para canal desejado
5. Copiar URL do webhook

**2. Adicionar URL no config**

```bash
# Adicionar ao config.py
echo 'SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")' >> /opt/chip-activator/config.py
```

**3. Criar modulo de alertas**

```bash
cat > /opt/chip-activator/api/alerts.py << 'EOF'
"""
Sistema de alertas via Slack.
"""
import logging
import httpx
from typing import Optional
from datetime import datetime

from config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


async def send_slack_alert(
    title: str,
    message: str,
    level: str = "warning",  # info, warning, error
    details: Optional[dict] = None
):
    """
    Envia alerta para Slack.

    Args:
        title: Titulo do alerta
        message: Mensagem principal
        level: Nivel (info=azul, warning=amarelo, error=vermelho)
        details: Detalhes adicionais
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL nao configurado")
        return

    colors = {
        "info": "#36a64f",
        "warning": "#ffcc00",
        "error": "#ff0000"
    }

    payload = {
        "attachments": [
            {
                "color": colors.get(level, colors["info"]),
                "title": f":robot_face: Chip Activator - {title}",
                "text": message,
                "fields": [
                    {"title": k, "value": str(v), "short": True}
                    for k, v in (details or {}).items()
                ],
                "footer": "Chip Activator VPS",
                "ts": int(datetime.utcnow().timestamp())
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Erro ao enviar Slack: {response.text}")
            else:
                logger.info(f"Alerta Slack enviado: {title}")

    except Exception as e:
        logger.error(f"Erro ao enviar Slack: {e}")


async def alert_activation_failed(numero: str, error: str, step: str):
    """Alerta de falha na ativacao."""
    await send_slack_alert(
        title="Falha na Ativacao",
        message=f"Chip {numero} falhou na ativacao",
        level="error",
        details={
            "Numero": numero[:6] + "****",
            "Etapa": step,
            "Erro": error[:100]
        }
    )


async def alert_consecutive_failures(count: int):
    """Alerta de falhas consecutivas."""
    await send_slack_alert(
        title="Falhas Consecutivas",
        message=f"{count} ativacoes falharam consecutivamente. Verificar sistema.",
        level="error",
        details={
            "Falhas": count,
            "Acao": "Verificar logs e emulador"
        }
    )


async def alert_emulator_error():
    """Alerta de erro no emulador."""
    await send_slack_alert(
        title="Emulador com Problemas",
        message="Emulador nao esta respondendo. Pode ser necessario reiniciar.",
        level="error",
        details={
            "Status": "error",
            "Acao": "Verificar VPS e reiniciar servicos"
        }
    )


async def alert_queue_full():
    """Alerta de fila cheia."""
    await send_slack_alert(
        title="Fila Cheia",
        message="Fila de ativacao esta cheia. Novas requisicoes serao rejeitadas.",
        level="warning",
        details={
            "Tamanho": "MAX",
            "Acao": "Aguardar processamento ou aumentar capacidade"
        }
    )
EOF
```

**4. Integrar alertas na API**

Adicionar ao final do worker em `main.py`:

```python
# No worker process_queue(), apos falha:
from api.alerts import alert_activation_failed, alert_consecutive_failures

consecutive_failures = 0

# Dentro do loop, apos falha:
if not resultado.get("success"):
    consecutive_failures += 1
    await alert_activation_failed(
        numero,
        resultado.get("message", "Erro desconhecido"),
        resultado.get("step", "unknown")
    )

    if consecutive_failures >= 3:
        await alert_consecutive_failures(consecutive_failures)
else:
    consecutive_failures = 0
```

**5. Definir variavel de ambiente**

```bash
# Adicionar ao .bashrc ou .env
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"
```

**6. Testar alerta**

```bash
cd /opt/chip-activator
source venv/bin/activate

python3 -c "
import asyncio
from api.alerts import send_slack_alert

asyncio.run(send_slack_alert(
    'Teste de Alerta',
    'Este e um teste do sistema de alertas.',
    'info',
    {'Status': 'OK', 'Ambiente': 'Teste'}
))
"
```

### DoD

- [ ] Webhook Slack configurado
- [ ] Modulo alerts.py criado
- [ ] Alertas enviando para Slack

---

## Story 4.6: Configurar Rotacao de Logs

### Objetivo
Evitar que logs cresçam indefinidamente.

### Passo a Passo

**1. Criar configuracao logrotate**

```bash
sudo cat > /etc/logrotate.d/chip-activator << 'EOF'
/var/log/chip-activator/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload chip-activator > /dev/null 2>&1 || true
    endscript
}
EOF
```

**2. Testar logrotate**

```bash
sudo logrotate -d /etc/logrotate.d/chip-activator
# Deve mostrar o que faria (dry-run)

# Forcar rotacao
sudo logrotate -f /etc/logrotate.d/chip-activator
```

### DoD

- [ ] Logrotate configurado
- [ ] Logs rotacionam diariamente

---

## Checklist Final E04

- [ ] **Story 4.1** - Servico chip-activator (API)
- [ ] **Story 4.2** - Servico appium
- [ ] **Story 4.3** - Nginx proxy reverso
- [ ] **Story 4.4** - SSL (HTTPS)
- [ ] **Story 4.5** - Alertas Slack
- [ ] **Story 4.6** - Rotacao de logs

---

## Comandos Uteis

```bash
# Ver status dos servicos
sudo systemctl status chip-activator
sudo systemctl status appium
sudo systemctl status nginx

# Ver logs em tempo real
sudo journalctl -u chip-activator -f
tail -f /var/log/chip-activator/api.log

# Reiniciar tudo
sudo systemctl restart appium chip-activator nginx

# Ver portas em uso
sudo netstat -tlnp | grep -E "(8000|4723|80|443)"
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 4.1 Systemd API | 30min |
| 4.2 Systemd Appium | 15min |
| 4.3 Nginx | 30min |
| 4.4 SSL | 30min |
| 4.5 Slack | 45min |
| 4.6 Logrotate | 15min |
| **Total** | ~3 horas |

---

## Proximo Epic

[E05: Integracao Railway](./epic-05-integracao-railway.md)
