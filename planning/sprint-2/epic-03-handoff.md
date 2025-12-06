# Epic 3: Sistema de Handoff

## Objetivo

> **Júlia sabe quando parar e passar a conversa para um humano.**

---

## Stories

---

# S2.E3.1 - Detectar triggers automáticos

## Objetivo

> **Identificar automaticamente quando Júlia deve parar de responder.**

**Resultado esperado:** Sistema detecta situações que requerem humano.

## Contexto

Triggers automáticos de handoff:
- Médico pede explicitamente para falar com humano
- Sentimento muito negativo (raiva, frustração)
- Situações complexas (jurídico, reclamação formal)
- Confiança baixa da Júlia na resposta

## Tarefas

### 1. Criar detector de handoff

```python
# app/services/handoff_detector.py

import re
from typing import Optional

# Frases que indicam pedido de humano
FRASES_PEDIDO_HUMANO = [
    r"falar com (um |uma )?(pessoa|humano|atendente|supervisor)",
    r"quero (um |uma )?(pessoa|humano|atendente)",
    r"(passa|transfere) (pra|para) (um |uma )?(supervisor|gerente|humano)",
    r"não (quero|vou) falar com (robô|bot|máquina)",
    r"(isso|vc|você) é (um |uma )?(robô|bot|ia|inteligência artificial)",
    r"me (liga|ligue|telefona)",
    r"(preciso|quero) (ligar|telefonar)",
]

# Frases que indicam situação jurídica/formal
FRASES_JURIDICO = [
    r"advogado",
    r"processo",
    r"justiça",
    r"(meu|minha) advogad[oa]",
    r"procon",
    r"reclamação formal",
    r"notificação extrajudicial",
]

# Palavras que indicam sentimento negativo forte
PALAVRAS_NEGATIVAS = [
    r"absurd[oa]",
    r"ridícul[oa]",
    r"vergonha",
    r"desrespeit[oa]",
    r"falta de respeito",
    r"nunca mais",
    r"péssim[oa]",
    r"horrível",
    r"odeio",
    r"raiva",
]


def detectar_trigger_handoff(mensagem: str) -> Optional[dict]:
    """
    Analisa mensagem e detecta se há trigger de handoff.

    Returns:
        dict com {trigger: True, motivo: str, tipo: str} ou None
    """
    mensagem_lower = mensagem.lower()

    # Verificar pedido de humano
    for padrao in FRASES_PEDIDO_HUMANO:
        if re.search(padrao, mensagem_lower):
            return {
                "trigger": True,
                "motivo": "Médico pediu para falar com humano",
                "tipo": "pedido_humano"
            }

    # Verificar situação jurídica
    for padrao in FRASES_JURIDICO:
        if re.search(padrao, mensagem_lower):
            return {
                "trigger": True,
                "motivo": "Situação jurídica/formal detectada",
                "tipo": "juridico"
            }

    # Verificar sentimento negativo forte
    negativos_encontrados = 0
    for padrao in PALAVRAS_NEGATIVAS:
        if re.search(padrao, mensagem_lower):
            negativos_encontrados += 1

    if negativos_encontrados >= 2:
        return {
            "trigger": True,
            "motivo": "Sentimento muito negativo detectado",
            "tipo": "sentimento_negativo"
        }

    return None
```

### 2. Detector baseado em confiança do LLM

```python
# app/services/handoff_detector.py (adicionar)

async def analisar_confianca_resposta(
    mensagem: str,
    resposta: str,
    contexto: dict
) -> Optional[dict]:
    """
    Usa LLM para avaliar se Júlia está confiante na resposta.

    Casos de baixa confiança:
    - Pergunta técnica muito específica
    - Informação que Júlia não tem
    - Situação ambígua
    """
    prompt = f"""
Analise esta interação e diga se a Júlia deveria passar para um humano.

MENSAGEM DO MÉDICO:
{mensagem}

RESPOSTA PROPOSTA:
{resposta}

CONTEXTO DISPONÍVEL:
{contexto.get('resumo', 'Sem contexto')}

Responda APENAS com JSON:
{{"passar_humano": true/false, "motivo": "explicação breve", "confianca": 0-100}}

Passe para humano se:
- Pergunta requer informação que Júlia não tem
- Situação complexa demais para IA
- Médico parece querer negociação especial
- Há risco de dano ao relacionamento
"""

    response = await anthropic_client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        resultado = json.loads(response.content[0].text)
        if resultado.get("passar_humano") and resultado.get("confianca", 100) < 50:
            return {
                "trigger": True,
                "motivo": resultado.get("motivo", "Baixa confiança na resposta"),
                "tipo": "baixa_confianca"
            }
    except:
        pass

    return None
```

