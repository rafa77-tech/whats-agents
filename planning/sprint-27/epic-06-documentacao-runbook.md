# Epic 06: Documentacao e Runbook

**Status:** Pendente
**Estimativa:** 2 horas
**Prioridade:** Media
**Dependencia:** E05 (Integracao Railway)
**Responsavel:** Dev Junior

---

## Objetivo

Criar documentacao operacional para:
- Manutencao do sistema
- Troubleshooting de problemas comuns
- Procedimentos de emergencia

---

## Story 6.1: README Operacional

### Objetivo
Criar README com instrucoes de uso e manutencao.

### Passo a Passo

**1. Criar README no VPS**

```bash
cat > /opt/chip-activator/README.md << 'EOF'
# Chip Activator

Sistema automatizado de ativacao de chips WhatsApp via emulador Android.

## Visao Geral

Este sistema permite ativar chips WhatsApp automaticamente, eliminando
a necessidade de escanear QR codes manualmente.

## Arquitetura

```
                   ┌─────────────────┐
 Railway Backend   │  VPS Hostinger  │
      │            │                 │
      │ HTTP POST  │  ┌───────────┐  │
      └───────────>│  │  FastAPI  │  │
                   │  └─────┬─────┘  │
                   │        │        │
                   │  ┌─────▼─────┐  │
                   │  │  Appium   │  │
                   │  └─────┬─────┘  │
                   │        │        │
                   │  ┌─────▼─────┐  │
                   │  │ Emulador  │  │
                   │  │ Android   │  │
                   │  └───────────┘  │
                   └─────────────────┘
```

## Servicos

| Servico | Porta | Comando |
|---------|-------|---------|
| API | 8000 | `systemctl status chip-activator` |
| Appium | 4723 | `systemctl status appium` |
| Nginx | 80/443 | `systemctl status nginx` |

## Comandos Rapidos

```bash
# Status de todos os servicos
systemctl status chip-activator appium nginx

# Reiniciar tudo
sudo systemctl restart appium chip-activator nginx

# Ver logs em tempo real
tail -f /var/log/chip-activator/api.log

# Ver logs do Appium
tail -f /var/log/chip-activator/appium.log

# Iniciar emulador manualmente
/opt/chip-activator/start_emulator.sh

# Parar emulador
/opt/chip-activator/stop_emulator.sh

# Status do emulador
/opt/chip-activator/status_emulator.sh

# Health check da API
curl http://localhost:8000/health
```

## Endpoints da API

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | /activate | Adiciona chip a fila de ativacao |
| GET | /activate/{id} | Consulta status de ativacao |
| GET | /queue | Status da fila |
| GET | /health | Health check (sem auth) |
| GET | /metrics | Metricas (com auth) |

## Autenticacao

Todas as requisicoes (exceto /health) requerem header:
```
X-API-Key: sua-api-key
```

## Estrutura de Arquivos

```
/opt/chip-activator/
├── api/                    # Codigo da API
├── apks/                   # APK do WhatsApp
├── venv/                   # Ambiente Python
├── config.py               # Configuracoes
├── whatsapp_automation.py  # Script de automacao
├── start_emulator.sh       # Iniciar emulador
├── stop_emulator.sh        # Parar emulador
├── status_emulator.sh      # Status emulador
├── start_appium.sh         # Iniciar Appium
├── stop_appium.sh          # Parar Appium
└── requirements.txt        # Deps Python

/var/log/chip-activator/
├── api.log                 # Log da API
├── api-error.log           # Erros da API
├── appium.log              # Log do Appium
├── emulator.log            # Log do emulador
└── screenshots/            # Capturas de erro
```

## Troubleshooting

Ver arquivo TROUBLESHOOTING.md para guia detalhado.

## Contato

Em caso de problemas criticos, contatar equipe via Slack.
EOF
```

### DoD

- [ ] README.md criado no VPS

---

## Story 6.2: Guia de Troubleshooting

### Objetivo
Documentar problemas comuns e solucoes.

### Passo a Passo

**1. Criar TROUBLESHOOTING.md**

```bash
cat > /opt/chip-activator/TROUBLESHOOTING.md << 'EOF'
# Troubleshooting - Chip Activator

## Problemas Comuns

### 1. API nao responde

**Sintomas:**
- `curl http://localhost:8000/health` retorna erro ou timeout

