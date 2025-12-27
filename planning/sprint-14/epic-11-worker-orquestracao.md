# E11 - Worker e Orquestração

## Objetivo

Implementar worker para processar mensagens de grupos em background de forma eficiente.

## Contexto

O pipeline completo tem 6 estágios:
1. Ingestão (E02)
2. Heurística (E03)
3. Classificação LLM (E04)
4. Extração (E05)
5. Normalização + Deduplicação (E06, E07, E08)
6. Importação (E09)

O worker deve orquestrar esses estágios de forma assíncrona, com retry e monitoramento.

## Stories

### S11.1 - Definir fila de processamento

**Descrição:** Estrutura para fila de mensagens a processar.

```python
# app/services/grupos/fila.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import datetime


class EstagioPipeline(Enum):
    """Estágios do pipeline de processamento."""
    PENDENTE = "pendente"
    HEURISTICA = "heuristica"
    CLASSIFICACAO = "classificacao"
    EXTRACAO = "extracao"
    NORMALIZACAO = "normalizacao"
    DEDUPLICACAO = "deduplicacao"
    IMPORTACAO = "importacao"
    FINALIZADO = "finalizado"
    ERRO = "erro"
    DESCARTADO = "descartado"


@dataclass
class ItemFila:
    """Item na fila de processamento."""
    mensagem_id: UUID
    estagio: EstagioPipeline
    tentativas: int = 0
    ultimo_erro: Optional[str] = None
    criado_em: datetime = None
    atualizado_em: datetime = None


# Criar tabela de controle
"""
CREATE TABLE fila_processamento_grupos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mensagem_id UUID NOT NULL REFERENCES mensagens_grupo(id),
    estagio VARCHAR(50) NOT NULL DEFAULT 'pendente',
    tentativas INT DEFAULT 0,
    max_tentativas INT DEFAULT 3,
    ultimo_erro TEXT,
    proximo_retry TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_fila_mensagem UNIQUE(mensagem_id)
);

CREATE INDEX idx_fila_estagio ON fila_processamento_grupos(estagio);
CREATE INDEX idx_fila_proximo_retry ON fila_processamento_grupos(proximo_retry);
"""
```

**Estimativa:** 1h

---

### S11.2 - Implementar enfileirador

**Descrição:** Adicionar mensagens à fila de processamento.

```python
from app.services.supabase import supabase
from datetime import datetime, timedelta


async def enfileirar_mensagem(mensagem_id: UUID) -> UUID:
    """
    Adiciona mensagem à fila de processamento.

    Returns:
        ID do item na fila
    """
    result = supabase.table("fila_processamento_grupos").upsert({
        "mensagem_id": str(mensagem_id),
        "estagio": EstagioPipeline.PENDENTE.value,
        "tentativas": 0,
        "updated_at": datetime.utcnow().isoformat(),
    }, on_conflict="mensagem_id").execute()

    return UUID(result.data[0]["id"])


async def buscar_proximos_pendentes(
    estagio: EstagioPipeline,
    limite: int = 50
) -> list:
    """
    Busca próximos itens para processar.

    Prioriza itens sem erro, depois com retry disponível.
    """
    agora = datetime.utcnow().isoformat()

    result = supabase.table("fila_processamento_grupos") \
        .select("id, mensagem_id, tentativas") \
        .eq("estagio", estagio.value) \
        .lt("tentativas", 3) \
        .or_(f"proximo_retry.is.null,proximo_retry.lte.{agora}") \
        .order("created_at") \
        .limit(limite) \
        .execute()

    return result.data


async def atualizar_estagio(
    item_id: UUID,
    novo_estagio: EstagioPipeline,
    erro: Optional[str] = None
) -> None:
    """Atualiza estágio de um item."""

    updates = {
        "estagio": novo_estagio.value,
        "updated_at": datetime.utcnow().isoformat(),
    }

    if erro:
        updates["ultimo_erro"] = erro
        updates["tentativas"] = supabase.sql("tentativas + 1")

        # Calcular próximo retry (backoff exponencial)
        # 1 min, 5 min, 15 min
        result = supabase.table("fila_processamento_grupos") \
            .select("tentativas") \
            .eq("id", str(item_id)) \
            .single() \
            .execute()

        tentativas = result.data["tentativas"]
        delay_minutos = [1, 5, 15][min(tentativas, 2)]
        updates["proximo_retry"] = (datetime.utcnow() + timedelta(minutes=delay_minutos)).isoformat()

    supabase.table("fila_processamento_grupos") \
        .update(updates) \
        .eq("id", str(item_id)) \
        .execute()
```

