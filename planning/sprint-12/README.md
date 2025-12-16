# Sprint 12: Deploy para Producao (VPS + Docker)

## Visao Geral

Colocar o Agente Julia em **producao na VPS** com Docker, garantindo seguranca, monitoramento e capacidade de deploys futuros sem downtime.

**Objetivo:** Sistema rodando em producao, acessivel via HTTPS, com monitoramento e processo de deploy automatizado.

**Status:** 🔴 Nao Iniciada

---

## Pre-requisitos

| Requisito | Descricao | Status |
|-----------|-----------|--------|
| VPS | Ubuntu 22.04+ com minimo 4GB RAM, 2 vCPUs | ⬜ |
| Dominio | Dominio apontando para IP da VPS | ⬜ |
| Acesso SSH | Chave SSH configurada | ⬜ |
| Sprints 0-11 | Todas completas e testadas | ✅ |

---

## Arquitetura de Producao

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VPS (Ubuntu 22.04)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Nginx (Reverse Proxy)                          │   │
│  │                     HTTPS/SSL (Let's Encrypt)                         │   │
│  │                         Porta 80/443                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                 ┌──────────────────┼──────────────────┐                     │
│                 ▼                  ▼                  ▼                     │
│        ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │
│        │ Julia API   │    │ Evolution   │    │  Chatwoot   │               │
│        │   :8000     │    │    :8080    │    │    :3000    │               │
│        └─────────────┘    └─────────────┘    └─────────────┘               │
│                │                                                             │
│        ┌───────┴───────┐                                                    │
│        ▼               ▼                                                    │
│  ┌───────────┐  ┌───────────┐                                              │
│  │  Worker   │  │ Scheduler │                                              │
│  └───────────┘  └───────────┘                                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Servicos de Suporte                            │   │
│  │   Redis :6379    │    PostgreSQL :5432    │    Watchtower             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Monitoramento                                  │   │
│  │        Prometheus :9090    │    Grafana :3001    │    Loki            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Epicos

| # | Epico | Descricao | Stories | Prioridade |
|---|-------|-----------|---------|------------|
| 01 | [Preparacao da VPS](./epic-01-preparacao-vps.md) | Setup inicial, seguranca, Docker | 5 | P0 |
| 02 | [Docker Producao](./epic-02-docker-producao.md) | Ajustes Docker, secrets, volumes | 4 | P0 |
| 03 | [SSL e Dominio](./epic-03-ssl-dominio.md) | Nginx, certificado, DNS | 4 | P0 |
| 04 | [Monitoramento](./epic-04-monitoramento.md) | Prometheus, Grafana, alertas | 4 | P1 |
| 05 | [Deploy Automatizado](./epic-05-deploy-automatizado.md) | Scripts, CI/CD, rollback | 4 | P1 |

---

## Ordem de Execucao

```
Dia 1:
├── E01.1 - Provisionar VPS
├── E01.2 - Hardening de seguranca
├── E01.3 - Instalar Docker
└── E01.4 - Configurar firewall

Dia 2:
├── E01.5 - Clonar repositorio
├── E02.1 - Ajustar docker-compose.prod.yml
├── E02.2 - Configurar secrets
└── E02.3 - Setup volumes persistentes

Dia 3:
├── E02.4 - Build e teste local
├── E03.1 - Configurar dominio DNS
├── E03.2 - Instalar Nginx
└── E03.3 - Configurar SSL Let's Encrypt

Dia 4:
├── E03.4 - Testar HTTPS end-to-end
├── E04.1 - Setup Prometheus
├── E04.2 - Setup Grafana
└── E04.3 - Configurar dashboards

Dia 5:
├── E04.4 - Alertas Slack
├── E05.1 - Script de deploy
├── E05.2 - Script de rollback
├── E05.3 - Backup automatico
└── E05.4 - Documentar runbook
```

---

## Servicos e Portas

| Servico | Porta Interna | Porta Externa | Acesso |
|---------|---------------|---------------|--------|
| Julia API | 8000 | 443 (via nginx) | HTTPS |
| Julia Worker | - | - | Interno |
| Julia Scheduler | - | - | Interno |
| Evolution API | 8080 | 443 (via nginx) | HTTPS |
| Chatwoot | 3000 | 443 (via nginx) | HTTPS |
| Redis | 6379 | - | Interno |
| PostgreSQL | 5432 | - | Interno |
| Prometheus | 9090 | - | Interno |
| Grafana | 3001 | 443 (via nginx) | HTTPS (protegido) |

---

## Recursos Necessarios

### VPS Minima (Desenvolvimento/Teste)
- **CPU:** 2 vCPUs
- **RAM:** 4 GB
- **Disco:** 40 GB SSD
- **Custo:** ~$20-30/mes

### VPS Recomendada (Producao)
- **CPU:** 4 vCPUs
- **RAM:** 8 GB
- **Disco:** 80 GB SSD
- **Custo:** ~$40-60/mes

### Provedores Sugeridos
- DigitalOcean (Droplets)
- Vultr
- Hetzner (melhor custo-beneficio na Europa)
- Contabo
- AWS Lightsail

---

## Checklist de Seguranca

- [ ] SSH apenas por chave (sem senha)
- [ ] Firewall ativo (UFW)
- [ ] Fail2ban instalado
- [ ] Usuarios nao-root para aplicacao
- [ ] Secrets em arquivos .env protegidos (chmod 600)
- [ ] HTTPS obrigatorio
- [ ] Headers de seguranca no Nginx
- [ ] Backups automaticos configurados
- [ ] Logs centralizados

---

## Definition of Done (Sprint)

A sprint so esta completa quando:

- [ ] VPS provisionada e acessivel via SSH
- [ ] Docker e Docker Compose instalados
- [ ] Firewall configurado (apenas 22, 80, 443)
- [ ] Todos os containers rodando sem erros
- [ ] HTTPS funcionando com certificado valido
- [ ] Webhook Evolution API respondendo
- [ ] Chatwoot acessivel externamente
- [ ] Julia API respondendo em /health
- [ ] Monitoramento basico funcionando
- [ ] Alertas de downtime configurados
- [ ] Script de deploy funcionando
- [ ] Backup diario configurado
- [ ] Runbook documentado

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| VPS fica sem espaco | Media | Alto | Alertas de disco, log rotation |
| Certificado SSL expira | Baixa | Alto | Auto-renewal com certbot |
| Container morre | Media | Alto | Restart policies, health checks |
| Banco corrompido | Baixa | Critico | Backup diario, replicacao |
| Ataque DDoS | Baixa | Alto | Rate limiting, Cloudflare |

---

## Estimativas

| Epico | Complexidade | Horas Estimadas |
|-------|--------------|-----------------|
| 01 - Preparacao VPS | Media | 4h |
| 02 - Docker Producao | Media | 3h |
| 03 - SSL e Dominio | Media | 3h |
| 04 - Monitoramento | Media | 4h |
| 05 - Deploy Automatizado | Alta | 4h |
| **Total** | | **~18h** |

---

## Proximos Passos

1. Contratar VPS com especificacoes recomendadas
2. Registrar/configurar dominio
3. Comecar pelo [Epic 01: Preparacao VPS](./epic-01-preparacao-vps.md)