**Diagnostico:**
```bash
# Verificar se servico esta rodando
systemctl status chip-activator

# Ver logs
journalctl -u chip-activator -n 50

# Verificar porta
netstat -tlnp | grep 8000
```

**Solucoes:**
```bash
# Reiniciar servico
sudo systemctl restart chip-activator

# Se persistir, verificar logs de erro
cat /var/log/chip-activator/api-error.log

# Verificar se Appium esta ok
curl http://localhost:4723/status
```

---

### 2. Emulador nao inicia

**Sintomas:**
- `/opt/chip-activator/start_emulator.sh` falha
- `adb devices` nao mostra emulador

**Diagnostico:**
```bash
# Verificar status
/opt/chip-activator/status_emulator.sh

# Verificar KVM
ls -la /dev/kvm

# Verificar espaco em disco
df -h /
```

**Solucoes:**
```bash
# Matar processos orfaos
pkill -9 -f emulator
pkill -9 -f qemu

# Limpar locks
rm -f ~/.android/avd/*.lock

# Reiniciar
/opt/chip-activator/start_emulator.sh

# Se KVM nao existe, verificar virtualizacao
kvm-ok
```

---

### 3. Appium nao conecta

**Sintomas:**
- `curl http://localhost:4723/status` falha
- Logs mostram "Unable to connect"

**Diagnostico:**
```bash
# Verificar servico
systemctl status appium

# Verificar se emulador esta pronto
adb devices
adb shell getprop sys.boot_completed
```

**Solucoes:**
```bash
# Reiniciar ADB
adb kill-server
adb start-server

# Reiniciar Appium
sudo systemctl restart appium

# Verificar se WhatsApp esta instalado
adb shell pm list packages | grep whatsapp
```

---

### 4. Ativacao falha - Elemento nao encontrado

**Sintomas:**
- Log mostra "Element not found"
- Screenshot mostra tela inesperada

**Diagnostico:**
1. Verificar screenshot em `/var/log/chip-activator/screenshots/`
2. Comparar com tela esperada

**Solucoes:**
```bash
# WhatsApp pode ter atualizado
# Verificar versao
adb shell dumpsys package com.whatsapp | grep versionName

# Reinstalar APK
adb uninstall com.whatsapp
/opt/chip-activator/install_whatsapp.sh

# Se UI mudou, ajustar locators em whatsapp_automation.py
```

---

### 5. QR Code nao escaneia

**Sintomas:**
- Ativacao para na etapa "link_device"
- Camera do emulador nao funciona

**Diagnostico:**
- Verificar se URL do QR e acessivel
- Verificar screenshot da camera

**Solucoes:**
```bash
# Testar acesso ao QR
curl -I "URL_DO_QR_CODE"

# Verificar configuracao da camera virtual
# (Pode requerer ajuste no AVD)

# Alternativa: usar camera via arquivo
adb push /tmp/qr.png /sdcard/qr.png
```

---

### 6. Fila cheia / Timeout

**Sintomas:**
- API retorna 503 "Fila cheia"
- Ativacoes demoram muito

**Diagnostico:**
```bash
# Verificar fila
curl http://localhost:8000/queue -H "X-API-Key: KEY"

# Verificar se ha ativacao travada
```

**Solucoes:**
```bash
# Se ha item travado, reiniciar servico
sudo systemctl restart chip-activator

# Aumentar capacidade (editar config.py)
# MAX_QUEUE_SIZE = 20

# Se persistir, verificar performance do VPS
htop
```

---

### 7. SSL nao funciona

**Sintomas:**
- HTTPS retorna erro de certificado
- Navegador mostra "Not Secure"

**Diagnostico:**
```bash
# Verificar certificado
sudo certbot certificates

# Verificar Nginx
sudo nginx -t
```

**Solucoes:**
```bash
# Renovar certificado
sudo certbot renew

# Se self-signed, gerar novo
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out /etc/nginx/ssl/selfsigned.crt

# Reiniciar Nginx
sudo systemctl restart nginx
```

---

### 8. Alertas Slack nao chegam

**Sintomas:**
- Falhas ocorrem mas Slack nao notifica

**Diagnostico:**
```bash
# Verificar variavel
echo $SLACK_WEBHOOK_URL

# Testar manualmente
curl -X POST $SLACK_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Teste"}'
```

**Solucoes:**
```bash
# Verificar se URL esta correta no config
# Verificar logs de erro da API
```

---

## Procedimentos de Emergencia

### Reiniciar Tudo