### 3. Integrar no fluxo de processamento

```python
# app/services/agente.py (atualizar)

from app.services.handoff_detector import detectar_trigger_handoff

async def processar_mensagem(conversa: dict, mensagem: str, contexto: dict):
    """Processa mensagem, verificando triggers de handoff."""

    # Verificar trigger baseado na mensagem
    trigger = detectar_trigger_handoff(mensagem)
    if trigger:
        await iniciar_handoff(
            conversa_id=conversa["id"],
            motivo=trigger["motivo"],
            trigger_type=trigger["tipo"]
        )
        return None  # Não gera resposta automática

    # Gerar resposta
    resposta = await gerar_resposta(mensagem, contexto)

    # Verificar confiança na resposta (opcional, mais custoso)
    # trigger_confianca = await analisar_confianca_resposta(mensagem, resposta, contexto)
    # if trigger_confianca:
    #     await iniciar_handoff(...)
    #     return None

    return resposta
```

## DoD

- [ ] Detector de frases de pedido de humano funciona
- [ ] Detector de situação jurídica funciona
- [ ] Detector de sentimento negativo funciona
- [ ] Integração no fluxo de processamento
- [ ] Handoff iniciado quando trigger detectado

---

# S2.E3.2 - Mensagem de transição

## Objetivo

> **Júlia avisa o médico antes de passar para humano.**

**Resultado esperado:** Médico sabe que vai falar com humano e por quê.

## Tarefas

### 1. Criar mensagens de transição

```python
# app/services/handoff.py

MENSAGENS_TRANSICAO = {
    "pedido_humano": [
        "Claro! Vou pedir pra minha supervisora te ajudar, ela é ótima 😊",
        "Entendi! Vou chamar alguém da equipe pra falar com vc",
        "Sem problema! Já to passando pro pessoal aqui",
    ],
    "juridico": [
        "Opa, esse assunto é mais delicado, vou passar pra minha supervisora que entende melhor",
        "Entendi a situação. Vou pedir pra alguém mais experiente te ajudar, ok?",
    ],
    "sentimento_negativo": [
        "Entendo sua frustração, vou chamar minha supervisora pra resolver isso da melhor forma",
        "Desculpa por qualquer inconveniente. Vou passar pro pessoal resolver pra vc",
    ],
    "baixa_confianca": [
        "Hmm, deixa eu confirmar uma coisa com o pessoal aqui. Já volto!",
        "Boa pergunta! Vou checar com a equipe e te retorno",
    ],
    "manual": [
        "Oi! Minha supervisora vai continuar o atendimento, tá? 😊",
    ],
}

import random

def obter_mensagem_transicao(tipo: str) -> str:
    """Retorna mensagem de transição apropriada para o tipo de handoff."""
    mensagens = MENSAGENS_TRANSICAO.get(tipo, MENSAGENS_TRANSICAO["manual"])
    return random.choice(mensagens)
```

### 2. Enviar mensagem antes do handoff

