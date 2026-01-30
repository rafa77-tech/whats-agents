# E06 - Formatadores Slack

**Epico:** E06
**Nome:** Formatadores de Mensagens Slack
**Dependencias:** E01, E02
**Prioridade:** Alta

---

## Objetivo

Implementar formatadores especializados por categoria de notificacao. Cada categoria tem visual distinto no Slack usando Block Kit.

---

## Contexto

Atualmente, cada funcao de notificacao formata sua propria mensagem de forma inconsistente:
- Algumas usam `attachments` (legado)
- Algumas usam `blocks` (Block Kit)
- Sem padrao de cores, icones ou estrutura

Com formatadores padronizados:
- Visual consistente por categoria
- Facil manutencao
- Reutilizavel em diferentes contextos

---

## Padroes Visuais

| Categoria | Cor | Icone | Header |
|-----------|-----|-------|--------|
| CRITICAL | #c62828 (vermelho) | 🚨 | Texto branco, negrito |
| ATTENTION | #f57c00 (laranja) | ⚠️ | Texto normal |
| DIGEST | #1976d2 (azul) | 📊 | Resumo com lista |
| INFO | #607d8b (cinza) | ℹ️ | Compacto |

---

## Entregaveis

### Arquivo: `formatters.py`

```python
"""
Formatadores de mensagens Slack por categoria.

Sprint 41

Cada categoria tem formato visual distinto:
- CRITICAL: Header vermelho, botoes de acao
- ATTENTION: Header laranja, campos detalhados
- DIGEST: Lista compacta agrupada
- INFO: Formato minimo
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .types import Notification, AlertCategory, AlertDomain, DigestBatch
from .config import CATEGORY_CONFIG

logger = logging.getLogger(__name__)


# Cores por categoria
COLORS = {
    AlertCategory.CRITICAL: "#c62828",
    AlertCategory.ATTENTION: "#f57c00",
    AlertCategory.DIGEST: "#1976d2",
    AlertCategory.INFO: "#607d8b",
}

# Icones por categoria
ICONS = {
    AlertCategory.CRITICAL: "🚨",
    AlertCategory.ATTENTION: "⚠️",
    AlertCategory.DIGEST: "📊",
    AlertCategory.INFO: "ℹ️",
}

# Icones por dominio
DOMAIN_ICONS = {
    AlertDomain.WHATSAPP: "📱",
    AlertDomain.FUNNEL: "📈",
    AlertDomain.CHIPS: "💳",
    AlertDomain.PERFORMANCE: "⚡",
    AlertDomain.SHIFT: "📅",
    AlertDomain.BUSINESS: "💼",
    AlertDomain.SYSTEM: "🔧",
}


class SlackFormatter:
    """
    Formata notificacoes para Slack Block Kit.

    Cada categoria tem seu proprio metodo de formatacao.
    """

    def format(self, notification: Notification) -> Dict[str, Any]:
        """
        Formata notificacao baseado na categoria.

        Args:
            notification: Notificacao a formatar

        Returns:
            Dict com text e blocks para Slack API
        """
        category = notification.category

        if category == AlertCategory.CRITICAL:
            return self._format_critical(notification)
        elif category == AlertCategory.ATTENTION:
            return self._format_attention(notification)
        elif category == AlertCategory.DIGEST:
            return self._format_digest_single(notification)
        else:
            return self._format_info(notification)

    def format_digest(self, batch: DigestBatch) -> Dict[str, Any]:
        """
        Formata batch de digest para envio consolidado.

        Args:
            batch: Batch de notificacoes

        Returns:
            Dict com text e blocks para Slack API
        """
        return self._format_digest_batch(batch)

    def _format_critical(self, notification: Notification) -> Dict[str, Any]:
        """
        Formata alerta critico.

        Visual: Header vermelho proeminente, campos detalhados, botoes de acao.
        """
        icon = ICONS[AlertCategory.CRITICAL]
        domain_icon = DOMAIN_ICONS.get(notification.domain, "🔔")
        color = COLORS[AlertCategory.CRITICAL]

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{icon} {notification.title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": notification.message
                }
            }
        ]

        # Adicionar campos de metadata se houver
        if notification.metadata:
            fields = self._build_fields(notification.metadata)
            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields[:10]  # Max 10 campos
                })

        # Adicionar contexto
        context_elements = [
            {"type": "mrkdwn", "text": f"{domain_icon} *{notification.domain.value}*"},
            {"type": "mrkdwn", "text": f"Tipo: `{notification.alert_type}`"},
        ]

        if notification.source:
            context_elements.append(
                {"type": "mrkdwn", "text": f"Fonte: {notification.source}"}
            )

        blocks.append({
            "type": "context",
            "elements": context_elements
        })

        # Adicionar botoes de acao se houver actions
        if notification.actions:
            blocks.append({"type": "divider"})
            blocks.append(self._build_actions(notification))

        return {
            "text": f"{icon} CRITICO: {notification.title}",
            "attachments": [{
                "color": color,
                "blocks": blocks
            }]
        }

    def _format_attention(self, notification: Notification) -> Dict[str, Any]:
        """
        Formata alerta de atencao.

        Visual: Header laranja, campos organizados, sem botoes.
        """
        icon = ICONS[AlertCategory.ATTENTION]
        domain_icon = DOMAIN_ICONS.get(notification.domain, "🔔")
        color = COLORS[AlertCategory.ATTENTION]

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{icon} {notification.title}*\n\n{notification.message}"
                }
            }
        ]

        # Adicionar campos se houver metadata
        if notification.metadata:
            fields = self._build_fields(notification.metadata)
            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields[:8]
                })

        # Contexto compacto
        timestamp = datetime.now(timezone.utc).strftime("%H:%M")
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"{domain_icon} {notification.domain.value} | `{notification.alert_type}` | {timestamp}"}
            ]
        })

        return {
            "text": f"{icon} Atencao: {notification.title}",
            "attachments": [{
                "color": color,
                "blocks": blocks
            }]
        }

    def _format_digest_single(self, notification: Notification) -> Dict[str, Any]:
        """
        Formata notificacao de digest individual.

        Visual: Compacto, uma linha por item.
        """
        icon = ICONS[AlertCategory.DIGEST]
        domain_icon = DOMAIN_ICONS.get(notification.domain, "📋")

        return {
            "text": f"{icon} {notification.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{domain_icon} *{notification.title}*\n{notification.message}"
                    }
                }
            ]
        }

    def _format_digest_batch(self, batch: DigestBatch) -> Dict[str, Any]:
        """
        Formata batch de digest consolidado.

        Visual: Header com contagem, lista agrupada por dominio.
        """
        icon = ICONS[AlertCategory.DIGEST]
        color = COLORS[AlertCategory.DIGEST]

        # Agrupar por dominio
        by_domain: Dict[AlertDomain, List[Notification]] = {}
        for notif in batch.notifications:
            if notif.domain not in by_domain:
                by_domain[notif.domain] = []
            by_domain[notif.domain].append(notif)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{icon} Resumo: {batch.count} notificacoes",
                    "emoji": True
                }
            }
        ]

        # Adicionar secao por dominio
        for domain, notifications in by_domain.items():
            domain_icon = DOMAIN_ICONS.get(domain, "📋")

            # Criar lista de items
            items = []
            for n in notifications[:5]:  # Max 5 por dominio
                items.append(f"• {n.title}")

            if len(notifications) > 5:
                items.append(f"_... e mais {len(notifications) - 5}_")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{domain_icon} {domain.value}* ({len(notifications)})\n" + "\n".join(items)
                }
            })

        # Contexto com periodo
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Periodo: {batch.window_start.strftime('%H:%M')} - {batch.window_end.strftime('%H:%M')}"}
            ]
        })

        return {
            "text": f"{icon} Resumo: {batch.count} notificacoes",
            "attachments": [{
                "color": color,
                "blocks": blocks
            }]
        }

    def _format_info(self, notification: Notification) -> Dict[str, Any]:
        """
        Formata notificacao informativa.

        Visual: Minimo, apenas texto.
        """
        icon = ICONS[AlertCategory.INFO]
        domain_icon = DOMAIN_ICONS.get(notification.domain, "ℹ️")

        return {
            "text": f"{icon} {notification.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{domain_icon} *{notification.title}*\n{notification.message}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"`{notification.alert_type}`"}
                    ]
                }
            ]
        }

    def _build_fields(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Converte metadata em campos do Slack.

        Args:
            metadata: Dict com dados

        Returns:
            Lista de campos formatados
        """
        fields = []

        for key, value in metadata.items():
            # Pular valores None ou vazios
            if value is None or value == "":
                continue

            # Formatar chave (snake_case -> Title Case)
            label = key.replace("_", " ").title()

            # Formatar valor
            if isinstance(value, bool):
                formatted = "Sim" if value else "Nao"
            elif isinstance(value, (int, float)):
                formatted = str(value)
            elif isinstance(value, datetime):
                formatted = value.strftime("%d/%m %H:%M")
            else:
                formatted = str(value)[:100]

            fields.append({
                "type": "mrkdwn",
                "text": f"*{label}:*\n{formatted}"
            })

        return fields

    def _build_actions(self, notification: Notification) -> Dict[str, Any]:
        """
        Constroi bloco de acoes.

        Args:
            notification: Notificacao com actions

        Returns:
            Bloco de actions
        """
        elements = []

        for action in notification.actions[:5]:  # Max 5 botoes
            button = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": action.get("label", "Acao"),
                    "emoji": True
                },
                "action_id": action.get("action_id", "action"),
                "value": action.get("value", "")
            }

            # Estilo do botao
            style = action.get("style")
            if style in ("primary", "danger"):
                button["style"] = style

            elements.append(button)

        return {
            "type": "actions",
            "block_id": f"actions_{notification.id[:8]}",
            "elements": elements
        }


# Singleton
slack_formatter = SlackFormatter()
```

