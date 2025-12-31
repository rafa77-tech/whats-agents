# Sprint 27: Sistema Automatizado de Ativacao de Chips WhatsApp

**Status:** Planejado
**Inicio:** A definir (paralelo com Sprint 25)
**Estimativa:** 2 semanas
**Dependencias:** Nenhuma (pode rodar em paralelo com Sprint 25/26)
**Responsavel:** Dev Junior

---

## Objetivo

Criar **sistema automatizado de ativacao de chips WhatsApp** usando emulador Android em VPS, eliminando o gargalo de ativacao manual.

### Problema Atual

```
HOJE (Manual):
┌─────────────────────────────────────────────────────────────┐
│  1. Salvy cria numero                                       │
│  2. Evolution cria instancia e gera QR code                 │
│  3. [GARGALO] Rafael escaneia QR no celular pessoal         │ ← 5-10 min CADA
│  4. WhatsApp envia SMS com codigo                           │
│  5. Rafael insere codigo manualmente                        │
│  6. Chip ativado!                                           │
└─────────────────────────────────────────────────────────────┘

Para 50 chips = 50 × 10 min = 8+ HORAS de trabalho manual
```

### Solucao

```
DEPOIS (Automatizado):
┌─────────────────────────────────────────────────────────────┐
│  1. Salvy cria numero                                       │
│  2. Evolution cria instancia e gera QR code                 │
│  3. [API] Backend chama POST /activate no VPS               │
│  4. [VPS] Emulador Android liga, escaneia QR                │ ← AUTOMATICO
│  5. [VPS] Webhook Salvy entrega codigo SMS                  │
│  6. [VPS] Emulador insere codigo                            │
│  7. [VPS] Chip ativado! Emulador desliga                    │
│  8. [API] Backend atualiza status do chip                   │
└─────────────────────────────────────────────────────────────┘

Para 50 chips = 50 × 5 min = ~4 HORAS SEM INTERVENCAO
```

---

## Por Que Paralelo com Sprint 25?

| Fator | Justificativa |
|-------|---------------|
| **Independencia tecnica** | Sprint 27 roda em VPS isolado, zero codigo compartilhado com 25/26 |
| **Gargalo critico** | Sem ativacao automatica, o multi-chip de 25/26 nao escala |
| **Risco tecnico** | Melhor descobrir se KVM funciona ANTES de precisar |
| **Tempo de teste** | Sistema de ativacao precisa ser testado antes de producao |
| **Dev junior** | Pode focar 100% nesta sprint enquanto senior faz 25/26 |

---

## Pre-Requisitos para Inicio

**ANTES de comecar E01, garantir que tudo abaixo esta pronto:**

| Item | Responsavel | Status |
|------|-------------|--------|
| VPS Hostinger: credenciais SSH | Rafael | [ ] |
| Dominio configurado: `activator.revoluna.com.br` | Rafael | [ ] |
| API Key gerada para auth Railway → VPS | Rafael | [ ] |
| WhatsApp APK: versao estavel identificada | Dev Junior | [ ] |
| Salvy webhook: endpoint `/webhooks/salvy/sms` configurado | Dev Senior | [ ] |
| Slack webhook: canal `#alertas-chips` com webhook URL | Rafael | [ ] |

### Dados Necessarios (Pedir ao Rafael)