```python
# app/services/handoff.py (adicionar)

async def iniciar_handoff(
    conversa_id: str,
    motivo: str,
    trigger_type: str
) -> dict:
    """
    Inicia processo de handoff para humano.

    1. Envia mensagem de transição
    2. Atualiza conversa para controlled_by = 'human'
    3. Cria registro de handoff
    4. Notifica gestor
    """
    # Buscar conversa com dados do médico
    conversa = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("id", conversa_id)
        .single()
        .execute()
    ).data

    telefone = conversa["clientes"]["telefone"]

    # 1. Enviar mensagem de transição
    mensagem_transicao = obter_mensagem_transicao(trigger_type)
    await whatsapp_service.enviar_mensagem(
        telefone=telefone,
        texto=mensagem_transicao
    )

    # Salvar mensagem de transição
    supabase.table("interacoes").insert({
        "conversa_id": conversa_id,
        "direcao": "saida",
        "tipo": "texto",
        "conteudo": mensagem_transicao,
        "origem": "ai",
        "metadata": {"tipo": "mensagem_transicao_handoff"}
    }).execute()

    # Sincronizar com Chatwoot
    if conversa.get("chatwoot_conversation_id"):
        await chatwoot_service.enviar_mensagem(
            conversation_id=conversa["chatwoot_conversation_id"],
            content=mensagem_transicao,
            message_type="outgoing"
        )

    # 2. Atualizar conversa
    supabase.table("conversations").update({
        "controlled_by": "human"
    }).eq("id", conversa_id).execute()

    # 3. Criar registro de handoff
    handoff = (
        supabase.table("handoffs")
        .insert({
            "conversa_id": conversa_id,
            "motivo": motivo,
            "trigger_type": trigger_type,
            "status": "pendente"
        })
        .execute()
    ).data[0]

    # 4. Notificar gestor (próxima story)
    await notificar_handoff(conversa, handoff)

    return handoff
```

## DoD

- [ ] Mensagens de transição definidas para cada tipo
- [ ] Mensagem enviada antes do handoff
- [ ] Tom natural e amigável
- [ ] Mensagem salva no histórico
- [ ] Mensagem sincronizada com Chatwoot

---

# S2.E3.3 - Bloquear Júlia em conversa humana

## Objetivo

> **Júlia não responde quando conversa está com humano.**

**Resultado esperado:** Mensagens em conversas com `controlled_by='human'` são ignoradas pela IA.

## Tarefas

### 1. Verificar controle no webhook

```python
# app/routes/webhook.py (atualizar)

async def processar_mensagem(mensagem: MensagemRecebida):
    """Processa mensagem recebida do WhatsApp."""

    # ... parsing e validação ...

    # Buscar conversa
    conversa = await buscar_ou_criar_conversa(medico["id"], mensagem.telefone)

    # VERIFICAR SE CONVERSA ESTÁ COM HUMANO
    if conversa.get("controlled_by") == "human":
        logger.info(
            f"Conversa {conversa['id']} controlada por humano, "
            f"Júlia não vai responder"
        )
        # Salvar mensagem para histórico
        await salvar_interacao(
            conversa_id=conversa["id"],
            direcao="entrada",
            conteudo=mensagem.texto,
            origem="medico"
        )

        # Sincronizar com Chatwoot para gestor ver
        if conversa.get("chatwoot_conversation_id"):
            await chatwoot_service.enviar_mensagem(
                conversation_id=conversa["chatwoot_conversation_id"],
                content=mensagem.texto,
                message_type="incoming"
            )

        return {"status": "forwarded_to_human"}

    # Continuar processamento normal com IA
    # ...
```

### 2. Função para devolver conversa à IA

```python
# app/services/handoff.py (adicionar)

async def devolver_para_ia(conversa_id: str) -> dict:
    """
    Devolve conversa para controle da Júlia.

    Usar quando humano termina atendimento.
    """
    # Atualizar conversa
    supabase.table("conversations").update({
        "controlled_by": "ai"
    }).eq("id", conversa_id).execute()

    # Atualizar handoff
    supabase.table("handoffs").update({
        "status": "resolvido",
        "resolvido_em": datetime.utcnow().isoformat()
    }).eq("conversa_id", conversa_id).eq("status", "pendente").execute()

    # Buscar conversa atualizada
    conversa = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("id", conversa_id)
        .single()
        .execute()
    ).data

    return conversa
```

### 3. Trigger por label no Chatwoot

```python
# app/routes/chatwoot.py (atualizar)

async def processar_conversation_updated(payload: dict):
    """Processa atualização de conversa (labels)."""
    conversation = payload.get("conversation", {})
    labels = conversation.get("labels", [])
    conversation_id = conversation.get("id")

    # Buscar nossa conversa
    response = (
        supabase.table("conversations")
        .select("*")
        .eq("chatwoot_conversation_id", conversation_id)
        .execute()
    )

    if not response.data:
        return

    conversa = response.data[0]

    # Label "humano" adicionada → Handoff
    if "humano" in labels and conversa["controlled_by"] != "human":
        await iniciar_handoff(
            conversa_id=conversa["id"],
            motivo="Label humano adicionada no Chatwoot",
            trigger_type="manual"
        )

    # Label "humano" removida → Devolver para IA
    if "humano" not in labels and conversa["controlled_by"] == "human":
        await devolver_para_ia(conversa["id"])
```

