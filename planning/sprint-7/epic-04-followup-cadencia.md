# Epic 04: Follow-up com Cadência Correta

## Prioridade: P1 (Importante)

## Objetivo

> **Garantir que follow-ups automáticos seguem a cadência documentada: 48h → 5d → 15d → pausa 60d.**

Documentado em `docs/FLUXOS.md` - Fluxo 8: Follow-ups Automáticos.

---

## Referência: FLUXOS.md

```
CADÊNCIA:

  Abertura
      │
      ├── 48h ──▶ Follow-up 1: "Oi de novo! Viu minha msg?"
      │
      ├── 5d ───▶ Follow-up 2: "Surgiu uma vaga que lembrei de vc"
      │                         (inclui vaga real)
      │
      ├── 15d ──▶ Follow-up 3: "Última tentativa! Se não tiver
      │                         interesse, sem problema"
      │
      └── FIM ──▶ stage = 'nao_respondeu'
                  Pausa 60 dias
```

---

## Problema Atual

- Job `followup_diario` existe em `scheduler.py`
- Configuração existe em `app/config/followup.py`
- **Validar:** A lógica segue exatamente a cadência?
- **Validar:** Pausa de 60 dias é respeitada?

---

## Stories

---

# S7.E4.1 - Validar/corrigir configuração de cadência

## Objetivo

> **Garantir que as regras de follow-up estão configuradas corretamente.**

## Código Esperado

**Arquivo:** `app/config/followup.py` (validar/corrigir)

```python
from datetime import timedelta

# Cadência de follow-ups (conforme docs/FLUXOS.md)
FOLLOWUP_CONFIG = {
    # Follow-up 1: 48 horas após última mensagem
    "followup_1": {
        "delay": timedelta(hours=48),
        "stage_anterior": "msg_enviada",  # Após mensagem inicial
        "stage_proximo": "followup_1_enviado",
        "tipo_mensagem": "lembrete_simples",
        "incluir_vaga": False,
        "template_hint": "Oi de novo! Viu minha msg?"
    },

    # Follow-up 2: 5 dias após follow-up 1
    "followup_2": {
        "delay": timedelta(days=5),
        "stage_anterior": "followup_1_enviado",
        "stage_proximo": "followup_2_enviado",
        "tipo_mensagem": "oferta_vaga",
        "incluir_vaga": True,  # IMPORTANTE: Inclui vaga real
        "template_hint": "Lembrei de vc pq surgiu uma vaga boa..."
    },

    # Follow-up 3 (último): 15 dias após follow-up 2
    "followup_3": {
        "delay": timedelta(days=15),
        "stage_anterior": "followup_2_enviado",
        "stage_proximo": "nao_respondeu",
        "tipo_mensagem": "ultima_tentativa",
        "incluir_vaga": False,
        "template_hint": "Última msg, prometo! Se não tiver interesse..."
    }
}

# Pausa após esgotar follow-ups
PAUSA_APOS_NAO_RESPOSTA = timedelta(days=60)

# Stages que indicam que conversa está ativa (não fazer follow-up)
STAGES_ATIVOS = [
    "respondeu",
    "qualificado",
    "negociando",
    "fechou",
    "optout"
]

# Stages elegíveis para follow-up
STAGES_FOLLOWUP = [
    "msg_enviada",
    "followup_1_enviado",
    "followup_2_enviado"
]
```

## Critérios de Aceite

1. **Delays corretos:** 48h, 5d, 15d conforme documentação
2. **Transição de stages:** Cada follow-up avança o stage
3. **Follow-up 2 com vaga:** Flag `incluir_vaga=True`
4. **Pausa 60 dias:** Constante definida
5. **Stages excluídos:** Não faz follow-up se médico respondeu

## DoD

- [x] Arquivo `app/config/followup.py` revisado
- [x] Delays: 48h → 5d → 15d corretos
- [x] Flag `incluir_vaga` no follow-up 2
- [x] `PAUSA_APOS_NAO_RESPOSTA = 60 dias`
- [x] Lista de stages excluídos do follow-up

