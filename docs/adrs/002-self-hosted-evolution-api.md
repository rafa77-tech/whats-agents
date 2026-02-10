# ADR-002: Evolution API Self-Hosted para WhatsApp

- Status: Aceita
- Data: Dezembro 2025
- Sprint: Sprint 0-1
- Decisores: Equipe de Engenharia

## Contexto

O Agente Julia precisa enviar e receber mensagens via WhatsApp para interagir com medicos. Existem varias opcoes de integracao:

1. **WhatsApp Business API Oficial** (Meta)
   - Requer aprovacao da Meta
   - Custo por conversa ($0.005-0.05 por mensagem)
   - Processo de onboarding complexo (1-2 semanas)

2. **Provedor SaaS** (Twilio, MessageBird, etc)
   - Infraestrutura gerenciada
   - Custo alto ($0.01-0.10 por mensagem)
   - Dependencia de terceiro

3. **API Nao-Oficial Self-Hosted** (Evolution API, Baileys, etc)
   - Controle total
   - Custo de infraestrutura apenas (servidor)
   - Risco de ban (uso nao-oficial)

**Requisitos especificos:**
- Multiplos numeros simultaneos (chips system)
- Controle total de delivery e read receipts
- Latencia baixa (< 2s para envio)
- Sem custo por mensagem (volume alto esperado: 1.000+ msgs/dia)

## Decisao

Usar **Evolution API self-hosted** como provider primario de WhatsApp:

1. **Evolution API** (Docker container)
   - Open source, mantido ativamente
   - Multi-device support (varios numeros em uma instancia)
   - API REST completa (send, receive, status, media)
   - Webhook para mensagens recebidas

2. **Z-API como fallback**
   - Provider HTTP alternativo
   - Ativado se Evolution ficar indisponivel
   - Circuit breaker pattern para failover

3. **Deployment**
   - Docker Compose local para desenvolvimento
   - Railway/VPS para producao
   - Cada chip = 1 instancia Evolution (isolamento)

**Trade-off consciente:** Risco de ban vs custo e controle.

## Alternativas Consideradas

### 1. WhatsApp Business API Oficial (Meta)
- **Pros**:
  - Totalmente oficial, sem risco de ban
  - Suporte da Meta
  - Escalabilidade ilimitada
- **Cons**:
  - Custo proibitivo ($0.005-0.05/msg * 30k msgs/mes = $150-1500/mes)
  - Processo de aprovacao complexo
  - Templates pre-aprovados (menos flexibilidade)
  - Webhooks com latencia variavel
- **Rejeicao**: Custo e rigidez de templates incompativeis com conversas naturais

### 2. Twilio WhatsApp API
- **Pros**:
  - Infraestrutura robusta
  - Documentacao excelente
  - Compliance garantido
- **Cons**:
  - Custo alto ($0.01-0.05/msg)
  - Dependencia de terceiro (vendor lock-in)
  - Menos controle sobre delivery flow
- **Rejeicao**: Custo e vendor lock-in

### 3. Baileys (biblioteca Node.js)
- **Pros**:
  - Open source, controle total
  - Sem custo de SaaS
  - Comunidade ativa
- **Cons**:
  - Requer desenvolvimento customizado
  - Stack Node.js (projeto eh Python)
  - Manutencao complexa
- **Rejeicao**: Evolution API oferece mesma funcionalidade com API pronta

### 4. Green API / Chat API
- **Pros**:
  - APIs prontas para uso
  - Precos competitivos
- **Cons**:
  - Menos controle que self-hosted
  - Risco de descontinuacao
  - Menos features (grupos, multi-device)
- **Rejeicao**: Menos features e controle que Evolution

## Consequencias

### Positivas

1. **Custo operacional minimo**
   - Apenas servidor ($20-50/mes para N chips)
   - Vs $150-1500/mes com API oficial
   - ROI positivo a partir de 200 mensagens/mes

2. **Controle total de delivery**
   - Acesso a status delivery (enviado, entregue, lido)
   - Marks read customizado
   - Typing indicator ("digitando...")