```
# VPS Hostinger
SSH_HOST=???
SSH_USER=???
SSH_PASSWORD=??? (ou chave SSH)

# Dominio
DOMAIN=activator.revoluna.com.br (ou IP temporario)

# API Key (gerar uma forte)
API_KEY=??? (minimo 32 caracteres)

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

### Checklist Pre-Sprint

- [ ] Consegue conectar via SSH ao VPS
- [ ] Dominio/IP acessivel na internet
- [ ] Canal Slack criado e webhook funcionando
- [ ] Webhook Salvy configurado para receber SMS

---

## Arquitetura

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         FLUXO DE ATIVACAO                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   RAILWAY (Backend Julia)                VPS HOSTINGER                     │
│   ┌─────────────────────┐               ┌─────────────────────┐           │
│   │                     │               │                     │           │
│   │  1. Chip novo       │               │   API Ativacao      │           │
│   │     precisa ativar  │               │   (FastAPI)         │           │
│   │                     │               │                     │           │
│   │  2. Provisiona      │               │   POST /activate    │           │
│   │     numero Salvy    │    ─────────> │   {                 │           │
│   │                     │    HTTP       │     numero,         │           │
│   │  3. Cria instancia  │               │     codigo_sms,     │           │
│   │     Evolution       │               │     qr_code_url     │           │
│   │                     │               │   }                 │           │
│   │  4. Gera QR code    │               │                     │           │
│   │                     │               └──────────┬──────────┘           │
│   │  5. Aguarda webhook │                          │                      │
│   │     Salvy (SMS)     │                          ▼                      │
│   │                     │               ┌─────────────────────┐           │
│   │  6. Chama           │               │   Emulador Android  │           │
│   │     POST /activate  │               │   (Efemero)         │           │
│   │                     │               │                     │           │
│   └─────────────────────┘               │   - Liga (~40s)     │           │
│            │                            │   - Abre WhatsApp   │           │
│            │                            │   - Registra numero │           │
│            │                            │   - Escaneia QR     │           │
│            ▼                            │   - Desliga         │           │
│   ┌─────────────────────┐               │                     │           │
│   │  7. Atualiza status │               └─────────────────────┘           │
│   │     chip: connected │                                                 │
│   │                     │                                                 │
│   │  8. Chip entra no   │                                                 │
│   │     pool warming    │                                                 │
│   └─────────────────────┘                                                 │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Componentes do Sistema

```
VPS HOSTINGER
├── /opt/chip-activator/           # Diretorio principal
│   ├── main.py                    # FastAPI app
│   ├── emulator.py                # Gerenciador do emulador
│   ├── whatsapp_automation.py     # Automacao Appium
│   ├── queue.py                   # Fila de ativacoes
│   ├── config.py                  # Configuracoes
│   └── requirements.txt           # Dependencias Python
│
├── /var/log/chip-activator/       # Logs
│   ├── activator.log              # Log principal
│   └── screenshots/               # Capturas de erro
│
├── Android SDK                    # SDK Android
│   ├── emulator/                  # Emulador
│   ├── platform-tools/            # ADB
│   └── system-images/             # Imagem Android
│
├── Appium Server                  # Automacao UI
│
└── Nginx                          # Proxy reverso + SSL
```

---

## Stack Tecnico

| Componente | Tecnologia | Versao | Motivo |
|------------|------------|--------|--------|
| VPS | Hostinger (existente) | Ubuntu 22.04 | Ja temos, suporte KVM |
| Emulador | Android SDK + Emulator | API 30 (Android 11) | Estavel, WhatsApp funciona |
| Automacao | Appium + Python | 2.x | Padrao industria mobile |
| API | FastAPI | 0.109+ | Leve, async, familiar |
| Proxy | Nginx | 1.18+ | SSL, proxy reverso |
| SSL | Certbot | Latest | Let's Encrypt gratuito |
| Process | Systemd | Native | Auto-restart, logs |

---

## Epicos

| # | Epico | Descricao | Tempo | Prioridade |
|---|-------|-----------|-------|------------|
| E00 | Validacao KVM | Verificar se VPS suporta virtualizacao | 1h | BLOQUEANTE |
| E01 | Setup VPS | Android SDK, emulador, AVD | 4h | Alta |
| E02 | Automacao WhatsApp | Script Appium completo | **12h** | Alta |
| E03 | API de Ativacao | FastAPI com endpoints | 3h | Alta |
| E04 | Deploy e Monitoramento | Systemd, Nginx, SSL, alertas | 3h | Alta |
| E05 | Integracao Railway | Chamada API no backend Julia | 2h | Alta |
| E06 | Documentacao e Runbook | README, troubleshooting | 2h | Media |

**Total Estimado:** ~27h (2 semanas com buffer)

> **Nota sobre E02:** Estimativa considera curva de aprendizado com Appium para dev junior.
> Breakdown realista: 4h setup/aprender + 4h automacao inicial + 4h debugging edge cases.

---

## Ordenacao de Execucao

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPENDENCIAS ENTRE EPICOS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   E00 (Validacao KVM) ──────────────────────────────────────┐   │
│         │                                                    │   │
│         │  SE KVM OK                                         │   │
│         ▼                                                    │   │
│   E01 (Setup VPS) ───────────────────────────────────────┐  │   │
│         │                                                 │  │   │
│         ▼                                                 │  │   │
│   E02 (Automacao WhatsApp) ◄─────────────────────────────┘  │   │
│         │                                                    │   │
│         ▼                                                    │   │
│   E03 (API de Ativacao)                                      │   │
│         │                                                    │   │
│         ▼                                                    │   │
│   E04 (Deploy e Monitoramento)                               │   │
│         │                                                    │   │
│         ▼                                                    │   │
│   E05 (Integracao Railway)                                   │   │
│         │                                                    │   │
│         ▼                                                    │   │
│   E06 (Documentacao)                                         │   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**IMPORTANTE:** E00 e BLOQUEANTE. Se KVM nao funcionar, parar e comunicar.

---

## Requisitos Funcionais

### RF01 - Endpoint de Ativacao

```
POST /activate
Content-Type: application/json
X-API-Key: {chave_secreta}