**NOTA:** Reescrito `app/config/followup.py` com nova estrutura `FOLLOWUP_CONFIG` usando stages e timedelta.

---

# S7.E4.2 - Implementar/validar serviço de follow-up

## Objetivo

> **Serviço que identifica conversas elegíveis e agenda follow-ups.**

## Código Esperado

**Arquivo:** `app/services/followup.py` (validar/completar)

```python
from datetime import datetime, timedelta
from app.config.followup import FOLLOWUP_CONFIG, PAUSA_APOS_NAO_RESPOSTA, STAGES_FOLLOWUP
from app.services.supabase import supabase
from app.services.fila_mensagens import enfileirar_mensagem
from app.services.vaga import buscar_vagas_compativeis
import logging

logger = logging.getLogger(__name__)


async def processar_followups_pendentes() -> dict:
    """
    Processa todas as conversas que precisam de follow-up.

    Returns:
        dict com estatísticas de processamento
    """
    stats = {
        "processadas": 0,
        "followups_agendados": 0,
        "erros": 0
    }

    for stage in STAGES_FOLLOWUP:
        config = _get_config_para_stage(stage)
        if not config:
            continue

        # Buscar conversas no stage, sem resposta há X tempo
        conversas = await _buscar_conversas_para_followup(stage, config["delay"])

        for conversa in conversas:
            try:
                await _agendar_followup(conversa, config)
                stats["followups_agendados"] += 1
            except Exception as e:
                logger.error(f"Erro ao agendar follow-up: {e}")
                stats["erros"] += 1

            stats["processadas"] += 1

    logger.info(f"Follow-ups processados: {stats}")
    return stats


def _get_config_para_stage(stage: str) -> dict | None:
    """Retorna configuração de follow-up para o stage."""
    for key, config in FOLLOWUP_CONFIG.items():
        if config["stage_anterior"] == stage:
            return {"key": key, **config}
    return None


async def _buscar_conversas_para_followup(stage: str, delay: timedelta) -> list:
    """
    Busca conversas no stage especificado, sem atividade há mais de delay.

    Critérios:
    - Stage correto
    - Última mensagem há mais de delay
    - Não em pausa
    - controlled_by = 'ai'
    """
    cutoff = datetime.utcnow() - delay

    response = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("stage", stage)
        .eq("controlled_by", "ai")
        .lte("ultima_mensagem_em", cutoff.isoformat())
        .is_("pausado_ate", "null")  # Não pausado
        .limit(50)  # Processar em lotes
        .execute()
    )

    return response.data or []


async def _agendar_followup(conversa: dict, config: dict):
    """
    Agenda mensagem de follow-up para a conversa.
    """
    medico = conversa.get("clientes", {})

    # Gerar mensagem de follow-up
    if config.get("incluir_vaga"):
        # Follow-up 2: inclui vaga real
        mensagem = await _gerar_followup_com_vaga(medico, config)
    else:
        mensagem = await _gerar_followup_simples(medico, config)

    # Enfileirar
    await enfileirar_mensagem(
        cliente_id=conversa["cliente_id"],
        conversa_id=conversa["id"],
        conteudo=mensagem,
        tipo=f"followup_{config['key']}",
        prioridade=5
    )

    # Atualizar stage da conversa
    await supabase.table("conversations").update({
        "stage": config["stage_proximo"],
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", conversa["id"]).execute()

    logger.info(f"Follow-up {config['key']} agendado para conversa {conversa['id']}")


async def _gerar_followup_simples(medico: dict, config: dict) -> str:
    """Gera mensagem de follow-up sem vaga específica."""
    nome = medico.get("primeiro_nome", "")

    templates = {
        "followup_1": [
            f"Oi {nome}! Tudo bem?\n\nMandei uma msg outro dia, não sei se vc viu",
            f"Oi de novo {nome}!\n\nViu minha msg? To com vagas legais aqui",
            f"E aí {nome}! Sumiu rs\n\nAinda tenho vagas boas, se tiver interesse"
        ],
        "followup_3": [
            f"Oi {nome}! Última msg, prometo rs\n\nSe não tiver interesse em plantões agora, sem problema!\n\nMas se quiser, é só me chamar",
            f"{nome}, vou parar de insistir rs\n\nSe mudar de ideia sobre plantões, to aqui!",
        ]
    }

    import random
    msgs = templates.get(config["key"], [config.get("template_hint", "Oi!")])
    return random.choice(msgs)


async def _gerar_followup_com_vaga(medico: dict, config: dict) -> str:
    """Gera follow-up incluindo uma vaga real."""
    nome = medico.get("primeiro_nome", "")
    especialidade_id = medico.get("especialidade_id")

    if not especialidade_id:
        return await _gerar_followup_simples(medico, config)

    # Buscar vaga real
    vagas = await buscar_vagas_compativeis(
        especialidade_id=especialidade_id,
        cliente_id=medico.get("id"),
        limite=1
    )

    if not vagas:
        return await _gerar_followup_simples(medico, config)

    vaga = vagas[0]
    hospital = vaga.get("hospitais", {}).get("nome", "hospital")
    data = vaga.get("data_plantao", "")
    periodo = vaga.get("periodos", {}).get("nome", "")
    valor = vaga.get("valor_min", 0)

    return (
        f"Oi {nome}!\n\n"
        f"Lembrei de vc pq surgiu uma vaga boa\n\n"
        f"{hospital}, {data}, {periodo}\n"
        f"R$ {valor:,.0f}\n\n"
        f"Tem interesse?"
    )
```

