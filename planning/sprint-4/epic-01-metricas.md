# Epic 1: Sistema de Métricas

## Objetivo

> **Medir e visualizar performance da Júlia em tempo real.**

---

## Stories

---

# S4.E1.1 - Dashboard de métricas básico

## Objetivo

> **Criar dashboard simples para visualizar métricas principais.**

**Resultado esperado:** Gestor vê métricas em tempo real numa página web.

## Contexto

Não precisamos de ferramenta complexa. Um dashboard simples em HTML/JS consultando uma API basta para o piloto.

## Tarefas

### 1. Criar endpoint de métricas

```python
# app/routes/metricas.py

from fastapi import APIRouter
from datetime import datetime, timedelta
from app.core.supabase import supabase

router = APIRouter(prefix="/metricas", tags=["metricas"])

@router.get("/resumo")
async def obter_resumo(dias: int = 7):
    """
    Retorna resumo de métricas dos últimos N dias.
    """
    data_inicio = (datetime.now() - timedelta(days=dias)).isoformat()

    # Total de conversas
    conversas = (
        supabase.table("conversations")
        .select("id, status, created_at")
        .gte("created_at", data_inicio)
        .execute()
    ).data

    # Total de interações
    interacoes = (
        supabase.table("interacoes")
        .select("id, direcao, origem, created_at")
        .gte("created_at", data_inicio)
        .execute()
    ).data

    # Handoffs
    handoffs = (
        supabase.table("handoffs")
        .select("id, trigger_type, status")
        .gte("created_at", data_inicio)
        .execute()
    ).data

    # Calcular métricas
    total_conversas = len(conversas)
    conversas_ativas = len([c for c in conversas if c["status"] == "ativa"])

    msgs_entrada = len([i for i in interacoes if i["direcao"] == "entrada"])
    msgs_saida = len([i for i in interacoes if i["direcao"] == "saida"])

    total_handoffs = len(handoffs)
    handoffs_por_tipo = {}
    for h in handoffs:
        tipo = h["trigger_type"]
        handoffs_por_tipo[tipo] = handoffs_por_tipo.get(tipo, 0) + 1

    return {
        "periodo_dias": dias,
        "conversas": {
            "total": total_conversas,
            "ativas": conversas_ativas,
        },
        "mensagens": {
            "recebidas": msgs_entrada,
            "enviadas": msgs_saida,
        },
        "handoffs": {
            "total": total_handoffs,
            "por_tipo": handoffs_por_tipo,
        },
        "taxas": {
            "resposta": msgs_entrada / total_conversas if total_conversas > 0 else 0,
            "handoff": total_handoffs / total_conversas if total_conversas > 0 else 0,
        }
    }
```

### 2. Criar página de dashboard

```html
<!-- static/dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Júlia - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 10px; display: inline-block; min-width: 200px; }
        .card h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; }
        .card .valor { font-size: 32px; font-weight: bold; color: #333; }
        .grid { display: flex; flex-wrap: wrap; }
        .refresh { position: fixed; top: 10px; right: 10px; }
    </style>
</head>
<body>
    <h1>📊 Dashboard Júlia</h1>
    <p>Últimos <select id="dias" onchange="atualizar()">
        <option value="1">1 dia</option>
        <option value="7" selected>7 dias</option>
        <option value="30">30 dias</option>
    </select></p>

    <div class="grid" id="metricas"></div>

    <button class="refresh" onclick="atualizar()">🔄 Atualizar</button>

    <script>
        async function atualizar() {
            const dias = document.getElementById('dias').value;
            const resp = await fetch(`/metricas/resumo?dias=${dias}`);
            const data = await resp.json();

            document.getElementById('metricas').innerHTML = `
                <div class="card">
                    <h3>Conversas</h3>
                    <div class="valor">${data.conversas.total}</div>
                </div>
                <div class="card">
                    <h3>Conversas Ativas</h3>
                    <div class="valor">${data.conversas.ativas}</div>
                </div>
                <div class="card">
                    <h3>Mensagens Recebidas</h3>
                    <div class="valor">${data.mensagens.recebidas}</div>
                </div>
                <div class="card">
                    <h3>Mensagens Enviadas</h3>
                    <div class="valor">${data.mensagens.enviadas}</div>
                </div>
                <div class="card">
                    <h3>Handoffs</h3>
                    <div class="valor">${data.handoffs.total}</div>
                </div>
                <div class="card">
                    <h3>Taxa de Resposta</h3>
                    <div class="valor">${(data.taxas.resposta * 100).toFixed(1)}%</div>
                </div>
            `;
        }

        // Atualizar a cada 30s
        atualizar();
        setInterval(atualizar, 30000);
    </script>
</body>
</html>
```

