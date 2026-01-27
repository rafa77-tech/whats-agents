# E02 - Configuracoes e Regras

**Epico:** E02
**Nome:** Configuracoes e Regras
**Dependencias:** E01
**Prioridade:** Alta

---

## Objetivo

Definir todas as configuracoes, thresholds e regras de correlacao do sistema de notificacoes. Este arquivo centraliza toda a logica de configuracao.

---

## Entregaveis

### Arquivo: `config.py`

```python
"""
Configuracoes do NotificationHub.

Sprint 41

Centraliza todas as configuracoes de:
- Cooldown por categoria
- Janela operacional
- Regras de correlacao
- Mapeamento de tipos de alerta
"""
from zoneinfo import ZoneInfo

from .types import AlertCategory, AlertDomain

# Timezone Brasil
TZ_SP = ZoneInfo("America/Sao_Paulo")

# =============================================================================
# CONFIGURACOES POR CATEGORIA
# =============================================================================

CATEGORY_CONFIG = {
    AlertCategory.CRITICAL: {
        "cooldown_minutes": 15,
        "operating_window": False,  # 24/7
        "max_per_hour": 10,
        "emoji": ":rotating_light:",
        "color": "#FF0000",
    },
    AlertCategory.ATTENTION: {
        "cooldown_minutes": 30,
        "operating_window": True,  # 08-20h
        "max_per_hour": 5,
        "emoji": ":warning:",
        "color": "#FF9800",
    },
    AlertCategory.DIGEST: {
        "cooldown_minutes": 0,  # Sem cooldown individual
        "operating_window": True,
        "digest_interval_minutes": 60,
        "emoji": ":memo:",
        "color": "#2196F3",
    },
    AlertCategory.INFO: {
        "cooldown_minutes": 60,
        "operating_window": True,
        "max_per_hour": 3,
        "emoji": ":information_source:",
        "color": "#607D8B",
    },
}

# =============================================================================
# JANELA OPERACIONAL
# =============================================================================

OPERATING_WINDOW = {
    "start_hour": 8,   # 08:00
    "end_hour": 20,    # 20:00
}

# =============================================================================
# CLUSTERS DE CORRELACAO
# =============================================================================

CORRELATION_CLUSTERS = {
    "whatsapp": {
        "domains": [AlertDomain.WHATSAPP],
        "types": ["desconectado", "criptografia", "evolution_down", "sem_respostas"],
        "window_minutes": 30,
        "priority_order": ["desconectado", "evolution_down", "criptografia", "sem_respostas"],
    },
    "chips": {
        "domains": [AlertDomain.CHIPS],
        "types": ["pool_vazio", "pool_baixo_prospeccao", "pool_baixo_followup", "trust_critico", "chip_desconectado"],
        "window_minutes": 60,
        "priority_order": ["pool_vazio", "pool_baixo_prospeccao", "pool_baixo_followup", "trust_critico"],
    },
    "funnel": {
        "domains": [AlertDomain.BUSINESS],
        "types": ["handoff_spike", "recusa_spike", "conversion_drop"],
        "window_minutes": 60,
        "aggregate_into_summary": True,
    },
    "performance": {
        "domains": [AlertDomain.SYSTEM],
        "types": ["performance_critica", "tempo_resposta_alto"],
        "window_minutes": 30,
        "priority_order": ["performance_critica", "tempo_resposta_alto"],
    },
}

# =============================================================================
# MAPEAMENTO DE TIPOS PARA CATEGORIAS
# =============================================================================

ALERT_TYPE_DEFAULTS = {
    # CRITICAL - Acao imediata necessaria
    "desconectado": AlertCategory.CRITICAL,
    "evolution_down": AlertCategory.CRITICAL,
    "pool_vazio": AlertCategory.CRITICAL,
    "sem_respostas": AlertCategory.CRITICAL,
    "shift_transition_failed": AlertCategory.CRITICAL,
    "performance_critica": AlertCategory.CRITICAL,

    # ATTENTION - Revisar quando possivel
    "taxa_handoff_alta": AlertCategory.ATTENTION,
    "tempo_resposta_alto": AlertCategory.ATTENTION,
    "score_qualidade_baixo": AlertCategory.ATTENTION,
    "trust_critico": AlertCategory.ATTENTION,
    "criptografia": AlertCategory.ATTENTION,
    "handoff_spike": AlertCategory.ATTENTION,
    "recusa_spike": AlertCategory.ATTENTION,
    "conversion_drop": AlertCategory.ATTENTION,
    "pool_baixo_prospeccao": AlertCategory.ATTENTION,
    "pool_baixo_followup": AlertCategory.ATTENTION,
    "confirmation_overdue": AlertCategory.ATTENTION,
    "handoff_criado": AlertCategory.ATTENTION,

    # DIGEST - Batched
    "plantao_reservado": AlertCategory.DIGEST,
    "handoff_resolvido": AlertCategory.DIGEST,
    "confirmacao_plantao": AlertCategory.DIGEST,
    "briefing_progresso": AlertCategory.DIGEST,
    "briefing_completo": AlertCategory.DIGEST,
    "hospital_bloqueado": AlertCategory.DIGEST,
    "hospital_desbloqueado": AlertCategory.DIGEST,
    "chip_ativado": AlertCategory.DIGEST,
    "external_handoff_confirmado": AlertCategory.DIGEST,

    # INFO - Baixa prioridade
    "reconectado": AlertCategory.INFO,
    "chip_promovido": AlertCategory.INFO,
    "reconciliation_ok": AlertCategory.INFO,
}

# =============================================================================
# CORES POR SEVERIDADE
# =============================================================================

SEVERITY_COLORS = {
    "info": "#2196F3",      # Azul
    "warning": "#FF9800",   # Laranja
    "error": "#F44336",     # Vermelho
    "critical": "#9C27B0",  # Roxo
}

# =============================================================================
# REDIS KEYS
# =============================================================================

REDIS_KEYS = {
    "cooldown_prefix": "notif:cooldown:",
    "correlation_prefix": "notif:corr:",
    "digest_pending": "notif:digest:pending",
    "stats_prefix": "notif:stats:",
    "enabled": "notif:enabled",
}

# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================


def get_category_for_alert_type(alert_type: str) -> AlertCategory:
    """
    Retorna categoria para um tipo de alerta.

    Args:
        alert_type: Tipo do alerta (ex: "desconectado")

    Returns:
        AlertCategory correspondente (default: ATTENTION)
    """
    return ALERT_TYPE_DEFAULTS.get(alert_type, AlertCategory.ATTENTION)


def get_cooldown_minutes(category: AlertCategory) -> int:
    """
    Retorna cooldown em minutos para categoria.

    Args:
        category: Categoria do alerta

    Returns:
        Cooldown em minutos
    """
    return CATEGORY_CONFIG[category]["cooldown_minutes"]


def get_cluster_for_alert(alert_type: str) -> str | None:
    """
    Retorna nome do cluster para um tipo de alerta.

    Args:
        alert_type: Tipo do alerta

    Returns:
        Nome do cluster ou None se nao pertence a nenhum
    """
    for cluster_name, cluster_config in CORRELATION_CLUSTERS.items():
        if alert_type in cluster_config["types"]:
            return cluster_name
    return None


def is_within_operating_window(hour: int) -> bool:
    """
    Verifica se hora esta dentro da janela operacional.

    Args:
        hour: Hora do dia (0-23)

    Returns:
        True se dentro da janela, False caso contrario
    """
    return OPERATING_WINDOW["start_hour"] <= hour < OPERATING_WINDOW["end_hour"]


def respects_operating_window(category: AlertCategory) -> bool:
    """
    Verifica se categoria respeita janela operacional.

    Args:
        category: Categoria do alerta

    Returns:
        True se respeita janela, False se e 24/7
    """
    return CATEGORY_CONFIG[category]["operating_window"]


def get_category_color(category: AlertCategory) -> str:
    """
    Retorna cor hex para categoria.

    Args:
        category: Categoria do alerta

    Returns:
        Cor em formato hex
    """
    return CATEGORY_CONFIG[category]["color"]


def get_category_emoji(category: AlertCategory) -> str:
    """
    Retorna emoji para categoria.

    Args:
        category: Categoria do alerta

    Returns:
        Emoji em formato Slack
    """
    return CATEGORY_CONFIG[category]["emoji"]
```