3. **Suporte a multiplos chips**
   - 1 instancia Evolution = 1 numero
   - Escalar horizontalmente (N containers)
   - Warm-up individual por chip

4. **Flexibilidade de mensagens**
   - Sem restricoes de templates
   - Conversas naturais ilimitadas
   - Media (imagens, docs, audio)

5. **Latencia controlada**
   - Deploy local ou VPS dedicado
   - < 500ms para envio de mensagem
   - Sem dependencia de API externa lenta

### Negativas

1. **Risco de ban do WhatsApp**
   - Uso nao-oficial viola ToS
   - Possibilidade de numero ser bloqueado
   - Mitigacao: warm-up, rate limiting rigoroso, comportamento humano

2. **DevOps overhead**
   - Precisa gerenciar containers Docker
   - Monitoramento de saude de instancias
   - Troubleshooting quando API nao conecta
   - Mitigacao: docker-compose.yml, health checks, circuit breaker

3. **Atualizacoes do WhatsApp**
   - WhatsApp pode mudar protocolo
   - Evolution precisa atualizar
   - Risco de downtime temporario
   - Mitigacao: Z-API fallback, updates regulares

4. **Sem SLA oficial**
   - Comunidade open source, sem garantias
   - Bugs podem nao ser resolvidos rapidamente
   - Mitigacao: contribuir com projeto, manter fork se necessario

### Mitigacoes

1. **Rate limiting rigoroso**
   - 20 msgs/hora por numero
   - 100 msgs/dia por numero
   - Delay humanizado (45-180s entre msgs)
   - Objetivo: parecer humano, evitar deteccao

2. **Warm-up de chips novos**
   - Julia Warmer system (Sprint 25)
   - Trafico gradual antes de uso total
   - Trust score baseado em delivery rate

3. **Circuit breaker + fallback**
   - Z-API como provider alternativo
   - Failover automatico se Evolution down
   - Notificacoes Slack em caso de falha

4. **Monitoring 24/7**
   - Health checks a cada 30s
   - Alertas criticos se instancia offline
   - Dashboard de status em tempo real

5. **Backup de numeros**
   - Pool de 5+ chips sempre prontos
   - Se 1 banido, ativar outro automaticamente
   - Processo de ativacao de chip em < 1h

## Metricas de Sucesso

1. **Uptime > 99.5%** (Evolution API availability)
2. **Taxa de ban < 1 chip/mes** (2% dos chips ativos)
3. **Latencia de envio p95 < 2s**
4. **Custo mensal < $100** (vs $500+ com SaaS)

## Implementacao

### Arquivos Chave
- `docker-compose.yml`: Definicao de servicos Evolution
- `app/services/evolution.py`: Cliente Python para Evolution API
- `app/services/zapi.py`: Cliente Z-API (fallback)
- `app/api/routes/webhook.py`: Endpoint para receber mensagens
- `app/api/routes/webhook_zapi.py`: Endpoint Z-API

### Configuracao
```yaml
# docker-compose.yml
services:
  evolution-api-1:
    image: atendai/evolution-api:latest
    ports:
      - "8080:8080"
    environment:
      - AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY}
      - WEBHOOK_URL=${WEBHOOK_URL}
```

### Failover Logic
```python
# app/services/evolution.py
async def enviar_mensagem(telefone: str, texto: str):
    try:
        return await evolution_client.send(telefone, texto)
    except EvolutionAPIError as e:
        logger.warning("Evolution falhou, usando Z-API")
        return await zapi_client.send(telefone, texto)
```

## Referencias

- Evolution API Docs: https://doc.evolution-api.com/v2/
- Codigo: `app/services/evolution.py`, `app/services/zapi.py`
- Config: `docker-compose.yml`
- Quick Ref: `docs/integracoes/evolution-api-quickref.md`
- Chips System: `docs/arquitetura/chips-system.md` (se existir)

## Historico de Mudancas

- **2025-12**: Decisao inicial (Evolution self-hosted)
- **2026-01**: Sprint 6 - Multi-instancia support
- **2026-01**: Sprint 27 - Z-API fallback implementado
- **2026-02**: Atual - 5 chips ativos, 0 bans no ultimo mes