### 3. Servir arquivos estáticos

```python
# app/main.py (adicionar)

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

## DoD

- [x] Endpoint `/metricas/resumo` funciona
- [x] Dashboard HTML mostra métricas
- [x] Atualização automática a cada 30s
- [x] Filtro por período (1, 7, 30 dias)
- [x] Acessível em `/static/dashboard.html`

---

# S4.E1.2 - Coletar métricas de conversa

## Objetivo

> **Registrar métricas detalhadas de cada conversa.**

**Resultado esperado:** Dados para análise de qualidade e performance.

## Tarefas

### 1. Criar tabela de métricas

```sql
-- migration: criar_tabela_metricas_conversa.sql

CREATE TABLE metricas_conversa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID REFERENCES conversations(id),

    -- Métricas de volume
    total_mensagens_medico INT DEFAULT 0,
    total_mensagens_julia INT DEFAULT 0,
    total_mensagens_humano INT DEFAULT 0,

    -- Métricas de tempo
    tempo_primeira_resposta_segundos FLOAT,
    tempo_medio_resposta_segundos FLOAT,
    duracao_total_minutos FLOAT,

    -- Métricas de resultado
    resultado VARCHAR(50), -- 'vaga_reservada', 'sem_interesse', 'optout', 'em_andamento'
    houve_handoff BOOLEAN DEFAULT FALSE,
    motivo_handoff VARCHAR(100),

    -- Timestamps
    primeira_mensagem_em TIMESTAMPTZ,
    ultima_mensagem_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metricas_conversa_resultado ON metricas_conversa(resultado);
CREATE INDEX idx_metricas_conversa_created ON metricas_conversa(created_at);
```

### 2. Criar serviço de métricas

```python
# app/services/metricas.py

from datetime import datetime
from app.core.supabase import supabase

