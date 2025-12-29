# E02: Classificador de Contexto

**Epico:** Detectar Tipo de Mensagem para Delay Inteligente
**Estimativa:** 3h
**Dependencias:** E01 (Migrations)

---

## Objetivo

Criar classificador que detecta o tipo de contexto de cada mensagem/resposta para determinar o delay apropriado.

---

## Escopo

### Incluido

- [x] Servico `message_context_classifier.py`
- [x] Deteccao de 6 tipos de contexto
- [x] Integracao com pipeline de mensagens
- [x] Testes unitarios

### Excluido

- [ ] Delay Engine (E03)
- [ ] Logica de fora do horario (E04)

---

## Tipos de Contexto

| Tipo | Descricao | Criterios de Deteccao | Prioridade |
|------|-----------|----------------------|------------|
| `reply_direta` | Resposta a pergunta da Julia | Conversa ativa < 5min, contexto de pergunta | 1 |
| `aceite_vaga` | Medico aceitando vaga | Keywords: "ok", "quero", "reserva", "fechado", "pode reservar" | 1 |
| `confirmacao` | Confirmacao operacional | Keywords: "sim", "confirmo", "certo", "combinado" em contexto de confirmacao | 2 |
| `oferta_ativa` | Julia oferecendo vaga | Ultima mensagem da Julia tem vaga, aguardando resposta | 3 |
| `followup` | Retomando conversa inativa | Conversa inativa > 24h | 4 |
| `campanha_fria` | Primeiro contato | Sem conversa previa ou conversa > 30 dias | 5 |

---

## Tarefas

### T01: Servico message_context_classifier.py

**Arquivo:** `app/services/message_context_classifier.py`

