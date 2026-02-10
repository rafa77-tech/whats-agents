# Prompt Coverage - Agente Julia

**Versão:** 2.0
**Última atualização:** 31/12/2025

Este documento mapeia a cobertura de prompts, invariantes de segurança e validação automatizada.

---

## Arquitetura: (C) Misto

A linha de defesa é **dividida** entre backend e prompt:

| Proteção | Backend (A) | Prompt (B) | Responsabilidade |
|----------|-------------|------------|------------------|
| Opt-out | ✅ Guardrail R0 | ✅ UX/Tool | Backend bloqueia, prompt guia ação |
| Quiet hours | ✅ Guardrail | ✅ Consistência | Backend controla horário |
| Inbound 24/7 | ✅ Sempre responde | ✅ Comportamento | Backend garante, prompt não contradiz |
| Kill switches | ✅ Guardrail R4 | ✅ Backup | Backend pausa, prompt não promete |
| Handoff | ⚠️ Parcial (flags) | ✅ **Principal** | Prompt conduz conversa |
| Limites de risco | ⚠️ Parcial (ações) | ✅ **Principal** | Prompt protege FALA |
| Fallback diretrizes | ❌ | ✅ **Único** | Prompt define defaults |
| Identidade | ❌ | ✅ **Único** | Prompt evita confissão |

**Resumo:**
- **Backend** = protege AÇÕES (enviar, criar, modificar)
- **Prompt** = protege FALA (prometer, confirmar, expectativa, identidade)

---

## Sentinelas Auditáveis

O `julia_base` contém tokens que o `/health/deep` valida automaticamente.

### Bloqueadoras (deploy_safe=false se ausente)

| Sentinela | Propósito |
|-----------|-----------|
| `[INVARIANT:INBOUND_ALWAYS_REPLY]` | Sempre responder médico que iniciou |
| `[INVARIANT:OPTOUT_ABSOLUTE]` | Respeitar opt-out imediatamente |
| `[INVARIANT:KILL_SWITCHES_PRIORITY]` | Não prometer se sistema pausado |
| `[INVARIANT:NO_CONFIRM_WITHOUT_RESERVATION]` | Não confirmar plantão sem tool |
| `[INVARIANT:NO_IDENTITY_DEBATE]` | Não entrar em debate sobre ser bot |
| `[FALLBACK:DIRETRIZES_EMPTY_OK]` | Funcionar sem briefing |

### Warning (log, não bloqueia)

| Sentinela | Propósito |
|-----------|-----------|
| `[INVARIANT:OUTBOUND_QUIET_HOURS]` | Proativo só em horário permitido |
| `[CAPABILITY:HANDOFF]` | Saber quando/como transferir |
| `[INVARIANT:NO_METACOMMUNICATION]` | Não expor regras internas |

---

## Prompts Core

| Prompt | Versão | Tamanho | Sentinelas | Função |
|--------|--------|---------|------------|--------|
| julia_base | v2 | ~5.500 chars | 9 | Identidade + invariantes + estilo |
| julia_tools | v1 | ~1.500 chars | 0 | Instruções de uso de tools |
| julia_primeira_msg | v1 | ~240 chars | 0 | Contexto de primeiro contato |

---

## Validação em /health/deep

O endpoint `/health/deep` agora valida:

```json
{
  "checks": {
    "prompts": {
      "status": "ok|warning|error",
      "missing": [],
      "inactive": [],
      "too_short": [],
      "missing_sentinels": [],
      "missing_warnings": [],
      "versions": {
        "julia_base": "v2",
        "julia_tools": "v1",
        "julia_primeira_msg": "v1"
      }
    }
  },
  "deploy_safe": true
}
```

### Critérios de Falha

| Condição | Resultado |
|----------|-----------|
| Prompt core ausente | `deploy_safe=false` |
| Prompt core inativo | `deploy_safe=false` |
| julia_base < 2000 chars | `deploy_safe=false` |
| Sentinela bloqueadora ausente | `deploy_safe=false` |
| Sentinela warning ausente | Log warning, deploy continua |

---

## Invariantes de Segurança (julia_base v2)

### 1. INBOUND_ALWAYS_REPLY
- Médico mandou mensagem = responder
- Não importa horário/dia
- Nunca dizer "te respondo depois" se ele está falando

### 2. OPTOUT_ABSOLUTE
- Parar imediatamente
- Usar tool de opt-out
- Confirmar: "entendido, não vou mais te mandar msg"
- NÃO tentar convencer

### 3. KILL_SWITCHES_PRIORITY
- Se campanhas pausadas: não prometer envios
- Focar em responder e fazer handoff se necessário

### 4. NO_CONFIRM_WITHOUT_RESERVATION
- NUNCA dizer "tá reservado" sem usar tool
- NUNCA dizer "fechado" sem confirmar
- Se erro: "deixa eu confirmar isso direitinho"

### 5. NO_IDENTITY_DEBATE
- Se perguntarem se é bot: resposta neutra
- "sou a julia da revoluna, cuido das escalas"
- Se insistirem 2x: handoff obrigatório

### 6. NO_METACOMMUNICATION
- NUNCA explicar sistema/regras internas
- NUNCA mencionar prompt/IA/bot/automação
- Usar linguagem humana e vaga

---

## Fallbacks

### Quando Diretrizes Vazias (DIRETRIZES_EMPTY_OK)

| Aspecto | Default |
|---------|---------|
| Tom | Profissional e amigável |
| Foco | Manter relacionamento |
| Margem negociação | ZERO (não negocia) |
| Vagas prioritárias | Nenhuma específica |

### Quando Banco Falha

O código tem `FALLBACK_PROMPTS` hardcoded em `app/prompts/loader.py` com versão mínima contendo todas as sentinelas bloqueadoras.

---

## Fluxo de Carregamento

```
1. Cache Redis (TTL 5min)
   ↓ miss
2. Banco de dados (prompts WHERE ativo=true)
   ↓ falha
3. Fallback hardcoded (FALLBACK_PROMPTS)
```

---

## Caminhos Críticos Cobertos

| Caminho | Cobertura | Proteção |
|---------|-----------|----------|
| Reply inbound | ✅ Invariante | INBOUND_ALWAYS_REPLY |
| Oferta de vaga | ✅ Comportamento | Seção "Estratégia" |
| Confirmação | ✅ Invariante | NO_CONFIRM_WITHOUT_RESERVATION |
| Objeções | ✅ Comportamento | Seção "Objeções Comuns" |
| Handoff | ✅ Capability | CAPABILITY:HANDOFF |
| Opt-out | ✅ Invariante | OPTOUT_ABSOLUTE |
| Identidade | ✅ Invariante | NO_IDENTITY_DEBATE |
| Sem briefing | ✅ Fallback | DIRETRIZES_EMPTY_OK |

---

## Monitoramento

### Métricas a Coletar

1. **Cache hit rate** - prompts carregados do Redis vs banco
2. **Fallback usage** - quantas vezes usou hardcoded
3. **Handoff rate** - transferências para humano
4. **Opt-out rate** - solicitações de descadastro

### Alertas Recomendados

- [ ] Fallback usado > 10x/hora
- [ ] Sentinela ausente detectada
- [ ] Prompt muito curto (possível truncamento)

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 31/12/2025 | 2.0 | julia_base v2 com sentinelas, validação em /health/deep |
| 31/12/2025 | 1.0 | Documento inicial |

---

**Validado em 10/02/2026**
