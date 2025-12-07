# Epic 05: Reports Múltiplos no Slack

## Prioridade: P1 (Importante)

## Objetivo

> **Enviar reports para o Slack em 4 horários diários + report semanal, conforme documentado.**

Documentado em `docs/FLUXOS.md` - Fluxo 9: Report para Gestor.

---

## Referência: FLUXOS.md

```
Horários:
• 10:00 - manhã
• 13:00 - almoço
• 17:00 - tarde
• 20:00 - fim do dia
• Seg 09:00 - semanal
```

---

## Problema Atual

- Existe apenas job `relatorio_diario` às 8h
- Faltam reports múltiplos por dia
- Falta report semanal

---

## Stories

---

# S7.E5.1 - Criar job de report periódico

## Objetivo

> **Criar função que gera report com métricas do período.**

## Código Esperado

**Arquivo:** `app/services/relatorio.py` (adicionar)

```python
from datetime import datetime, timedelta
from app.services.supabase import supabase
from app.services.slack import enviar_slack
import logging

logger = logging.getLogger(__name__)


async def gerar_report_periodo(tipo: str = "manha") -> dict:
    """
    Gera report de métricas para o período especificado.

    Args:
        tipo: 'manha' (desde 00h), 'almoco' (desde 10h),
              'tarde' (desde 13h), 'fim_dia' (desde 17h)

    Returns:
        dict com métricas do período
    """
    # Definir período
    agora = datetime.utcnow()
    periodos = {
        "manha": agora.replace(hour=0, minute=0, second=0),
        "almoco": agora.replace(hour=10, minute=0, second=0),
        "tarde": agora.replace(hour=13, minute=0, second=0),
        "fim_dia": agora.replace(hour=17, minute=0, second=0),
    }
    inicio = periodos.get(tipo, periodos["manha"])

    # Coletar métricas
    metricas = await _coletar_metricas(inicio, agora)

    # Buscar destaques
    destaques = await _buscar_destaques(inicio, agora)

    return {
        "periodo": tipo,
        "inicio": inicio.isoformat(),
        "fim": agora.isoformat(),
        "metricas": metricas,
        "destaques": destaques
    }


async def _coletar_metricas(inicio: datetime, fim: datetime) -> dict:
    """Coleta métricas do período."""

    # Mensagens enviadas
    enviadas = await supabase.table("interacoes").select(
        "id", count="exact"
    ).eq("direcao", "saida").gte(
        "created_at", inicio.isoformat()
    ).lte("created_at", fim.isoformat()).execute()

    # Mensagens recebidas (respostas)
    recebidas = await supabase.table("interacoes").select(
        "id", count="exact"
    ).eq("direcao", "entrada").gte(
        "created_at", inicio.isoformat()
    ).lte("created_at", fim.isoformat()).execute()

    # Plantões fechados
    plantoes = await supabase.table("vagas").select(
        "id", count="exact"
    ).eq("status", "reservada").gte(
        "reservada_em", inicio.isoformat()
    ).lte("reservada_em", fim.isoformat()).execute()

    # Handoffs
    handoffs = await supabase.table("handoffs").select(
        "id", count="exact"
    ).gte("created_at", inicio.isoformat()
    ).lte("created_at", fim.isoformat()).execute()

    total_enviadas = enviadas.count or 0
    total_recebidas = recebidas.count or 0
    taxa_resposta = (total_recebidas / total_enviadas * 100) if total_enviadas > 0 else 0

    return {
        "msgs_enviadas": total_enviadas,
        "msgs_recebidas": total_recebidas,
        "taxa_resposta": round(taxa_resposta, 1),
        "plantoes_fechados": plantoes.count or 0,
        "handoffs": handoffs.count or 0
    }


async def _buscar_destaques(inicio: datetime, fim: datetime) -> list:
    """Busca eventos destacados do período."""
    destaques = []

    # Plantões fechados (detalhes)
    plantoes = await supabase.table("vagas").select(
        "*, clientes(primeiro_nome), hospitais(nome)"
    ).eq("status", "reservada").gte(
        "reservada_em", inicio.isoformat()
    ).execute()

    for p in plantoes.data or []:
        medico = p.get("clientes", {}).get("primeiro_nome", "Médico")
        hospital = p.get("hospitais", {}).get("nome", "Hospital")
        destaques.append({
            "tipo": "plantao_fechado",
            "icone": "✅",
            "texto": f"{medico} fechou vaga no {hospital}"
        })

    # Handoffs
    handoffs = await supabase.table("handoffs").select(
        "*, clientes:conversa_id(cliente_id(primeiro_nome))"
    ).gte("created_at", inicio.isoformat()
    ).is_("resolvido_em", "null").execute()

    for h in handoffs.data or []:
        motivo = h.get("motivo", "")[:50]
        destaques.append({
            "tipo": "handoff",
            "icone": "⚠️",
            "texto": f"Handoff: {motivo}"
        })

    return destaques[:5]  # Máximo 5 destaques


async def enviar_report_slack(report: dict):
    """Formata e envia report para Slack."""
    metricas = report["metricas"]
    destaques = report["destaques"]

    # Títulos por período
    titulos = {
        "manha": "📊 Júlia - Report Manhã",
        "almoco": "📊 Júlia - Report Almoço",
        "tarde": "📊 Júlia - Report Tarde",
        "fim_dia": "📊 Júlia - Report Fim do Dia",
        "semanal": "📈 Júlia - Report Semanal"
    }

    # Montar blocos Slack
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": titulos.get(report["periodo"], "📊 Report")}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Mensagens:* {metricas['msgs_enviadas']} enviadas"},
                {"type": "mrkdwn", "text": f"*Respostas:* {metricas['msgs_recebidas']} ({metricas['taxa_resposta']}%)"},
                {"type": "mrkdwn", "text": f"*Plantões:* {metricas['plantoes_fechados']} fechados"},
                {"type": "mrkdwn", "text": f"*Handoffs:* {metricas['handoffs']}"},
            ]
        }
    ]

    # Adicionar destaques
    if destaques:
        destaque_text = "\n".join([f"{d['icone']} {d['texto']}" for d in destaques])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Destaques:*\n{destaque_text}"}
        })

    await enviar_slack({"blocks": blocks})
    logger.info(f"Report {report['periodo']} enviado para Slack")
```

