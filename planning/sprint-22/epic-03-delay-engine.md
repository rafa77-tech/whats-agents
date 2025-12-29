# E03: Delay Engine

**Epico:** Motor de Delay por Contexto
**Estimativa:** 4h
**Dependencias:** E01 (Migrations), E02 (Classificador)

---

## Objetivo

Criar motor que calcula delay apropriado baseado no tipo de contexto, substituindo o delay fixo atual por delay inteligente.

---

## Escopo

### Incluido

- [x] Servico `delay_engine.py`
- [x] Configuracao de delays por tipo
- [x] Variacao humanizada (nao robotico)
- [x] Integracao com fila de mensagens
- [x] Bypass para replies urgentes

### Excluido

- [ ] Logica de fora do horario (E04)
- [ ] Alteracao de jobs (E05)

---

## Configuracao de Delays

| Tipo | Min (ms) | Max (ms) | Prioridade | Fora Horario |
|------|----------|----------|------------|--------------|
| `reply_direta` | 0 | 3000 | 1 | Sim |
| `aceite_vaga` | 0 | 2000 | 1 | Sim |
| `confirmacao` | 2000 | 5000 | 2 | Sim |
| `oferta_ativa` | 15000 | 45000 | 3 | Nao |
| `followup` | 30000 | 120000 | 4 | Nao |
| `campanha_fria` | 60000 | 180000 | 5 | Nao |

---

## Tarefas

### T01: Servico delay_engine.py

**Arquivo:** `app/services/delay_engine.py`