## DoD

- [ ] Júlia não responde quando `controlled_by='human'`
- [ ] Mensagens ainda são salvas no histórico
- [ ] Mensagens sincronizadas com Chatwoot
- [ ] Função `devolver_para_ia()` implementada
- [ ] Label "humano" removida devolve para IA

---

# S2.E3.4 - Registrar handoff no banco

## Objetivo

> **Manter histórico de todos os handoffs para análise.**

**Resultado esperado:** Tabela `handoffs` com dados completos de cada transferência.

## Contexto

A tabela `handoffs` já existe no schema:
```sql
CREATE TABLE handoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID REFERENCES conversations(id),
    motivo TEXT,
    trigger_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pendente',
    resolvido_em TIMESTAMPTZ,
    resolvido_por UUID REFERENCES usuarios(id),
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Tarefas

### 1. Garantir registro completo

```python
# app/services/handoff.py (atualizar)

async def iniciar_handoff(
    conversa_id: str,
    motivo: str,
    trigger_type: str
) -> dict:
    """Inicia handoff com registro completo."""

    # ... código existente ...

    # Criar registro de handoff com mais contexto
    handoff = (
        supabase.table("handoffs")
        .insert({
            "conversa_id": conversa_id,
            "motivo": motivo,
            "trigger_type": trigger_type,
            "status": "pendente",
            "metadata": {
                "ultima_mensagem": ultima_mensagem,
                "total_interacoes": total_interacoes,
                "duracao_conversa_minutos": duracao_minutos
            }
        })
        .execute()
    ).data[0]

    return handoff


async def resolver_handoff(
    handoff_id: str,
    resolvido_por: str = None,
    notas: str = None
) -> dict:
    """Marca handoff como resolvido."""

    handoff = (
        supabase.table("handoffs")
        .update({
            "status": "resolvido",
            "resolvido_em": datetime.utcnow().isoformat(),
            "resolvido_por": resolvido_por,
            "notas": notas
        })
        .eq("id", handoff_id)
        .execute()
    ).data[0]

    return handoff
```

### 2. Queries úteis para relatórios

```python
# app/services/handoff.py (adicionar)

async def listar_handoffs_pendentes() -> list:
    """Lista todos os handoffs pendentes."""
    response = (
        supabase.table("handoffs")
        .select("*, conversations(*, clientes(*))")
        .eq("status", "pendente")
        .order("created_at")
        .execute()
    )
    return response.data


async def obter_metricas_handoff(periodo_dias: int = 30) -> dict:
    """Retorna métricas de handoff do período."""
    data_inicio = (datetime.now() - timedelta(days=periodo_dias)).isoformat()

    response = (
        supabase.table("handoffs")
        .select("trigger_type, status")
        .gte("created_at", data_inicio)
        .execute()
    )

    handoffs = response.data

    # Agrupar por tipo
    por_tipo = {}
    for h in handoffs:
        tipo = h["trigger_type"]
        if tipo not in por_tipo:
            por_tipo[tipo] = 0
        por_tipo[tipo] += 1

    # Calcular tempo médio de resolução
    resolvidos = [h for h in handoffs if h["status"] == "resolvido"]

    return {
        "total": len(handoffs),
        "pendentes": len([h for h in handoffs if h["status"] == "pendente"]),
        "resolvidos": len(resolvidos),
        "por_tipo": por_tipo,
    }
```

## DoD

- [ ] Handoff criado com todos os campos
- [ ] Metadata inclui contexto útil
- [ ] Função `resolver_handoff()` implementada
- [ ] Queries de listagem funcionam
- [ ] Métricas básicas disponíveis

---

# S2.E3.5 - Notificar gestor no Slack

## Objetivo

> **Enviar notificação imediata no Slack quando handoff ocorrer.**

**Resultado esperado:** Gestor recebe alerta com dados do médico e motivo.

## Tarefas

### 1. Criar serviço de notificação Slack

```python
# app/services/slack.py

