# E05: Gatilhos Automáticos

**Fase:** 2 - Julia Autônoma
**Estimativa:** 8h
**Prioridade:** Alta
**Dependências:** E03 (Modo Piloto), E04 (checkNumberStatus)

---

## Objetivo

Implementar sistema de gatilhos automáticos que faz Julia agir baseado no estado do banco de dados, sem necessidade de briefing manual do gestor.

## Visão

Julia deve funcionar como um escalista humano:

```
1. OLHA O BANCO DE DADOS (carteira de médicos)
   → "Tenho 50 médicos, mas só sei especialidade de 30"
   → "Preciso enriquecer esses 20"
   → AÇÃO: Discovery nos 20

2. OLHA AS ESCALAS (vagas)
   → "Escala de março do Hospital X tem 15 furos"
   → "Quais médicos da minha carteira são compatíveis?"
   → AÇÃO: Oferta direcionada

3. OLHA O RELACIONAMENTO
   → "Dr Carlos não responde há 2 meses"
   → AÇÃO: Reativação

4. OLHA FEEDBACK
   → "Dr Maria fez plantão ontem no Hospital Y"
   → AÇÃO: Pedir feedback
```

---

## Gatilhos a Implementar

| Gatilho | Condição | Ação | Prioridade |
|---------|----------|------|------------|
| **Discovery** | Médico não-enriquecido (só nome+telefone) | Campanha Discovery | P1 |
| **Oferta** | Vaga sem médico < 20 dias | Oferta para compatíveis | P1 |
| **Reativação** | Sem interação > 60 dias | Campanha Reativação | P2 |
| **Feedback** | Fez plantão ontem | Campanha Feedback | P2 |

---

## Tarefas

### T1: Criar tabela de gatilhos (30min)

**Migration:** `create_gatilhos_automaticos_table`

```sql
-- Migration: create_gatilhos_automaticos_table
-- Sprint 32 E05: Sistema de gatilhos automáticos

CREATE TABLE IF NOT EXISTS gatilhos_automaticos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo TEXT NOT NULL,  -- discovery | oferta | reativacao | feedback
    cliente_id UUID REFERENCES clientes(id),
    vaga_id UUID REFERENCES vagas(id),
    status TEXT NOT NULL DEFAULT 'pendente',  -- pendente | processando | executado | cancelado | erro
    prioridade INT DEFAULT 0,  -- Maior = mais prioritário
    dados JSONB,  -- Contexto adicional
    criado_em TIMESTAMPTZ DEFAULT now(),
    processado_em TIMESTAMPTZ,
    erro TEXT,
    campanha_id INT REFERENCES campanhas(id),  -- Campanha gerada (se executado)

    CONSTRAINT chk_gatilho_tipo CHECK (tipo IN ('discovery', 'oferta', 'reativacao', 'feedback')),
    CONSTRAINT chk_gatilho_status CHECK (status IN ('pendente', 'processando', 'executado', 'cancelado', 'erro'))
);

-- Índice para buscar pendentes por prioridade
CREATE INDEX idx_gatilhos_pendentes
ON gatilhos_automaticos (status, prioridade DESC, criado_em ASC)
WHERE status = 'pendente';

-- Índice para evitar duplicatas
CREATE UNIQUE INDEX idx_gatilhos_unique_cliente
ON gatilhos_automaticos (tipo, cliente_id)
WHERE status IN ('pendente', 'processando');

-- Comentários
COMMENT ON TABLE gatilhos_automaticos IS 'Fila de gatilhos automáticos para Julia processar';
COMMENT ON COLUMN gatilhos_automaticos.prioridade IS 'Maior valor = maior prioridade (vagas urgentes > discovery)';
```

### T2: Criar serviço base de gatilhos (45min)

**Arquivo:** `app/services/gatilhos/base.py`