## Critérios de Aceite

1. **4 períodos:** Manhã, almoço, tarde, fim do dia
2. **Métricas corretas:** Conta apenas no período
3. **Destaques:** Mostra plantões fechados e handoffs
4. **Formato Slack:** Usa blocks para melhor visualização

## DoD

- [x] `gerar_report_periodo()` implementada
- [x] `_coletar_metricas()` conta corretamente
- [x] `_buscar_destaques()` lista eventos importantes
- [x] `enviar_report_slack()` formata bonito
- [x] Teste: cada período gera métricas corretas

**NOTA:** Implementado em `app/services/relatorio.py` - funcoes `gerar_report_periodo()`, `_coletar_metricas_periodo()`, `_buscar_destaques_periodo()`, `enviar_report_periodo_slack()`.

---

# S7.E5.2 - Criar report semanal

## Objetivo

> **Report consolidado da semana enviado segunda às 9h.**

## Código Esperado

**Arquivo:** `app/services/relatorio.py` (adicionar)

```python
async def gerar_report_semanal() -> dict:
    """
    Gera report consolidado da semana anterior.

    Enviado toda segunda-feira às 9h.
    """
    agora = datetime.utcnow()

    # Semana anterior (segunda a domingo)
    dias_desde_segunda = agora.weekday()  # 0 = segunda
    inicio_semana = agora - timedelta(days=dias_desde_segunda + 7)
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0)
    fim_semana = inicio_semana + timedelta(days=7)

    # Métricas da semana
    metricas = await _coletar_metricas(inicio_semana, fim_semana)

    # Métricas adicionais para semanal
    metricas_extras = await _coletar_metricas_semanais(inicio_semana, fim_semana)

    # Top objeções
    objecoes = await _analisar_objecoes(inicio_semana, fim_semana)

    return {
        "periodo": "semanal",
        "semana": inicio_semana.strftime("%d/%m") + " - " + fim_semana.strftime("%d/%m"),
        "metricas": {**metricas, **metricas_extras},
        "objecoes": objecoes
    }


async def _coletar_metricas_semanais(inicio: datetime, fim: datetime) -> dict:
    """Métricas adicionais para report semanal."""

    # Médicos contatados (únicos)
    contatados = await supabase.table("interacoes").select(
        "cliente_id"
    ).eq("tipo", "abertura").gte(
        "created_at", inicio.isoformat()
    ).execute()
    unicos = len(set(c["cliente_id"] for c in contatados.data or []))

    # Conversões (responderam → fecharam)
    responderam = await supabase.table("conversations").select(
        "id", count="exact"
    ).in_("stage", ["respondeu", "qualificado", "fechou"]).gte(
        "updated_at", inicio.isoformat()
    ).execute()

    return {
        "medicos_contatados": unicos,
        "conversoes": responderam.count or 0
    }


async def _analisar_objecoes(inicio: datetime, fim: datetime) -> list:
    """Analisa principais objeções da semana."""
    # Buscar mensagens com objeções comuns
    objecoes_keywords = {
        "valor": ["valor baixo", "pouco", "não compensa", "paga mal"],
        "disponibilidade": ["não posso", "ocupado", "sem tempo", "agenda cheia"],
        "distancia": ["longe", "distante", "não é perto"],
        "outra_empresa": ["já trabalho", "outra empresa", "concorrente"]
    }

    # Simplificado: retorna placeholder
    # Em produção, analisar mensagens com LLM
    return [
        {"objecao": "Valor baixo", "percentual": 34},
        {"objecao": "Sem disponibilidade", "percentual": 28},
        {"objecao": "Hospital longe", "percentual": 18},
    ]


async def enviar_report_semanal_slack(report: dict):
    """Formata e envia report semanal para Slack."""
    metricas = report["metricas"]
    objecoes = report["objecoes"]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📈 Júlia - Report Semanal ({report['semana']})"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*FUNIL*"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"├── Contatados: {metricas['medicos_contatados']}"},
                {"type": "mrkdwn", "text": f"├── Responderam: {metricas['msgs_recebidas']} ({metricas['taxa_resposta']}%)"},
                {"type": "mrkdwn", "text": f"├── Conversões: {metricas['conversoes']}"},
                {"type": "mrkdwn", "text": f"└── Plantões: {metricas['plantoes_fechados']}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*TOP OBJEÇÕES*"}
        }
    ]

    # Adicionar objeções
    objecao_text = "\n".join([f"├── {o['objecao']}: {o['percentual']}%" for o in objecoes])
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": objecao_text}
    })

    await enviar_slack({"blocks": blocks})
    logger.info("Report semanal enviado para Slack")
```