---

## Testes Obrigatorios

### Arquivo: `tests/services/notifications/test_config.py`

```python
"""Testes para configuracoes do NotificationHub."""
import pytest

from app.services.notifications import AlertCategory, AlertDomain
from app.services.notifications.config import (
    CATEGORY_CONFIG,
    CORRELATION_CLUSTERS,
    ALERT_TYPE_DEFAULTS,
    OPERATING_WINDOW,
    SEVERITY_COLORS,
    REDIS_KEYS,
    get_category_for_alert_type,
    get_cooldown_minutes,
    get_cluster_for_alert,
    is_within_operating_window,
    respects_operating_window,
    get_category_color,
    get_category_emoji,
)


class TestCategoryConfig:
    """Testes para CATEGORY_CONFIG."""

    def test_todas_categorias_configuradas(self):
        """Verifica que todas as categorias tem config."""
        for category in AlertCategory:
            assert category in CATEGORY_CONFIG
            assert "cooldown_minutes" in CATEGORY_CONFIG[category]
            assert "operating_window" in CATEGORY_CONFIG[category]
            assert "emoji" in CATEGORY_CONFIG[category]
            assert "color" in CATEGORY_CONFIG[category]

    def test_critical_24h(self):
        """CRITICAL nao respeita janela operacional."""
        assert CATEGORY_CONFIG[AlertCategory.CRITICAL]["operating_window"] is False

    def test_attention_tem_janela(self):
        """ATTENTION respeita janela operacional."""
        assert CATEGORY_CONFIG[AlertCategory.ATTENTION]["operating_window"] is True

    def test_digest_sem_cooldown(self):
        """DIGEST tem cooldown 0."""
        assert CATEGORY_CONFIG[AlertCategory.DIGEST]["cooldown_minutes"] == 0

    def test_cooldowns_definidos(self):
        """Todas as categorias tem cooldown definido."""
        for category in AlertCategory:
            assert "cooldown_minutes" in CATEGORY_CONFIG[category]
            assert isinstance(CATEGORY_CONFIG[category]["cooldown_minutes"], int)
            assert CATEGORY_CONFIG[category]["cooldown_minutes"] >= 0

    def test_cores_sao_hex_validas(self):
        """Todas as cores sao hex validas."""
        for category in AlertCategory:
            color = CATEGORY_CONFIG[category]["color"]
            assert color.startswith("#")
            assert len(color) == 7


class TestOperatingWindow:
    """Testes para OPERATING_WINDOW."""

    def test_janela_configurada(self):
        """Janela operacional esta configurada."""
        assert "start_hour" in OPERATING_WINDOW
        assert "end_hour" in OPERATING_WINDOW

    def test_janela_08_20(self):
        """Janela e 08:00 a 20:00."""
        assert OPERATING_WINDOW["start_hour"] == 8
        assert OPERATING_WINDOW["end_hour"] == 20


class TestCorrelationClusters:
    """Testes para CORRELATION_CLUSTERS."""

    def test_cluster_whatsapp_existe(self):
        """Cluster whatsapp esta configurado."""
        assert "whatsapp" in CORRELATION_CLUSTERS
        assert "desconectado" in CORRELATION_CLUSTERS["whatsapp"]["types"]
        assert "criptografia" in CORRELATION_CLUSTERS["whatsapp"]["types"]

    def test_cluster_chips_existe(self):
        """Cluster chips esta configurado."""
        assert "chips" in CORRELATION_CLUSTERS
        assert "pool_vazio" in CORRELATION_CLUSTERS["chips"]["types"]

    def test_cluster_funnel_existe(self):
        """Cluster funnel esta configurado."""
        assert "funnel" in CORRELATION_CLUSTERS
        assert "handoff_spike" in CORRELATION_CLUSTERS["funnel"]["types"]

    def test_cluster_performance_existe(self):
        """Cluster performance esta configurado."""
        assert "performance" in CORRELATION_CLUSTERS
        assert "performance_critica" in CORRELATION_CLUSTERS["performance"]["types"]

    def test_clusters_tem_window(self):
        """Todos os clusters tem janela de tempo."""
        for cluster_name, config in CORRELATION_CLUSTERS.items():
            assert "window_minutes" in config
            assert config["window_minutes"] > 0

    def test_clusters_tem_types(self):
        """Todos os clusters tem tipos definidos."""
        for cluster_name, config in CORRELATION_CLUSTERS.items():
            assert "types" in config
            assert len(config["types"]) > 0


class TestAlertTypeDefaults:
    """Testes para ALERT_TYPE_DEFAULTS."""

    def test_critical_alerts(self):
        """Alertas criticos estao mapeados."""
        critical_types = ["desconectado", "pool_vazio", "sem_respostas"]
        for alert_type in critical_types:
            assert alert_type in ALERT_TYPE_DEFAULTS
            assert ALERT_TYPE_DEFAULTS[alert_type] == AlertCategory.CRITICAL

    def test_attention_alerts(self):
        """Alertas attention estao mapeados."""
        attention_types = ["handoff_spike", "trust_critico", "criptografia"]
        for alert_type in attention_types:
            assert alert_type in ALERT_TYPE_DEFAULTS
            assert ALERT_TYPE_DEFAULTS[alert_type] == AlertCategory.ATTENTION

    def test_digest_alerts(self):
        """Alertas digest estao mapeados."""
        digest_types = ["plantao_reservado", "handoff_resolvido"]
        for alert_type in digest_types:
            assert alert_type in ALERT_TYPE_DEFAULTS
            assert ALERT_TYPE_DEFAULTS[alert_type] == AlertCategory.DIGEST

    def test_info_alerts(self):
        """Alertas info estao mapeados."""
        info_types = ["reconectado", "chip_promovido"]
        for alert_type in info_types:
            assert alert_type in ALERT_TYPE_DEFAULTS
            assert ALERT_TYPE_DEFAULTS[alert_type] == AlertCategory.INFO


class TestRedisKeys:
    """Testes para REDIS_KEYS."""

    def test_todas_chaves_definidas(self):
        """Todas as chaves Redis estao definidas."""
        assert "cooldown_prefix" in REDIS_KEYS
        assert "correlation_prefix" in REDIS_KEYS
        assert "digest_pending" in REDIS_KEYS
        assert "stats_prefix" in REDIS_KEYS
        assert "enabled" in REDIS_KEYS

    def test_prefixos_consistentes(self):
        """Prefixos comecam com 'notif:'."""
        assert REDIS_KEYS["cooldown_prefix"].startswith("notif:")
        assert REDIS_KEYS["correlation_prefix"].startswith("notif:")
        assert REDIS_KEYS["digest_pending"].startswith("notif:")


class TestGetCategoryForAlertType:
    """Testes para get_category_for_alert_type."""

    def test_tipo_conhecido_critical(self):
        """Retorna CRITICAL para tipo critico."""
        assert get_category_for_alert_type("desconectado") == AlertCategory.CRITICAL

    def test_tipo_conhecido_digest(self):
        """Retorna DIGEST para tipo digest."""
        assert get_category_for_alert_type("plantao_reservado") == AlertCategory.DIGEST

    def test_tipo_desconhecido_retorna_attention(self):
        """Retorna ATTENTION para tipo desconhecido."""
        assert get_category_for_alert_type("tipo_inexistente") == AlertCategory.ATTENTION


class TestGetCooldownMinutes:
    """Testes para get_cooldown_minutes."""

    def test_cooldown_critical(self):
        """Retorna 15min para CRITICAL."""
        assert get_cooldown_minutes(AlertCategory.CRITICAL) == 15

    def test_cooldown_attention(self):
        """Retorna 30min para ATTENTION."""
        assert get_cooldown_minutes(AlertCategory.ATTENTION) == 30

    def test_cooldown_digest(self):
        """Retorna 0 para DIGEST."""
        assert get_cooldown_minutes(AlertCategory.DIGEST) == 0

    def test_cooldown_info(self):
        """Retorna 60min para INFO."""
        assert get_cooldown_minutes(AlertCategory.INFO) == 60


class TestGetClusterForAlert:
    """Testes para get_cluster_for_alert."""

    def test_desconectado_cluster_whatsapp(self):
        """desconectado pertence ao cluster whatsapp."""
        assert get_cluster_for_alert("desconectado") == "whatsapp"

    def test_pool_vazio_cluster_chips(self):
        """pool_vazio pertence ao cluster chips."""
        assert get_cluster_for_alert("pool_vazio") == "chips"

    def test_handoff_spike_cluster_funnel(self):
        """handoff_spike pertence ao cluster funnel."""
        assert get_cluster_for_alert("handoff_spike") == "funnel"

    def test_tipo_sem_cluster(self):
        """Tipo sem cluster retorna None."""
        assert get_cluster_for_alert("tipo_sem_cluster") is None

    def test_plantao_reservado_sem_cluster(self):
        """plantao_reservado nao pertence a nenhum cluster."""
        assert get_cluster_for_alert("plantao_reservado") is None


class TestIsWithinOperatingWindow:
    """Testes para is_within_operating_window."""

    def test_dentro_janela_inicio(self):
        """08:00 esta dentro da janela."""
        assert is_within_operating_window(8) is True

    def test_dentro_janela_meio(self):
        """12:00 esta dentro da janela."""
        assert is_within_operating_window(12) is True

    def test_dentro_janela_fim(self):
        """19:00 esta dentro da janela."""
        assert is_within_operating_window(19) is True

    def test_fora_janela_antes(self):
        """07:00 esta fora da janela."""
        assert is_within_operating_window(7) is False

    def test_fora_janela_limite(self):
        """20:00 esta fora da janela (limite exclusivo)."""
        assert is_within_operating_window(20) is False

    def test_fora_janela_noite(self):
        """23:00 esta fora da janela."""
        assert is_within_operating_window(23) is False

    def test_fora_janela_madrugada(self):
        """03:00 esta fora da janela."""
        assert is_within_operating_window(3) is False


class TestRespectsOperatingWindow:
    """Testes para respects_operating_window."""

    def test_critical_nao_respeita(self):
        """CRITICAL nao respeita janela."""
        assert respects_operating_window(AlertCategory.CRITICAL) is False

    def test_attention_respeita(self):
        """ATTENTION respeita janela."""
        assert respects_operating_window(AlertCategory.ATTENTION) is True

    def test_digest_respeita(self):
        """DIGEST respeita janela."""
        assert respects_operating_window(AlertCategory.DIGEST) is True

    def test_info_respeita(self):
        """INFO respeita janela."""
        assert respects_operating_window(AlertCategory.INFO) is True


class TestGetCategoryColor:
    """Testes para get_category_color."""

    def test_critical_vermelho(self):
        """CRITICAL e vermelho."""
        assert get_category_color(AlertCategory.CRITICAL) == "#FF0000"

    def test_attention_laranja(self):
        """ATTENTION e laranja."""
        assert get_category_color(AlertCategory.ATTENTION) == "#FF9800"

    def test_retorna_hex_valido(self):
        """Todas as cores sao hex validas."""
        for category in AlertCategory:
            color = get_category_color(category)
            assert color.startswith("#")
            assert len(color) == 7


class TestGetCategoryEmoji:
    """Testes para get_category_emoji."""

    def test_critical_emoji(self):
        """CRITICAL tem emoji de alerta."""
        emoji = get_category_emoji(AlertCategory.CRITICAL)
        assert emoji == ":rotating_light:"

    def test_attention_emoji(self):
        """ATTENTION tem emoji de warning."""
        emoji = get_category_emoji(AlertCategory.ATTENTION)
        assert emoji == ":warning:"

    def test_digest_emoji(self):
        """DIGEST tem emoji de memo."""
        emoji = get_category_emoji(AlertCategory.DIGEST)
        assert emoji == ":memo:"

    def test_info_emoji(self):
        """INFO tem emoji de informacao."""
        emoji = get_category_emoji(AlertCategory.INFO)
        assert emoji == ":information_source:"
```

