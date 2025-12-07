# Epic 02: Handoff Humano → IA

## Prioridade: P0 (Crítico)

## Objetivo

> **Garantir que quando o gestor remove a label "humano" no Chatwoot, a Júlia volta a responder automaticamente.**

O fluxo IA→Humano está implementado (label "humano" bloqueia Júlia). Mas o caminho inverso (Humano→IA) precisa ser validado e completado.

---

## Referência: FLUXOS.md - Fluxo 7

```
GESTOR         CHATWOOT          WEBHOOK         BANCO     JÚLIA
  │               │                 │              │          │
  │  1. Remove    │                 │              │          │
  │     label     │                 │              │          │
  │     "humano"  │                 │              │          │
  │──────────────▶│                 │              │          │
  │               │                 │              │          │
  │               │─────────────────▶              │          │
  │               │  conversation_  │              │          │
  │               │  updated        │              │          │
  │               │                 │              │          │
  │               │                 │  2. Detecta  │          │
  │               │                 │     remoção  │          │
  │               │                 │     do label │          │
  │               │                 │              │          │
  │               │                 │  3. UPDATE   │          │
  │               │                 │─────────────▶│          │
  │               │                 │  controlled_ │          │
  │               │                 │  by = 'ai'   │          │
  │               │                 │              │          │
  │               │                 │              │  4. Júlia│
  │               │                 │              │  volta a │
  │               │                 │              │  responder
```

---

## Problema Atual

1. **Webhook recebe evento:** `conversation_updated` com labels
2. **Detecta adição de "humano":** Funciona (inicia handoff)
3. **Detecta remoção de "humano":** Precisa validar se funciona
4. **Atualiza banco:** `controlled_by = 'ai'`
5. **Júlia volta:** Precisa ler histórico do humano para contexto

---

## Stories

---

# S7.E2.1 - Validar webhook de remoção de label

## Objetivo

> **Garantir que webhook Chatwoot detecta quando label "humano" é REMOVIDA.**

## Contexto Técnico

O Chatwoot envia evento `conversation_updated` tanto quando label é adicionada quanto removida. Precisamos:
1. Guardar labels anteriores para comparar
2. Detectar quando "humano" estava presente e agora não está
3. Chamar `finalizar_handoff()`

## Código Esperado

**Arquivo:** `app/api/routes/chatwoot.py` (modificar)

```python
from typing import Optional

# Cache de labels por conversa (pode usar Redis em produção)
_labels_cache: dict[str, set] = {}

@router.post("/webhook")
async def chatwoot_webhook(request: Request):
    """Processa webhooks do Chatwoot."""
    payload = await request.json()
    event = payload.get("event")

    if event == "conversation_updated":
        await _handle_conversation_updated(payload)

    return {"status": "ok"}


async def _handle_conversation_updated(payload: dict):
    """Processa atualização de conversa (labels, status, etc)."""
    conversation = payload.get("conversation", {})
    conversation_id = conversation.get("id")
    current_labels = set(conversation.get("labels", []))

    # Buscar labels anteriores
    previous_labels = _labels_cache.get(str(conversation_id), set())

    # Detectar mudanças
    labels_adicionadas = current_labels - previous_labels
    labels_removidas = previous_labels - current_labels

    # Atualizar cache
    _labels_cache[str(conversation_id)] = current_labels

    # Tratar label "humano"
    if "humano" in labels_adicionadas:
        logger.info(f"Label 'humano' ADICIONADA na conversa {conversation_id}")
        await _iniciar_handoff_por_label(conversation_id)

    elif "humano" in labels_removidas:
        logger.info(f"Label 'humano' REMOVIDA da conversa {conversation_id}")
        await _finalizar_handoff_por_label(conversation_id)


async def _iniciar_handoff_por_label(chatwoot_conversation_id: int):
    """Inicia handoff quando gestor adiciona label 'humano'."""
    # Buscar conversa pelo chatwoot_id
    conversa = await buscar_conversa_por_chatwoot_id(chatwoot_conversation_id)
    if not conversa:
        logger.warning(f"Conversa Chatwoot {chatwoot_conversation_id} não encontrada no banco")
        return

    await iniciar_handoff(
        conversa_id=conversa["id"],
        motivo="Label 'humano' adicionada pelo gestor",
        tipo="manual"
    )


async def _finalizar_handoff_por_label(chatwoot_conversation_id: int):
    """Finaliza handoff quando gestor remove label 'humano'."""
    conversa = await buscar_conversa_por_chatwoot_id(chatwoot_conversation_id)
    if not conversa:
        logger.warning(f"Conversa Chatwoot {chatwoot_conversation_id} não encontrada no banco")
        return

    await finalizar_handoff(
        conversa_id=conversa["id"],
        notas="Gestor removeu label 'humano' no Chatwoot"
    )
```

