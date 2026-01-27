# E09 - Refatoracao e Seguranca

**Epico:** E09
**Nome:** Refatoracao, Seguranca e Code Review Final
**Dependencias:** E01-E08 (todos os epicos)
**Prioridade:** Alta

---

## Objetivo

Revisar toda a implementacao da Sprint 41, identificar oportunidades de refatoracao, verificar seguranca e garantir qualidade do codigo antes do merge.

---

## Contexto

Este epico e executado apos todos os componentes estarem implementados e testados. O objetivo e:

1. **Refatoracao**: Eliminar duplicacao, melhorar legibilidade
2. **Seguranca**: Verificar vulnerabilidades, dados sensiveis
3. **Performance**: Identificar gargalos, otimizar chamadas Redis
4. **Documentacao**: Garantir docstrings, type hints
5. **Cobertura**: Verificar testes, edge cases

---

## Checklist de Review

### 1. Code Review

#### 1.1 Estrutura e Organizacao

- [ ] Todos os arquivos estao no diretorio correto (`app/services/notifications/`)
- [ ] `__init__.py` exporta todos os componentes publicos
- [ ] Nomes de arquivos seguem convencao (snake_case)
- [ ] Imports organizados (stdlib, terceiros, locais)

#### 1.2 Qualidade do Codigo

- [ ] Todas as funcoes tem docstrings
- [ ] Todos os parametros tem type hints
- [ ] Retornos tem type hints
- [ ] Nomes de variaveis sao descritivos
- [ ] Funcoes tem responsabilidade unica
- [ ] Nao ha codigo duplicado

#### 1.3 Tratamento de Erros

- [ ] Todas as operacoes async tem try/except
- [ ] Erros sao logados com contexto
- [ ] Falhas nao propagam excecoes para chamadores (fail gracefully)
- [ ] Erros de Redis nao bloqueiam notificacoes (fail open)

### 2. Seguranca

#### 2.1 Dados Sensiveis

- [ ] Nenhum dado sensivel em logs (telefones, tokens)
- [ ] Metadata nao contem credenciais
- [ ] IDs truncados em logs (`id[:8]`)
- [ ] Nenhuma chave de API hardcoded

#### 2.2 Validacao de Entrada

- [ ] `alert_type` e validado antes de uso
- [ ] `domain` e `category` sao enums (nao strings arbitrarias)
- [ ] Metadata e sanitizada antes de formatacao
- [ ] Tamanho de mensagens e limitado

#### 2.3 Redis

- [ ] Chaves tem prefixo para evitar colisao (`notif:`)
- [ ] TTL definido para todas as chaves
- [ ] Nenhuma chave permanece indefinidamente
- [ ] Operacoes tem timeout

### 3. Performance

#### 3.1 Redis

- [ ] Verificar se ha chamadas Redis desnecessarias
- [ ] Pipeline para multiplas operacoes
- [ ] TTLs adequados (nao muito longos, nao muito curtos)
- [ ] Serialization eficiente (JSON vs msgpack)

#### 3.2 Async

- [ ] Nenhum bloqueio sincrono em funcoes async
- [ ] Tasks concorrentes onde possivel
- [ ] Timeouts em operacoes externas

#### 3.3 Memory

- [ ] Listas em digest tem limite maximo
- [ ] Objetos grandes nao mantidos em memoria
- [ ] Sem vazamentos de referencias

### 4. Testes

#### 4.1 Cobertura

- [ ] Cobertura minima de 90%
- [ ] Todos os caminhos principais testados
- [ ] Edge cases cobertos:
  - [ ] Notificacao com metadata vazia
  - [ ] Notificacao com metadata muito grande
  - [ ] Redis indisponivel
  - [ ] Slack indisponivel
  - [ ] Cluster de correlacao vazio
  - [ ] Digest com muitas notificacoes

#### 4.2 Qualidade dos Testes

- [ ] Testes sao isolados (nao dependem de ordem)
- [ ] Mocks sao apropriados
- [ ] Assertions sao especificos
- [ ] Nomes descrevem o que testam

#### 4.3 Execucao

- [ ] Todos os testes passam: `pytest tests/services/notifications/ -v`
- [ ] Nenhum teste skipped
- [ ] Nenhum warning de deprecation

### 5. Linting e Typing

#### 5.1 Ruff

- [ ] Zero erros: `ruff check app/services/notifications/`
- [ ] Zero warnings
- [ ] Formatacao correta: `ruff format --check app/services/notifications/`