```bash
sudo systemctl stop chip-activator appium
pkill -9 -f emulator
sleep 5
sudo systemctl start appium
sleep 10
sudo systemctl start chip-activator
```

### Resetar Emulador

```bash
# Parar tudo
pkill -9 -f emulator
pkill -9 -f qemu

# Limpar dados do emulador
rm -rf ~/.android/avd/chip-activator.avd/*.lock
rm -rf ~/.android/avd/chip-activator.avd/cache.img
rm -rf ~/.android/avd/chip-activator.avd/userdata-qemu.img

# Reiniciar
/opt/chip-activator/start_emulator.sh
```

### Rollback para Ativacao Manual

Se sistema estiver completamente fora:
1. Desabilitar chamadas automaticas no Railway
2. Ativar chips manualmente via celular
3. Comunicar equipe no Slack
4. Investigar problema com calma

---

## Logs Importantes

```bash
# API
/var/log/chip-activator/api.log
/var/log/chip-activator/api-error.log

# Appium
/var/log/chip-activator/appium.log

# Emulador
/var/log/chip-activator/emulator.log

# Sistema
journalctl -u chip-activator
journalctl -u appium
journalctl -u nginx
```

## Monitoramento

```bash
# Ver metricas
curl http://localhost:8000/metrics -H "X-API-Key: KEY"

# Ver fila em tempo real
watch -n 5 'curl -s http://localhost:8000/queue -H "X-API-Key: KEY" | jq'

# Ver uso de recursos
htop
df -h
free -h
```
EOF
```

### DoD

- [ ] TROUBLESHOOTING.md criado
- [ ] Problemas comuns documentados
- [ ] Procedimentos de emergencia definidos

---

## Story 6.3: Runbook de Operacao

### Objetivo
Criar procedimentos operacionais padronizados.

### Passo a Passo

**1. Criar RUNBOOK.md**

```bash
cat > /opt/chip-activator/RUNBOOK.md << 'EOF'
# Runbook - Chip Activator

## Procedimentos Operacionais

### 1. Verificacao Diaria (Health Check)

**Frequencia:** 1x ao dia (manha)

```bash
# 1. Verificar status dos servicos
systemctl status chip-activator appium nginx

# 2. Verificar health da API
curl http://localhost:8000/health

# 3. Verificar metricas
curl http://localhost:8000/metrics -H "X-API-Key: KEY"

# 4. Verificar espaco em disco
df -h /

# 5. Verificar logs de erro
tail -20 /var/log/chip-activator/api-error.log
```

**Criterios OK:**
- Todos os servicos "active (running)"
- Health status "healthy"
- Disco com >20% livre
- Sem erros criticos nos logs

---

### 2. Atualizacao do WhatsApp APK

**Frequencia:** Mensal ou quando UI mudar

**Procedimento:**

```bash
# 1. Baixar novo APK do APKMirror
# https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/

# 2. Copiar para VPS
scp whatsapp-new.apk usuario@VPS:/tmp/

# 3. No VPS
cd /opt/chip-activator

# 4. Backup do APK atual
cp apks/whatsapp.apk apks/whatsapp.apk.bak

# 5. Substituir
mv /tmp/whatsapp-new.apk apks/whatsapp.apk

# 6. Reinstalar no emulador
/opt/chip-activator/stop_emulator.sh
sleep 5
/opt/chip-activator/start_emulator.sh
sleep 60
adb uninstall com.whatsapp
/opt/chip-activator/install_whatsapp.sh

# 7. Testar ativacao
# (usar numero de teste)
```

---

### 3. Limpeza de Logs e Screenshots

**Frequencia:** Semanal

```bash
# 1. Limpar screenshots antigos (>7 dias)
find /var/log/chip-activator/screenshots -type f -mtime +7 -delete

# 2. Verificar tamanho dos logs
du -sh /var/log/chip-activator/*

# 3. Logrotate deve cuidar, mas forcar se necessario
sudo logrotate -f /etc/logrotate.d/chip-activator
```

---

### 4. Reinicio Preventivo

**Frequencia:** Semanal (domingo noite)

```bash
# 1. Verificar se fila esta vazia
curl http://localhost:8000/queue -H "X-API-Key: KEY"
# Deve mostrar size: 0

# 2. Reiniciar servicos
sudo systemctl restart appium
sleep 10
sudo systemctl restart chip-activator

# 3. Reiniciar emulador
/opt/chip-activator/stop_emulator.sh
sleep 5
/opt/chip-activator/start_emulator.sh

# 4. Verificar health
curl http://localhost:8000/health
```

