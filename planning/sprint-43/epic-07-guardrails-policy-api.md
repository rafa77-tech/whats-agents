# Epic 07 - Guardrails & Policy Engine (API + UI)

## Objetivo
Expor via API HTTP as funcionalidades de guardrails e policy engine que JA EXISTEM no backend mas nao tem endpoints, e criar UI correspondente.

## Descoberta: Backend Completo sem API

O backend possui dois modulos completos sem exposicao HTTP:

### 1. `app/services/sistema_guardrails.py`
```python
# Feature Flags (15+ flags)
FeatureFlag.ENVIO_PROSPECCAO
FeatureFlag.ENVIO_FOLLOWUP
FeatureFlag.ENVIO_RESPOSTA
FeatureFlag.ENVIO_CAMPANHA
FeatureFlag.CHIP_AUTO_REPLACE
FeatureFlag.CHIP_AUTO_PROVISION
FeatureFlag.WORKER_FILA
FeatureFlag.WORKER_CAMPANHAS
FeatureFlag.WORKER_GRUPOS
FeatureFlag.INTEGRATION_EVOLUTION
FeatureFlag.INTEGRATION_CHATWOOT
FeatureFlag.INTEGRATION_SLACK
# ... etc

# Funcoes disponiveis
async def obter_feature_flag(flag) -> bool
async def definir_feature_flag(flag, habilitada, motivo, usuario) -> bool
async def listar_feature_flags() -> Dict[str, bool]

# Desbloqueio
async def desbloquear_chip(chip_id, motivo, usuario) -> bool
async def desbloquear_cliente(cliente_id, motivo, usuario) -> bool

# Circuit Breakers
async def resetar_circuit_breaker_global(circuit_name, motivo, usuario) -> bool

# Emergencia
async def ativar_modo_emergencia(motivo, usuario) -> bool
async def desativar_modo_emergencia(motivo, usuario) -> bool

# Audit Trail
async def registrar_audit_trail(acao, entidade, detalhes, usuario)
async def buscar_audit_trail(acao, entidade, horas, limite)
```

### 2. `app/services/policy/` (Sprint 15-16)
```python
# Flags do Policy Engine
async def is_policy_engine_enabled() -> bool
async def is_safe_mode_active() -> bool
async def get_safe_mode_action() -> str
async def are_campaigns_enabled() -> bool
async def is_rule_disabled(rule_id) -> bool

# Controles
async def enable_safe_mode(mode, updated_by) -> bool
async def disable_safe_mode(updated_by) -> bool
async def enable_policy_engine(updated_by) -> bool
async def disable_policy_engine(updated_by) -> bool
async def enable_rule(rule_id, updated_by) -> bool
async def disable_rule(rule_id, updated_by) -> bool

# Metricas
async def get_decisions_count(horas) -> int
async def get_decisions_by_rule(horas) -> Dict
async def get_decisions_by_action(horas) -> Dict
async def get_orphan_decisions(horas) -> List
async def get_policy_summary(horas) -> Dict
```

## Stories

---

### S43.E7.1 - Criar Router de Guardrails

**Objetivo:** Expor funcionalidades de `sistema_guardrails.py` via API HTTP.

**Endpoints a criar em `app/api/routes/guardrails.py`:**

```python
# Feature Flags
GET  /guardrails/flags                    # Lista todas as flags
GET  /guardrails/flags/{flag_name}        # Valor de uma flag
POST /guardrails/flags/{flag_name}        # Define valor (com motivo)

# Desbloqueio
POST /guardrails/desbloquear/chip/{id}    # Desbloqueia chip
POST /guardrails/desbloquear/cliente/{id} # Desbloqueia cliente

# Circuit Breakers
GET  /guardrails/circuits                 # Lista circuits e estados
POST /guardrails/circuits/{name}/reset    # Reseta circuit breaker

# Emergencia
POST /guardrails/emergencia/ativar        # Ativa modo emergencia
POST /guardrails/emergencia/desativar     # Desativa modo emergencia
GET  /guardrails/emergencia/status        # Status atual

# Audit Trail
GET  /guardrails/audit                    # Busca audit trail
```

**Tarefas:**
1. Criar arquivo `app/api/routes/guardrails.py`
2. Implementar todos os endpoints acima
3. Adicionar autenticacao/autorizacao
4. Adicionar ao router principal
5. Testes de integracao

**DoD:**
- [ ] Router criado e registrado
- [ ] Todos os endpoints funcionando
- [ ] Autenticacao obrigatoria
- [ ] Testes de integracao
- [ ] Documentacao OpenAPI