{
  "numero": "5511999990001",
  "codigo_sms": "123456",
  "evolution_qr_url": "https://evolution.railway.app/qr/001"
}

Response (sucesso):
{
  "status": "success",
  "message": "Chip ativado com sucesso",
  "tempo_segundos": 245,
  "chip_id": "julia-001"
}

Response (erro):
{
  "status": "error",
  "message": "Timeout ao escanear QR code",
  "step": "scan_qr",
  "screenshot_url": "/screenshots/2025-01-15_14-30-00.png"
}
```

### RF02 - Gerenciamento de Emulador

- Inicia emulador on-demand (nao fica ligado 24/7)
- Garante shutdown apos ativacao (sucesso ou falha via `finally:` block)
- **Timeouts escalonados:**
  - Boot emulador: 2 min (se nao bootar, kill + retry)
  - Automacao WhatsApp: 5 min
  - Buffer: 1 min
  - **Total: 8 minutos max por ativacao**
- Apenas 1 ativacao por vez (fila sequencial)

### RF03 - Automacao WhatsApp

1. Instala WhatsApp APK (se nao instalado)
2. Abre WhatsApp
3. Aceita termos (se aparecer)
4. Preenche numero de telefone
5. Insere codigo SMS recebido
6. Navega ate "Dispositivos vinculados"
7. Clica em "Vincular dispositivo"
8. Escaneia QR code da Evolution API
9. Aguarda confirmacao de pareamento
10. Fecha WhatsApp

### RF04 - Fila Sequencial

- Apenas 1 ativacao por vez
- Novas requisicoes entram na fila
- Timeout de fila: 10 minutos
- Endpoint para consultar status: GET /queue

### RF05 - Health Check

```
GET /health

Response:
{
  "status": "healthy",
  "emulator": "idle",  // idle, running, error
  "queue_size": 0,
  "last_activation": "2025-01-15T14:30:00Z",
  "uptime_seconds": 86400
}
```

---

## Requisitos Nao-Funcionais

### RNF01 - Performance

| Metrica | Meta |
|---------|------|
| Tempo medio ativacao | < 5 minutos |
| Tempo boot emulador | < 60 segundos |
| Throughput | 20-30 ativacoes/dia |

### RNF02 - Confiabilidade

| Metrica | Meta |
|---------|------|
| Taxa de sucesso | > 90% |
| Retry automatico | 1x em caso de falha |
| Alertas Slack | Em falhas consecutivas (3+) |

### RNF03 - Seguranca

- HTTPS obrigatorio (Let's Encrypt)
- API key para autenticacao
- Logs NAO expõem codigos SMS completos (mascarar)
- Acesso restrito por IP (opcional)

### RNF04 - Manutenibilidade

- Systemd service (auto-restart)
- Logs estruturados (JSON)
- Health check endpoint
- Screenshots em caso de erro

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| **VPS nao suporta KVM** | Media | BLOQUEANTE | E00 valida ANTES de tudo; fallback: Hetzner R$ 100/mes |
| **WhatsApp muda UI** | Baixa | Alto | Versionamento do APK; locators flexiveis; testes regulares |
| **Emulador trava** | Media | Medio | Timeout boot 2min, total 8min + kill process + retry |
| **Deteccao de emulador** | Baixa | Alto | Usar emulador vanilla; monitorar bans; testar com chips descartaveis |
| **Falha de rede** | Baixa | Medio | Retry com backoff; fila persistente |

### Fallback

Se Sprint 27 falhar completamente:
- Volta para ativacao manual (Rafael)
- Nao bloqueia Sprint 25/26
- Reavalia alternativas (Hetzner, farm celulares)

---

## Metricas de Sucesso

**Apos 2 semanas em producao:**

| Metrica | Meta | Como Medir |
|---------|------|------------|
| Taxa de sucesso | > 90% | `ativacoes_sucesso / ativacoes_total` |
| Tempo medio | < 5 min | Media de `tempo_segundos` nos logs |
| Intervencao manual | < 10% | `ativacoes_manuais / ativacoes_total` |
| Downtime API | < 1h/mes | Uptime do health check |
| Alertas Slack | < 5/semana | Contagem de notificacoes |

---

## Cronograma

```
SEMANA 1:
├─ Dia 1 (1h):
│   └─ E00: Validacao KVM
│       └─ SE FALHAR: Parar e comunicar
│
├─ Dia 1-2 (4h):
│   └─ E01: Setup VPS
│       ├─ Instalar Android SDK
│       ├─ Criar AVD
│       └─ Testar emulador
│
├─ Dia 3-5 (12h):
│   └─ E02: Automacao WhatsApp
│       ├─ Dia 3: Instalar Appium, aprender, primeiros testes
│       ├─ Dia 4: Script de automacao (50% funcionando)
│       └─ Dia 5: Debugging edge cases, testes finais