```python
"""
Motor de delay inteligente.

Calcula delay apropriado baseado no tipo de contexto da mensagem.

Sprint 22 - Responsividade Inteligente
"""
import random
import logging
import asyncio
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from app.services.message_context_classifier import ContextType, ContextClassification

logger = logging.getLogger(__name__)


@dataclass
class DelayConfig:
    """Configuracao de delay para um tipo de contexto."""
    tipo: ContextType
    min_delay_ms: int
    max_delay_ms: int
    prioridade: int
    fora_horario_permitido: bool
    descricao: str


# Configuracoes de delay por tipo
DELAY_CONFIGS: dict[ContextType, DelayConfig] = {
    ContextType.REPLY_DIRETA: DelayConfig(
        tipo=ContextType.REPLY_DIRETA,
        min_delay_ms=0,
        max_delay_ms=3000,
        prioridade=1,
        fora_horario_permitido=True,
        descricao="Resposta imediata a conversa ativa"
    ),
    ContextType.ACEITE_VAGA: DelayConfig(
        tipo=ContextType.ACEITE_VAGA,
        min_delay_ms=0,
        max_delay_ms=2000,
        prioridade=1,
        fora_horario_permitido=True,
        descricao="Medico aceitando vaga - resposta urgente"
    ),
    ContextType.CONFIRMACAO: DelayConfig(
        tipo=ContextType.CONFIRMACAO,
        min_delay_ms=2000,
        max_delay_ms=5000,
        prioridade=2,
        fora_horario_permitido=True,
        descricao="Confirmacao operacional"
    ),
    ContextType.OFERTA_ATIVA: DelayConfig(
        tipo=ContextType.OFERTA_ATIVA,
        min_delay_ms=15000,
        max_delay_ms=45000,
        prioridade=3,
        fora_horario_permitido=False,
        descricao="Julia oferecendo vaga"
    ),
    ContextType.FOLLOWUP: DelayConfig(
        tipo=ContextType.FOLLOWUP,
        min_delay_ms=30000,
        max_delay_ms=120000,
        prioridade=4,
        fora_horario_permitido=False,
        descricao="Retomando conversa inativa"
    ),
    ContextType.CAMPANHA_FRIA: DelayConfig(
        tipo=ContextType.CAMPANHA_FRIA,
        min_delay_ms=60000,
        max_delay_ms=180000,
        prioridade=5,
        fora_horario_permitido=False,
        descricao="Primeiro contato de campanha"
    ),
}


@dataclass
class DelayResult:
    """Resultado do calculo de delay."""
    delay_ms: int
    tipo_contexto: ContextType
    prioridade: int
    fora_horario_permitido: bool
    razao: str


def _adicionar_variacao_humana(delay_base_ms: int) -> int:
    """
    Adiciona variacao para parecer mais humano.

    Variacao de +/- 15% para nao parecer robotico.
    """
    variacao = int(delay_base_ms * 0.15)
    return delay_base_ms + random.randint(-variacao, variacao)


def calcular_delay(
    classificacao: ContextClassification,
    fator_carga: float = 1.0
) -> DelayResult:
    """
    Calcula delay apropriado para uma mensagem.

    Args:
        classificacao: Resultado da classificacao de contexto
        fator_carga: Multiplicador de carga (1.0 = normal, 2.0 = dobro)

    Returns:
        DelayResult com delay calculado em ms
    """
    config = DELAY_CONFIGS.get(classificacao.tipo)

    if not config:
        logger.warning(f"Tipo de contexto nao configurado: {classificacao.tipo}")
        config = DELAY_CONFIGS[ContextType.CAMPANHA_FRIA]

    # Calcular delay base (aleatorio entre min e max)
    delay_base = random.randint(config.min_delay_ms, config.max_delay_ms)

    # Aplicar fator de carga (sistema ocupado = mais delay)
    delay_com_carga = int(delay_base * fator_carga)

    # Adicionar variacao humana
    delay_final = _adicionar_variacao_humana(delay_com_carga)

    # Garantir minimo (nao pode ser negativo)
    delay_final = max(0, delay_final)

    # Garantir maximo razoavel (5 minutos)
    delay_final = min(delay_final, 300000)

    logger.info(
        f"Delay calculado: {delay_final}ms "
        f"(tipo={classificacao.tipo.value}, prioridade={config.prioridade})"
    )

    return DelayResult(
        delay_ms=delay_final,
        tipo_contexto=classificacao.tipo,
        prioridade=config.prioridade,
        fora_horario_permitido=config.fora_horario_permitido,
        razao=config.descricao
    )


async def aplicar_delay(delay_result: DelayResult) -> None:
    """
    Aplica o delay calculado (aguarda).

    Args:
        delay_result: Resultado do calculo de delay
    """
    if delay_result.delay_ms <= 0:
        return

    delay_seconds = delay_result.delay_ms / 1000
    logger.debug(f"Aplicando delay de {delay_seconds:.1f}s")
    await asyncio.sleep(delay_seconds)


def obter_config_delay(tipo: ContextType) -> Optional[DelayConfig]:
    """Retorna configuracao de delay para um tipo."""
    return DELAY_CONFIGS.get(tipo)


def eh_resposta_urgente(classificacao: ContextClassification) -> bool:
    """
    Verifica se eh uma resposta urgente (prioridade 1).

    Respostas urgentes:
    - Reply direta
    - Aceite de vaga
    """
    return classificacao.prioridade == 1


def pode_enviar_fora_horario(classificacao: ContextClassification) -> bool:
    """
    Verifica se pode enviar fora do horario comercial.

    Permitidos fora do horario:
    - Reply direta
    - Aceite de vaga
    - Confirmacao
    """
    config = DELAY_CONFIGS.get(classificacao.tipo)
    return config.fora_horario_permitido if config else False


# ============================================================================
# Integracao com Fila de Mensagens
# ============================================================================

async def atualizar_fila_com_delay(
    fila_mensagem_id: str,
    classificacao: ContextClassification,
    delay_result: DelayResult
) -> None:
    """
    Atualiza registro na fila com informacoes de delay.

    Args:
        fila_mensagem_id: ID do registro na fila
        classificacao: Classificacao de contexto
        delay_result: Resultado do calculo de delay
    """
    from app.services.supabase import supabase

    try:
        supabase.table("fila_mensagens").update({
            "tipo_contexto": classificacao.tipo.value,
            "prioridade": classificacao.prioridade,
            "delay_calculado_ms": delay_result.delay_ms,
        }).eq("id", fila_mensagem_id).execute()

        logger.debug(f"Fila atualizada: {fila_mensagem_id} (delay={delay_result.delay_ms}ms)")
    except Exception as e:
        logger.error(f"Erro ao atualizar fila com delay: {e}")
```

**DoD:**
- [ ] Arquivo criado em `app/services/`
- [ ] Todas as configuracoes de delay definidas
- [ ] Variacao humana funcionando
- [ ] Funcoes de verificacao (urgente, fora horario)

---

### T02: Testes Unitarios

**Arquivo:** `tests/unit/test_delay_engine.py`

