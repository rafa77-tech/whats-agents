# Epic 06: Detector de Keywords (Fallback)

## Objetivo

Implementar deteccao de keywords como fallback para confirmacao quando o divulgador responde via WhatsApp ao inves de clicar no link.

## Contexto

Devido a limitacao do Baileys (sem suporte a botoes), o divulgador pode preferir responder diretamente no WhatsApp com:
- "CONFIRMADO" / "fechou" / "ok" → confirma plantao
- "NAO FECHOU" / "nao deu" / "desistiu" → nao confirma

O detector deve:
1. Identificar telefone do divulgador com handoff pendente
2. Detectar keywords na mensagem
3. Processar confirmacao automaticamente
4. Julia responde agradecendo

---

## Story 6.1: Detector no Pipeline

### Objetivo
Criar step no pipeline que detecta mensagens de divulgadores com handoff pendente.

### Arquivo: `app/pipeline/steps/handoff_keyword_detector.py`

```python
"""
Detector de keywords para confirmacao de handoff.

Sprint 20 - E06 - Fallback via WhatsApp.
"""
import logging
import re
from typing import Optional

from app.pipeline.context import PipelineContext
from app.services.external_handoff.repository import buscar_handoff_pendente_por_telefone
from app.services.external_handoff.confirmacao import processar_confirmacao
from app.services.business_events import emit_event, EventType

logger = logging.getLogger(__name__)

# Keywords de confirmacao (case insensitive)
KEYWORDS_CONFIRMED = [
    r"\bconfirmado\b",
    r"\bfechou\b",
    r"\bfechado\b",
    r"\bconfirmo\b",
    r"\bok\s*,?\s*fechou\b",
    r"\bfechamos\b",
    r"\bcontrato\s+fechado\b",
    r"\bpode\s+confirmar\b",
    r"\btudo\s+certo\b",
]

KEYWORDS_NOT_CONFIRMED = [
    r"\bnao\s+fechou\b",
    r"\bnão\s+fechou\b",
    r"\bnao\s+deu\b",
    r"\bnão\s+deu\b",
    r"\bdesistiu\b",
    r"\bcancelou\b",
    r"\bnao\s+vai\s+dar\b",
    r"\bnão\s+vai\s+dar\b",
    r"\bperdeu\b",
    r"\bnao\s+confirmou\b",
    r"\bnão\s+confirmou\b",
    r"\bnao\s+rolou\b",
    r"\bnão\s+rolou\b",
]


class HandoffKeywordDetector:
    """
    Step do pipeline que detecta keywords de confirmacao de handoff.

    Executa ANTES do agente Julia para interceptar mensagens de divulgadores.
    """

    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        Verifica se mensagem e de divulgador com handoff pendente.

        Se detectar keyword, processa confirmacao e marca para Julia nao responder
        como conversa normal.
        """
        # Pular se nao for mensagem de texto
        if not context.mensagem_texto:
            return context

        telefone = context.telefone
        mensagem = context.mensagem_texto.lower()

        # Buscar handoff pendente para este telefone
        handoff = await buscar_handoff_pendente_por_telefone(telefone)

        if not handoff:
            # Nao e divulgador com handoff pendente
            return context

        logger.info(
            f"Telefone {telefone} tem handoff pendente: {handoff['id'][:8]}"
        )

        # Detectar keyword
        action = self._detectar_keyword(mensagem)

        if not action:
            # Nao detectou keyword, deixar Julia responder normalmente
            logger.debug(f"Nenhuma keyword detectada na mensagem do divulgador")
            return context

        logger.info(f"Keyword detectada: action={action}")

        # Processar confirmacao
        try:
            resultado = await processar_confirmacao(
                handoff=handoff,
                action=action,
                confirmed_by="keyword",
            )

            # Emitir evento especifico de keyword
            await emit_event(
                EventType.HANDOFF_CONFIRM_CLICKED,  # Reusar evento
                {
                    "handoff_id": handoff["id"],
                    "action": action,
                    "via": "keyword",
                    "mensagem_original": context.mensagem_texto[:100],
                }
            )

            # Marcar para Julia responder como agradecimento
            context.metadata["handoff_confirmacao"] = {
                "processado": True,
                "action": action,
                "handoff_id": handoff["id"],
            }

            # Definir resposta automatica
            context.resposta_override = self._gerar_resposta_agradecimento(action)
            context.skip_agent = True  # Pular agente Julia

            logger.info(
                f"Handoff {handoff['id'][:8]} processado via keyword: {action}"
            )

        except Exception as e:
            logger.error(f"Erro ao processar keyword de handoff: {e}")
            # Deixar Julia responder normalmente

        return context

    def _detectar_keyword(self, mensagem: str) -> Optional[str]:
        """
        Detecta keyword na mensagem.

        Args:
            mensagem: Texto da mensagem (lowercase)

        Returns:
            'confirmed', 'not_confirmed' ou None
        """
        # Verificar NOT_CONFIRMED primeiro (mais especifico)
        for pattern in KEYWORDS_NOT_CONFIRMED:
            if re.search(pattern, mensagem, re.IGNORECASE):
                return "not_confirmed"

        # Verificar CONFIRMED
        for pattern in KEYWORDS_CONFIRMED:
            if re.search(pattern, mensagem, re.IGNORECASE):
                return "confirmed"

        return None

    def _gerar_resposta_agradecimento(self, action: str) -> str:
        """
        Gera resposta de agradecimento para o divulgador.

        Args:
            action: 'confirmed' ou 'not_confirmed'

        Returns:
            Mensagem de agradecimento
        """
        if action == "confirmed":
            return (
                "Anotado! Obrigada pela confirmacao.\n\n"
                "Ja atualizei aqui no sistema. Qualquer coisa me avisa!"
            )
        else:
            return (
                "Entendido! Ja atualizei aqui.\n\n"
                "Obrigada por avisar. Se surgir outra oportunidade, te procuro!"
            )


# Instancia singleton
handoff_keyword_detector = HandoffKeywordDetector()
```