**Estimativa:** 1.5h

---

### S11.3 - Implementar processador de pipeline

**Descrição:** Orquestrador que executa cada estágio.

```python
# app/services/grupos/pipeline_worker.py

from app.core.logging import get_logger
from app.services.grupos.heuristica import calcular_score_heuristica
from app.services.grupos.classificador_llm import classificar_com_llm
from app.services.grupos.extrator import extrair_dados_vaga
from app.services.grupos.normalizador import normalizar_vaga
from app.services.grupos.deduplicador import processar_deduplicacao
from app.services.grupos.importador import processar_importacao

logger = get_logger(__name__)


class PipelineGrupos:
    """Processador do pipeline de mensagens de grupos."""

    THRESHOLD_HEURISTICA = 0.3
    THRESHOLD_LLM = 0.7

    async def processar_pendente(self, mensagem_id: UUID) -> dict:
        """
        Processa mensagem pendente (estágio inicial).

        Aplica heurística para decidir se continua.
        """
        # Buscar mensagem
        msg = supabase.table("mensagens_grupo") \
            .select("texto") \
            .eq("id", str(mensagem_id)) \
            .single() \
            .execute()

        if not msg.data or not msg.data.get("texto"):
            return {"acao": "descartar", "motivo": "sem_texto"}

        # Aplicar heurística
        resultado = calcular_score_heuristica(msg.data["texto"])

        if resultado.score < self.THRESHOLD_HEURISTICA:
            return {"acao": "descartar", "motivo": "heuristica_baixa", "score": resultado.score}

        if resultado.score >= 0.8:
            # Alta confiança - pula classificação LLM
            return {"acao": "extrair", "score": resultado.score}

        return {"acao": "classificar", "score": resultado.score}

    async def processar_classificacao(self, mensagem_id: UUID) -> dict:
        """
        Classifica mensagem com LLM.
        """
        msg = supabase.table("mensagens_grupo") \
            .select("texto") \
            .eq("id", str(mensagem_id)) \
            .single() \
            .execute()

        resultado = await classificar_com_llm(msg.data["texto"])

        if resultado.eh_oferta and resultado.confianca >= self.THRESHOLD_LLM:
            return {"acao": "extrair", "confianca": resultado.confianca}

        return {"acao": "descartar", "motivo": "nao_eh_oferta", "confianca": resultado.confianca}

    async def processar_extracao(self, mensagem_id: UUID) -> dict:
        """
        Extrai dados estruturados da mensagem.
        """
        msg = supabase.table("mensagens_grupo") \
            .select("*") \
            .eq("id", str(mensagem_id)) \
            .single() \
            .execute()

        resultado = await extrair_dados_vaga(msg.data["texto"])

        if not resultado.vagas:
            return {"acao": "descartar", "motivo": "extracao_falhou"}

        # Criar vagas_grupo para cada vaga extraída
        vagas_criadas = []
        for vaga in resultado.vagas:
            vaga_id = await criar_vaga_grupo(mensagem_id, vaga, msg.data)
            vagas_criadas.append(str(vaga_id))

        return {"acao": "normalizar", "vagas": vagas_criadas}

    async def processar_normalizacao(self, vaga_grupo_id: UUID) -> dict:
        """
        Normaliza dados da vaga.
        """
        resultado = await normalizar_vaga(vaga_grupo_id)
        return {"acao": "deduplicar", **resultado}

    async def processar_deduplicacao(self, vaga_grupo_id: UUID) -> dict:
        """
        Processa deduplicação.
        """
        resultado = await processar_deduplicacao(vaga_grupo_id)

        if resultado.get("duplicada"):
            return {"acao": "finalizar", "status": "duplicada"}

        return {"acao": "importar", **resultado}

    async def processar_importacao(self, vaga_grupo_id: UUID) -> dict:
        """
        Processa importação automática.
        """
        resultado = await processar_importacao(vaga_grupo_id)
        return {"acao": "finalizar", **resultado}
```

**Estimativa:** 3h

---

### S11.4 - Implementar worker principal

**Descrição:** Loop principal do worker.