## Critérios de Aceite

1. **Cache de labels:** Sistema guarda labels anteriores por conversa
2. **Detecta adição:** "humano" adicionada → inicia handoff
3. **Detecta remoção:** "humano" removida → finaliza handoff
4. **Idempotente:** Se label já foi processada, não processa de novo
5. **Log claro:** Logs indicam claramente adição/remoção

## DoD

- [x] Webhook detecta remoção de label "humano"
- [x] Log gerado quando label é removida
- [x] `_finalizar_handoff_por_label()` é chamada
- [x] Cache de labels funciona (ou alternativa com Redis)
- [x] Teste manual: remover label no Chatwoot → log aparece

**NOTA:** Já implementado em `app/api/routes/chatwoot.py` - webhook detecta mudanças de labels e chama `finalizar_handoff()` automaticamente.

## Teste Manual

1. No Chatwoot, abrir conversa em modo humano (com label "humano")
2. Remover a label "humano"
3. Verificar logs: deve aparecer "Label 'humano' REMOVIDA"
4. Verificar banco: `controlled_by` deve ser 'ai'

---

# S7.E2.2 - Implementar finalizar_handoff completo

## Objetivo

> **Função que reverte conversa para controle da IA e registra fim do handoff.**

## Contexto Técnico

Quando handoff termina, precisamos:
1. Atualizar `conversations.controlled_by = 'ai'`
2. Atualizar `handoffs` com `resolvido_em` e notas
3. Notificar gestor que handoff foi resolvido (opcional)
4. Garantir que próxima mensagem será respondida por Júlia

## Código Esperado

**Arquivo:** `app/services/handoff.py` (modificar/completar)