## Critérios de Aceite

1. **Busca correta:** Encontra conversas no stage certo, sem atividade há delay
2. **Não processa pausados:** Conversas pausadas são ignoradas
3. **Não processa humano:** `controlled_by='ai'` obrigatório
4. **Atualiza stage:** Conversa avança para próximo stage
5. **Follow-up 2 com vaga:** Inclui vaga real quando aplicável
6. **Templates variados:** Mensagens diferentes para evitar repetição

## DoD

- [x] `processar_followups_pendentes()` implementada
- [x] Busca respeita delay de cada follow-up
- [x] Follow-up 2 inclui vaga real do banco
- [x] Stage atualizado após agendar follow-up
- [x] Templates variados para parecer natural
- [x] Teste: conversa 48h sem resposta → follow-up 1 agendado

**NOTA:** Implementado em `app/services/followup.py` - `processar_followups_pendentes()` processa stages com cadência correta, `_gerar_followup_com_vaga()` inclui vaga real.

---

# S7.E4.3 - Implementar pausa de 60 dias

## Objetivo

> **Após follow-up 3, pausar conversa por 60 dias antes de retomar.**

## Código Esperado

**Arquivo:** `app/services/followup.py` (adicionar)

```python
async def processar_pausas_expiradas() -> dict:
    """
    Reativa conversas cuja pausa de 60 dias expirou.

    Conversas em stage 'nao_respondeu' com pausa expirada
    voltam para 'novo' para serem prospectadas novamente.
    """
    stats = {"reativadas": 0}

    # Buscar conversas com pausa expirada
    response = (
        supabase.table("conversations")
        .select("id, cliente_id")
        .eq("stage", "nao_respondeu")
        .lte("pausado_ate", datetime.utcnow().isoformat())
        .limit(50)
        .execute()
    )

    for conversa in response.data or []:
        await supabase.table("conversations").update({
            "stage": "recontato",  # Novo stage para segunda tentativa
            "pausado_ate": None,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversa["id"]).execute()

        logger.info(f"Conversa {conversa['id']} reativada após pausa de 60 dias")
        stats["reativadas"] += 1

    return stats


async def aplicar_pausa_60_dias(conversa_id: str):
    """
    Aplica pausa de 60 dias em conversa que não respondeu.

    Chamado quando conversa atinge stage 'nao_respondeu'.
    """
    pausa_ate = datetime.utcnow() + PAUSA_APOS_NAO_RESPOSTA

    await supabase.table("conversations").update({
        "pausado_ate": pausa_ate.isoformat()
    }).eq("id", conversa_id).execute()

    logger.info(f"Conversa {conversa_id} pausada até {pausa_ate.date()}")
```