### DoD

- [ ] Classe `HandoffKeywordDetector` criada
- [ ] Keywords de confirmacao definidas
- [ ] Keywords de nao-confirmacao definidas
- [ ] Integracao com pipeline

---

## Story 6.2: Repository - Busca por Telefone

### Objetivo
Adicionar funcao para buscar handoff por telefone do divulgador.

### Arquivo: `app/services/external_handoff/repository.py`

```python
# Adicionar funcao:

async def buscar_handoff_pendente_por_telefone(telefone: str) -> Optional[dict]:
    """
    Busca handoff pendente pelo telefone do divulgador.

    Args:
        telefone: Telefone do divulgador (com ou sem formatacao)

    Returns:
        Handoff pendente ou None
    """
    # Normalizar telefone (remover formatacao)
    telefone_normalizado = re.sub(r'\D', '', telefone)

    # Buscar apenas os ultimos 8-9 digitos para flexibilidade
    if len(telefone_normalizado) > 9:
        telefone_sufixo = telefone_normalizado[-9:]
    else:
        telefone_sufixo = telefone_normalizado

    try:
        response = supabase.table("external_handoffs") \
            .select("*") \
            .in_("status", ["pending", "contacted"]) \
            .like("divulgador_telefone", f"%{telefone_sufixo}") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if response.data:
            return response.data[0]

        return None

    except Exception as e:
        logger.error(f"Erro ao buscar handoff por telefone: {e}")
        return None
```

### DoD

- [ ] Funcao `buscar_handoff_pendente_por_telefone` criada
- [ ] Normalizacao de telefone implementada
- [ ] Busca por sufixo para flexibilidade

---

## Story 6.3: Registrar no Pipeline

### Objetivo
Adicionar detector ao pipeline de mensagens.

### Arquivo: `app/pipeline/pipeline.py`

```python
# Adicionar import
from app.pipeline.steps.handoff_keyword_detector import handoff_keyword_detector

# Adicionar como um dos primeiros steps (antes do agente)
PIPELINE_STEPS = [
    # ... outros steps iniciais ...
    handoff_keyword_detector,  # NOVO: Detectar keywords de handoff
    # ... step do agente Julia ...
]
```

### DoD

- [ ] Import adicionado
- [ ] Step registrado no pipeline
- [ ] Executa antes do agente Julia

---

## Story 6.4: Testes de Keywords

### Arquivo: `tests/external_handoff/test_keyword_detector.py`