```python
"""
Classificador de contexto de mensagem.

Detecta o tipo de contexto para determinar delay apropriado.

Sprint 22 - Responsividade Inteligente
"""
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Tipos de contexto de mensagem."""
    REPLY_DIRETA = "reply_direta"
    ACEITE_VAGA = "aceite_vaga"
    CONFIRMACAO = "confirmacao"
    OFERTA_ATIVA = "oferta_ativa"
    FOLLOWUP = "followup"
    CAMPANHA_FRIA = "campanha_fria"


@dataclass
class ContextClassification:
    """Resultado da classificacao."""
    tipo: ContextType
    prioridade: int
    confianca: float  # 0.0 a 1.0
    razao: str


# Patterns para deteccao
ACEITE_PATTERNS = [
    r'\b(ok|okay|blz|beleza)\b',
    r'\b(quero|aceito|topo|fechado)\b',
    r'\b(pode\s*reservar|reserva\s*pra\s*mim)\b',
    r'\b(vou\s*fazer|vou\s*pegar|to\s*dentro)\b',
    r'\b(manda|envia|passa)\s*(os\s*)?(dados|docs|documentos)\b',
]

CONFIRMACAO_PATTERNS = [
    r'\b(sim|confirmo|confirmado)\b',
    r'\b(certo|combinado|fechado)\b',
    r'\b(isso|exato|perfeito)\b',
    r'\b(pode\s*ser|ta\s*bom|ta\s*certo)\b',
]

NEGACAO_PATTERNS = [
    r'\b(nao|n[aã]o|nope)\b',
    r'\b(desculpa|infelizmente)\b',
    r'\b(nao\s*posso|nao\s*consigo|nao\s*da)\b',
    r'\b(obrigado\s*mas|valeu\s*mas)\b',
]


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto para matching."""
    texto = texto.lower().strip()
    # Remover acentos comuns
    texto = texto.replace('ã', 'a').replace('é', 'e').replace('ç', 'c')
    return texto


def _match_patterns(texto: str, patterns: list[str]) -> tuple[bool, float]:
    """Verifica se texto match algum pattern."""
    texto_norm = _normalizar_texto(texto)
    for pattern in patterns:
        if re.search(pattern, texto_norm, re.IGNORECASE):
            return True, 0.9
    return False, 0.0


async def classificar_contexto(
    mensagem: str,
    cliente_id: str,
    ultima_mensagem_julia: Optional[str] = None,
    ultima_interacao_at: Optional[datetime] = None,
    contexto_conversa: Optional[dict] = None
) -> ContextClassification:
    """
    Classifica o contexto de uma mensagem recebida.

    Args:
        mensagem: Texto da mensagem recebida
        cliente_id: ID do cliente/medico
        ultima_mensagem_julia: Ultima mensagem enviada pela Julia
        ultima_interacao_at: Timestamp da ultima interacao
        contexto_conversa: Contexto adicional da conversa

    Returns:
        ContextClassification com tipo, prioridade e confianca
    """
    contexto = contexto_conversa or {}
    agora = datetime.now()

    # 1. Verificar aceite de vaga (prioridade maxima)
    is_aceite, conf_aceite = _match_patterns(mensagem, ACEITE_PATTERNS)
    if is_aceite:
        # Verificar se nao eh negacao
        is_negacao, _ = _match_patterns(mensagem, NEGACAO_PATTERNS)
        if not is_negacao:
            logger.info(f"Contexto detectado: ACEITE_VAGA (cliente={cliente_id})")
            return ContextClassification(
                tipo=ContextType.ACEITE_VAGA,
                prioridade=1,
                confianca=conf_aceite,
                razao="Keywords de aceite detectadas"
            )

    # 2. Verificar confirmacao operacional
    is_confirmacao, conf_confirmacao = _match_patterns(mensagem, CONFIRMACAO_PATTERNS)
    if is_confirmacao and contexto.get("aguardando_confirmacao"):
        logger.info(f"Contexto detectado: CONFIRMACAO (cliente={cliente_id})")
        return ContextClassification(
            tipo=ContextType.CONFIRMACAO,
            prioridade=2,
            confianca=conf_confirmacao,
            razao="Confirmacao em contexto de espera"
        )

    # 3. Verificar reply direta (conversa ativa recente)
    if ultima_interacao_at:
        tempo_desde_ultima = agora - ultima_interacao_at
        if tempo_desde_ultima < timedelta(minutes=5):
            logger.info(f"Contexto detectado: REPLY_DIRETA (cliente={cliente_id})")
            return ContextClassification(
                tipo=ContextType.REPLY_DIRETA,
                prioridade=1,
                confianca=0.95,
                razao=f"Conversa ativa ({tempo_desde_ultima.seconds}s desde ultima)"
            )

    # 4. Verificar se Julia fez oferta (aguardando resposta)
    if ultima_mensagem_julia and contexto.get("oferta_pendente"):
        logger.info(f"Contexto detectado: OFERTA_ATIVA (cliente={cliente_id})")
        return ContextClassification(
            tipo=ContextType.OFERTA_ATIVA,
            prioridade=3,
            confianca=0.85,
            razao="Resposta a oferta pendente"
        )

    # 5. Verificar followup (conversa inativa > 24h mas < 30 dias)
    if ultima_interacao_at:
        tempo_desde_ultima = agora - ultima_interacao_at
        if timedelta(hours=24) <= tempo_desde_ultima < timedelta(days=30):
            logger.info(f"Contexto detectado: FOLLOWUP (cliente={cliente_id})")
            return ContextClassification(
                tipo=ContextType.FOLLOWUP,
                prioridade=4,
                confianca=0.8,
                razao=f"Conversa inativa por {tempo_desde_ultima.days} dias"
            )

    # 6. Default: campanha fria
    logger.info(f"Contexto detectado: CAMPANHA_FRIA (cliente={cliente_id})")
    return ContextClassification(
        tipo=ContextType.CAMPANHA_FRIA,
        prioridade=5,
        confianca=0.7,
        razao="Sem contexto especifico detectado"
    )


async def classificar_mensagem_saida(
    tipo_envio: str,
    cliente_id: str,
    contexto_campanha: Optional[dict] = None
) -> ContextClassification:
    """
    Classifica contexto para mensagem de SAIDA (Julia -> Medico).

    Args:
        tipo_envio: Tipo de envio (campanha, followup, oferta, etc)
        cliente_id: ID do cliente
        contexto_campanha: Contexto da campanha

    Returns:
        ContextClassification
    """
    tipo_map = {
        "discovery": ContextType.CAMPANHA_FRIA,
        "reativacao": ContextType.CAMPANHA_FRIA,
        "oferta": ContextType.OFERTA_ATIVA,
        "followup": ContextType.FOLLOWUP,
        "feedback": ContextType.FOLLOWUP,
        "confirmacao": ContextType.CONFIRMACAO,
        "reply": ContextType.REPLY_DIRETA,
    }

    prioridade_map = {
        ContextType.REPLY_DIRETA: 1,
        ContextType.ACEITE_VAGA: 1,
        ContextType.CONFIRMACAO: 2,
        ContextType.OFERTA_ATIVA: 3,
        ContextType.FOLLOWUP: 4,
        ContextType.CAMPANHA_FRIA: 5,
    }

    tipo = tipo_map.get(tipo_envio, ContextType.CAMPANHA_FRIA)
    prioridade = prioridade_map.get(tipo, 5)

    return ContextClassification(
        tipo=tipo,
        prioridade=prioridade,
        confianca=1.0,
        razao=f"Tipo de envio: {tipo_envio}"
    )
```

