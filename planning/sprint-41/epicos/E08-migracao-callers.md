# E08 - Migracao dos Callers

**Epico:** E08
**Nome:** Migracao dos 36 Callers
**Dependencias:** E01-E07 (todos os componentes)
**Prioridade:** Alta

---

## Objetivo

Migrar todos os call sites existentes de `enviar_slack()` e funcoes `notificar_*()` para usar o novo `NotificationHub`.

---

## Contexto

Atualmente existem ~36 chamadas diretas espalhadas em 19 arquivos:

| Arquivo | Chamadas | Tipo |
|---------|----------|------|
| `alertas.py` | 1 | enviar_slack |
| `grupos/alertas.py` | 1 | enviar_slack |
| `chips/health_monitor.py` | 5 | notificar_slack |
| `chips/orchestrator.py` | 8 | notificar_slack |
| `handoff/flow.py` | 2 | notificar_handoff |
| `confirmacao_plantao.py` | 1 | notificar_confirmacao |
| `briefing_executor.py` | 4 | enviar_slack |
| `hospitais_bloqueados.py` | 2 | enviar_slack |
| `business_events/alerts.py` | 1 | enviar_slack |
| `business_events/reconciliation.py` | 1 | enviar_slack |
| `relatorios/periodo.py` | 1 | enviar_slack |
| `relatorios/semanal.py` | 1 | enviar_slack |
| `relatorios/diario.py` | 1 | enviar_slack |
| `external_handoff/service.py` | 3 | enviar_slack |
| `external_handoff/confirmacao.py` | 2 | enviar_slack |
| `vagas/service.py` | 1 | notificar_plantao |
| `slack/tool_executor.py` | 1 | enviar_slack |
| `canal_ajuda.py` | 2 | enviar_slack |
| `briefing.py` | 1 | enviar_slack |
| `monitor_whatsapp.py` | 1 | enviar_slack |
| `workers/handoff_processor.py` | 1 | enviar_slack |

---

## Estrategia de Migracao

### Principios

1. **Incremental**: Migrar arquivo por arquivo
2. **Retrocompatibilidade**: Manter funcoes antigas como wrappers
3. **Testes**: Cada migracao deve ter testes atualizados
4. **Rollback**: Manter fallback para `enviar_slack` direto em caso de erro

### Padrao de Migracao

**Antes:**
```python
from app.services.slack import enviar_slack

await enviar_slack({
    "text": "Alerta: WhatsApp offline",
    "attachments": [...]
})
```

**Depois:**
```python
from app.services.notifications import notification_hub, AlertDomain, AlertCategory

await notification_hub.notify(
    domain=AlertDomain.WHATSAPP,
    category=AlertCategory.CRITICAL,
    alert_type="desconectado",
    title="WhatsApp Offline",
    message="Conexao perdida com Evolution API",
    metadata={"instancia": "julia-01"},
)
```

---

## Entregaveis

### 1. Arquivo: `migrations/notification_migrator.py`

Helper para facilitar migracao gradual:

