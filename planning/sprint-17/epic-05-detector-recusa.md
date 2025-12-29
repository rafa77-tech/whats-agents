# Epic 05: Detector de Recusa

## Objetivo

Criar heurística para detectar quando médico recusa uma oferta específica e emitir `offer_declined`.

## Contexto

### Desafio

Diferente de `offer_accepted` (tem transição clara de status), recusa é mais sutil:
- Médico pode dizer "não tenho interesse"
- Pode simplesmente ignorar
- Pode dar desculpa ("já tenho compromisso")
- Pode pedir para não enviar mais (opt-out, diferente de recusa)

### Abordagem Conservadora

Começar com heurística simples baseada em texto:
1. Detectar padrões de recusa explícita
2. Associar com última oferta feita (vaga_id)
3. Emitir evento apenas quando confiança alta

**NÃO usar LLM** nesta sprint (custo + latência).

---

## Story 5.1: Padrões de Recusa

### Objetivo
Definir e implementar padrões de texto que indicam recusa.

### Padrões de Recusa

```python
# Recusa explícita (alta confiança)
RECUSA_EXPLICITA = [
    "não tenho interesse",
    "nao tenho interesse",
    "não quero",
    "nao quero",
    "não posso",
    "nao posso",
    "não vou poder",
    "nao vou poder",
    "não dá pra mim",
    "nao da pra mim",
    "declino",
    "recuso",
    "passa essa",
    "passo essa",
    "não me interessa",
    "nao me interessa",
]

# Desculpas com contexto (média confiança)
DESCULPAS = [
    "já tenho compromisso",
    "ja tenho compromisso",
    "tenho outro plantão",
    "já estou escalado",
    "ja estou escalado",
    "viagem marcada",
    "estou de férias",
    "não trabalho nesse dia",
    "não faço noturno",
    "não faço final de semana",
    "muito longe",
    "valor baixo",
    "não compensa",
]

# NÃO são recusa (evitar falso positivo)
NAO_RECUSA = [
    "não entendi",
    "não recebi",
    "pode me explicar",
    "qual o valor",
    "onde fica",
    "me fala mais",
]
```

### Tarefas

1. **Criar módulo detector**:

```python
# app/services/business_events/recusa_detector.py

import re
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class RecusaResult:
    """Resultado da detecção de recusa."""
    is_recusa: bool
    confianca: float  # 0.0 a 1.0
    padrao_matched: Optional[str] = None
    tipo: Optional[str] = None  # "explicita", "desculpa", None


# Padrões compilados
RECUSA_EXPLICITA = [
    r"n[aã]o\s+tenho\s+interesse",
    r"n[aã]o\s+quero",
    r"n[aã]o\s+(vou\s+)?poder",
    r"n[aã]o\s+d[aá]\s+(pra|para)\s+mim",
    r"pass[oa]\s+essa",
    r"n[aã]o\s+me\s+interessa",
    r"declino",
    r"recuso",
]

DESCULPAS = [
    r"j[aá]\s+tenho\s+compromisso",
    r"tenho\s+outro\s+plant[aã]o",
    r"j[aá]\s+estou\s+escalad[oa]",
    r"viagem\s+marcada",
    r"estou\s+de\s+f[eé]rias",
    r"n[aã]o\s+trabalho\s+nesse\s+dia",
    r"n[aã]o\s+fa[cç]o\s+noturno",
    r"muito\s+longe",
    r"valor\s+baixo",
    r"n[aã]o\s+compensa",
]

NAO_RECUSA = [
    r"n[aã]o\s+entendi",
    r"n[aã]o\s+recebi",
    r"pode\s+me\s+explicar",
    r"qual\s+o\s+valor",
    r"onde\s+fica",
    r"me\s+fala\s+mais",
]


def detectar_recusa(mensagem: str) -> RecusaResult:
    """
    Detecta se mensagem indica recusa de oferta.

    Args:
        mensagem: Texto da mensagem do médico

    Returns:
        RecusaResult com is_recusa, confianca e detalhes
    """
    texto = mensagem.lower().strip()

    # Primeiro, verificar se NÃO é recusa (evitar falso positivo)
    for pattern in NAO_RECUSA:
        if re.search(pattern, texto):
            return RecusaResult(is_recusa=False, confianca=0.9)

    # Verificar recusa explícita (alta confiança)
    for pattern in RECUSA_EXPLICITA:
        match = re.search(pattern, texto)
        if match:
            return RecusaResult(
                is_recusa=True,
                confianca=0.9,
                padrao_matched=match.group(),
                tipo="explicita",
            )

    # Verificar desculpas (média confiança)
    for pattern in DESCULPAS:
        match = re.search(pattern, texto)
        if match:
            return RecusaResult(
                is_recusa=True,
                confianca=0.6,
                padrao_matched=match.group(),
                tipo="desculpa",
            )

    # Nenhum padrão encontrado
    return RecusaResult(is_recusa=False, confianca=0.5)
```