#### 5.2 Mypy

- [ ] Zero erros: `mypy app/services/notifications/`
- [ ] Nenhum `# type: ignore` desnecessario
- [ ] Generics corretamente tipados

---

## Refatoracoes Comuns

### 5.1 Duplicacao em Formatters

Se houver codigo duplicado entre `_format_*` metodos:

```python
# Antes - duplicado
def _format_critical(self, n):
    blocks = [{"type": "header", ...}]
    blocks.append({"type": "section", ...})
    blocks.append(self._build_context(n))
    return {"text": ..., "attachments": [...]}

def _format_attention(self, n):
    blocks = [{"type": "section", ...}]
    blocks.append(self._build_context(n))
    return {"text": ..., "attachments": [...]}

# Depois - extraido
def _wrap_in_attachment(self, blocks, color):
    return {"attachments": [{"color": color, "blocks": blocks}]}

def _format_critical(self, n):
    blocks = [self._build_header(n), self._build_section(n), self._build_context(n)]
    return {"text": ..., **self._wrap_in_attachment(blocks, COLORS[CRITICAL])}
```

### 5.2 Constantes Duplicadas

Se constantes aparecem em multiplos lugares:

```python
# Antes - duplicado
# Em cooldown.py
REDIS_PREFIX = "notif:cooldown:"

# Em correlation.py
REDIS_PREFIX = "notif:corr:"

# Depois - centralizado em config.py
REDIS_KEYS = {
    "cooldown_prefix": "notif:cooldown:",
    "correlation_prefix": "notif:corr:",
    "digest_prefix": "notif:digest:",
}
```

### 5.3 Error Handling Repetitivo

```python
# Antes - repetitivo
async def check_cooldown(self, n):
    try:
        data = await cache_get_json(key)
        ...
    except Exception as e:
        logger.error(f"Erro ao verificar cooldown: {e}")
        return False

# Depois - decorator
def redis_operation(default_on_error):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Redis error em {func.__name__}: {e}")
                return default_on_error
        return wrapper
    return decorator

@redis_operation(default_on_error=False)
async def check_cooldown(self, n):
    data = await cache_get_json(key)
    ...
```

---

## Vulnerabilidades a Verificar

### 6.1 Injection

```python
# Verificar se alert_type pode conter caracteres perigosos
# que poderiam ser interpretados pelo Slack

# Ruim
message = f"Alerta: {alert_type}"  # alert_type nao sanitizado

# Bom
def sanitize_alert_type(t: str) -> str:
    return re.sub(r'[^a-z0-9_]', '', t.lower())

message = f"Alerta: {sanitize_alert_type(alert_type)}"
```

### 6.2 Information Disclosure

```python
# Verificar se erros expoe detalhes internos

# Ruim
return NotificationResult(reason=f"error: {traceback.format_exc()}")

# Bom
return NotificationResult(reason="internal_error")
# Log completo apenas internamente
logger.exception("Erro ao processar notificacao")
```

### 6.3 DoS via Digest

```python
# Verificar limite no digest
MAX_DIGEST_SIZE = 100

async def add(self, notification):
    current = await self.count()
    if current >= MAX_DIGEST_SIZE:
        # Descartar mais antigo ou rejeitar
        await self._evict_oldest()
```

---

## Documentacao Final

### 7.1 README do Modulo

Criar `app/services/notifications/README.md`:

```markdown
# NotificationHub

Sistema centralizado de notificacoes Slack.

## Uso Basico

```python
from app.services.notifications import notification_hub, AlertDomain, AlertCategory

await notification_hub.notify(
    domain=AlertDomain.WHATSAPP,
    category=AlertCategory.CRITICAL,
    alert_type="desconectado",
    title="WhatsApp Offline",
    message="Conexao perdida",
)
```

## Categorias

| Categoria | Cooldown | Envio |
|-----------|----------|-------|
| CRITICAL | 15min | Imediato, 24/7 |
| ATTENTION | 30min | Imediato, 08-20h |
| DIGEST | - | Agrupado, horario |
| INFO | 60min | Agrupado |

## Clusters de Correlacao

- `whatsapp`: desconectado, criptografia, evolution_down
- `chips`: pool_vazio, pool_baixo, trust_critico
- `funnel`: handoff_spike, conversion_drop

## Configuracao

Ver `config.py` para ajustar:
- Cooldowns por categoria
- Janela operacional
- Clusters de correlacao
```