```python
"""
Helper para migracao gradual de notificacoes.

Sprint 41

Permite migrar callers existentes sem quebrar funcionalidade.
"""
import logging
from typing import Dict, Any, Optional

from app.services.slack import enviar_slack
from app.services.notifications import (
    notification_hub,
    AlertDomain,
    AlertCategory,
    AlertSeverity,
)
from app.services.notifications.config import (
    get_domain_for_alert_type,
    get_category_for_alert_type,
)

logger = logging.getLogger(__name__)

# Flag para habilitar/desabilitar novo sistema
USE_NOTIFICATION_HUB = True


async def notify_with_fallback(
    alert_type: str,
    title: str,
    message: str,
    legacy_payload: Optional[Dict[str, Any]] = None,
    domain: Optional[AlertDomain] = None,
    category: Optional[AlertCategory] = None,
    metadata: Optional[Dict[str, Any]] = None,
    force: bool = False,
) -> bool:
    """
    Envia notificacao com fallback para sistema legado.

    Durante a migracao, tenta enviar pelo NotificationHub.
    Se falhar ou estiver desabilitado, usa enviar_slack.

    Args:
        alert_type: Tipo do alerta
        title: Titulo
        message: Mensagem
        legacy_payload: Payload original para fallback
        domain: Dominio (inferido se None)
        category: Categoria (inferida se None)
        metadata: Dados adicionais
        force: Ignorar cooldown

    Returns:
        True se enviou com sucesso
    """
    if USE_NOTIFICATION_HUB:
        try:
            # Inferir domain/category se nao fornecidos
            if domain is None:
                domain = get_domain_for_alert_type(alert_type)
            if category is None:
                category = get_category_for_alert_type(alert_type)

            result = await notification_hub.notify(
                domain=domain,
                category=category,
                alert_type=alert_type,
                title=title,
                message=message,
                metadata=metadata or {},
                force=force,
            )

            # Considerar sucesso se enviou ou foi suprimido
            return result.sent or result.suppressed

        except Exception as e:
            logger.warning(
                f"Falha no NotificationHub, usando fallback: {e}"
            )

    # Fallback para sistema legado
    if legacy_payload:
        return await enviar_slack(legacy_payload, force=force)

    # Construir payload minimo
    return await enviar_slack({
        "text": f"{title}: {message}",
    }, force=force)


# Mapeamento de funcoes legadas para novos parametros
LEGACY_FUNCTION_MAPPING = {
    "notificar_handoff": {
        "domain": AlertDomain.WHATSAPP,
        "category": AlertCategory.CRITICAL,
        "alert_type": "handoff",
    },
    "notificar_plantao_reservado": {
        "domain": AlertDomain.SHIFT,
        "category": AlertCategory.ATTENTION,
        "alert_type": "plantao_reservado",
    },
    "notificar_confirmacao_plantao": {
        "domain": AlertDomain.SHIFT,
        "category": AlertCategory.ATTENTION,
        "alert_type": "confirmacao_plantao",
    },
    "notificar_handoff_resolvido": {
        "domain": AlertDomain.WHATSAPP,
        "category": AlertCategory.INFO,
        "alert_type": "handoff_resolvido",
    },
}
```

### 2. Migracoes por Arquivo

#### `app/services/alertas.py`

```python
# ANTES (linha ~310)
async def enviar_alerta_slack(alerta: Dict):
    cor = CORES_SEVERIDADE.get(alerta["severidade"], "#607D8B")
    mensagem = {
        "text": f"⚠️ Alerta: {alerta['tipo']}",
        "attachments": [{...}]
    }
    await enviar_slack(mensagem)

# DEPOIS
from app.services.notifications import notification_hub, AlertDomain, AlertCategory

async def enviar_alerta_slack(alerta: Dict):
    """Envia alerta via NotificationHub."""
    # Mapear severidade para categoria
    severity_to_category = {
        "critical": AlertCategory.CRITICAL,
        "error": AlertCategory.ATTENTION,
        "warning": AlertCategory.ATTENTION,
        "info": AlertCategory.INFO,
    }

    await notification_hub.notify(
        domain=AlertDomain.SYSTEM,
        category=severity_to_category.get(alerta["severidade"], AlertCategory.ATTENTION),
        alert_type=alerta["tipo"],
        title=f"Alerta: {alerta['tipo']}",
        message=alerta["mensagem"],
        metadata={"severidade": alerta["severidade"], "valor": alerta.get("valor")},
    )
```

#### `app/services/monitor_whatsapp.py`

```python
# ANTES (linha ~155)
await enviar_slack(slack_msg)

# DEPOIS
from app.services.notifications import notification_hub, AlertDomain, AlertCategory

await notification_hub.notify(
    domain=AlertDomain.WHATSAPP,
    category=AlertCategory.CRITICAL,
    alert_type="desconectado",
    title="WhatsApp Desconectado",
    message=f"Instancia {instancia} perdeu conexao",
    metadata={
        "instancia": instancia,
        "ultimo_ping": ultimo_ping,
        "tempo_offline": tempo_offline,
    },
)
```