```python
"""
Serviço base para gatilhos automáticos.

Sprint 32 E05 - Julia Autônoma.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from abc import ABC, abstractmethod

from app.services.supabase import supabase
from app.workers.pilot_mode import is_pilot_mode, AutonomousFeature

logger = logging.getLogger(__name__)

TipoGatilho = Literal["discovery", "oferta", "reativacao", "feedback"]


class GatilhoBase(ABC):
    """Classe base para implementação de gatilhos."""

    tipo: TipoGatilho
    feature: AutonomousFeature

    @abstractmethod
    async def detectar(self) -> list[dict]:
        """
        Detecta condições que acionam o gatilho.

        Returns:
            Lista de dicts com dados para criar gatilhos
        """
        pass

    @abstractmethod
    async def executar(self, gatilho: dict) -> bool:
        """
        Executa a ação do gatilho.

        Args:
            gatilho: Dados do gatilho a executar

        Returns:
            True se executou com sucesso
        """
        pass


async def criar_gatilho(
    tipo: TipoGatilho,
    cliente_id: Optional[str] = None,
    vaga_id: Optional[str] = None,
    prioridade: int = 0,
    dados: Optional[dict] = None,
) -> Optional[str]:
    """
    Cria um novo gatilho na fila.

    Args:
        tipo: Tipo do gatilho
        cliente_id: ID do cliente (se aplicável)
        vaga_id: ID da vaga (se aplicável)
        prioridade: Prioridade (maior = mais urgente)
        dados: Dados adicionais em JSON

    Returns:
        ID do gatilho criado ou None se já existe
    """
    try:
        response = supabase.table("gatilhos_automaticos").insert({
            "tipo": tipo,
            "cliente_id": cliente_id,
            "vaga_id": vaga_id,
            "prioridade": prioridade,
            "dados": dados or {},
            "status": "pendente",
        }).execute()

        if response.data:
            gatilho_id = response.data[0]["id"]
            logger.debug(f"Gatilho {tipo} criado: {gatilho_id}")
            return gatilho_id

        return None

    except Exception as e:
        # Unique constraint violation = já existe gatilho pendente
        if "unique" in str(e).lower():
            logger.debug(f"Gatilho {tipo} já existe para cliente {cliente_id}")
            return None
        logger.error(f"Erro ao criar gatilho: {e}")
        return None


async def buscar_gatilhos_pendentes(
    tipo: Optional[TipoGatilho] = None,
    limit: int = 50
) -> list[dict]:
    """
    Busca gatilhos pendentes ordenados por prioridade.

    Args:
        tipo: Filtrar por tipo (opcional)
        limit: Máximo de registros

    Returns:
        Lista de gatilhos pendentes
    """
    query = (
        supabase.table("gatilhos_automaticos")
        .select("*")
        .eq("status", "pendente")
        .order("prioridade", desc=True)
        .order("criado_em", desc=False)
        .limit(limit)
    )

    if tipo:
        query = query.eq("tipo", tipo)

    response = query.execute()
    return response.data or []


async def marcar_gatilho_processando(gatilho_id: str) -> bool:
    """Marca gatilho como em processamento."""
    try:
        response = (
            supabase.table("gatilhos_automaticos")
            .update({"status": "processando"})
            .eq("id", gatilho_id)
            .eq("status", "pendente")
            .execute()
        )
        return len(response.data or []) > 0
    except Exception as e:
        logger.error(f"Erro ao marcar gatilho processando: {e}")
        return False


async def marcar_gatilho_executado(
    gatilho_id: str,
    campanha_id: Optional[int] = None
) -> bool:
    """Marca gatilho como executado."""
    try:
        response = (
            supabase.table("gatilhos_automaticos")
            .update({
                "status": "executado",
                "processado_em": datetime.now(timezone.utc).isoformat(),
                "campanha_id": campanha_id,
            })
            .eq("id", gatilho_id)
            .execute()
        )
        return len(response.data or []) > 0
    except Exception as e:
        logger.error(f"Erro ao marcar gatilho executado: {e}")
        return False


async def marcar_gatilho_erro(gatilho_id: str, erro: str) -> bool:
    """Marca gatilho como erro."""
    try:
        response = (
            supabase.table("gatilhos_automaticos")
            .update({
                "status": "erro",
                "processado_em": datetime.now(timezone.utc).isoformat(),
                "erro": erro[:500],
            })
            .eq("id", gatilho_id)
            .execute()
        )
        return len(response.data or []) > 0
    except Exception as e:
        logger.error(f"Erro ao marcar gatilho erro: {e}")
        return False
```