---

## Checklist de Conclusao

### Implementacao
- [ ] Criar arquivo `config.py` com todas as configuracoes
- [ ] Definir CATEGORY_CONFIG para todas as categorias
- [ ] Definir CORRELATION_CLUSTERS para todos os clusters
- [ ] Definir ALERT_TYPE_DEFAULTS para todos os tipos conhecidos
- [ ] Definir SEVERITY_COLORS
- [ ] Definir REDIS_KEYS
- [ ] Implementar todas as funcoes auxiliares
- [ ] Atualizar `__init__.py` para exportar config

### Testes
- [ ] Criar `tests/services/notifications/test_config.py`
- [ ] Testar todas as configuracoes
- [ ] Testar todas as funcoes auxiliares
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros de mypy
- [ ] Zero erros de ruff

---

## Definition of Done (E02)

Este epico esta **COMPLETO** quando:

1. [ ] Arquivo `config.py` criado com todas as configuracoes
2. [ ] Todas as categorias configuradas em CATEGORY_CONFIG
3. [ ] Todos os clusters de correlacao definidos
4. [ ] Mapeamento de tipos completo em ALERT_TYPE_DEFAULTS
5. [ ] Todas as funcoes auxiliares implementadas
6. [ ] 100% dos testes passando (0 skipped)
7. [ ] Zero erros de tipo/lint