## DoD

- [x] `gerar_report_semanal()` implementada
- [x] Calcula métricas da semana anterior
- [x] Inclui análise de objeções
- [x] Formato Slack bonito com funil
- [x] Teste: segunda gera report da semana anterior

**NOTA:** Implementado em `app/services/relatorio.py` - funcoes `gerar_report_semanal()`, `_coletar_metricas_semanais()`, `_analisar_objecoes()`, `enviar_report_semanal_slack()`.

---

# S7.E5.3 - Configurar jobs no scheduler

## Objetivo

> **Adicionar jobs de report nos horários corretos.**

## Código Esperado

**Arquivo:** `app/workers/scheduler.py` (modificar)

```python
JOBS = [
    # ... jobs existentes ...

    # Reports periódicos
    {
        "name": "report_manha",
        "endpoint": "/jobs/report-periodo?tipo=manha",
        "schedule": "0 10 * * *",  # 10h todos os dias
    },
    {
        "name": "report_almoco",
        "endpoint": "/jobs/report-periodo?tipo=almoco",
        "schedule": "0 13 * * *",  # 13h todos os dias
    },
    {
        "name": "report_tarde",
        "endpoint": "/jobs/report-periodo?tipo=tarde",
        "schedule": "0 17 * * *",  # 17h todos os dias
    },
    {
        "name": "report_fim_dia",
        "endpoint": "/jobs/report-periodo?tipo=fim_dia",
        "schedule": "0 20 * * *",  # 20h todos os dias
    },
    {
        "name": "report_semanal",
        "endpoint": "/jobs/report-semanal",
        "schedule": "0 9 * * 1",  # Segunda às 9h
    },
]
```

**Arquivo:** `app/api/routes/jobs.py` (adicionar)

```python
@router.post("/report-periodo")
async def job_report_periodo(tipo: str = "manha"):
    """Gera e envia report do período."""
    from app.services.relatorio import gerar_report_periodo, enviar_report_slack
    report = await gerar_report_periodo(tipo)
    await enviar_report_slack(report)
    return {"status": "ok", "periodo": tipo}


@router.post("/report-semanal")
async def job_report_semanal():
    """Gera e envia report semanal."""
    from app.services.relatorio import gerar_report_semanal, enviar_report_semanal_slack
    report = await gerar_report_semanal()
    await enviar_report_semanal_slack(report)
    return {"status": "ok", "semana": report["semana"]}
```

## DoD

- [x] 4 jobs de report diário configurados (10h, 13h, 17h, 20h)
- [x] 1 job de report semanal (segunda 9h)
- [x] Endpoints funcionam quando chamados
- [x] Slack recebe mensagens formatadas

**NOTA:** Jobs adicionados em `app/workers/scheduler.py` (report_manha, report_almoco, report_tarde, report_fim_dia, report_semanal). Endpoints `/jobs/report-periodo` e `/jobs/report-semanal` em `app/api/routes/jobs.py`.

---

## Resumo do Epic

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S7.E5.1 | Report periódico | Alta |
| S7.E5.2 | Report semanal | Média |
| S7.E5.3 | Jobs no scheduler | Baixa |

## Arquivos Modificados

| Arquivo | Ação |
|---------|------|
| `app/services/relatorio.py` | Adicionar funções de report |
| `app/workers/scheduler.py` | Adicionar 5 jobs |
| `app/api/routes/jobs.py` | Adicionar 2 endpoints |