```python
# app/workers/grupos_worker.py

import asyncio
from datetime import datetime
from app.core.logging import get_logger
from app.services.grupos.fila import (
    EstagioPipeline,
    buscar_proximos_pendentes,
    atualizar_estagio,
)
from app.services.grupos.pipeline_worker import PipelineGrupos

logger = get_logger(__name__)


class GruposWorker:
    """Worker para processar mensagens de grupos."""

    def __init__(
        self,
        batch_size: int = 50,
        intervalo_segundos: int = 10,
        max_workers: int = 5
    ):
        self.batch_size = batch_size
        self.intervalo = intervalo_segundos
        self.max_workers = max_workers
        self.pipeline = PipelineGrupos()
        self.running = False

    async def start(self):
        """Inicia o worker."""
        self.running = True
        logger.info("GruposWorker iniciado")

        while self.running:
            try:
                await self.processar_ciclo()
            except Exception as e:
                logger.error(f"Erro no ciclo do worker: {e}")

            await asyncio.sleep(self.intervalo)

    async def stop(self):
        """Para o worker."""
        self.running = False
        logger.info("GruposWorker parado")

    async def processar_ciclo(self):
        """Processa um ciclo de todas as filas."""

        # Processar cada estágio em ordem
        estagios = [
            (EstagioPipeline.PENDENTE, self.processar_pendente),
            (EstagioPipeline.CLASSIFICACAO, self.processar_classificacao),
            (EstagioPipeline.EXTRACAO, self.processar_extracao),
            (EstagioPipeline.NORMALIZACAO, self.processar_normalizacao),
            (EstagioPipeline.DEDUPLICACAO, self.processar_deduplicacao),
            (EstagioPipeline.IMPORTACAO, self.processar_importacao),
        ]

        stats = {"processados": 0, "erros": 0}

        for estagio, handler in estagios:
            itens = await buscar_proximos_pendentes(estagio, self.batch_size)

            if not itens:
                continue

            logger.info(f"Processando {len(itens)} itens em {estagio.value}")

            # Processar em paralelo (limitado)
            semaphore = asyncio.Semaphore(self.max_workers)

            async def processar_item(item):
                async with semaphore:
                    try:
                        resultado = await handler(UUID(item["mensagem_id"]))
                        proximo = self.decidir_proximo_estagio(resultado)
                        await atualizar_estagio(UUID(item["id"]), proximo)
                        stats["processados"] += 1
                    except Exception as e:
                        logger.error(f"Erro ao processar {item['id']}: {e}")
                        await atualizar_estagio(
                            UUID(item["id"]),
                            estagio,  # Mantém no mesmo estágio para retry
                            erro=str(e)
                        )
                        stats["erros"] += 1

            await asyncio.gather(*[processar_item(item) for item in itens])

        if stats["processados"] > 0:
            logger.info(f"Ciclo concluído: {stats}")

    def decidir_proximo_estagio(self, resultado: dict) -> EstagioPipeline:
        """Decide próximo estágio baseado no resultado."""
        acao = resultado.get("acao")

        if acao == "descartar":
            return EstagioPipeline.DESCARTADO
        elif acao == "classificar":
            return EstagioPipeline.CLASSIFICACAO
        elif acao == "extrair":
            return EstagioPipeline.EXTRACAO
        elif acao == "normalizar":
            return EstagioPipeline.NORMALIZACAO
        elif acao == "deduplicar":
            return EstagioPipeline.DEDUPLICACAO
        elif acao == "importar":
            return EstagioPipeline.IMPORTACAO
        elif acao == "finalizar":
            return EstagioPipeline.FINALIZADO
        else:
            return EstagioPipeline.ERRO

    # Handlers delegam para pipeline
    async def processar_pendente(self, mensagem_id: UUID) -> dict:
        return await self.pipeline.processar_pendente(mensagem_id)

    async def processar_classificacao(self, mensagem_id: UUID) -> dict:
        return await self.pipeline.processar_classificacao(mensagem_id)

    async def processar_extracao(self, mensagem_id: UUID) -> dict:
        return await self.pipeline.processar_extracao(mensagem_id)

    async def processar_normalizacao(self, vaga_id: UUID) -> dict:
        return await self.pipeline.processar_normalizacao(vaga_id)

    async def processar_deduplicacao(self, vaga_id: UUID) -> dict:
        return await self.pipeline.processar_deduplicacao(vaga_id)

    async def processar_importacao(self, vaga_id: UUID) -> dict:
        return await self.pipeline.processar_importacao(vaga_id)
```