**DoD:**
- [ ] Arquivo criado em `app/services/`
- [ ] Imports funcionam
- [ ] Todas as funcoes tem docstrings
- [ ] Logging estruturado

---

### T02: Testes Unitarios

**Arquivo:** `tests/unit/test_message_context_classifier.py`

```python
"""
Testes para classificador de contexto.
"""
import pytest
from datetime import datetime, timedelta
from app.services.message_context_classifier import (
    classificar_contexto,
    classificar_mensagem_saida,
    ContextType,
)


class TestClassificarContexto:
    """Testes para classificar_contexto."""

    @pytest.mark.asyncio
    async def test_aceite_vaga_ok(self):
        """Detecta 'ok' como aceite."""
        result = await classificar_contexto(
            mensagem="ok pode reservar",
            cliente_id="123"
        )
        assert result.tipo == ContextType.ACEITE_VAGA
        assert result.prioridade == 1

    @pytest.mark.asyncio
    async def test_aceite_vaga_quero(self):
        """Detecta 'quero' como aceite."""
        result = await classificar_contexto(
            mensagem="quero essa vaga",
            cliente_id="123"
        )
        assert result.tipo == ContextType.ACEITE_VAGA

    @pytest.mark.asyncio
    async def test_aceite_negado(self):
        """'ok mas nao posso' nao eh aceite."""
        result = await classificar_contexto(
            mensagem="ok mas nao posso dessa vez",
            cliente_id="123"
        )
        # Deve detectar negacao e nao classificar como aceite
        assert result.tipo != ContextType.ACEITE_VAGA

    @pytest.mark.asyncio
    async def test_reply_direta_conversa_ativa(self):
        """Conversa recente = reply direta."""
        result = await classificar_contexto(
            mensagem="sim, pode ser",
            cliente_id="123",
            ultima_interacao_at=datetime.now() - timedelta(minutes=2)
        )
        assert result.tipo == ContextType.REPLY_DIRETA
        assert result.prioridade == 1

    @pytest.mark.asyncio
    async def test_confirmacao_com_contexto(self):
        """Confirmacao quando aguardando."""
        result = await classificar_contexto(
            mensagem="sim, confirmo",
            cliente_id="123",
            contexto_conversa={"aguardando_confirmacao": True}
        )
        assert result.tipo == ContextType.CONFIRMACAO
        assert result.prioridade == 2

    @pytest.mark.asyncio
    async def test_followup_conversa_inativa(self):
        """Conversa inativa > 24h = followup."""
        result = await classificar_contexto(
            mensagem="oi, tudo bem?",
            cliente_id="123",
            ultima_interacao_at=datetime.now() - timedelta(days=3)
        )
        assert result.tipo == ContextType.FOLLOWUP
        assert result.prioridade == 4

    @pytest.mark.asyncio
    async def test_campanha_fria_sem_contexto(self):
        """Sem contexto = campanha fria."""
        result = await classificar_contexto(
            mensagem="oi",
            cliente_id="123"
        )
        assert result.tipo == ContextType.CAMPANHA_FRIA
        assert result.prioridade == 5

    @pytest.mark.asyncio
    async def test_campanha_fria_conversa_antiga(self):
        """Conversa > 30 dias = campanha fria."""
        result = await classificar_contexto(
            mensagem="oi",
            cliente_id="123",
            ultima_interacao_at=datetime.now() - timedelta(days=45)
        )
        assert result.tipo == ContextType.CAMPANHA_FRIA


class TestClassificarMensagemSaida:
    """Testes para classificar_mensagem_saida."""

    @pytest.mark.asyncio
    async def test_tipo_discovery(self):
        """Discovery = campanha fria."""
        result = await classificar_mensagem_saida(
            tipo_envio="discovery",
            cliente_id="123"
        )
        assert result.tipo == ContextType.CAMPANHA_FRIA
        assert result.prioridade == 5

    @pytest.mark.asyncio
    async def test_tipo_oferta(self):
        """Oferta = oferta ativa."""
        result = await classificar_mensagem_saida(
            tipo_envio="oferta",
            cliente_id="123"
        )
        assert result.tipo == ContextType.OFERTA_ATIVA
        assert result.prioridade == 3

    @pytest.mark.asyncio
    async def test_tipo_reply(self):
        """Reply = reply direta."""
        result = await classificar_mensagem_saida(
            tipo_envio="reply",
            cliente_id="123"
        )
        assert result.tipo == ContextType.REPLY_DIRETA
        assert result.prioridade == 1
```