```python
from datetime import datetime
from app.services.supabase import supabase
from app.services.slack import notificar_handoff_resolvido
import logging

logger = logging.getLogger(__name__)


async def finalizar_handoff(
    conversa_id: str,
    notas: str = "",
    resolvido_por: str = "gestor"
) -> dict:
    """
    Finaliza handoff e devolve controle para a IA.

    Args:
        conversa_id: ID da conversa no banco
        notas: Observações sobre a resolução
        resolvido_por: Quem resolveu (gestor, sistema, etc)

    Returns:
        dict com status da operação
    """
    try:
        # 1. Atualizar conversa para voltar ao controle da IA
        conversa_response = (
            supabase.table("conversations")
            .update({
                "controlled_by": "ai",
                "updated_at": datetime.utcnow().isoformat()
            })
            .eq("id", conversa_id)
            .execute()
        )

        if not conversa_response.data:
            logger.error(f"Conversa {conversa_id} não encontrada para finalizar handoff")
            return {"success": False, "error": "Conversa não encontrada"}

        conversa = conversa_response.data[0]
        logger.info(f"Conversa {conversa_id} devolvida para controle da IA")

        # 2. Buscar e atualizar handoff ativo
        handoff_response = (
            supabase.table("handoffs")
            .update({
                "resolvido_em": datetime.utcnow().isoformat(),
                "resolvido_por": resolvido_por,
                "notas_resolucao": notas
            })
            .eq("conversa_id", conversa_id)
            .is_("resolvido_em", "null")  # Apenas handoffs não resolvidos
            .execute()
        )

        if handoff_response.data:
            handoff = handoff_response.data[0]
            logger.info(f"Handoff {handoff['id']} marcado como resolvido")

            # 3. Calcular duração e notificar
            iniciado_em = datetime.fromisoformat(handoff["created_at"].replace("Z", "+00:00"))
            resolvido_em = datetime.utcnow()
            duracao = resolvido_em - iniciado_em.replace(tzinfo=None)

            # Buscar dados do médico para notificação
            cliente_response = (
                supabase.table("clientes")
                .select("primeiro_nome, sobrenome")
                .eq("id", conversa["cliente_id"])
                .single()
                .execute()
            )

            if cliente_response.data:
                medico = cliente_response.data
                await notificar_handoff_resolvido(
                    medico_nome=f"{medico['primeiro_nome']} {medico.get('sobrenome', '')}",
                    duracao_minutos=int(duracao.total_seconds() / 60),
                    notas=notas
                )

        return {
            "success": True,
            "conversa_id": conversa_id,
            "controlled_by": "ai"
        }

    except Exception as e:
        logger.error(f"Erro ao finalizar handoff: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

## Critérios de Aceite

1. **Conversa atualizada:** `controlled_by = 'ai'` no banco
2. **Handoff fechado:** `resolvido_em` preenchido
3. **Notas registradas:** Observações salvas no handoff
4. **Notificação enviada:** Slack notificado (se configurado)
5. **Duração calculada:** Tempo de handoff registrado
6. **Idempotente:** Chamar 2x não causa erro

## DoD

- [x] Função `finalizar_handoff()` implementada
- [x] `conversations.controlled_by` atualizado para 'ai'
- [x] `handoffs.resolvido_em` preenchido
- [x] `handoffs.notas_resolucao` salvas
- [x] Notificação Slack enviada com duração
- [x] Logs claros indicando sucesso/erro
- [x] Teste: após finalizar, Júlia responde próxima mensagem

**NOTA:** Implementado em `app/services/handoff.py` - função melhorada com notificação Slack e notas.

---

# S7.E2.3 - Júlia lê contexto do atendimento humano

## Objetivo

> **Após handoff, Júlia deve ter contexto do que o humano conversou para continuar naturalmente.**

## Contexto Técnico

Quando Júlia volta, ela precisa:
1. Saber que houve handoff (não ficar surpresa com contexto)
2. Ler mensagens trocadas durante período humano
3. Continuar conversa sem repetir o que humano disse

## Código Esperado

**Arquivo:** `app/services/contexto.py` (modificar)

```python
async def montar_contexto_completo(
    medico: dict,
    conversa: dict,
    incluir_vagas: bool = True
) -> dict:
    """
    Monta contexto completo para o agente.

    Inclui:
    - Dados do médico
    - Histórico recente (últimas 10 msgs)
    - Vagas disponíveis
    - Indicação se houve handoff recente
    """
    contexto = {
        "medico": medico,
        "conversa": conversa,
        # ... outros campos
    }

    # Carregar histórico (inclui mensagens do humano)
    historico = await carregar_historico_recente(
        conversa_id=conversa["id"],
        limite=10
    )
    contexto["historico"] = historico

    # Verificar se houve handoff recente
    handoff_recente = await verificar_handoff_recente(conversa["id"])
    if handoff_recente:
        contexto["retorno_de_handoff"] = True
        contexto["handoff_info"] = {
            "motivo": handoff_recente.get("motivo"),
            "duracao_minutos": handoff_recente.get("duracao_minutos"),
            "notas": handoff_recente.get("notas_resolucao")
        }

    return contexto