### T3: Implementar gatilho de Discovery (60min)

**Arquivo:** `app/services/gatilhos/discovery.py`

```python
"""
Gatilho de Discovery automático.

Detecta médicos não-enriquecidos e cria campanhas de Discovery.
"""
import logging
from typing import Optional

from app.services.supabase import supabase
from app.services.gatilhos.base import (
    GatilhoBase,
    criar_gatilho,
    marcar_gatilho_executado,
    marcar_gatilho_erro,
)
from app.workers.pilot_mode import (
    skip_if_pilot,
    AutonomousFeature,
)

logger = logging.getLogger(__name__)


class GatilhoDiscovery(GatilhoBase):
    """
    Gatilho para Discovery automático.

    Condição: Médico só tem nome+telefone, sem especialidade ou outras infos.
    Ação: Criar campanha de Discovery para conhecer o médico.
    """

    tipo = "discovery"
    feature = AutonomousFeature.DISCOVERY

    async def detectar(self) -> list[dict]:
        """
        Detecta médicos que precisam de Discovery.

        Critérios:
        - status_telefone = 'validado' (telefone funciona)
        - especialidade IS NULL (não sabemos especialidade)
        - opt_out = false (não pediu para não receber)
        - Não tem gatilho pendente
        """
        # Buscar médicos não-enriquecidos
        response = (
            supabase.table("clientes")
            .select("id, nome, telefone")
            .eq("status_telefone", "validado")
            .is_("especialidade", "null")
            .eq("opt_out", False)
            .limit(100)
            .execute()
        )

        medicos = response.data or []

        if not medicos:
            logger.debug("Nenhum médico elegível para Discovery")
            return []

        # Filtrar quem já tem gatilho pendente
        ids = [m["id"] for m in medicos]
        gatilhos_existentes = (
            supabase.table("gatilhos_automaticos")
            .select("cliente_id")
            .eq("tipo", "discovery")
            .in_("status", ["pendente", "processando"])
            .in_("cliente_id", ids)
            .execute()
        )

        ids_com_gatilho = {g["cliente_id"] for g in (gatilhos_existentes.data or [])}

        elegíveis = [m for m in medicos if m["id"] not in ids_com_gatilho]

        logger.info(f"Discovery: {len(elegíveis)} médicos elegíveis de {len(medicos)} encontrados")

        return elegíveis

    async def executar(self, gatilho: dict) -> bool:
        """
        Executa gatilho de Discovery.

        Cria uma campanha de Discovery para o médico.
        """
        cliente_id = gatilho.get("cliente_id")

        if not cliente_id:
            logger.error("Gatilho sem cliente_id")
            return False

        try:
            # Buscar dados do médico
            medico = (
                supabase.table("clientes")
                .select("*")
                .eq("id", cliente_id)
                .single()
                .execute()
            )

            if not medico.data:
                await marcar_gatilho_erro(gatilho["id"], "Médico não encontrado")
                return False

            # Criar campanha de Discovery
            campanha = await criar_campanha_discovery(medico.data)

            if campanha:
                await marcar_gatilho_executado(gatilho["id"], campanha["id"])
                logger.info(f"Discovery criado para {medico.data.get('nome')}")
                return True
            else:
                await marcar_gatilho_erro(gatilho["id"], "Falha ao criar campanha")
                return False

        except Exception as e:
            await marcar_gatilho_erro(gatilho["id"], str(e))
            logger.error(f"Erro ao executar Discovery: {e}")
            return False


async def criar_campanha_discovery(medico: dict) -> Optional[dict]:
    """
    Cria campanha de Discovery para um médico.

    Args:
        medico: Dados do médico

    Returns:
        Dados da campanha criada
    """
    try:
        campanha_data = {
            "nome": f"Discovery - {medico.get('nome', 'Médico')}",
            "tipo": "discovery",
            "objetivo": "Conhecer o médico, descobrir especialidade e preferências",
            "status": "ativa",
            "filtros_medicos": {"cliente_id": medico["id"]},
        }

        response = supabase.table("campanhas").insert(campanha_data).execute()

        if response.data:
            campanha = response.data[0]

            # Enfileirar mensagem
            await enfileirar_primeira_mensagem(campanha["id"], medico["id"])

            return campanha

        return None

    except Exception as e:
        logger.error(f"Erro ao criar campanha Discovery: {e}")
        return None


async def enfileirar_primeira_mensagem(campanha_id: int, cliente_id: str) -> bool:
    """Enfileira primeira mensagem da campanha."""
    try:
        response = supabase.table("fila_mensagens").insert({
            "cliente_id": cliente_id,
            "campaign_id": campanha_id,
            "send_type": "discovery",
            "queue_status": "queued",
        }).execute()

        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao enfileirar mensagem: {e}")
        return False


@skip_if_pilot(AutonomousFeature.DISCOVERY)
async def executar_deteccao_discovery() -> dict:
    """
    Detecta e cria gatilhos de Discovery.

    Retorna estatísticas.
    """
    gatilho = GatilhoDiscovery()
    elegíveis = await gatilho.detectar()

    criados = 0
    for medico in elegíveis:
        gatilho_id = await criar_gatilho(
            tipo="discovery",
            cliente_id=medico["id"],
            prioridade=0,  # Discovery tem prioridade baixa
            dados={"nome": medico.get("nome")},
        )
        if gatilho_id:
            criados += 1

    return {
        "detectados": len(elegíveis),
        "gatilhos_criados": criados,
    }
```