---

### S43.E7.2 - Criar Router de Policy Engine

**Objetivo:** Expor funcionalidades de `policy/` via API HTTP.

**Endpoints a criar em `app/api/routes/policy.py`:**

```python
# Status e Flags
GET  /policy/status                       # Status geral (enabled, safe_mode, etc)
POST /policy/enable                       # Habilita policy engine
POST /policy/disable                      # Desabilita policy engine

# Safe Mode
GET  /policy/safe-mode                    # Status do safe mode
POST /policy/safe-mode/enable             # Ativa safe mode (mode: wait/handoff)
POST /policy/safe-mode/disable            # Desativa safe mode

# Regras
GET  /policy/rules                        # Lista regras e status
POST /policy/rules/{rule_id}/disable      # Desabilita regra
POST /policy/rules/{rule_id}/enable       # Habilita regra

# Metricas
GET  /policy/metrics                      # Resumo de metricas
GET  /policy/metrics/decisions            # Decisoes por periodo
GET  /policy/metrics/rules                # Decisoes por regra
GET  /policy/metrics/orphans              # Decisoes orfas

# Decisoes (debug)
GET  /policy/decisions/{decision_id}      # Detalhe de uma decisao
GET  /policy/decisions/cliente/{id}       # Decisoes de um cliente
```

**Tarefas:**
1. Criar arquivo `app/api/routes/policy.py`
2. Implementar todos os endpoints
3. Adicionar autenticacao
4. Adicionar ao router principal
5. Testes de integracao

**DoD:**
- [ ] Router criado e registrado
- [ ] Todos os endpoints funcionando
- [ ] Autenticacao obrigatoria
- [ ] Testes de integracao

---

### S43.E7.3 - UI de Feature Flags

**Objetivo:** Criar UI para gerenciar feature flags.

**Layout:**
```
+----------------------------------------------------------+
| Feature Flags                                    [Refresh] |
+----------------------------------------------------------+
| Categoria: [Todas v]                                       |
+----------------------------------------------------------+
| Flag                    | Status  | Ultima alteracao | Acao|
|-------------------------|---------|------------------|-----|
| ENVIO_PROSPECCAO        | ON      | 2h atras         | [T] |
| ENVIO_FOLLOWUP          | ON      | 1d atras         | [T] |
| ENVIO_CAMPANHA          | OFF     | 30min atras      | [T] |
| WORKER_FILA             | ON      | -                | [T] |
| INTEGRATION_EVOLUTION   | ON      | -                | [T] |
+----------------------------------------------------------+
| Legenda: [T] = Toggle com confirmacao                     |
+----------------------------------------------------------+

--- Modal de Toggle ---

+------------------------------------------+
| Desabilitar ENVIO_CAMPANHA?      [Fechar] |
+------------------------------------------+
| Esta flag controla o envio de            |
| mensagens de campanha.                    |
|                                           |
| Impacto:                                  |
| - Campanhas ativas serao pausadas         |
| - Novos envios nao serao processados      |
|                                           |
| Motivo (obrigatorio):                     |
| [________________________________]        |
|                                           |
| [Cancelar] [Confirmar]                   |
+------------------------------------------+
```

**Tarefas:**
1. Criar pagina `/sistema/flags` ou aba em `/sistema`
2. Lista de flags com status
3. Toggle com modal de confirmacao e motivo
4. Agrupamento por categoria
5. Historico de alteracoes

**API Calls:**
- `GET /guardrails/flags`
- `POST /guardrails/flags/{name}`

**DoD:**
- [ ] Lista de flags
- [ ] Toggle funcional
- [ ] Confirmacao com motivo
- [ ] Historico visivel
- [ ] Testes unitarios

---

### S43.E7.4 - UI de Policy Engine

**Objetivo:** Criar UI para controlar o Policy Engine.