### DoD

- [ ] Módulo `recusa_detector.py` criado
- [ ] Padrões de recusa explícita definidos
- [ ] Padrões de desculpas definidos
- [ ] Padrões de não-recusa (evitar falso positivo)
- [ ] Função `detectar_recusa` retorna confiança

---

## Story 5.2: Associação com Última Oferta

### Objetivo
Associar recusa detectada com a última oferta feita ao médico.

### Contexto

Para emitir `offer_declined` precisamos de:
- `cliente_id` (médico que recusou)
- `vaga_id` (vaga que foi recusada)

### Tarefas

1. **Buscar última oferta do médico**:

```python
# app/services/business_events/recusa_detector.py

from datetime import datetime, timedelta
from app.services.supabase import supabase

async def buscar_ultima_oferta(
    cliente_id: str,
    max_horas: int = 48,
) -> Optional[dict]:
    """
    Busca a última oferta feita ao médico.

    Args:
        cliente_id: UUID do cliente/médico
        max_horas: Janela de tempo para considerar (default 48h)

    Returns:
        Dados da última oferta ou None
    """
    since = (datetime.utcnow() - timedelta(hours=max_horas)).isoformat()

    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("cliente_id", cliente_id)
            .eq("event_type", "offer_made")
            .gte("ts", since)
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar última oferta: {e}")
        return None


async def processar_possivel_recusa(
    cliente_id: str,
    mensagem: str,
    conversation_id: str = None,
    interaction_id: int = None,
) -> bool:
    """
    Processa mensagem verificando se é recusa.

    Args:
        cliente_id: UUID do médico
        mensagem: Texto da mensagem
        conversation_id: UUID da conversa
        interaction_id: ID da interação

    Returns:
        True se detectou e emitiu offer_declined
    """
    # Detectar recusa
    result = detectar_recusa(mensagem)

    if not result.is_recusa or result.confianca < 0.6:
        return False

    # Buscar última oferta
    ultima_oferta = await buscar_ultima_oferta(cliente_id)

    if not ultima_oferta:
        logger.info(f"Recusa detectada mas sem oferta recente: {cliente_id}")
        return False

    # Emitir evento
    await emit_event(BusinessEvent(
        event_type=EventType.OFFER_DECLINED,
        cliente_id=cliente_id,
        vaga_id=ultima_oferta.get("vaga_id"),
        hospital_id=ultima_oferta.get("hospital_id"),
        conversation_id=conversation_id,
        interaction_id=interaction_id,
        event_props={
            "tipo_recusa": result.tipo,
            "confianca": result.confianca,
            "padrao_matched": result.padrao_matched,
            "offer_made_event_id": ultima_oferta.get("event_id"),
            "horas_desde_oferta": _calcular_horas(ultima_oferta.get("ts")),
        },
    ))

    logger.info(
        f"offer_declined emitido: cliente={cliente_id} "
        f"vaga={ultima_oferta.get('vaga_id')} "
        f"confianca={result.confianca}"
    )
    return True
```

### DoD

- [ ] Função `buscar_ultima_oferta` implementada
- [ ] Função `processar_possivel_recusa` implementada
- [ ] Associa recusa com oferta das últimas 48h
- [ ] Não emite se não houver oferta recente
- [ ] Log informativo quando detecta recusa

---

## Story 5.3: Integração no Pipeline

### Objetivo
Integrar detector de recusa no pipeline de mensagens.

### Tarefas

1. **Chamar detector no processamento de mensagem**:

```python
# app/pipeline/processors/business_events.py

from app.services.business_events.recusa_detector import processar_possivel_recusa

class BusinessEventsProcessor:
    """Processor para emitir eventos de negócio."""

    async def process(self, context: dict) -> dict:
        """Processa mensagem para eventos de negócio."""

        # Se é mensagem do médico (inbound)
        if context.get("is_inbound"):
            cliente_id = context.get("cliente_id")
            mensagem = context.get("mensagem_texto")

            # Verificar se é recusa
            if mensagem and cliente_id:
                await processar_possivel_recusa(
                    cliente_id=cliente_id,
                    mensagem=mensagem,
                    conversation_id=context.get("conversation_id"),
                    interaction_id=context.get("interaction_id"),
                )

        return context
```