import httpx
from app.core.config import settings

class SlackService:
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL

    async def enviar_mensagem(self, mensagem: dict) -> bool:
        """
        Envia mensagem para Slack via webhook.

        Args:
            mensagem: Payload do Slack (text, attachments, blocks)

        Returns:
            True se enviado com sucesso
        """
        if not self.webhook_url:
            return False

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json=mensagem
            )
            return response.status_code == 200


slack_service = SlackService()
```

### 2. Criar notificação de handoff

```python
# app/services/slack.py (adicionar)

async def notificar_handoff(conversa: dict, handoff: dict):
    """
    Notifica gestor sobre novo handoff.

    Inclui:
    - Nome do médico
    - Motivo do handoff
    - Link para Chatwoot
    - Últimas mensagens
    """
    medico = conversa.get("clientes", {})
    chatwoot_id = conversa.get("chatwoot_conversation_id")

    # Montar link do Chatwoot
    chatwoot_link = ""
    if chatwoot_id:
        chatwoot_link = (
            f"{settings.CHATWOOT_URL}/app/accounts/"
            f"{settings.CHATWOOT_ACCOUNT_ID}/conversations/{chatwoot_id}"
        )

    # Cor baseada no tipo
    cores = {
        "pedido_humano": "#2196F3",  # Azul
        "juridico": "#F44336",       # Vermelho
        "sentimento_negativo": "#FF9800",  # Laranja
        "baixa_confianca": "#9C27B0",  # Roxo
        "manual": "#4CAF50",          # Verde
    }

    cor = cores.get(handoff["trigger_type"], "#607D8B")

    mensagem = {
        "text": "🚨 Handoff necessário!",
        "attachments": [{
            "color": cor,
            "fields": [
                {
                    "title": "Médico",
                    "value": medico.get("primeiro_nome", "Desconhecido"),
                    "short": True
                },
                {
                    "title": "Telefone",
                    "value": medico.get("telefone", "N/A"),
                    "short": True
                },
                {
                    "title": "Motivo",
                    "value": handoff["motivo"],
                    "short": False
                },
                {
                    "title": "Tipo",
                    "value": handoff["trigger_type"],
                    "short": True
                },
            ],
            "actions": []
        }]
    }

    # Adicionar link do Chatwoot se disponível
    if chatwoot_link:
        mensagem["attachments"][0]["actions"].append({
            "type": "button",
            "text": "Abrir no Chatwoot",
            "url": chatwoot_link
        })

    await slack_service.enviar_mensagem(mensagem)
```

### 3. Integrar na função de handoff

```python
# app/services/handoff.py (atualizar)

from app.services.slack import notificar_handoff

async def iniciar_handoff(
    conversa_id: str,
    motivo: str,
    trigger_type: str
) -> dict:
    # ... código existente ...

    # 4. Notificar gestor no Slack
    try:
        await notificar_handoff(conversa, handoff)
    except Exception as e:
        logger.error(f"Erro ao notificar Slack: {e}")
        # Não falha a operação principal

    return handoff
```

### 4. Notificação de handoff resolvido

```python
# app/services/slack.py (adicionar)

async def notificar_handoff_resolvido(conversa: dict, handoff: dict):
    """Notifica que handoff foi resolvido."""
    medico = conversa.get("clientes", {})

    mensagem = {
        "text": "✅ Handoff resolvido!",
        "attachments": [{
            "color": "#4CAF50",
            "fields": [
                {
                    "title": "Médico",
                    "value": medico.get("primeiro_nome", "Desconhecido"),
                    "short": True
                },
                {
                    "title": "Duração",
                    "value": calcular_duracao(handoff),
                    "short": True
                },
                {
                    "title": "Notas",
                    "value": handoff.get("notas", "Sem notas"),
                    "short": False
                },
            ]
        }]
    }

    await slack_service.enviar_mensagem(mensagem)
```

## DoD

- [ ] Serviço Slack implementado
- [ ] Notificação enviada quando handoff inicia
- [ ] Mensagem inclui dados do médico
- [ ] Mensagem inclui motivo e tipo
- [ ] Link direto para Chatwoot
- [ ] Notificação de handoff resolvido
- [ ] Cores diferentes por tipo de handoff