**Layout:**
```
+----------------------------------------------------------+
| Policy Engine                                             |
+----------------------------------------------------------+
| Status: ATIVO                     [Desabilitar]           |
| Safe Mode: INATIVO                [Ativar Safe Mode]      |
+----------------------------------------------------------+
| Metricas (ultimas 24h):                                   |
| Decisoes: 1.234  |  Por regra: [ver]  |  Orfas: 2 (0.1%) |
+----------------------------------------------------------+
| Regras:                                                   |
| +------------------------------------------------------+ |
| | Regra                      | Decisoes | Status | Acao | |
| |----------------------------|----------|--------|------| |
| | rule_grave_objection       | 45       | ON     | [T]  | |
| | rule_explicit_optout       | 12       | ON     | [T]  | |
| | rule_temperature_cold      | 89       | OFF    | [T]  | |
| | rule_default               | 1088     | ON     | [-]  | |
| +------------------------------------------------------+ |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar pagina `/sistema/policy` ou aba em `/sistema`
2. Status do engine e safe mode
3. Cards de metricas
4. Lista de regras com toggle
5. Confirmacao para acoes criticas

**API Calls:**
- `GET /policy/status`
- `GET /policy/rules`
- `GET /policy/metrics`
- `POST /policy/enable` / `POST /policy/disable`
- `POST /policy/safe-mode/enable` / `disable`
- `POST /policy/rules/{id}/enable` / `disable`

**DoD:**
- [ ] Status visivel
- [ ] Toggle de engine e safe mode
- [ ] Lista de regras
- [ ] Metricas basicas
- [ ] Testes unitarios

---

### S43.E7.5 - UI de Circuit Breakers com Reset

**Objetivo:** Adicionar funcionalidade de reset manual aos circuit breakers.

**Atualizar layout do Health Center:**
```
+----------------------------------------------------------+
| Circuit Breakers                                          |
+----------------------------------------------------------+
| Circuit       | Estado    | Falhas | Ultimo Reset | Acao  |
|---------------|-----------|--------|--------------|-------|
| evolution     | CLOSED    | 0/5    | 2h atras     | [-]   |
| claude        | HALF_OPEN | 3/5    | 10min atras  | [Reset]|
| supabase      | OPEN      | 5/5    | 5min atras   | [Reset]|
+----------------------------------------------------------+

--- Modal de Reset ---

+------------------------------------------+
| Resetar Circuit Breaker: claude  [Fechar] |
+------------------------------------------+
| Estado atual: HALF_OPEN (3/5 falhas)     |
|                                           |
| O reset ira:                              |
| - Zerar contadores de falha               |
| - Mudar estado para CLOSED                |
| - Permitir novas requisicoes              |
|                                           |
| ! Use apenas se tiver certeza que o       |
|   problema foi resolvido                  |
|                                           |
| Motivo (obrigatorio):                     |
| [________________________________]        |
|                                           |
| [Cancelar] [Resetar Circuit]             |
+------------------------------------------+
```

**Tarefas:**
1. Adicionar botao de reset na tabela de circuits
2. Modal de confirmacao com motivo
3. Chamar API de reset
4. Atualizar estado apos reset
5. Registrar no audit trail

**API Calls:**
- `GET /health/circuits` (existente)
- `POST /guardrails/circuits/{name}/reset` (novo)

**DoD:**
- [ ] Botao de reset visivel
- [ ] Modal de confirmacao
- [ ] Reset funcional
- [ ] Audit trail registrado
- [ ] Testes unitarios

---

## Impacto na Sprint

### Adicao ao Escopo

| Item | Stories | Backend | Frontend |
|------|---------|---------|----------|
| Router Guardrails | 1 | Novo | - |
| Router Policy | 1 | Novo | - |
| UI Feature Flags | 1 | - | Novo |
| UI Policy Engine | 1 | - | Novo |
| UI Circuit Reset | 1 | - | Update |
| **Total** | **5** | **2 routers** | **3 UIs** |

### Novo Total da Sprint

| Epic | Stories |
|------|---------|
| E01 - Integridade | 4 |
| E02 - Group Entry | 5 |
| E03 - Qualidade | 4 |
| E04 - Health Center | 4 |
| E05 - Sistema Avancado | 3 |
| E06 - UX | 4 |
| **E07 - Guardrails/Policy** | **5** |
| **Total** | **29** |

## Ordem de Execucao

```
1. Backend primeiro:
   S43.E7.1 - Router Guardrails
   S43.E7.2 - Router Policy

2. Frontend depois:
   S43.E7.3 - UI Feature Flags
   S43.E7.4 - UI Policy Engine
   S43.E7.5 - UI Circuit Reset
```

## Consideracoes Tecnicas

### Seguranca
- Todos os endpoints requerem autenticacao
- Acoes criticas requerem role `admin` ou `manager`
- Todas as alteracoes registradas no audit trail

### Backwards Compatibility
- Novos routers, nao altera existentes
- Feature flags tem default seguro (enabled)

### Testes
- Testes de integracao para todos os endpoints
- Testes de permissao (role-based)
- Testes de audit trail