### DoD

- [ ] Detector integrado no pipeline
- [ ] Chamado apenas para mensagens inbound
- [ ] Não bloqueia processamento principal
- [ ] Logs de debug disponíveis

---

## Story 5.4: Testes do Detector

### Objetivo
Garantir que o detector funciona corretamente.

### Testes

```python
# tests/business_events/test_recusa_detector.py

import pytest
from app.services.business_events.recusa_detector import (
    detectar_recusa,
    RecusaResult,
)


class TestDetectarRecusa:
    """Testes para detecção de recusa."""

    @pytest.mark.parametrize("mensagem,esperado", [
        # Recusa explícita - alta confiança
        ("não tenho interesse", True),
        ("Não quero esse plantão", True),
        ("não vou poder", True),
        ("passo essa", True),
        ("não me interessa", True),

        # Desculpas - média confiança
        ("já tenho compromisso nesse dia", True),
        ("tenho outro plantão", True),
        ("estou de férias", True),
        ("muito longe pra mim", True),
        ("valor baixo demais", True),

        # NÃO são recusa
        ("não entendi, pode explicar?", False),
        ("não recebi a mensagem", False),
        ("qual o valor mesmo?", False),
        ("onde fica o hospital?", False),
        ("me fala mais sobre a vaga", False),

        # Neutros
        ("ok", False),
        ("vou pensar", False),
        ("me manda mais detalhes", False),
    ])
    def test_detectar_recusa(self, mensagem, esperado):
        """Detecta recusas corretamente."""
        result = detectar_recusa(mensagem)
        assert result.is_recusa == esperado

    def test_recusa_explicita_alta_confianca(self):
        """Recusa explícita tem alta confiança."""
        result = detectar_recusa("não tenho interesse")
        assert result.is_recusa is True
        assert result.confianca >= 0.8
        assert result.tipo == "explicita"

    def test_desculpa_media_confianca(self):
        """Desculpa tem média confiança."""
        result = detectar_recusa("já tenho compromisso")
        assert result.is_recusa is True
        assert 0.5 <= result.confianca < 0.8
        assert result.tipo == "desculpa"

    def test_nao_recusa_alta_confianca_negativa(self):
        """Não-recusa tem alta confiança de que não é recusa."""
        result = detectar_recusa("não entendi a proposta")
        assert result.is_recusa is False
        assert result.confianca >= 0.8


class TestAssociacaoOferta:
    """Testes para associação com oferta."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.supabase")
    async def test_busca_ultima_oferta(self, mock_supabase):
        """Busca última oferta do médico."""
        mock_response = MagicMock()
        mock_response.data = [{
            "event_id": "evt-123",
            "vaga_id": "vaga-456",
            "hospital_id": "hosp-789",
            "ts": "2025-01-10T10:00:00Z",
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        from app.services.business_events.recusa_detector import buscar_ultima_oferta
        oferta = await buscar_ultima_oferta("cliente-123")

        assert oferta is not None
        assert oferta["vaga_id"] == "vaga-456"

    @pytest.mark.asyncio
    async def test_nao_emite_sem_oferta_recente(self):
        """Não emite offer_declined se não houver oferta recente."""
        # Mock sem ofertas
        with patch("app.services.business_events.recusa_detector.buscar_ultima_oferta") as mock:
            mock.return_value = None

            from app.services.business_events.recusa_detector import processar_possivel_recusa
            result = await processar_possivel_recusa(
                cliente_id="cliente-123",
                mensagem="não quero",
            )

            assert result is False
```

### DoD

- [ ] Testes para padrões de recusa explícita
- [ ] Testes para padrões de desculpas
- [ ] Testes para padrões de não-recusa
- [ ] Testes para associação com oferta
- [ ] Cobertura > 80% do módulo

---

## Checklist do Épico

- [ ] **S17.E05.1** - Padrões de recusa definidos
- [ ] **S17.E05.2** - Associação com última oferta
- [ ] **S17.E05.3** - Integração no pipeline
- [ ] **S17.E05.4** - Testes passando
- [ ] Detector conservador (evita falso positivo)
- [ ] Confiança reflete certeza da detecção
- [ ] Associa com oferta das últimas 48h
- [ ] Logs informativos para debug