### T4: Implementar gatilho de Reativação (45min)

**Arquivo:** `app/services/gatilhos/reativacao.py`

```python
"""
Gatilho de Reativação automático.

Detecta médicos inativos e cria campanhas de Reativação.
"""
import logging
from datetime import datetime, timezone, timedelta

from app.services.supabase import supabase
from app.services.gatilhos.base import (
    GatilhoBase,
    criar_gatilho,
    marcar_gatilho_executado,
    marcar_gatilho_erro,
)
from app.workers.pilot_mode import skip_if_pilot, AutonomousFeature

logger = logging.getLogger(__name__)

# Médico é considerado inativo após X dias sem interação
DIAS_INATIVIDADE = 60


class GatilhoReativacao(GatilhoBase):
    """
    Gatilho para Reativação automática.

    Condição: Médico sem interação > 60 dias.
    Ação: Criar campanha de Reativação para retomar contato.
    """

    tipo = "reativacao"
    feature = AutonomousFeature.REATIVACAO

    async def detectar(self) -> list[dict]:
        """
        Detecta médicos inativos.

        Critérios:
        - Última interação > 60 dias atrás
        - status_telefone = 'validado'
        - opt_out = false
        - Não tem gatilho pendente
        """
        data_limite = (
            datetime.now(timezone.utc) - timedelta(days=DIAS_INATIVIDADE)
        ).isoformat()

        # Buscar médicos com última interação antiga
        # Usando subquery para pegar última interação
        response = supabase.rpc(
            "buscar_medicos_inativos",
            {"dias": DIAS_INATIVIDADE, "limite": 100}
        ).execute()

        medicos = response.data or []

        if not medicos:
            logger.debug("Nenhum médico inativo encontrado")
            return []

        # Filtrar quem já tem gatilho pendente
        ids = [m["id"] for m in medicos]
        gatilhos_existentes = (
            supabase.table("gatilhos_automaticos")
            .select("cliente_id")
            .eq("tipo", "reativacao")
            .in_("status", ["pendente", "processando"])
            .in_("cliente_id", ids)
            .execute()
        )

        ids_com_gatilho = {g["cliente_id"] for g in (gatilhos_existentes.data or [])}

        elegiveis = [m for m in medicos if m["id"] not in ids_com_gatilho]

        logger.info(f"Reativação: {len(elegiveis)} médicos elegíveis")

        return elegiveis

    async def executar(self, gatilho: dict) -> bool:
        """Executa gatilho de Reativação."""
        cliente_id = gatilho.get("cliente_id")

        try:
            # Criar campanha de Reativação
            campanha_data = {
                "nome": f"Reativação - {gatilho.get('dados', {}).get('nome', 'Médico')}",
                "tipo": "reativacao",
                "objetivo": "Retomar contato com médico inativo",
                "status": "ativa",
                "filtros_medicos": {"cliente_id": cliente_id},
            }

            response = supabase.table("campanhas").insert(campanha_data).execute()

            if response.data:
                campanha = response.data[0]

                # Enfileirar mensagem
                supabase.table("fila_mensagens").insert({
                    "cliente_id": cliente_id,
                    "campaign_id": campanha["id"],
                    "send_type": "reativacao",
                    "queue_status": "queued",
                }).execute()

                await marcar_gatilho_executado(gatilho["id"], campanha["id"])
                return True

            await marcar_gatilho_erro(gatilho["id"], "Falha ao criar campanha")
            return False

        except Exception as e:
            await marcar_gatilho_erro(gatilho["id"], str(e))
            logger.error(f"Erro ao executar Reativação: {e}")
            return False


@skip_if_pilot(AutonomousFeature.REATIVACAO)
async def executar_deteccao_reativacao() -> dict:
    """Detecta e cria gatilhos de Reativação."""
    gatilho = GatilhoReativacao()
    elegiveis = await gatilho.detectar()

    criados = 0
    for medico in elegiveis:
        gatilho_id = await criar_gatilho(
            tipo="reativacao",
            cliente_id=medico["id"],
            prioridade=1,  # Reativação tem prioridade média
            dados={"nome": medico.get("nome"), "dias_inativo": medico.get("dias_inativo")},
        )
        if gatilho_id:
            criados += 1

    return {"detectados": len(elegiveis), "gatilhos_criados": criados}
```