## Critérios de Aceite

1. **Pausa aplicada:** Ao atingir 'nao_respondeu', `pausado_ate` é setado
2. **60 dias:** Pausa é exatamente 60 dias
3. **Reativação:** Após 60 dias, conversa volta para 'recontato'
4. **Log:** Registra quando pausa aplicada e quando reativada

## DoD

- [x] `aplicar_pausa_60_dias()` implementada
- [x] `processar_pausas_expiradas()` implementada
- [x] Campo `pausado_ate` usado corretamente
- [x] Job no scheduler para processar pausas
- [x] Teste: conversa pausada há 61 dias → reativada

**NOTA:** Implementado em `app/services/followup.py` - ambas funções implementadas, pausa aplicada automaticamente ao atingir stage 'nao_respondeu'.

---

# S7.E4.4 - Adicionar job de follow-up no scheduler

## Objetivo

> **Garantir que job de follow-up roda corretamente.**

## Código Esperado

**Arquivo:** `app/workers/scheduler.py` (validar)

```python
JOBS = [
    # ... outros jobs ...

    {
        "name": "processar_followups",
        "endpoint": "/jobs/processar-followups",
        "schedule": "0 10 * * *",  # Diário às 10h
    },
    {
        "name": "processar_pausas_expiradas",
        "endpoint": "/jobs/processar-pausas-expiradas",
        "schedule": "0 6 * * *",  # Diário às 6h
    },
]
```

**Arquivo:** `app/api/routes/jobs.py` (adicionar endpoints)

```python
@router.post("/processar-followups")
async def job_processar_followups():
    """Job diário para processar follow-ups pendentes."""
    from app.services.followup import processar_followups_pendentes
    stats = await processar_followups_pendentes()
    return {"status": "ok", "stats": stats}


@router.post("/processar-pausas-expiradas")
async def job_processar_pausas_expiradas():
    """Job diário para reativar conversas pausadas."""
    from app.services.followup import processar_pausas_expiradas
    stats = await processar_pausas_expiradas()
    return {"status": "ok", "stats": stats}
```

## DoD

- [x] Job `processar_followups` no scheduler (10h)
- [x] Job `processar_pausas_expiradas` no scheduler (6h)
- [x] Endpoints `/jobs/processar-followups` funciona
- [x] Endpoints `/jobs/processar-pausas-expiradas` funciona
- [x] Logs indicam execução diária

**NOTA:** Jobs adicionados em `app/workers/scheduler.py`, endpoints em `app/api/routes/jobs.py`. Job legado `/followup-diario` mantido para compatibilidade.

---

## Resumo do Epic

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S7.E4.1 | Configuração de cadência | Baixa |
| S7.E4.2 | Serviço de follow-up | Alta |
| S7.E4.3 | Pausa de 60 dias | Média |
| S7.E4.4 | Jobs no scheduler | Baixa |

## Arquivos Modificados

| Arquivo | Ação |
|---------|------|
| `app/config/followup.py` | Validar/corrigir configuração |
| `app/services/followup.py` | Implementar lógica completa |
| `app/workers/scheduler.py` | Adicionar jobs |
| `app/api/routes/jobs.py` | Adicionar endpoints |

## Validação Final

```
Timeline esperada:
Dia 0:  Abertura enviada, stage = msg_enviada
Dia 2:  Follow-up 1 (48h), stage = followup_1_enviado
Dia 7:  Follow-up 2 com vaga (5d), stage = followup_2_enviado
Dia 22: Follow-up 3 último (15d), stage = nao_respondeu, pausado_ate = +60d
Dia 82: Pausa expira, stage = recontato
```