async def verificar_handoff_recente(conversa_id: str, minutos: int = 60) -> Optional[dict]:
    """
    Verifica se houve handoff resolvido recentemente.

    Returns:
        dict com info do handoff se resolvido nas últimas N minutos, None caso contrário
    """
    limite = datetime.utcnow() - timedelta(minutes=minutos)

    response = (
        supabase.table("handoffs")
        .select("*")
        .eq("conversa_id", conversa_id)
        .gte("resolvido_em", limite.isoformat())
        .order("resolvido_em", desc=True)
        .limit(1)
        .execute()
    )

    if response.data:
        handoff = response.data[0]
        # Calcular duração
        iniciado = datetime.fromisoformat(handoff["created_at"].replace("Z", "+00:00"))
        resolvido = datetime.fromisoformat(handoff["resolvido_em"].replace("Z", "+00:00"))
        duracao = (resolvido - iniciado).total_seconds() / 60

        return {
            **handoff,
            "duracao_minutos": int(duracao)
        }

    return None
```

**Arquivo:** `app/core/prompts.py` (adicionar instrução)

```python
INSTRUCAO_RETORNO_HANDOFF = """
## Retorno de Handoff

Se o contexto indicar que você está retornando de um handoff (quando um humano assumiu a conversa):

1. NÃO pergunte "como posso ajudar?" - você já sabe o contexto
2. Leia as mensagens recentes para entender o que foi discutido
3. Continue naturalmente de onde parou
4. Se apropriado, pode mencionar: "Oi de novo! Vi que minha supervisora já te ajudou"

Exemplo de retorno bom:
"Oi {nome}! Vi que a equipe já resolveu aquela questão.
Se precisar de mais alguma coisa sobre plantões, to aqui!"

Exemplo ruim (não faça):
"Olá! Sou a Júlia, como posso ajudar?" (ignora contexto)
"""
```

## Critérios de Aceite

1. **Contexto carregado:** Mensagens do período humano incluídas
2. **Flag de handoff:** Contexto indica que houve handoff
3. **Prompt instruído:** Júlia sabe como se comportar pós-handoff
4. **Continuidade natural:** Júlia não repete perguntas já respondidas
5. **Reconhecimento:** Júlia pode mencionar que supervisora ajudou

## DoD

- [x] `verificar_handoff_recente()` implementada
- [x] Contexto inclui `handoff_recente` quando aplicável
- [x] Histórico inclui mensagens do humano (remetente != 'julia')
- [x] Prompt tem instrução específica para retorno de handoff
- [x] Teste: após handoff, Júlia continua naturalmente

**NOTA:** Implementado em:
- `app/services/contexto.py`: funções `verificar_handoff_recente()` e `formatar_contexto_handoff()`
- `app/core/prompts.py`: constante `JULIA_PROMPT_RETORNO_HANDOFF` e parâmetro `contexto_handoff` em `montar_prompt_julia()`
- `app/services/agente.py`: passa `handoff_recente` para o prompt

## Teste Manual

1. Iniciar handoff (adicionar label "humano")
2. Enviar algumas mensagens como humano no Chatwoot
3. Finalizar handoff (remover label "humano")
4. Médico envia nova mensagem
5. Verificar: Júlia responde considerando contexto do humano

---

## Resumo do Epic

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S7.E2.1 | Validar webhook remoção label | Média |
| S7.E2.2 | Implementar finalizar_handoff | Média |
| S7.E2.3 | Contexto pós-handoff | Média |

## Arquivos Modificados

| Arquivo | Ação |
|---------|------|
| `app/api/routes/chatwoot.py` | Detectar remoção de label |
| `app/services/handoff.py` | Implementar finalizar_handoff |
| `app/services/contexto.py` | Verificar handoff recente |
| `app/core/prompts.py` | Instrução de retorno |

## Fluxo Completo Validado

```
1. Médico envia mensagem → Júlia responde
2. Júlia detecta trigger → Inicia handoff
3. conversations.controlled_by = 'human'
4. Gestor vê no Chatwoot (label "humano")
5. Gestor conversa com médico
6. Gestor resolve e remove label
7. Webhook detecta remoção
8. finalizar_handoff() chamada
9. conversations.controlled_by = 'ai'
10. Médico envia mensagem → Júlia responde (com contexto)
```