### T5: Implementar gatilho de Feedback (45min)

**Arquivo:** `app/services/gatilhos/feedback.py`

```python
"""
Gatilho de Feedback automático.

Detecta médicos que fizeram plantão recentemente e pede feedback.
"""
import logging
from datetime import datetime, timezone, timedelta

from app.services.supabase import supabase
from app.services.gatilhos.base import (
    criar_gatilho,
    marcar_gatilho_executado,
    marcar_gatilho_erro,
)
from app.workers.pilot_mode import skip_if_pilot, AutonomousFeature

logger = logging.getLogger(__name__)


async def detectar_plantoes_para_feedback() -> list[dict]:
    """
    Detecta médicos que fizeram plantão ontem.

    Critérios:
    - Plantão com status = 'realizado'
    - Data do plantão = ontem
    - Não tem feedback pendente para este plantão
    """
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()

    # Buscar plantões realizados ontem
    response = (
        supabase.table("plantoes_realizados")  # ou tabela equivalente
        .select("id, cliente_id, vaga_id, hospital_nome, data_plantao")
        .eq("data_plantao", ontem)
        .eq("status", "realizado")
        .execute()
    )

    plantoes = response.data or []

    if not plantoes:
        logger.debug("Nenhum plantão realizado ontem")
        return []

    # Filtrar quem já tem gatilho de feedback pendente
    cliente_ids = [p["cliente_id"] for p in plantoes]

    gatilhos_existentes = (
        supabase.table("gatilhos_automaticos")
        .select("cliente_id, dados")
        .eq("tipo", "feedback")
        .in_("status", ["pendente", "processando"])
        .in_("cliente_id", cliente_ids)
        .execute()
    )

    # Criar set de (cliente_id, vaga_id) já com gatilho
    ja_tem_gatilho = {
        (g["cliente_id"], g.get("dados", {}).get("vaga_id"))
        for g in (gatilhos_existentes.data or [])
    }

    elegiveis = [
        p for p in plantoes
        if (p["cliente_id"], p["vaga_id"]) not in ja_tem_gatilho
    ]

    logger.info(f"Feedback: {len(elegiveis)} plantões elegíveis")

    return elegiveis


@skip_if_pilot(AutonomousFeature.FEEDBACK)
async def executar_deteccao_feedback() -> dict:
    """Detecta e cria gatilhos de Feedback."""
    plantoes = await detectar_plantoes_para_feedback()

    criados = 0
    for plantao in plantoes:
        gatilho_id = await criar_gatilho(
            tipo="feedback",
            cliente_id=plantao["cliente_id"],
            vaga_id=plantao["vaga_id"],
            prioridade=2,  # Feedback tem prioridade alta (médico acabou de trabalhar)
            dados={
                "hospital_nome": plantao.get("hospital_nome"),
                "data_plantao": plantao.get("data_plantao"),
            },
        )
        if gatilho_id:
            criados += 1

    return {"detectados": len(plantoes), "gatilhos_criados": criados}
```