```python
"""Testes para detector de keywords de handoff."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.steps.handoff_keyword_detector import (
    HandoffKeywordDetector,
    KEYWORDS_CONFIRMED,
    KEYWORDS_NOT_CONFIRMED,
)


class TestDetectarKeyword:
    """Testes de deteccao de keywords."""

    def setup_method(self):
        self.detector = HandoffKeywordDetector()

    def test_detecta_confirmado(self):
        """Deve detectar 'confirmado'."""
        assert self.detector._detectar_keyword("confirmado") == "confirmed"
        assert self.detector._detectar_keyword("CONFIRMADO!") == "confirmed"
        assert self.detector._detectar_keyword("ta confirmado") == "confirmed"

    def test_detecta_fechou(self):
        """Deve detectar 'fechou'."""
        assert self.detector._detectar_keyword("fechou") == "confirmed"
        assert self.detector._detectar_keyword("ok, fechou") == "confirmed"
        assert self.detector._detectar_keyword("ja fechamos") == "confirmed"

    def test_detecta_nao_fechou(self):
        """Deve detectar 'nao fechou'."""
        assert self.detector._detectar_keyword("nao fechou") == "not_confirmed"
        assert self.detector._detectar_keyword("não fechou") == "not_confirmed"
        assert self.detector._detectar_keyword("infelizmente nao deu") == "not_confirmed"

    def test_detecta_desistiu(self):
        """Deve detectar 'desistiu'."""
        assert self.detector._detectar_keyword("ele desistiu") == "not_confirmed"
        assert self.detector._detectar_keyword("medico cancelou") == "not_confirmed"

    def test_nao_confirma_prioriza_nao_fechou(self):
        """'Nao fechou' deve ter prioridade sobre 'fechou'."""
        # Mensagem ambigua
        mensagem = "o plantao nao fechou como esperado"
        assert self.detector._detectar_keyword(mensagem) == "not_confirmed"

    def test_nao_detecta_mensagem_generica(self):
        """Mensagem generica nao deve detectar keyword."""
        assert self.detector._detectar_keyword("oi tudo bem") is None
        assert self.detector._detectar_keyword("qual plantao?") is None
        assert self.detector._detectar_keyword("me manda mais info") is None


class TestRespostaAgradecimento:
    """Testes de geracao de resposta."""

    def setup_method(self):
        self.detector = HandoffKeywordDetector()

    def test_resposta_confirmed(self):
        """Resposta para confirmado deve agradecer."""
        resposta = self.detector._gerar_resposta_agradecimento("confirmed")
        assert "obrigada" in resposta.lower()
        assert "confirmacao" in resposta.lower()

    def test_resposta_not_confirmed(self):
        """Resposta para nao confirmado deve agradecer."""
        resposta = self.detector._gerar_resposta_agradecimento("not_confirmed")
        assert "obrigada" in resposta.lower()


class TestPipelineIntegration:
    """Testes de integracao com pipeline."""

    @pytest.mark.asyncio
    async def test_processa_mensagem_divulgador(self):
        """Deve processar mensagem de divulgador com handoff."""
        detector = HandoffKeywordDetector()

        mock_handoff = {
            "id": "handoff-123",
            "vaga_id": "vaga-456",
            "cliente_id": "cliente-789",
            "divulgador_nome": "Joao",
        }

        with patch(
            "app.pipeline.steps.handoff_keyword_detector.buscar_handoff_pendente_por_telefone",
            new_callable=AsyncMock,
            return_value=mock_handoff
        ), patch(
            "app.pipeline.steps.handoff_keyword_detector.processar_confirmacao",
            new_callable=AsyncMock,
            return_value={"success": True}
        ), patch(
            "app.pipeline.steps.handoff_keyword_detector.emit_event",
            new_callable=AsyncMock
        ):
            context = MagicMock()
            context.mensagem_texto = "confirmado"
            context.telefone = "11999998888"
            context.metadata = {}

            result = await detector.process(context)

            assert result.skip_agent is True
            assert "obrigada" in result.resposta_override.lower()

    @pytest.mark.asyncio
    async def test_ignora_mensagem_sem_handoff(self):
        """Deve ignorar mensagem de telefone sem handoff."""
        detector = HandoffKeywordDetector()

        with patch(
            "app.pipeline.steps.handoff_keyword_detector.buscar_handoff_pendente_por_telefone",
            new_callable=AsyncMock,
            return_value=None
        ):
            context = MagicMock()
            context.mensagem_texto = "confirmado"
            context.telefone = "11999998888"
            context.metadata = {}

            result = await detector.process(context)

            # Nao deve marcar para pular agente
            assert not hasattr(result, 'skip_agent') or not result.skip_agent
```

### DoD

- [ ] Testes de deteccao de keywords
- [ ] Testes de prioridade (nao_fechou > fechou)
- [ ] Testes de resposta de agradecimento
- [ ] Testes de integracao com pipeline

---

## Checklist do Epico

- [ ] **S20.E06.1** - Detector de keywords criado
- [ ] **S20.E06.2** - Busca por telefone implementada
- [ ] **S20.E06.3** - Registrado no pipeline
- [ ] **S20.E06.4** - Testes passando
- [ ] Keywords de confirmacao funcionando
- [ ] Keywords de nao-confirmacao funcionando
- [ ] Resposta automatica enviada
- [ ] Medico notificado do resultado

---

## Keywords Suportadas

### Confirmacao (→ CONFIRMED)
- "confirmado", "confirmo"
- "fechou", "fechamos", "fechado"
- "ok, fechou"
- "tudo certo"
- "pode confirmar"
- "contrato fechado"

### Nao-Confirmacao (→ NOT_CONFIRMED)
- "nao fechou", "não fechou"
- "nao deu", "não deu"
- "desistiu", "cancelou"
- "nao vai dar", "não vai dar"
- "perdeu"
- "nao confirmou", "não confirmou"
- "nao rolou", "não rolou"

---

## Fluxo

```
1. Divulgador envia msg: "fechou!"
2. Webhook recebe mensagem
3. Pipeline inicia
4. HandoffKeywordDetector.process():
   a. Busca handoff por telefone
   b. Encontra handoff pendente
   c. Detecta keyword "fechou" → confirmed
   d. Chama processar_confirmacao()
   e. Define resposta_override
   f. Marca skip_agent=True
5. Pipeline continua mas pula agente Julia
6. Resposta enviada: "Anotado! Obrigada..."
7. Medico notificado via Julia
```