```python
"""
Testes para delay engine.
"""
import pytest
from app.services.delay_engine import (
    calcular_delay,
    eh_resposta_urgente,
    pode_enviar_fora_horario,
    DELAY_CONFIGS,
    DelayResult,
)
from app.services.message_context_classifier import ContextType, ContextClassification


class TestCalcularDelay:
    """Testes para calcular_delay."""

    def test_reply_direta_delay_baixo(self):
        """Reply direta tem delay 0-3s."""
        classificacao = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        result = calcular_delay(classificacao)

        assert result.delay_ms >= 0
        assert result.delay_ms <= 5000  # Com variacao
        assert result.prioridade == 1

    def test_aceite_vaga_delay_minimo(self):
        """Aceite de vaga tem delay 0-2s."""
        classificacao = ContextClassification(
            tipo=ContextType.ACEITE_VAGA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        result = calcular_delay(classificacao)

        assert result.delay_ms >= 0
        assert result.delay_ms <= 4000  # Com variacao
        assert result.prioridade == 1

    def test_campanha_fria_delay_alto(self):
        """Campanha fria tem delay 60-180s."""
        classificacao = ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.7,
            razao="teste"
        )
        result = calcular_delay(classificacao)

        assert result.delay_ms >= 50000  # Min com variacao
        assert result.delay_ms <= 210000  # Max com variacao
        assert result.prioridade == 5

    def test_fator_carga_aumenta_delay(self):
        """Fator de carga aumenta delay."""
        classificacao = ContextClassification(
            tipo=ContextType.OFERTA_ATIVA,
            prioridade=3,
            confianca=0.8,
            razao="teste"
        )

        result_normal = calcular_delay(classificacao, fator_carga=1.0)
        result_carga = calcular_delay(classificacao, fator_carga=2.0)

        # Em media, com carga deve ser maior
        # (aleatorio, entao testamos varias vezes)
        delays_normal = [calcular_delay(classificacao, 1.0).delay_ms for _ in range(10)]
        delays_carga = [calcular_delay(classificacao, 2.0).delay_ms for _ in range(10)]

        assert sum(delays_carga) / 10 > sum(delays_normal) / 10


class TestEhRespostaUrgente:
    """Testes para eh_resposta_urgente."""

    def test_reply_direta_urgente(self):
        """Reply direta eh urgente."""
        classificacao = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        assert eh_resposta_urgente(classificacao) is True

    def test_aceite_vaga_urgente(self):
        """Aceite de vaga eh urgente."""
        classificacao = ContextClassification(
            tipo=ContextType.ACEITE_VAGA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        assert eh_resposta_urgente(classificacao) is True

    def test_campanha_nao_urgente(self):
        """Campanha nao eh urgente."""
        classificacao = ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.7,
            razao="teste"
        )
        assert eh_resposta_urgente(classificacao) is False


class TestPodeEnviarForaHorario:
    """Testes para pode_enviar_fora_horario."""

    def test_reply_pode_fora_horario(self):
        """Reply pode fora do horario."""
        classificacao = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        assert pode_enviar_fora_horario(classificacao) is True

    def test_campanha_nao_pode_fora_horario(self):
        """Campanha nao pode fora do horario."""
        classificacao = ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.7,
            razao="teste"
        )
        assert pode_enviar_fora_horario(classificacao) is False

    def test_oferta_nao_pode_fora_horario(self):
        """Oferta nao pode fora do horario."""
        classificacao = ContextClassification(
            tipo=ContextType.OFERTA_ATIVA,
            prioridade=3,
            confianca=0.8,
            razao="teste"
        )
        assert pode_enviar_fora_horario(classificacao) is False
```

**DoD:**
- [ ] Todos os testes passam
- [ ] Cobertura > 90%
- [ ] Testes para edge cases

---

### T03: Integracao com Agente

**Arquivo:** Modificar `app/services/agente.py`

```python
# Adicionar imports
from app.services.message_context_classifier import classificar_contexto
from app.services.delay_engine import calcular_delay, aplicar_delay, eh_resposta_urgente

# No metodo de processar mensagem:
async def processar_mensagem(self, mensagem: str, cliente_id: str, ...):
    # 1. Classificar contexto
    classificacao = await classificar_contexto(
        mensagem=mensagem,
        cliente_id=cliente_id,
        ultima_interacao_at=self._get_ultima_interacao(cliente_id),
        contexto_conversa=self._get_contexto(cliente_id)
    )

    # 2. Calcular delay
    delay_result = calcular_delay(classificacao)

    # 3. Aplicar delay (se nao urgente)
    if not eh_resposta_urgente(classificacao):
        await aplicar_delay(delay_result)

    # 4. Processar mensagem normalmente
    resposta = await self._gerar_resposta(mensagem, ...)

    return resposta
```

**DoD:**
- [ ] Classificador integrado no fluxo
- [ ] Delay aplicado antes de responder
- [ ] Respostas urgentes sem delay
- [ ] Logs estruturados

---

## Validacao

### Metricas

```sql
-- Distribuicao de delays calculados (ultimas 24h)
SELECT
    tipo_contexto,
    COUNT(*) as total,
    ROUND(AVG(delay_calculado_ms)) as delay_medio_ms,
    MIN(delay_calculado_ms) as delay_min_ms,
    MAX(delay_calculado_ms) as delay_max_ms
FROM fila_mensagens
WHERE criado_em >= now() - interval '24 hours'
AND delay_calculado_ms IS NOT NULL
GROUP BY tipo_contexto
ORDER BY delay_medio_ms;
```

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Servico `delay_engine.py` implementado
- [ ] 6 tipos de delay configurados
- [ ] Variacao humana (+/- 15%)
- [ ] Integracao com agente
- [ ] Testes unitarios passando

### Qualidade

- [ ] Delays dentro dos limites esperados
- [ ] Logging estruturado
- [ ] Docstrings completas

### Performance

- [ ] Calculo de delay < 1ms
- [ ] asyncio.sleep nao bloqueia outras tasks

---

*Epico criado em 29/12/2025*