### T6: Criar RPC para buscar inativos (30min)

**Migration:** `create_buscar_medicos_inativos_rpc`

```sql
-- Migration: create_buscar_medicos_inativos_rpc
-- Sprint 32 E05: Função para buscar médicos inativos

CREATE OR REPLACE FUNCTION buscar_medicos_inativos(
    dias INT DEFAULT 60,
    limite INT DEFAULT 100
)
RETURNS TABLE (
    id UUID,
    nome TEXT,
    telefone TEXT,
    dias_inativo INT
)
LANGUAGE sql
STABLE
AS $$
    WITH ultima_interacao AS (
        SELECT
            cliente_id,
            MAX(created_at) as ultima_msg
        FROM interacoes
        GROUP BY cliente_id
    )
    SELECT
        c.id,
        c.nome,
        c.telefone,
        EXTRACT(DAY FROM (now() - COALESCE(ui.ultima_msg, c.created_at)))::INT as dias_inativo
    FROM clientes c
    LEFT JOIN ultima_interacao ui ON ui.cliente_id = c.id
    WHERE c.status_telefone = 'validado'
      AND c.opt_out = false
      AND (
          ui.ultima_msg IS NULL
          OR ui.ultima_msg < (now() - (dias || ' days')::INTERVAL)
      )
    ORDER BY dias_inativo DESC
    LIMIT limite;
$$;

COMMENT ON FUNCTION buscar_medicos_inativos IS 'Busca médicos sem interação há X dias para reativação';
```

### T7: Criar worker de processamento de gatilhos (60min)

**Arquivo:** `app/workers/gatilhos_worker.py`