---

## Testes Obrigatorios

### Arquivo: `tests/services/notifications/test_formatters.py`

```python
"""Testes para formatadores Slack."""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.notifications import (
    Notification,
    AlertCategory,
    AlertDomain,
    DigestBatch,
)
from app.services.notifications.formatters import (
    SlackFormatter,
    slack_formatter,
    COLORS,
    ICONS,
    DOMAIN_ICONS,
)


@pytest.fixture
def formatter():
    """Fixture para SlackFormatter."""
    return SlackFormatter()


@pytest.fixture
def notification_critical():
    """Notificacao critica."""
    return Notification(
        domain=AlertDomain.WHATSAPP,
        category=AlertCategory.CRITICAL,
        alert_type="desconectado",
        title="WhatsApp Offline",
        message="Conexao perdida com Evolution API",
        metadata={"instancia": "julia-01", "ultimo_ping": "10:30"},
    )


@pytest.fixture
def notification_attention():
    """Notificacao de atencao."""
    return Notification(
        domain=AlertDomain.FUNNEL,
        category=AlertCategory.ATTENTION,
        alert_type="conversion_drop",
        title="Queda na Conversao",
        message="Taxa de conversao caiu 15%",
        metadata={"taxa_atual": "12%", "taxa_anterior": "27%"},
    )


@pytest.fixture
def notification_digest():
    """Notificacao de digest."""
    return Notification(
        domain=AlertDomain.SHIFT,
        category=AlertCategory.DIGEST,
        alert_type="plantao_reservado",
        title="Plantao Reservado",
        message="Dr. Silva reservou plantao dia 20/01",
    )


@pytest.fixture
def notification_info():
    """Notificacao informativa."""
    return Notification(
        domain=AlertDomain.SYSTEM,
        category=AlertCategory.INFO,
        alert_type="backup_ok",
        title="Backup Concluido",
        message="Backup diario finalizado com sucesso",
    )


@pytest.fixture
def notification_with_actions():
    """Notificacao com acoes."""
    return Notification(
        domain=AlertDomain.WHATSAPP,
        category=AlertCategory.CRITICAL,
        alert_type="handoff_pendente",
        title="Handoff Pendente",
        message="Medico aguardando atendimento humano",
        actions=[
            {"label": "Assumir", "action_id": "assumir_handoff", "value": "123", "style": "primary"},
            {"label": "Ignorar", "action_id": "ignorar_handoff", "value": "123", "style": "danger"},
        ]
    )


class TestFormatCritical:
    """Testes para formato critico."""

    def test_tem_header_com_icone(self, formatter, notification_critical):
        """Header deve ter icone de critico."""
        result = formatter.format(notification_critical)

        assert "attachments" in result
        blocks = result["attachments"][0]["blocks"]
        header = blocks[0]

        assert header["type"] == "header"
        assert "🚨" in header["text"]["text"]

    def test_cor_vermelha(self, formatter, notification_critical):
        """Attachment deve ter cor vermelha."""
        result = formatter.format(notification_critical)

        color = result["attachments"][0]["color"]
        assert color == COLORS[AlertCategory.CRITICAL]
        assert color == "#c62828"

    def test_tem_campos_metadata(self, formatter, notification_critical):
        """Deve incluir campos de metadata."""
        result = formatter.format(notification_critical)

        blocks = result["attachments"][0]["blocks"]

        # Procurar bloco com fields
        has_fields = any(
            "fields" in block
            for block in blocks
            if block.get("type") == "section"
        )
        assert has_fields

    def test_tem_contexto(self, formatter, notification_critical):
        """Deve incluir contexto com dominio e tipo."""
        result = formatter.format(notification_critical)

        blocks = result["attachments"][0]["blocks"]
        context = next(
            (b for b in blocks if b.get("type") == "context"),
            None
        )

        assert context is not None
        elements_text = str(context["elements"])
        assert "whatsapp" in elements_text.lower()
        assert "desconectado" in elements_text


class TestFormatAttention:
    """Testes para formato de atencao."""

    def test_cor_laranja(self, formatter, notification_attention):
        """Attachment deve ter cor laranja."""
        result = formatter.format(notification_attention)

        color = result["attachments"][0]["color"]
        assert color == COLORS[AlertCategory.ATTENTION]
        assert color == "#f57c00"

    def test_tem_icone_atencao(self, formatter, notification_attention):
        """Deve ter icone de atencao."""
        result = formatter.format(notification_attention)

        text = result["text"]
        assert "⚠️" in text

    def test_titulo_em_negrito(self, formatter, notification_attention):
        """Titulo deve estar em negrito."""
        result = formatter.format(notification_attention)

        blocks = result["attachments"][0]["blocks"]
        section = blocks[0]

        assert "*" in section["text"]["text"]  # Markdown bold


class TestFormatDigestSingle:
    """Testes para formato de digest individual."""

    def test_formato_compacto(self, formatter, notification_digest):
        """Digest individual deve ser compacto."""
        result = formatter.format(notification_digest)

        assert "blocks" in result
        assert len(result["blocks"]) <= 2  # Maximo 2 blocos

    def test_sem_attachments(self, formatter, notification_digest):
        """Digest individual nao usa attachments."""
        result = formatter.format(notification_digest)

        assert "attachments" not in result


class TestFormatDigestBatch:
    """Testes para formato de digest em batch."""

    def test_header_com_contagem(self, formatter):
        """Header deve mostrar contagem."""
        notifications = [
            Notification(
                domain=AlertDomain.SHIFT,
                category=AlertCategory.DIGEST,
                alert_type="plantao_reservado",
                title=f"Plantao {i}",
                message=f"Mensagem {i}",
            )
            for i in range(3)
        ]

        batch = DigestBatch(
            notifications=notifications,
            window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            window_end=datetime.now(timezone.utc),
        )

        result = formatter.format_digest(batch)

        assert "3 notificacoes" in result["text"]

    def test_agrupa_por_dominio(self, formatter):
        """Deve agrupar notificacoes por dominio."""
        notifications = [
            Notification(domain=AlertDomain.SHIFT, category=AlertCategory.DIGEST,
                        alert_type="plantao_reservado", title="Plantao 1", message="Msg"),
            Notification(domain=AlertDomain.SHIFT, category=AlertCategory.DIGEST,
                        alert_type="plantao_reservado", title="Plantao 2", message="Msg"),
            Notification(domain=AlertDomain.BUSINESS, category=AlertCategory.DIGEST,
                        alert_type="evento_business", title="Evento 1", message="Msg"),
        ]

        batch = DigestBatch(
            notifications=notifications,
            window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            window_end=datetime.now(timezone.utc),
        )

        result = formatter.format_digest(batch)
        blocks = result["attachments"][0]["blocks"]

        # Deve ter secoes para SHIFT e BUSINESS
        blocks_text = str(blocks)
        assert "shift" in blocks_text.lower() or "📅" in blocks_text
        assert "business" in blocks_text.lower() or "💼" in blocks_text

    def test_limita_items_por_dominio(self, formatter):
        """Deve limitar a 5 items por dominio."""
        notifications = [
            Notification(domain=AlertDomain.SHIFT, category=AlertCategory.DIGEST,
                        alert_type="plantao_reservado", title=f"Plantao {i}", message="Msg")
            for i in range(10)
        ]

        batch = DigestBatch(
            notifications=notifications,
            window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            window_end=datetime.now(timezone.utc),
        )

        result = formatter.format_digest(batch)
        blocks_text = str(result)

        # Deve mostrar "e mais X"
        assert "e mais" in blocks_text


class TestFormatInfo:
    """Testes para formato informativo."""

    def test_formato_minimo(self, formatter, notification_info):
        """Info deve ter formato minimo."""
        result = formatter.format(notification_info)

        assert "blocks" in result
        # Apenas section e context
        assert len(result["blocks"]) == 2

    def test_tem_icone_info(self, formatter, notification_info):
        """Deve ter icone de info."""
        result = formatter.format(notification_info)

        assert "ℹ️" in result["text"]


class TestFormatWithActions:
    """Testes para notificacoes com acoes."""

    def test_inclui_botoes(self, formatter, notification_with_actions):
        """Deve incluir botoes de acao."""
        result = formatter.format(notification_with_actions)

        blocks = result["attachments"][0]["blocks"]
        actions_block = next(
            (b for b in blocks if b.get("type") == "actions"),
            None
        )

        assert actions_block is not None
        assert len(actions_block["elements"]) == 2

    def test_botoes_tem_estilo(self, formatter, notification_with_actions):
        """Botoes devem ter estilo correto."""
        result = formatter.format(notification_with_actions)

        blocks = result["attachments"][0]["blocks"]
        actions_block = next(
            (b for b in blocks if b.get("type") == "actions"),
            None
        )

        buttons = actions_block["elements"]
        assert buttons[0]["style"] == "primary"
        assert buttons[1]["style"] == "danger"


class TestBuildFields:
    """Testes para _build_fields."""

    def test_converte_metadata_em_campos(self, formatter):
        """Converte dict em campos Slack."""
        metadata = {
            "hospital": "Sao Luiz",
            "valor": 2500,
            "ativo": True,
        }

        fields = formatter._build_fields(metadata)

        assert len(fields) == 3
        assert all(f["type"] == "mrkdwn" for f in fields)

    def test_ignora_valores_none(self, formatter):
        """Ignora valores None."""
        metadata = {
            "hospital": "Sao Luiz",
            "setor": None,
            "valor": "",
        }

        fields = formatter._build_fields(metadata)

        assert len(fields) == 1  # Apenas hospital

    def test_formata_booleanos(self, formatter):
        """Formata booleanos como Sim/Nao."""
        metadata = {"ativo": True, "urgente": False}

        fields = formatter._build_fields(metadata)

        values = [f["text"] for f in fields]
        assert any("Sim" in v for v in values)
        assert any("Nao" in v for v in values)


class TestConstants:
    """Testes para constantes."""

    def test_todas_categorias_tem_cor(self):
        """Todas categorias devem ter cor definida."""
        for category in AlertCategory:
            assert category in COLORS

    def test_todas_categorias_tem_icone(self):
        """Todas categorias devem ter icone definido."""
        for category in AlertCategory:
            assert category in ICONS

    def test_todos_dominios_tem_icone(self):
        """Todos dominios devem ter icone definido."""
        for domain in AlertDomain:
            assert domain in DOMAIN_ICONS


class TestSingleton:
    """Testes para singleton."""

    def test_singleton_exportado(self):
        """slack_formatter e um singleton."""
        assert slack_formatter is not None
        assert isinstance(slack_formatter, SlackFormatter)
```