class MetricasService:

    async def iniciar_metricas_conversa(self, conversa_id: str) -> dict:
        """Cria registro de métricas para nova conversa."""
        return (
            supabase.table("metricas_conversa")
            .insert({
                "conversa_id": conversa_id,
                "primeira_mensagem_em": datetime.utcnow().isoformat()
            })
            .execute()
        ).data[0]

    async def registrar_mensagem(
        self,
        conversa_id: str,
        origem: str,  # 'medico', 'ai', 'humano'
        tempo_resposta_segundos: float = None
    ):
        """Atualiza métricas após cada mensagem."""
        # Buscar métricas existentes
        metricas = (
            supabase.table("metricas_conversa")
            .select("*")
            .eq("conversa_id", conversa_id)
            .single()
            .execute()
        ).data

        if not metricas:
            metricas = await self.iniciar_metricas_conversa(conversa_id)

        # Atualizar contadores
        atualizacao = {
            "ultima_mensagem_em": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        if origem == "medico":
            atualizacao["total_mensagens_medico"] = metricas["total_mensagens_medico"] + 1
        elif origem == "ai":
            atualizacao["total_mensagens_julia"] = metricas["total_mensagens_julia"] + 1
        elif origem == "humano":
            atualizacao["total_mensagens_humano"] = metricas["total_mensagens_humano"] + 1

        # Tempo de resposta
        if tempo_resposta_segundos:
            if metricas["tempo_primeira_resposta_segundos"] is None:
                atualizacao["tempo_primeira_resposta_segundos"] = tempo_resposta_segundos

            # Atualizar média
            total_respostas = metricas["total_mensagens_julia"] + metricas["total_mensagens_humano"]
            if total_respostas > 0:
                media_atual = metricas["tempo_medio_resposta_segundos"] or 0
                nova_media = (media_atual * total_respostas + tempo_resposta_segundos) / (total_respostas + 1)
                atualizacao["tempo_medio_resposta_segundos"] = nova_media

        supabase.table("metricas_conversa").update(atualizacao).eq("id", metricas["id"]).execute()

    async def finalizar_conversa(
        self,
        conversa_id: str,
        resultado: str,
        houve_handoff: bool = False,
        motivo_handoff: str = None
    ):
        """Registra métricas finais da conversa."""
        metricas = (
            supabase.table("metricas_conversa")
            .select("*")
            .eq("conversa_id", conversa_id)
            .single()
            .execute()
        ).data

        if metricas:
            # Calcular duração
            inicio = datetime.fromisoformat(metricas["primeira_mensagem_em"])
            duracao = (datetime.utcnow() - inicio).total_seconds() / 60

            supabase.table("metricas_conversa").update({
                "resultado": resultado,
                "houve_handoff": houve_handoff,
                "motivo_handoff": motivo_handoff,
                "duracao_total_minutos": duracao,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", metricas["id"]).execute()


metricas_service = MetricasService()
```

### 3. Integrar no fluxo

```python
# app/services/agente.py (atualizar)

from app.services.metricas import metricas_service

async def processar_e_responder(conversa, mensagem, contexto):
    inicio = time.time()

    # Registrar mensagem do médico
    await metricas_service.registrar_mensagem(
        conversa_id=conversa["id"],
        origem="medico"
    )

    # Processar e responder...
    resposta = await gerar_resposta(mensagem, contexto)

    tempo_resposta = time.time() - inicio

    # Registrar resposta da Júlia
    await metricas_service.registrar_mensagem(
        conversa_id=conversa["id"],
        origem="ai",
        tempo_resposta_segundos=tempo_resposta
    )

    return resposta
```

## DoD

- [x] Tabela `metricas_conversa` criada (SQL na epic)
- [x] Métricas iniciadas com cada conversa (via serviço)
- [x] Contadores atualizados por mensagem
- [x] Tempo de resposta registrado
- [x] Métricas finalizadas ao encerrar conversa

**Nota:** A tabela `metricas_conversa` precisa ser criada no banco de dados conforme SQL na epic (linhas 206-237).

---

# S4.E1.3 - Coletar métricas de qualidade

## Objetivo

> **Medir qualidade das respostas da Júlia automaticamente.**

**Resultado esperado:** Score de qualidade para cada conversa.

## Tarefas

### 1. Definir métricas de qualidade

```python
# app/services/qualidade.py

from anthropic import Anthropic

client = Anthropic()

async def avaliar_qualidade_conversa(conversa_id: str) -> dict:
    """
    Avalia qualidade de uma conversa usando LLM.

    Critérios:
    - Naturalidade das respostas
    - Consistência da persona
    - Resolução do objetivo
    - Satisfação aparente do médico
    """
    # Buscar interações
    interacoes = (
        supabase.table("interacoes")
        .select("*")
        .eq("conversa_id", conversa_id)
        .order("created_at")
        .execute()
    ).data

    # Montar conversa
    conversa_texto = "\n".join([
        f"{'MÉDICO' if i['direcao'] == 'entrada' else 'JÚLIA'}: {i['conteudo']}"
        for i in interacoes
    ])

    prompt = f"""
Avalie esta conversa entre uma escalista (Júlia) e um médico.

CONVERSA:
{conversa_texto}

Avalie de 1 a 10 nos seguintes critérios:
1. Naturalidade - As respostas parecem de humano?
2. Persona - Manteve tom informal de escalista?
3. Objetivo - Progrediu em direção ao objetivo (oferecer vaga)?
4. Satisfação - O médico parece satisfeito?

Responda em JSON:
{{
    "naturalidade": 1-10,
    "persona": 1-10,
    "objetivo": 1-10,
    "satisfacao": 1-10,
    "score_geral": 1-10,
    "pontos_positivos": ["..."],
    "pontos_negativos": ["..."],
    "sugestoes": ["..."]
}}
"""

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    return json.loads(response.content[0].text)
```

### 2. Salvar avaliação

```python
# app/services/qualidade.py (adicionar)

async def salvar_avaliacao_qualidade(
    conversa_id: str,
    avaliacao: dict
) -> dict:
    """Salva avaliação de qualidade no banco."""
    return (
        supabase.table("avaliacoes_qualidade")
        .insert({
            "conversa_id": conversa_id,
            "naturalidade": avaliacao["naturalidade"],
            "persona": avaliacao["persona"],
            "objetivo": avaliacao["objetivo"],
            "satisfacao": avaliacao["satisfacao"],
            "score_geral": avaliacao["score_geral"],
            "pontos_positivos": avaliacao["pontos_positivos"],
            "pontos_negativos": avaliacao["pontos_negativos"],
            "sugestoes": avaliacao["sugestoes"],
            "avaliador": "auto"  # vs "gestor"
        })
        .execute()
    ).data[0]
```

### 3. Criar tabela de avaliações

```sql
-- migration: criar_tabela_avaliacoes_qualidade.sql

CREATE TABLE avaliacoes_qualidade (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID REFERENCES conversations(id),

    -- Scores
    naturalidade INT CHECK (naturalidade BETWEEN 1 AND 10),
    persona INT CHECK (persona BETWEEN 1 AND 10),
    objetivo INT CHECK (objetivo BETWEEN 1 AND 10),
    satisfacao INT CHECK (satisfacao BETWEEN 1 AND 10),
    score_geral INT CHECK (score_geral BETWEEN 1 AND 10),

    -- Feedback
    pontos_positivos JSONB,
    pontos_negativos JSONB,
    sugestoes JSONB,

    -- Metadata
    avaliador VARCHAR(20) DEFAULT 'auto', -- 'auto' ou 'gestor'
    avaliador_id UUID REFERENCES usuarios(id),
    notas TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_avaliacoes_conversa ON avaliacoes_qualidade(conversa_id);
CREATE INDEX idx_avaliacoes_score ON avaliacoes_qualidade(score_geral);
```

### 4. Agendar avaliação automática

```python
# Job para avaliar conversas encerradas

async def avaliar_conversas_pendentes():
    """
    Avalia conversas que foram encerradas mas não avaliadas.
    Executar via cron diariamente.
    """
    # Conversas encerradas sem avaliação
    response = supabase.rpc(
        "conversas_sem_avaliacao",
        {"limite": 50}
    ).execute()

    for conversa in response.data:
        try:
            avaliacao = await avaliar_qualidade_conversa(conversa["id"])
            await salvar_avaliacao_qualidade(conversa["id"], avaliacao)
        except Exception as e:
            logger.error(f"Erro ao avaliar conversa {conversa['id']}: {e}")
```

## DoD

- [x] Função de avaliação automática funciona
- [x] Critérios de qualidade definidos
- [x] Avaliação salva no banco
- [x] Job de avaliação em batch funciona
- [x] Scores disponíveis no dashboard (via endpoint de métricas)

**Nota:** A tabela `avaliacoes_qualidade` precisa ser criada no banco de dados conforme SQL na epic (linhas 489-518).

---

# S4.E1.4 - Alertas de anomalias

## Objetivo

> **Notificar gestor quando algo anormal acontecer.**

**Resultado esperado:** Alertas no Slack para situações que requerem atenção.

## Tarefas

### 1. Definir thresholds de alerta

```python
# app/services/alertas.py

ALERTAS = {
    "taxa_handoff_alta": {
        "descricao": "Taxa de handoff acima do normal",
        "threshold": 0.20,  # > 20%
        "janela_minutos": 60,
        "severidade": "warning"
    },
    "tempo_resposta_alto": {
        "descricao": "Tempo médio de resposta muito alto",
        "threshold": 120,  # > 120 segundos
        "janela_minutos": 30,
        "severidade": "warning"
    },
    "score_qualidade_baixo": {
        "descricao": "Score de qualidade abaixo do aceitável",
        "threshold": 5,  # < 5/10
        "janela_minutos": 60,
        "severidade": "error"
    },
    "sem_respostas": {
        "descricao": "Nenhuma resposta enviada",
        "threshold": 0,
        "janela_minutos": 30,
        "severidade": "critical"
    },
}
```

### 2. Implementar verificador de alertas

```python
# app/services/alertas.py (adicionar)

from datetime import datetime, timedelta

async def verificar_alertas() -> list[dict]:
    """
    Verifica todas as condições de alerta.

    Returns:
        Lista de alertas ativos
    """
    alertas_ativos = []

    # Taxa de handoff
    alertas_ativos.extend(await verificar_taxa_handoff())

    # Tempo de resposta
    alertas_ativos.extend(await verificar_tempo_resposta())

    # Score de qualidade
    alertas_ativos.extend(await verificar_score_qualidade())

    # Sem respostas
    alertas_ativos.extend(await verificar_atividade())

    return alertas_ativos


async def verificar_taxa_handoff() -> list[dict]:
    """Verifica se taxa de handoff está alta."""
    config = ALERTAS["taxa_handoff_alta"]
    desde = (datetime.now() - timedelta(minutes=config["janela_minutos"])).isoformat()

    # Buscar conversas e handoffs
    conversas = (
        supabase.table("conversations")
        .select("id")
        .gte("created_at", desde)
        .execute()
    ).data

    handoffs = (
        supabase.table("handoffs")
        .select("id")
        .gte("created_at", desde)
        .execute()
    ).data

    if len(conversas) > 0:
        taxa = len(handoffs) / len(conversas)
        if taxa > config["threshold"]:
            return [{
                "tipo": "taxa_handoff_alta",
                "mensagem": f"Taxa de handoff em {taxa*100:.1f}% (threshold: {config['threshold']*100}%)",
                "severidade": config["severidade"],
                "valor": taxa
            }]

    return []
```

### 3. Notificar via Slack

```python
# app/services/alertas.py (adicionar)

CORES_SEVERIDADE = {
    "info": "#2196F3",
    "warning": "#FF9800",
    "error": "#F44336",
    "critical": "#9C27B0",
}

async def enviar_alerta_slack(alerta: dict):
    """Envia alerta para Slack."""
    cor = CORES_SEVERIDADE.get(alerta["severidade"], "#607D8B")

    mensagem = {
        "text": f"⚠️ Alerta: {alerta['tipo']}",
        "attachments": [{
            "color": cor,
            "fields": [
                {"title": "Descrição", "value": alerta["mensagem"], "short": False},
                {"title": "Severidade", "value": alerta["severidade"], "short": True},
                {"title": "Horário", "value": datetime.now().strftime("%H:%M"), "short": True},
            ]
        }]
    }

    await slack_service.enviar_mensagem(mensagem)


async def executar_verificacao_alertas():
    """Job para verificar alertas periodicamente."""
    alertas = await verificar_alertas()

    for alerta in alertas:
        await enviar_alerta_slack(alerta)

        # Salvar no banco para não repetir
        supabase.table("alertas_enviados").insert({
            "tipo": alerta["tipo"],
            "mensagem": alerta["mensagem"],
            "severidade": alerta["severidade"]
        }).execute()
```

## DoD

- [x] Thresholds de alerta definidos
- [x] Verificador de cada tipo de alerta
- [x] Notificação no Slack funciona
- [x] Job de verificação periódica
- [x] Sistema de alertas implementado

**Nota:** A tabela `alertas_enviados` é opcional e pode ser criada posteriormente para histórico.

---

# S4.E1.5 - Relatório diário automático

## Objetivo

> **Enviar resumo diário de métricas para o gestor.**

**Resultado esperado:** Email/Slack com resumo às 8h todo dia.

## Tarefas

### 1. Criar gerador de relatório

```python
# app/services/relatorio.py

from datetime import datetime, timedelta

async def gerar_relatorio_diario() -> dict:
    """Gera relatório do dia anterior."""
    ontem = datetime.now() - timedelta(days=1)
    inicio = ontem.replace(hour=0, minute=0, second=0).isoformat()
    fim = ontem.replace(hour=23, minute=59, second=59).isoformat()

    # Buscar dados
    conversas = (
        supabase.table("conversations")
        .select("*")
        .gte("created_at", inicio)
        .lte("created_at", fim)
        .execute()
    ).data

    interacoes = (
        supabase.table("interacoes")
        .select("*")
        .gte("created_at", inicio)
        .lte("created_at", fim)
        .execute()
    ).data

    handoffs = (
        supabase.table("handoffs")
        .select("*")
        .gte("created_at", inicio)
        .lte("created_at", fim)
        .execute()
    ).data

    avaliacoes = (
        supabase.table("avaliacoes_qualidade")
        .select("score_geral")
        .gte("created_at", inicio)
        .lte("created_at", fim)
        .execute()
    ).data

    # Calcular métricas
    total_conversas = len(conversas)
    total_msgs_recebidas = len([i for i in interacoes if i["direcao"] == "entrada"])
    total_msgs_enviadas = len([i for i in interacoes if i["direcao"] == "saida"])
    total_handoffs = len(handoffs)

    score_medio = 0
    if avaliacoes:
        score_medio = sum(a["score_geral"] for a in avaliacoes) / len(avaliacoes)

    return {
        "data": ontem.strftime("%d/%m/%Y"),
        "conversas": {
            "total": total_conversas,
            "novas": len([c for c in conversas if c["created_at"] >= inicio]),
        },
        "mensagens": {
            "recebidas": total_msgs_recebidas,
            "enviadas": total_msgs_enviadas,
        },
        "handoffs": {
            "total": total_handoffs,
            "taxa": total_handoffs / total_conversas if total_conversas > 0 else 0,
        },
        "qualidade": {
            "score_medio": round(score_medio, 1),
            "avaliacoes": len(avaliacoes),
        }
    }
```

### 2. Formatar para Slack

```python
async def enviar_relatorio_slack(relatorio: dict):
    """Envia relatório formatado para Slack."""
    mensagem = {
        "text": f"📊 Relatório Diário - {relatorio['data']}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📊 Relatório Diário - {relatorio['data']}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Conversas:* {relatorio['conversas']['total']}"},
                    {"type": "mrkdwn", "text": f"*Novas:* {relatorio['conversas']['novas']}"},
                    {"type": "mrkdwn", "text": f"*Msgs Recebidas:* {relatorio['mensagens']['recebidas']}"},
                    {"type": "mrkdwn", "text": f"*Msgs Enviadas:* {relatorio['mensagens']['enviadas']}"},
                ]
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Handoffs:* {relatorio['handoffs']['total']}"},
                    {"type": "mrkdwn", "text": f"*Taxa Handoff:* {relatorio['handoffs']['taxa']*100:.1f}%"},
                    {"type": "mrkdwn", "text": f"*Score Médio:* {relatorio['qualidade']['score_medio']}/10"},
                    {"type": "mrkdwn", "text": f"*Avaliações:* {relatorio['qualidade']['avaliacoes']}"},
                ]
            },
        ]
    }

    await slack_service.enviar_mensagem(mensagem)
```

### 3. Agendar envio

```python
# Configurar cron para 8h

# Em produção, usar APScheduler ou cron do sistema
# Exemplo com APScheduler:

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=8, minute=0)
async def job_relatorio_diario():
    """Envia relatório diário às 8h."""
    try:
        relatorio = await gerar_relatorio_diario()
        await enviar_relatorio_slack(relatorio)
        logger.info("Relatório diário enviado")
    except Exception as e:
        logger.error(f"Erro ao enviar relatório: {e}")

# Iniciar scheduler
scheduler.start()
```

## DoD

- [x] Gerador de relatório funciona
- [x] Relatório inclui todas as métricas principais
- [x] Formatação para Slack legível
- [x] Job de envio criado (executar via cron às 8h)
- [x] Erro no envio não quebra sistema