```python
"""
Worker para processamento de gatilhos automáticos.

Sprint 32 E05 - Processa a fila de gatilhos e executa ações.
"""
import logging
import asyncio

from app.services.gatilhos.base import (
    buscar_gatilhos_pendentes,
    marcar_gatilho_processando,
)
from app.services.gatilhos.discovery import GatilhoDiscovery
from app.services.gatilhos.reativacao import GatilhoReativacao
from app.workers.pilot_mode import is_pilot_mode, log_pilot_status

logger = logging.getLogger(__name__)

# Mapeamento tipo -> classe
GATILHO_HANDLERS = {
    "discovery": GatilhoDiscovery(),
    "reativacao": GatilhoReativacao(),
    # "oferta" e "feedback" serão adicionados depois
}


async def processar_gatilhos_pendentes(limit: int = 20) -> dict:
    """
    Processa lote de gatilhos pendentes.

    Args:
        limit: Máximo de gatilhos a processar

    Returns:
        Estatísticas do processamento
    """
    # Verificar modo piloto
    if is_pilot_mode():
        logger.info("Modo piloto ativo - pulando processamento de gatilhos")
        return {"status": "skipped", "reason": "pilot_mode"}

    stats = {
        "processados": 0,
        "sucesso": 0,
        "erro": 0,
        "por_tipo": {},
    }

    gatilhos = await buscar_gatilhos_pendentes(limit=limit)

    if not gatilhos:
        logger.debug("Nenhum gatilho pendente")
        return stats

    logger.info(f"Processando {len(gatilhos)} gatilhos pendentes")

    for gatilho in gatilhos:
        tipo = gatilho["tipo"]
        handler = GATILHO_HANDLERS.get(tipo)

        if not handler:
            logger.warning(f"Handler não encontrado para tipo: {tipo}")
            continue

        # Marcar como processando
        if not await marcar_gatilho_processando(gatilho["id"]):
            continue

        # Executar
        try:
            sucesso = await handler.executar(gatilho)

            stats["processados"] += 1

            if sucesso:
                stats["sucesso"] += 1
            else:
                stats["erro"] += 1

            # Contagem por tipo
            stats["por_tipo"][tipo] = stats["por_tipo"].get(tipo, 0) + 1

        except Exception as e:
            logger.error(f"Erro ao processar gatilho {gatilho['id']}: {e}")
            stats["erro"] += 1

    logger.info(
        f"Gatilhos processados: {stats['sucesso']} sucesso, {stats['erro']} erro"
    )

    return stats


async def executar_ciclo_gatilhos():
    """
    Executa um ciclo completo de detecção e processamento.

    1. Detecta novas condições
    2. Cria gatilhos
    3. Processa gatilhos pendentes
    """
    log_pilot_status()

    if is_pilot_mode():
        return {"status": "skipped", "reason": "pilot_mode"}

    # Importar funções de detecção
    from app.services.gatilhos.discovery import executar_deteccao_discovery
    from app.services.gatilhos.reativacao import executar_deteccao_reativacao
    from app.services.gatilhos.feedback import executar_deteccao_feedback

    # 1. Detectar novas condições
    deteccoes = {}

    try:
        deteccoes["discovery"] = await executar_deteccao_discovery()
    except Exception as e:
        logger.error(f"Erro na detecção de Discovery: {e}")

    try:
        deteccoes["reativacao"] = await executar_deteccao_reativacao()
    except Exception as e:
        logger.error(f"Erro na detecção de Reativação: {e}")

    try:
        deteccoes["feedback"] = await executar_deteccao_feedback()
    except Exception as e:
        logger.error(f"Erro na detecção de Feedback: {e}")

    # 2. Processar gatilhos pendentes
    processamento = await processar_gatilhos_pendentes()

    return {
        "deteccoes": deteccoes,
        "processamento": processamento,
    }
```

### T8: Adicionar job ao scheduler (30min)

**Arquivo:** `app/workers/scheduler.py`

**Adicionar:**

```python
from app.workers.gatilhos_worker import executar_ciclo_gatilhos

async def job_processar_gatilhos():
    """
    Job de processamento de gatilhos automáticos.

    Roda a cada 15 minutos.
    Detecta condições e processa fila.

    Sprint 32 E05.
    """
    try:
        resultado = await executar_ciclo_gatilhos()
        return {"status": "success", "resultado": resultado}
    except Exception as e:
        logger.error(f"Erro no job de gatilhos: {e}")
        return {"status": "error", "error": str(e)}


# Adicionar ao agendamento
JOBS.append({
    "name": "processar_gatilhos",
    "function": job_processar_gatilhos,
    "cron": "*/15 * * * *",  # A cada 15 minutos
    "description": "Detecta e processa gatilhos automáticos (Discovery, Reativação, Feedback)",
})
```

### T9: Criar testes (60min)