### 7.2 Comentarios em Codigo

Garantir que logica complexa esta documentada:

```python
def _get_window_key(self, cluster_name: str) -> str:
    """
    Gera chave de janela baseada no tempo.

    A janela e truncada para o inicio do periodo.
    Exemplo: window=30min, 14:45 -> 14:30

    Isso garante que alertas na mesma janela
    compartilham a mesma chave Redis.
    """
```

---

## Entregaveis

### Arquivo: `tests/services/notifications/test_integration.py`

```python
"""Testes de integracao para NotificationHub."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services.notifications import (
    notification_hub,
    AlertDomain,
    AlertCategory,
)


class TestFullPipeline:
    """Testes do pipeline completo."""

    @pytest.mark.asyncio
    async def test_critical_enviado_imediatamente(self):
        """Alerta critico passa por todo pipeline e e enviado."""
        with patch("app.services.notifications.hub.enviar_slack", new_callable=AsyncMock) as mock_slack:
            mock_slack.return_value = True

            with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock_cache_get:
                mock_cache_get.return_value = None

                with patch("app.services.notifications.cooldown.cache_set_json", new_callable=AsyncMock):
                    with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock_corr:
                        mock_corr.return_value = None

                        with patch("app.services.notifications.correlation.cache_set_json", new_callable=AsyncMock):
                            result = await notification_hub.notify(
                                domain=AlertDomain.WHATSAPP,
                                category=AlertCategory.CRITICAL,
                                alert_type="desconectado",
                                title="WhatsApp Offline",
                                message="Conexao perdida",
                            )

        assert result.sent is True
        mock_slack.assert_called_once()

    @pytest.mark.asyncio
    async def test_correlacao_suprime_segundo_alerta(self):
        """Segundo alerta do mesmo cluster e suprimido."""
        with patch("app.services.notifications.hub.enviar_slack", new_callable=AsyncMock) as mock_slack:
            mock_slack.return_value = True

            # Simular que desconectado ja foi enviado
            correlation_data = {
                "alert_type": "desconectado",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock_cooldown:
                mock_cooldown.return_value = None

                with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock_corr:
                    mock_corr.return_value = correlation_data

                    # Tentar enviar criptografia (mesmo cluster whatsapp)
                    result = await notification_hub.notify(
                        domain=AlertDomain.WHATSAPP,
                        category=AlertCategory.ATTENTION,
                        alert_type="criptografia",
                        title="Erro Criptografia",
                        message="PreKeyError",
                    )

        assert result.sent is False
        assert result.suppressed is True
        assert result.reason == "correlation"
        mock_slack.assert_not_called()

    @pytest.mark.asyncio
    async def test_cooldown_suprime_repeticao(self):
        """Repeticao rapida e suprimida por cooldown."""
        with patch("app.services.notifications.hub.enviar_slack", new_callable=AsyncMock) as mock_slack:
            mock_slack.return_value = True

            # Simular cooldown ativo
            cooldown_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock_cooldown:
                mock_cooldown.return_value = cooldown_data

                result = await notification_hub.notify(
                    domain=AlertDomain.WHATSAPP,
                    category=AlertCategory.CRITICAL,
                    alert_type="desconectado",
                    title="WhatsApp Offline",
                    message="Conexao perdida",
                )

        assert result.sent is False
        assert result.suppressed is True
        assert result.reason == "cooldown"
        mock_slack.assert_not_called()


class TestEdgeCases:
    """Testes de edge cases."""

    @pytest.mark.asyncio
    async def test_metadata_vazia(self):
        """Notificacao com metadata vazia funciona."""
        with patch("app.services.notifications.hub.enviar_slack", new_callable=AsyncMock) as mock_slack:
            mock_slack.return_value = True

            with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock_cache:
                mock_cache.return_value = None

                with patch("app.services.notifications.cooldown.cache_set_json", new_callable=AsyncMock):
                    with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock_corr:
                        mock_corr.return_value = None

                        with patch("app.services.notifications.correlation.cache_set_json", new_callable=AsyncMock):
                            result = await notification_hub.notify(
                                domain=AlertDomain.SYSTEM,
                                category=AlertCategory.INFO,
                                alert_type="test",
                                title="Test",
                                message="Test message",
                                metadata={},
                            )

        # Deve ter sido adicionado ao digest
        assert result.digest_queued is True

    @pytest.mark.asyncio
    async def test_redis_falha_graciosamente(self):
        """Redis indisponivel nao bloqueia envio."""
        with patch("app.services.notifications.hub.enviar_slack", new_callable=AsyncMock) as mock_slack:
            mock_slack.return_value = True

            with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock_cache:
                mock_cache.side_effect = Exception("Redis unavailable")

                # Mesmo com Redis falhando, deve tentar enviar
                result = await notification_hub.notify(
                    domain=AlertDomain.WHATSAPP,
                    category=AlertCategory.CRITICAL,
                    alert_type="desconectado",
                    title="WhatsApp Offline",
                    message="Conexao perdida",
                )

        # Fail open: deve enviar mesmo sem verificar cooldown
        assert result.sent is True

    @pytest.mark.asyncio
    async def test_slack_falha(self):
        """Falha do Slack e tratada."""
        with patch("app.services.notifications.hub.enviar_slack", new_callable=AsyncMock) as mock_slack:
            mock_slack.return_value = False

            with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock_cache:
                mock_cache.return_value = None

                with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock_corr:
                    mock_corr.return_value = None

                    result = await notification_hub.notify(
                        domain=AlertDomain.WHATSAPP,
                        category=AlertCategory.CRITICAL,
                        alert_type="desconectado",
                        title="WhatsApp Offline",
                        message="Conexao perdida",
                    )

        assert result.sent is False
        assert result.reason == "send_failed"


class TestSecurity:
    """Testes de seguranca."""

    @pytest.mark.asyncio
    async def test_metadata_grande_truncada(self):
        """Metadata muito grande e truncada."""
        from app.services.notifications.formatters import SlackFormatter

        formatter = SlackFormatter()
        metadata = {"campo": "x" * 1000}  # String muito longa

        fields = formatter._build_fields(metadata)

        # Valor deve ser truncado
        assert len(fields[0]["text"]) < 200

    def test_alert_type_sanitizado(self):
        """alert_type com caracteres especiais e tratado."""
        from app.services.notifications import Notification, AlertDomain, AlertCategory

        # Nao deve lancar excecao
        notif = Notification(
            domain=AlertDomain.SYSTEM,
            category=AlertCategory.INFO,
            alert_type="test<script>alert(1)</script>",
            title="Test",
            message="Test",
        )

        # alert_type deve ser usado de forma segura
        assert notif.alert_type is not None
```