#### `app/services/chips/health_monitor.py`

```python
# ANTES (funcao notificar_slack)
async def notificar_slack(mensagem: str, canal: str = "operacoes") -> bool:
    return await enviar_slack({"text": mensagem})

# DEPOIS - Remover funcao e usar hub diretamente nos callers

# Antes (linha ~295)
await notificar_slack(f"⚠️ Chip {chip['numero']} com trust baixo")

# Depois
await notification_hub.notify(
    domain=AlertDomain.CHIPS,
    category=AlertCategory.ATTENTION,
    alert_type="trust_baixo",
    title="Trust de Chip Baixo",
    message=f"Chip {chip['numero']} com trust {chip['trust_score']}%",
    metadata={
        "chip_id": chip["id"],
        "numero": chip["numero"],
        "trust_score": chip["trust_score"],
    },
)
```

#### `app/services/business_events/alerts.py`

```python
# ANTES (linha ~520)
result = await enviar_slack(message)

# DEPOIS
from app.services.notifications import notification_hub, AlertDomain, AlertCategory

result = await notification_hub.notify(
    domain=AlertDomain.FUNNEL,
    category=AlertCategory.ATTENTION,
    alert_type=alert["tipo"],
    title=alert["titulo"],
    message=alert["mensagem"],
    metadata=alert.get("contexto", {}),
)
```

#### `app/services/handoff/flow.py`

```python
# ANTES (linha ~123)
await notificar_handoff(conversa, handoff)

# DEPOIS
from app.services.notifications import notification_hub, AlertDomain, AlertCategory

await notification_hub.notify(
    domain=AlertDomain.WHATSAPP,
    category=AlertCategory.CRITICAL,
    alert_type="handoff_iniciado",
    title="Handoff Iniciado",
    message=f"Medico {conversa.get('nome', 'Desconhecido')} requer atencao humana",
    metadata={
        "conversa_id": conversa.get("id"),
        "medico_id": conversa.get("cliente_id"),
        "motivo": handoff.get("motivo"),
    },
    actions=[
        {"label": "Assumir", "action_id": "assumir_handoff", "value": handoff["id"], "style": "primary"},
    ],
)
```

#### `app/services/relatorios/diario.py`

```python
# ANTES (linha ~136)
await enviar_slack(mensagem)

# DEPOIS
from app.services.notifications import notification_hub, AlertDomain, AlertCategory

await notification_hub.notify(
    domain=AlertDomain.BUSINESS,
    category=AlertCategory.DIGEST,
    alert_type="relatorio_diario",
    title="Relatorio Diario",
    message=f"Resumo do dia {data}",
    metadata={
        "total_conversas": metricas["total_conversas"],
        "taxa_conversao": metricas["taxa_conversao"],
        "plantoes_reservados": metricas["plantoes_reservados"],
    },
)
```

---

## Ordem de Migracao

Migrar na seguinte ordem (menor risco primeiro):