**Arquivo:** `tests/unit/test_gatilhos.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.gatilhos.base import criar_gatilho, buscar_gatilhos_pendentes
from app.services.gatilhos.discovery import GatilhoDiscovery, executar_deteccao_discovery


class TestGatilhoBase:
    """Testes para funções base de gatilhos."""

    @pytest.mark.asyncio
    async def test_criar_gatilho_novo(self):
        """Deve criar gatilho quando não existe."""
        with patch("app.services.gatilhos.base.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "uuid-123"}
            ]

            resultado = await criar_gatilho(
                tipo="discovery",
                cliente_id="cliente-123",
                prioridade=0,
            )

            assert resultado == "uuid-123"

    @pytest.mark.asyncio
    async def test_criar_gatilho_duplicado(self):
        """Deve retornar None quando gatilho já existe."""
        with patch("app.services.gatilhos.base.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.side_effect = (
                Exception("unique constraint violation")
            )

            resultado = await criar_gatilho(
                tipo="discovery",
                cliente_id="cliente-123",
            )

            assert resultado is None


class TestGatilhoDiscovery:
    """Testes para gatilho de Discovery."""

    @pytest.mark.asyncio
    async def test_detectar_medicos_nao_enriquecidos(self):
        """Deve detectar médicos sem especialidade."""
        gatilho = GatilhoDiscovery()

        with patch("app.services.gatilhos.discovery.supabase") as mock_supabase:
            # Mock da busca de médicos
            mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                {"id": "1", "nome": "Dr João", "telefone": "5511999999999"},
                {"id": "2", "nome": "Dra Maria", "telefone": "5511888888888"},
            ]

            # Mock da busca de gatilhos existentes
            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.in_.return_value.execute.return_value.data = []

            resultado = await gatilho.detectar()

            assert len(resultado) == 2

    @pytest.mark.asyncio
    async def test_discovery_pulado_em_modo_piloto(self):
        """Discovery deve ser pulado em modo piloto."""
        with patch("app.services.gatilhos.discovery.is_pilot_mode") as mock_pilot:
            mock_pilot.return_value = True

            with patch("app.workers.pilot_mode.settings") as mock_settings:
                mock_settings.is_pilot_mode = True

                # A função decorada deve retornar None
                resultado = await executar_deteccao_discovery()

                assert resultado is None
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Tabela gatilhos_automaticos criada**
  - [ ] Migration aplicada
  - [ ] Índices funcionando
  - [ ] Constraint de tipos válida

- [ ] **Gatilho Discovery funciona**
  - [ ] Detecta médicos não-enriquecidos
  - [ ] Cria campanhas corretamente
  - [ ] Enfileira mensagens

- [ ] **Gatilho Reativação funciona**
  - [ ] Detecta médicos inativos > 60 dias
  - [ ] Cria campanhas corretamente

- [ ] **Gatilho Feedback funciona**
  - [ ] Detecta plantões realizados ontem
  - [ ] Cria gatilhos para feedback

- [ ] **Worker integrado**
  - [ ] Job roda a cada 15 minutos
  - [ ] Detecta e processa em sequência
  - [ ] Respeita modo piloto

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_gatilhos.py -v` = OK

### Verificação Manual

```sql
-- Verificar gatilhos criados
SELECT tipo, status, COUNT(*)
FROM gatilhos_automaticos
GROUP BY tipo, status;

-- Verificar médicos elegíveis para Discovery
SELECT COUNT(*)
FROM clientes
WHERE status_telefone = 'validado'
  AND especialidade IS NULL
  AND opt_out = false;
```

---

## Notas para o Desenvolvedor

1. **Modo piloto é crítico:**
   - TODAS as funções de execução devem usar `@skip_if_pilot`
   - Detecção pode rodar, mas execução não

2. **Evitar duplicatas:**
   - Unique index impede criar gatilho duplicado
   - Verificar existentes antes de criar

3. **Prioridade:**
   - Feedback (2) > Reativação (1) > Discovery (0)
   - Vagas urgentes terão prioridade ainda maior (E06)

4. **Oferta automática (E06):**
   - Não está neste épico
   - Será implementado separadamente