---

## Checklist de Conclusao

### Code Review
- [ ] Estrutura de arquivos correta
- [ ] Imports organizados
- [ ] Docstrings em todas funcoes
- [ ] Type hints completos
- [ ] Codigo sem duplicacao

### Seguranca
- [ ] Nenhum dado sensivel em logs
- [ ] Entradas validadas
- [ ] Chaves Redis com prefixo e TTL
- [ ] Erros nao expoe detalhes internos

### Performance
- [ ] Chamadas Redis otimizadas
- [ ] Nenhum bloqueio sincrono
- [ ] Limites em listas/digest

### Testes
- [ ] Cobertura >= 90%
- [ ] Edge cases cobertos
- [ ] Testes de integracao passando
- [ ] 0 testes skipped

### Linting
- [ ] `ruff check` sem erros
- [ ] `ruff format --check` sem erros
- [ ] `mypy` sem erros

### Documentacao
- [ ] README do modulo criado
- [ ] Logica complexa comentada

---

## Definition of Done (E09)

1. [ ] Code review completo
2. [ ] Todas as refatoracoes aplicadas
3. [ ] Zero vulnerabilidades de seguranca
4. [ ] Performance otimizada
5. [ ] Cobertura de testes >= 90%
6. [ ] 100% dos testes passando (0 skipped)
7. [ ] Zero erros de ruff e mypy
8. [ ] Documentacao completa
9. [ ] PR aprovado
10. [ ] Merge para main

---

## Comandos de Validacao Final

```bash
# Rodar todos os testes
uv run pytest tests/services/notifications/ -v --cov=app/services/notifications --cov-report=term-missing

# Verificar cobertura minima
uv run pytest tests/services/notifications/ --cov=app/services/notifications --cov-fail-under=90

# Linting
uv run ruff check app/services/notifications/
uv run ruff format --check app/services/notifications/

# Type checking
uv run mypy app/services/notifications/

# Tudo junto (deve passar 100%)
uv run pytest tests/services/notifications/ -v && \
uv run ruff check app/services/notifications/ && \
uv run mypy app/services/notifications/
```