| Fase | Arquivos | Risco | Motivo |
|------|----------|-------|--------|
| 1 | relatorios/*.py | Baixo | Apenas relatorios, nao criticos |
| 2 | briefing*.py | Baixo | Notificacoes informativas |
| 3 | business_events/*.py | Medio | Alertas de funil |
| 4 | chips/*.py | Medio | Multiplas chamadas, mas testavel |
| 5 | alertas.py | Medio | Sistema central de alertas |
| 6 | handoff/*.py | Alto | Critico para operacao |
| 7 | monitor_whatsapp.py | Alto | Critico, mas simples |
| 8 | external_handoff/*.py | Alto | Critico |

---

## Testes de Migracao

### Arquivo: `tests/services/notifications/test_migration.py`

```python
"""Testes para migracao de notificacoes."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.notifications.migrations.notification_migrator import (
    notify_with_fallback,
    USE_NOTIFICATION_HUB,
    LEGACY_FUNCTION_MAPPING,
)
from app.services.notifications import AlertDomain, AlertCategory


class TestNotifyWithFallback:
    """Testes para notify_with_fallback."""

    @pytest.mark.asyncio
    async def test_usa_notification_hub_quando_habilitado(self):
        """Usa NotificationHub quando habilitado."""
        with patch("app.services.notifications.migrations.notification_migrator.notification_hub") as mock_hub:
            mock_hub.notify = AsyncMock(return_value=AsyncMock(sent=True, suppressed=False))

            result = await notify_with_fallback(
                alert_type="desconectado",
                title="WhatsApp Offline",
                message="Conexao perdida",
            )

            assert result is True
            mock_hub.notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_para_enviar_slack(self):
        """Usa fallback quando hub falha."""
        with patch("app.services.notifications.migrations.notification_migrator.notification_hub") as mock_hub:
            mock_hub.notify = AsyncMock(side_effect=Exception("Hub error"))

            with patch("app.services.notifications.migrations.notification_migrator.enviar_slack") as mock_slack:
                mock_slack.return_value = True

                result = await notify_with_fallback(
                    alert_type="desconectado",
                    title="WhatsApp Offline",
                    message="Conexao perdida",
                    legacy_payload={"text": "fallback"},
                )

                assert result is True
                mock_slack.assert_called_once()

    @pytest.mark.asyncio
    async def test_considera_suprimido_como_sucesso(self):
        """Notificacao suprimida e considerada sucesso."""
        with patch("app.services.notifications.migrations.notification_migrator.notification_hub") as mock_hub:
            mock_hub.notify = AsyncMock(return_value=AsyncMock(sent=False, suppressed=True))

            result = await notify_with_fallback(
                alert_type="desconectado",
                title="WhatsApp Offline",
                message="Conexao perdida",
            )

            assert result is True  # Suprimido = sucesso

    @pytest.mark.asyncio
    async def test_infere_domain_e_category(self):
        """Infere domain e category do alert_type."""
        with patch("app.services.notifications.migrations.notification_migrator.notification_hub") as mock_hub:
            mock_hub.notify = AsyncMock(return_value=AsyncMock(sent=True, suppressed=False))

            await notify_with_fallback(
                alert_type="desconectado",
                title="WhatsApp Offline",
                message="Conexao perdida",
            )

            call_kwargs = mock_hub.notify.call_args.kwargs
            assert call_kwargs["domain"] == AlertDomain.WHATSAPP
            assert call_kwargs["category"] == AlertCategory.CRITICAL


class TestLegacyFunctionMapping:
    """Testes para mapeamento de funcoes legadas."""

    def test_notificar_handoff_mapeado(self):
        """notificar_handoff tem mapeamento."""
        mapping = LEGACY_FUNCTION_MAPPING["notificar_handoff"]
        assert mapping["domain"] == AlertDomain.WHATSAPP
        assert mapping["category"] == AlertCategory.CRITICAL

    def test_notificar_plantao_mapeado(self):
        """notificar_plantao_reservado tem mapeamento."""
        mapping = LEGACY_FUNCTION_MAPPING["notificar_plantao_reservado"]
        assert mapping["domain"] == AlertDomain.SHIFT
        assert mapping["category"] == AlertCategory.ATTENTION


class TestIntegrationMigration:
    """Testes de integracao para migracao."""

    @pytest.mark.asyncio
    async def test_alertas_py_migration(self):
        """Testa migracao do alertas.py."""
        with patch("app.services.notifications.notification_hub") as mock_hub:
            mock_hub.notify = AsyncMock(return_value=AsyncMock(sent=True))

            # Simular chamada migrada
            from app.services.notifications import notification_hub, AlertDomain, AlertCategory

            alerta = {
                "tipo": "sem_respostas",
                "mensagem": "10 mensagens sem resposta",
                "severidade": "warning",
            }

            await notification_hub.notify(
                domain=AlertDomain.SYSTEM,
                category=AlertCategory.ATTENTION,
                alert_type=alerta["tipo"],
                title=f"Alerta: {alerta['tipo']}",
                message=alerta["mensagem"],
                metadata={"severidade": alerta["severidade"]},
            )

            mock_hub.notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_whatsapp_migration(self):
        """Testa migracao do monitor_whatsapp.py."""
        with patch("app.services.notifications.notification_hub") as mock_hub:
            mock_hub.notify = AsyncMock(return_value=AsyncMock(sent=True))

            from app.services.notifications import notification_hub, AlertDomain, AlertCategory

            await notification_hub.notify(
                domain=AlertDomain.WHATSAPP,
                category=AlertCategory.CRITICAL,
                alert_type="desconectado",
                title="WhatsApp Desconectado",
                message="Instancia julia-01 perdeu conexao",
                metadata={"instancia": "julia-01"},
            )

            call_kwargs = mock_hub.notify.call_args.kwargs
            assert call_kwargs["domain"] == AlertDomain.WHATSAPP
            assert call_kwargs["category"] == AlertCategory.CRITICAL
```

---

## Checklist de Conclusao

### Preparacao
- [ ] Criar `migrations/notification_migrator.py`
- [ ] Configurar flag `USE_NOTIFICATION_HUB`
- [ ] Criar mapeamento de funcoes legadas

### Fase 1 - Relatorios (Baixo Risco)
- [ ] Migrar `relatorios/diario.py`
- [ ] Migrar `relatorios/semanal.py`
- [ ] Migrar `relatorios/periodo.py`
- [ ] Testar em staging

### Fase 2 - Briefing (Baixo Risco)
- [ ] Migrar `briefing.py`
- [ ] Migrar `briefing_executor.py`
- [ ] Testar em staging

### Fase 3 - Business Events (Medio Risco)
- [ ] Migrar `business_events/alerts.py`
- [ ] Migrar `business_events/reconciliation.py`
- [ ] Testar em staging

### Fase 4 - Chips (Medio Risco)
- [ ] Migrar `chips/health_monitor.py`
- [ ] Migrar `chips/orchestrator.py`
- [ ] Testar em staging

### Fase 5 - Alertas (Medio Risco)
- [ ] Migrar `alertas.py`
- [ ] Migrar `grupos/alertas.py`
- [ ] Testar em staging

### Fase 6 - Handoff (Alto Risco)
- [ ] Migrar `handoff/flow.py`
- [ ] Testar em staging
- [ ] Validar em producao com monitoramento

### Fase 7 - Monitor WhatsApp (Alto Risco)
- [ ] Migrar `monitor_whatsapp.py`
- [ ] Testar em staging
- [ ] Validar em producao

### Fase 8 - External Handoff (Alto Risco)
- [ ] Migrar `external_handoff/service.py`
- [ ] Migrar `external_handoff/confirmacao.py`
- [ ] Testar em staging
- [ ] Validar em producao

### Outros
- [ ] Migrar `vagas/service.py`
- [ ] Migrar `canal_ajuda.py`
- [ ] Migrar `hospitais_bloqueados.py`
- [ ] Migrar `slack/tool_executor.py`
- [ ] Migrar `workers/handoff_processor.py`

### Finalizacao
- [ ] Remover funcoes `notificar_slack` locais
- [ ] Deprecar wrappers em `slack.py`
- [ ] 100% dos testes passando

---

## Definition of Done (E08)

1. [ ] Helper de migracao funcionando
2. [ ] Todas as 36 chamadas migradas
3. [ ] Fallback funcionando para casos de erro
4. [ ] Funcoes locais `notificar_slack` removidas
5. [ ] Testes de integracao passando
6. [ ] Validado em staging
7. [ ] 100% dos testes passando (0 skipped)
8. [ ] Zero erros de tipo/lint