**Estimativa:** 3h

---

### S11.5 - Integrar com scheduler existente

**Descrição:** Adicionar worker ao scheduler do sistema.

```python
# Adicionar em app/workers/scheduler.py

from app.workers.grupos_worker import GruposWorker


class Scheduler:
    """Scheduler principal do sistema."""

    def __init__(self):
        self.grupos_worker = GruposWorker(
            batch_size=50,
            intervalo_segundos=10,
            max_workers=5
        )
        # ... outros workers

    async def start(self):
        """Inicia todos os workers."""
        tasks = [
            asyncio.create_task(self.grupos_worker.start()),
            # ... outros workers
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        """Para todos os workers."""
        await self.grupos_worker.stop()
        # ... outros workers
```

**Estimativa:** 1h

---

### S11.6 - Implementar health check

**Descrição:** Endpoint para verificar saúde do worker.

```python
# app/api/routes/health.py

@router.get("/health/grupos-worker")
async def health_grupos_worker():
    """Health check do worker de grupos."""

    # Verificar se há itens travados (muito tempo no mesmo estágio)
    from datetime import datetime, timedelta

    limite = (datetime.utcnow() - timedelta(hours=1)).isoformat()

    travados = supabase.table("fila_processamento_grupos") \
        .select("id", count="exact") \
        .not_.in_("estagio", ["finalizado", "descartado", "erro"]) \
        .lt("updated_at", limite) \
        .execute()

    # Verificar fila pendente
    pendentes = supabase.table("fila_processamento_grupos") \
        .select("id", count="exact") \
        .eq("estagio", "pendente") \
        .execute()

    # Erros recentes
    erros = supabase.table("fila_processamento_grupos") \
        .select("id", count="exact") \
        .eq("estagio", "erro") \
        .gte("updated_at", (datetime.utcnow() - timedelta(hours=24)).isoformat()) \
        .execute()

    status = "healthy"
    if travados.count > 100:
        status = "degraded"
    if travados.count > 500:
        status = "unhealthy"

    return {
        "status": status,
        "metrics": {
            "pendentes": pendentes.count,
            "travados": travados.count,
            "erros_24h": erros.count,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
```

**Estimativa:** 1h

---

### S11.7 - Comando manual de reprocessamento

**Descrição:** Tool para reprocessar itens com erro.

```python
async def tool_reprocessar_fila(
    estagio: Optional[str] = None,
    limite: int = 100
) -> dict:
    """
    Reprocessa itens da fila com erro.

    Args:
        estagio: Filtrar por estágio específico
        limite: Máximo de itens a reprocessar
    """
    query = supabase.table("fila_processamento_grupos") \
        .select("id") \
        .eq("estagio", "erro") \
        .lt("tentativas", 3)

    if estagio:
        # Reprocessar a partir de estágio específico
        query = query.eq("ultimo_estagio", estagio)

    result = query.limit(limite).execute()

    count = 0
    for item in result.data:
        supabase.table("fila_processamento_grupos") \
            .update({
                "estagio": EstagioPipeline.PENDENTE.value,
                "tentativas": 0,
                "ultimo_erro": None,
                "proximo_retry": None,
            }) \
            .eq("id", item["id"]) \
            .execute()
        count += 1

    return {
        "sucesso": True,
        "reprocessados": count,
        "mensagem": f"{count} itens enviados para reprocessamento"
    }
```

**Estimativa:** 1h

---

### S11.8 - Testes do worker

**Estimativa:** 2h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S11.1 | Fila de processamento | 1h |
| S11.2 | Enfileirador | 1.5h |
| S11.3 | Processador pipeline | 3h |
| S11.4 | Worker principal | 3h |
| S11.5 | Integração scheduler | 1h |
| S11.6 | Health check | 1h |
| S11.7 | Reprocessamento manual | 1h |
| S11.8 | Testes | 2h |

**Total:** 13.5h (~1.7 dias)

## Dependências

- Todos os épicos anteriores (E02-E09)

## Entregáveis

- Fila de processamento com retry
- Worker assíncrono com paralelização
- Health check do pipeline
- Reprocessamento manual
- Integração com scheduler existente
