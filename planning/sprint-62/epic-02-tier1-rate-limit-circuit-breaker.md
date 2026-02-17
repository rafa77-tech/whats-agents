# EPIC 02: Tier 1 Coverage — Rate Limiting & Circuit Breaker

## Contexto

Rate limiting e o que impede ban de chips WhatsApp. Circuit breaker e o que impede cascata de falhas.
O rate_limiter.py principal tem 20 testes (bom), mas `rate_limit.py` (API) tem zero.
O circuit_breaker.py principal tem 22 testes (bom), mas `chips/circuit_breaker.py` tem zero.

## Escopo

- **Incluido**: Testes para `rate_limit.py`, `chips/circuit_breaker.py`, e gaps nos modulos existentes
- **Excluido**: Refatoracao dos modulos (apenas testes)

---

## Tarefa 2.1: Testes para `app/services/rate_limit.py` (API rate limiting)

### Objetivo
Cobrir o rate limiter de endpoints API (217 linhas) que hoje tem zero testes.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/unit/test_rate_limit_api.py` |
| Ler | `app/services/rate_limit.py` |

### Testes Obrigatorios

**Unitarios:**
- [ ] Rate limit por IP — aceita dentro do limite
- [ ] Rate limit por IP — rejeita apos exceder limite
- [ ] Rate limit por rota — diferentes rotas tem limites diferentes
- [ ] Reset de contadores apos janela de tempo
- [ ] Headers de rate limit no response (X-RateLimit-*)
- [ ] Fallback quando Redis esta indisponivel

**Edge cases:**
- [ ] IP spoofing via X-Forwarded-For
- [ ] Multiplas requests simultaneas (race condition no contador)

### Definition of Done
- [ ] >90% de cobertura em `rate_limit.py`
- [ ] Todos os testes passando
- [ ] Marcados como `@pytest.mark.unit`

---

## Tarefa 2.2: Testes para `app/services/chips/circuit_breaker.py`

### Objetivo
Cobrir o circuit breaker especifico de chips (228 linhas) que hoje tem zero testes.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/services/chips/test_circuit_breaker.py` |
| Ler | `app/services/chips/circuit_breaker.py` |

### Testes Obrigatorios

**Unitarios:**
- [ ] Transicao CLOSED -> OPEN apos N falhas
- [ ] Transicao OPEN -> HALF_OPEN apos timeout
- [ ] Transicao HALF_OPEN -> CLOSED apos sucesso
- [ ] Transicao HALF_OPEN -> OPEN apos falha
- [ ] Fallback executado quando circuito aberto
- [ ] Configuracao de thresholds por chip
- [ ] Estado persistido/recuperado (se aplicavel)

**Edge cases:**
- [ ] Reset manual do circuito
- [ ] Multiplos chips com circuitos independentes
- [ ] Timeout exato na fronteira OPEN -> HALF_OPEN

### Definition of Done
- [ ] >90% de cobertura em `chips/circuit_breaker.py`
- [ ] Todos os testes passando

---

## Tarefa 2.3: Complementar testes do rate_limiter.py principal

### Objetivo
Verificar gaps no rate_limiter.py principal (603 linhas, 20 testes) e adicionar testes faltantes.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `tests/test_rate_limiter.py` |
| Ler | `app/services/rate_limiter.py` |

### Testes Obrigatorios

Rodar coverage para identificar linhas nao cobertas:
```bash
uv run pytest tests/test_rate_limiter.py --cov=app/services/rate_limiter --cov-report=term-missing
```

Focar em:
- [ ] Caminhos de fallback Supabase quando Redis falha
- [ ] Jitter calculation (aleatoriedade no delay)
- [ ] Edge case: relogio perto da fronteira 08h/20h
- [ ] Concorrencia: multiplos registros de envio simultaneos

### Definition of Done
- [ ] >90% de cobertura em `rate_limiter.py`
- [ ] Coverage report salvo como evidencia
