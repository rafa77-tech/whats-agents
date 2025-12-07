# Epic 06: Métrica de Detecção como Bot

## Prioridade: P2 (Melhoria)

## Objetivo

> **Registrar e monitorar quando médicos percebem que estão falando com uma IA.**

Documentado em `docs/METRICAS_MVP.md` - Meta: taxa de detecção < 5%.

---

## Referência: METRICAS_MVP.md

```
Taxa de detecção como bot | < 5% | `detectados / conversas`

Como medir detecção:
- Médico menciona: "bot", "robô", "IA", "automático"
- Médico pergunta: "isso é automático?", "tô falando com máquina?"
- Flag manual pelo gestor ao revisar conversas
```

---

## Problema Atual

- Detecção existe em `handoff_detector.py` para trigger de handoff
- Mas **não está sendo logada como métrica separada**
- Não há dashboard/report mostrando taxa de detecção

---

## Stories

---

# S7.E6.1 - Criar função de detecção de bot

## Objetivo

> **Função dedicada para detectar quando médico percebe que é bot.**

## Código Esperado

**Arquivo:** `app/services/deteccao_bot.py` (criar)

```python
import re
import logging
from datetime import datetime
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Padrões que indicam detecção como bot
PADROES_DETECCAO = [
    # Menções diretas
    r"\bbot\b",
    r"\brob[oô]\b",
    r"\bia\b",
    r"\bintelig[eê]ncia artificial\b",
    r"\bautom[aá]tico\b",
    r"\bmáquina\b",
    r"\balgoritmo\b",
    r"\bchatbot\b",

    # Perguntas suspeitas
    r"isso [eé] autom[aá]tico",
    r"[eé] um? bot",
    r"[eé] uma? ia",
    r"t[oô] falando com (uma? )?(m[aá]quina|rob[oô]|bot)",
    r"voc[eê] [eé] (uma? )?(m[aá]quina|rob[oô]|bot|ia)",
    r"[eé] (uma? )?pessoa (real|de verdade)",
    r"tem (algu[eé]m|gente) a[ií]",
    r"falar com (uma? )?pessoa",
    r"atendente (humano|real)",
    r"resposta autom[aá]tica",
    r"mensagem autom[aá]tica",
]

# Compilar regex para performance
_padroes_compilados = [re.compile(p, re.IGNORECASE) for p in PADROES_DETECCAO]


def detectar_mencao_bot(mensagem: str) -> dict:
    """
    Detecta se mensagem indica que médico percebeu que é bot.

    Args:
        mensagem: Texto da mensagem do médico

    Returns:
        dict com:
        - detectado: bool
        - padrao: str (qual padrão matchou)
        - trecho: str (parte da mensagem que matchou)
    """
    mensagem_limpa = mensagem.lower().strip()

    for padrao in _padroes_compilados:
        match = padrao.search(mensagem_limpa)
        if match:
            return {
                "detectado": True,
                "padrao": padrao.pattern,
                "trecho": match.group(0)
            }

    return {
        "detectado": False,
        "padrao": None,
        "trecho": None
    }


async def registrar_deteccao_bot(
    cliente_id: str,
    conversa_id: str,
    mensagem: str,
    padrao: str,
    trecho: str
):
    """
    Registra detecção de bot na tabela de métricas.

    Args:
        cliente_id: ID do médico
        conversa_id: ID da conversa
        mensagem: Mensagem completa do médico
        padrao: Padrão regex que matchou
        trecho: Trecho específico que indicou detecção
    """
    try:
        await supabase.table("metricas_deteccao_bot").insert({
            "cliente_id": cliente_id,
            "conversa_id": conversa_id,
            "mensagem": mensagem[:500],  # Limitar tamanho
            "padrao_detectado": padrao,
            "trecho": trecho,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        logger.warning(
            f"DETECÇÃO BOT: cliente={cliente_id}, trecho='{trecho}'"
        )

    except Exception as e:
        logger.error(f"Erro ao registrar detecção bot: {e}")


async def calcular_taxa_deteccao(dias: int = 7) -> dict:
    """
    Calcula taxa de detecção como bot nos últimos N dias.

    Returns:
        dict com:
        - total_conversas: int
        - deteccoes: int
        - taxa_percentual: float
    """
    desde = datetime.utcnow() - timedelta(days=dias)

    # Total de conversas no período
    conversas = await supabase.table("conversations").select(
        "id", count="exact"
    ).gte("created_at", desde.isoformat()).execute()

    # Total de detecções no período
    deteccoes = await supabase.table("metricas_deteccao_bot").select(
        "id", count="exact"
    ).gte("created_at", desde.isoformat()).execute()

    total = conversas.count or 0
    det = deteccoes.count or 0
    taxa = (det / total * 100) if total > 0 else 0

    return {
        "total_conversas": total,
        "deteccoes": det,
        "taxa_percentual": round(taxa, 2),
        "periodo_dias": dias
    }
```

## Critérios de Aceite

1. **Padrões abrangentes:** Cobre "bot", "robô", "IA", perguntas, etc
2. **Case insensitive:** Funciona com maiúsculas/minúsculas
3. **Retorna contexto:** Indica qual padrão e trecho matchou
4. **Performance:** Regex pré-compilado

## DoD