**DoD:**
- [ ] Arquivo criado em `tests/unit/`
- [ ] Todos os testes passam
- [ ] Cobertura > 90% do classificador
- [ ] Testes para edge cases

---

### T03: Integracao com Pipeline

**Arquivo:** Modificar `app/services/agente.py` ou `app/pipeline/`

Adicionar chamada ao classificador quando processar mensagem:

```python
from app.services.message_context_classifier import classificar_contexto

# No processamento de mensagem recebida:
classificacao = await classificar_contexto(
    mensagem=mensagem_texto,
    cliente_id=cliente_id,
    ultima_mensagem_julia=ultima_msg_julia,
    ultima_interacao_at=ultima_interacao,
    contexto_conversa=contexto
)

# Passar para delay engine (E03)
delay_ms = await calcular_delay(classificacao)
```

**DoD:**
- [ ] Classificador chamado no fluxo de mensagem
- [ ] Resultado disponivel para delay engine
- [ ] Log estruturado com tipo detectado

---

## Validacao

### Testes Manuais

```bash
# Rodar testes unitarios
uv run pytest tests/unit/test_message_context_classifier.py -v

# Testar classificacao via Python
uv run python -c "
import asyncio
from app.services.message_context_classifier import classificar_contexto

async def test():
    # Aceite
    r = await classificar_contexto('ok pode reservar', '123')
    print(f'Aceite: {r.tipo} (prioridade={r.prioridade})')

    # Reply
    from datetime import datetime, timedelta
    r = await classificar_contexto(
        'sim',
        '123',
        ultima_interacao_at=datetime.now() - timedelta(minutes=1)
    )
    print(f'Reply: {r.tipo} (prioridade={r.prioridade})')

asyncio.run(test())
"
```

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Servico `message_context_classifier.py` implementado
- [ ] 6 tipos de contexto funcionando
- [ ] Prioridades corretas (1-5)
- [ ] Testes unitarios passando (100%)
- [ ] Integracao com pipeline

### Qualidade

- [ ] Patterns testados com mensagens reais
- [ ] Confianca calculada corretamente
- [ ] Logging estruturado
- [ ] Docstrings completas

### Performance

- [ ] Classificacao < 10ms
- [ ] Sem chamadas externas (apenas regex)

---

*Epico criado em 29/12/2025*