SEMANA 2:
├─ Dia 1 (3h):
│   └─ E03: API de Ativacao
│       ├─ FastAPI endpoints
│       └─ Integracao com emulador
│
├─ Dia 2 (3h):
│   └─ E04: Deploy
│       ├─ Systemd service
│       ├─ Nginx + SSL
│       └─ Alertas Slack
│
├─ Dia 3 (2h):
│   └─ E05: Integracao Railway
│       └─ Chamar API do backend
│
├─ Dia 4 (2h):
│   └─ E06: Documentacao
│
└─ Dia 5:
    └─ Testes em producao
        ├─ 5 ativacoes reais
        └─ Ajustes e correcoes
```

---

## Custos

```
┌─────────────────────────────────────────────┐
│              CUSTO TOTAL                    │
├─────────────────────────────────────────────┤
│ Setup inicial:                              │
│ - Dev time: 27h                             │
│ - Infra: R$ 0 (VPS ja existe)               │
│                                             │
│ Recorrente (mensal):                        │
│ - VPS: R$ 0 (ja pago)                       │
│ - Manutencao: ~2h/mes                       │
│                                             │
│ TOTAL ADICIONAL: R$ 0                       │
│                                             │
│ Fallback (se VPS nao tiver KVM):            │
│ - Hetzner CX21: ~R$ 100/mes                 │
└─────────────────────────────────────────────┘
```

---

## Glossario

| Termo | Definicao |
|-------|-----------|
| **KVM** | Kernel-based Virtual Machine. Virtualizacao de hardware no Linux. Necessario para rodar emulador Android em VPS. |
| **AVD** | Android Virtual Device. Configuracao do dispositivo emulado (modelo, API level, RAM, etc). |
| **Appium** | Framework de automacao de UI para apps mobile. Permite controlar WhatsApp programaticamente. |
| **ADB** | Android Debug Bridge. Ferramenta para comunicar com dispositivos Android (emulados ou reais). |
| **Evolution API** | API self-hosted para WhatsApp via Baileys. Gera QR code que precisa ser escaneado. |
| **Salvy** | Provedor de numeros virtuais brasileiros. Recebe SMS e entrega via webhook. |

---

## Arquivos de Epic

- [E00: Validacao KVM](./epic-00-validacao-kvm.md) - BLOQUEANTE
- [E01: Setup VPS](./epic-01-setup-vps.md)
- [E02: Automacao WhatsApp](./epic-02-automacao-whatsapp.md)
- [E03: API de Ativacao](./epic-03-api-ativacao.md)
- [E04: Deploy e Monitoramento](./epic-04-deploy-monitoramento.md)
- [E05: Integracao Railway](./epic-05-integracao-railway.md)
- [E06: Documentacao e Runbook](./epic-06-documentacao-runbook.md)

---

## Definition of Done (Sprint 27)

### Sprint esta COMPLETA quando:

- [ ] **5 chips ativados** automaticamente via API (sem intervencao manual)
- [ ] **Taxa de sucesso >= 80%** nessas 5 ativacoes
- [ ] **Logs estruturados** disponiveis e consultaveis
- [ ] **Rafael consegue ativar 1 chip** sem ajuda do dev (via curl ou script)
- [ ] **Documentacao** permite que qualquer dev debugue problemas

### Sprint NAO esta completa se:

- API funciona mas taxa sucesso < 80%
- Funciona so com dev presente para "dar jeitinho"
- Sem documentacao de troubleshooting
- Logs nao mostram o que deu errado
- Emulador fica travado apos ativacoes

### Criterios de Aceitacao por Epic

| Epic | Criterio |
|------|----------|
| E00 | `kvm-ok` retorna "can be used" |
| E01 | `adb devices` mostra emulador, boot < 2min |
| E02 | Script Python ativa WhatsApp de forma autonoma |
| E03 | `curl /health` retorna status, `curl /activate` adiciona a fila |
| E04 | Servicos sobrevivem reboot do VPS |
| E05 | Chip muda de status `provisioned` -> `warming` automaticamente |
| E06 | README explica como debugar os 5 problemas mais comuns |

---

## Checklist Final

- [ ] **E00** - KVM validado e funcionando
- [ ] **E01** - Android SDK instalado, AVD criado, emulador liga/desliga
- [ ] **E02** - Script Appium ativa WhatsApp end-to-end
- [ ] **E03** - API FastAPI respondendo com autenticacao
- [ ] **E04** - Systemd rodando, Nginx com SSL, alertas Slack
- [ ] **E05** - Backend Julia chama API e atualiza chip
- [ ] **E06** - README e troubleshooting documentados
- [ ] **DoD** - 5 ativacoes reais com >= 80% sucesso

---

*Sprint criada em 31/12/2025*
*Autor: Claude + Rafael*