---

## Checklist de Conclusao

### Implementacao
- [ ] Criar arquivo `formatters.py`
- [ ] Implementar `SlackFormatter`
- [ ] Implementar `_format_critical`
- [ ] Implementar `_format_attention`
- [ ] Implementar `_format_digest_single`
- [ ] Implementar `_format_digest_batch`
- [ ] Implementar `_format_info`
- [ ] Implementar `_build_fields`
- [ ] Implementar `_build_actions`
- [ ] Definir constantes COLORS, ICONS, DOMAIN_ICONS
- [ ] Exportar singleton
- [ ] Atualizar `__init__.py`

### Testes
- [ ] Criar `tests/services/notifications/test_formatters.py`
- [ ] Testar formato critico
- [ ] Testar formato atencao
- [ ] Testar formato digest single
- [ ] Testar formato digest batch
- [ ] Testar formato info
- [ ] Testar acoes/botoes
- [ ] Testar build_fields
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros de mypy
- [ ] Zero erros de ruff

---

## Definition of Done (E06)

1. [ ] `SlackFormatter` implementado
2. [ ] 4 formatos por categoria funcionando
3. [ ] Digest batch agrupando por dominio
4. [ ] Botoes de acao funcionando
5. [ ] Singleton exportado
6. [ ] 100% dos testes passando (0 skipped)
7. [ ] Zero erros de tipo/lint