---

### 5. Escalonamento de Incidentes

**Nivel 1 - Auto-resolucao (Dev Junior):**
- Reiniciar servicos
- Limpar logs/cache
- Reinstalar WhatsApp

**Nivel 2 - Investigacao (Dev Senior):**
- Analisar logs detalhados
- Ajustar locators de automacao
- Atualizar dependencias

**Nivel 3 - Infra (Ops/Rafael):**
- Problemas de KVM/virtualizacao
- Migracao de VPS
- Questoes de rede/SSL

---

### 6. Adicionar Novo Locator (WhatsApp Mudou UI)

Quando WhatsApp atualiza e elementos mudam:

```bash
# 1. Conectar ao emulador via Appium Inspector
# https://github.com/appium/appium-inspector

# 2. Navegar ate a tela problematica

# 3. Identificar novo locator (ID, XPath, etc)

# 4. Atualizar whatsapp_automation.py
nano /opt/chip-activator/whatsapp_automation.py

# 5. Testar
cd /opt/chip-activator
source venv/bin/activate
python whatsapp_automation.py 11999990001 123456 http://example.com/qr

# 6. Se OK, reiniciar servico
sudo systemctl restart chip-activator
```

---

## Contatos

| Funcao | Contato |
|--------|---------|
| Dev Junior | @junior no Slack |
| Dev Senior | @senior no Slack |
| Ops/Infra | @rafael no Slack |

## Historico de Mudancas

| Data | Descricao | Autor |
|------|-----------|-------|
| YYYY-MM-DD | Criacao inicial | Dev Junior |
EOF
```

### DoD

- [ ] RUNBOOK.md criado
- [ ] Procedimentos operacionais documentados

---

## Story 6.4: Atualizar CLAUDE.md

### Objetivo
Adicionar referencia a Sprint 27 no CLAUDE.md do projeto.

### Passo a Passo

**1. Atualizar tabela de sprints**

Adicionar na tabela de "Sprints Concluidas" quando finalizar:

```markdown
| 27 | Ativacao Automatizada de Chips | ✅ Completa |
```

**2. Adicionar secao de infraestrutura**

```markdown
### VPS Hostinger (Chip Activator)

Sistema de ativacao automatizada de chips WhatsApp.

| Componente | Valor |
|------------|-------|
| URL | https://activator.example.com |
| Servico | chip-activator, appium, nginx |
| Logs | /var/log/chip-activator/ |
| Docs | planning/sprint-27/ |
```

### DoD

- [ ] CLAUDE.md atualizado com Sprint 27

---

## Checklist Final E06

- [ ] **Story 6.1** - README.md operacional
- [ ] **Story 6.2** - TROUBLESHOOTING.md
- [ ] **Story 6.3** - RUNBOOK.md
- [ ] **Story 6.4** - CLAUDE.md atualizado

---

## Arquivos Criados

```
/opt/chip-activator/
├── README.md              # Visao geral e comandos rapidos
├── TROUBLESHOOTING.md     # Problemas e solucoes
└── RUNBOOK.md             # Procedimentos operacionais
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 6.1 README | 30min |
| 6.2 Troubleshooting | 45min |
| 6.3 Runbook | 30min |
| 6.4 CLAUDE.md | 15min |
| **Total** | ~2 horas |

---

## Sprint Concluida!

Ao finalizar todos os epicos, a Sprint 27 esta completa.

### Checklist Final da Sprint

- [ ] E00 - KVM validado
- [ ] E01 - VPS configurado (Android SDK, emulador)
- [ ] E02 - Automacao WhatsApp funcionando
- [ ] E03 - API de ativacao respondendo
- [ ] E04 - Deploy em producao (Systemd, Nginx, SSL)
- [ ] E05 - Integracao com Railway
- [ ] E06 - Documentacao completa
- [ ] 5 ativacoes reais com >80% sucesso

### Metricas de Sucesso

| Metrica | Meta | Atual |
|---------|------|-------|
| Taxa de sucesso | >90% | ___ |
| Tempo medio | <5 min | ___ |
| Intervencao manual | <10% | ___ |
| Downtime API | <1h/mes | ___ |
EOF
```

### DoD

- [ ] Todos os documentos criados
- [ ] Checklist final da sprint documentado