- [x] Arquivo `app/services/deteccao_bot.py` criado
- [x] Função `detectar_mencao_bot()` implementada
- [x] 15+ padrões de detecção configurados (37 padrões)
- [x] Função `registrar_deteccao_bot()` salva no banco
- [x] Função `calcular_taxa_deteccao()` calcula métrica
- [x] Teste: "isso é um bot?" → detectado=True

**NOTA:** Implementado em `app/services/deteccao_bot.py` com 37 padrões regex compilados.

---

# S7.E6.2 - Criar tabela de métricas

## Objetivo

> **Criar tabela no Supabase para armazenar detecções.**

## Código Esperado

**Migration SQL:**

```sql
-- Tabela para registrar detecções de bot
CREATE TABLE IF NOT EXISTS metricas_deteccao_bot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID REFERENCES clientes(id),
    conversa_id UUID REFERENCES conversations(id),
    mensagem TEXT,
    padrao_detectado TEXT,
    trecho TEXT,
    revisado_por TEXT,  -- Para revisão manual do gestor
    falso_positivo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para queries
CREATE INDEX idx_deteccao_bot_cliente ON metricas_deteccao_bot(cliente_id);
CREATE INDEX idx_deteccao_bot_data ON metricas_deteccao_bot(created_at);
```

## DoD

- [x] Tabela `metricas_deteccao_bot` criada
- [x] Campos: cliente_id, conversa_id, mensagem, padrao, trecho
- [x] Campo `falso_positivo` para revisão manual
- [x] Índices criados para performance

**NOTA:** Migration aplicada via Supabase MCP.

---

# S7.E6.3 - Integrar detecção no webhook

## Objetivo

> **Verificar detecção em toda mensagem recebida e registrar.**

## Código Esperado

**Arquivo:** `app/api/routes/webhook.py` (modificar)

```python
from app.services.deteccao_bot import detectar_mencao_bot, registrar_deteccao_bot

async def processar_mensagem(mensagem: str, medico: dict, conversa: dict):
    """Processa mensagem recebida."""

    # ... código existente ...

    # VERIFICAR DETECÇÃO DE BOT (novo)
    deteccao = detectar_mencao_bot(mensagem)
    if deteccao["detectado"]:
        await registrar_deteccao_bot(
            cliente_id=medico["id"],
            conversa_id=conversa["id"],
            mensagem=mensagem,
            padrao=deteccao["padrao"],
            trecho=deteccao["trecho"]
        )
        # NÃO bloqueia processamento, apenas registra

    # ... continua processamento normal ...
```

## DoD

- [x] Toda mensagem recebida passa por `detectar_mencao_bot()`
- [x] Detecções são registradas automaticamente
- [x] Processamento continua normalmente (não bloqueia)
- [x] Log de warning quando detectado

**NOTA:** Integrado em `app/api/routes/webhook.py` linha 145-157.

---

# S7.E6.4 - Adicionar métrica no report

## Objetivo

> **Incluir taxa de detecção nos reports do Slack.**

## Código Esperado

**Arquivo:** `app/services/relatorio.py` (modificar)

```python
async def _coletar_metricas(inicio: datetime, fim: datetime) -> dict:
    """Coleta métricas do período."""

    # ... métricas existentes ...

    # Taxa de detecção como bot (nova)
    from app.services.deteccao_bot import calcular_taxa_deteccao

    deteccao = await calcular_taxa_deteccao(dias=1)  # Último dia

    return {
        # ... outras métricas ...
        "deteccao_bot": deteccao["taxa_percentual"],
        "deteccoes_total": deteccao["deteccoes"]
    }
```

**No formato do report:**

```python
blocks.append({
    "type": "section",
    "fields": [
        # ... outros campos ...
        {"type": "mrkdwn", "text": f"*Detecção bot:* {metricas['deteccao_bot']}% ({metricas['deteccoes_total']} casos)"},
    ]
})
```

## DoD

- [x] Report diário inclui taxa de detecção
- [x] Report semanal inclui taxa de detecção
- [x] Formato: "X% (N casos)"
- [x] Alerta visual se taxa > 5%

**NOTA:** Implementado em `app/services/relatorio.py` - `_coletar_metricas_periodo()`, `enviar_report_periodo_slack()` e `enviar_report_semanal_slack()`.

---

## Resumo do Epic

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S7.E6.1 | Função de detecção | Média |
| S7.E6.2 | Tabela de métricas | Baixa |
| S7.E6.3 | Integrar no webhook | Baixa |
| S7.E6.4 | Adicionar no report | Baixa |

## Arquivos Criados/Modificados

| Arquivo | Ação |
|---------|------|
| `app/services/deteccao_bot.py` | Criar |
| `migrations/xxx_deteccao_bot.sql` | Criar |
| `app/api/routes/webhook.py` | Modificar |
| `app/services/relatorio.py` | Modificar |

## Dashboard de Monitoramento

```
Métricas de Detecção (últimos 7 dias):
- Total conversas: 150
- Detecções: 3
- Taxa: 2.0% ✅ (meta < 5%)

Casos recentes:
1. Dr. Carlos: "isso é um bot?"
2. Dra. Ana: "tô falando com máquina?"
3. Dr. João: "resposta muito automática"
```
