# Epic 2: Campanhas Automatizadas

## Objetivo

> **Automatizar envio de campanhas e follow-ups em escala.**

---

## Stories

---

# S5.E2.1 - Sistema de filas de envio

## Objetivo

> **Criar sistema robusto de filas para envio de mensagens.**

**Resultado esperado:** Mensagens enfileiradas e processadas respeitando rate limiting.

## Contexto

Para escalar, precisamos:
- Fila persistente (sobrevive restart)
- Rate limiting por número de WhatsApp
- Retry automático em falhas
- Priorização de mensagens

## Tarefas

### 1. Criar tabela de fila

```sql
-- migration: criar_tabela_fila_mensagens.sql

CREATE TABLE fila_mensagens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID REFERENCES clientes(id),
    conversa_id UUID REFERENCES conversations(id),

    tipo VARCHAR(50) NOT NULL, -- 'primeiro_contato', 'resposta', 'followup', 'campanha'
    conteudo TEXT NOT NULL,
    prioridade INT DEFAULT 5, -- 1-10, maior = mais urgente

    status VARCHAR(20) DEFAULT 'pendente', -- 'pendente', 'processando', 'enviada', 'erro'
    tentativas INT DEFAULT 0,
    max_tentativas INT DEFAULT 3,

    agendar_para TIMESTAMPTZ,
    processando_desde TIMESTAMPTZ,
    enviada_em TIMESTAMPTZ,
    erro TEXT,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fila_status_prioridade ON fila_mensagens(status, prioridade DESC, agendar_para);
CREATE INDEX idx_fila_cliente ON fila_mensagens(cliente_id);
```

### 2. Criar serviço de fila

```python
# app/services/fila.py

from datetime import datetime, timedelta
from app.core.supabase import supabase

class FilaService:
    """Gerencia fila de mensagens a enviar."""

    async def enfileirar(
        self,
        cliente_id: str,
        conteudo: str,
        tipo: str,
        conversa_id: str = None,
        prioridade: int = 5,
        agendar_para: datetime = None
    ) -> dict:
        """Adiciona mensagem à fila."""
        return (
            supabase.table("fila_mensagens")
            .insert({
                "cliente_id": cliente_id,
                "conversa_id": conversa_id,
                "conteudo": conteudo,
                "tipo": tipo,
                "prioridade": prioridade,
                "agendar_para": (agendar_para or datetime.utcnow()).isoformat(),
                "status": "pendente"
            })
            .execute()
        ).data[0]

    async def obter_proxima(self) -> dict | None:
        """
        Obtém próxima mensagem para processar.

        Considera:
        - Status pendente
        - Agendamento <= agora
        - Maior prioridade primeiro
        """
        agora = datetime.utcnow()

        # Buscar próxima disponível
        mensagem = (
            supabase.table("fila_mensagens")
            .select("*, clientes(telefone, primeiro_nome)")
            .eq("status", "pendente")
            .lte("agendar_para", agora.isoformat())
            .order("prioridade", desc=True)
            .order("created_at")
            .limit(1)
            .execute()
        ).data

        if not mensagem:
            return None

        mensagem = mensagem[0]

        # Marcar como processando
        supabase.table("fila_mensagens").update({
            "status": "processando",
            "processando_desde": agora.isoformat()
        }).eq("id", mensagem["id"]).execute()

        return mensagem

    async def marcar_enviada(self, mensagem_id: str):
        """Marca mensagem como enviada com sucesso."""
        supabase.table("fila_mensagens").update({
            "status": "enviada",
            "enviada_em": datetime.utcnow().isoformat()
        }).eq("id", mensagem_id).execute()

    async def marcar_erro(self, mensagem_id: str, erro: str):
        """Marca erro e agenda retry se possível."""
        mensagem = (
            supabase.table("fila_mensagens")
            .select("tentativas, max_tentativas")
            .eq("id", mensagem_id)
            .single()
            .execute()
        ).data

        nova_tentativa = mensagem["tentativas"] + 1

        if nova_tentativa < mensagem["max_tentativas"]:
            # Agendar retry com backoff exponencial
            delay = 60 * (2 ** nova_tentativa)  # 2min, 4min, 8min
            novo_agendamento = datetime.utcnow() + timedelta(seconds=delay)

            supabase.table("fila_mensagens").update({
                "status": "pendente",
                "tentativas": nova_tentativa,
                "erro": erro,
                "agendar_para": novo_agendamento.isoformat(),
                "processando_desde": None
            }).eq("id", mensagem_id).execute()
        else:
            # Esgotou tentativas
            supabase.table("fila_mensagens").update({
                "status": "erro",
                "tentativas": nova_tentativa,
                "erro": erro
            }).eq("id", mensagem_id).execute()


fila_service = FilaService()
```

### 3. Worker de processamento

```python
# app/workers/fila_worker.py

import asyncio
from app.services.fila import fila_service
from app.services.whatsapp import whatsapp_service
from app.services.timing import calcular_delay_resposta

async def processar_fila():
    """
    Worker que processa fila de mensagens.

    Roda continuamente, processando uma mensagem por vez
    respeitando rate limiting.
    """
    logger.info("Worker de fila iniciado")

    while True:
        try:
            # Obter próxima mensagem
            mensagem = await fila_service.obter_proxima()

            if not mensagem:
                # Fila vazia, aguardar
                await asyncio.sleep(5)
                continue

            # Verificar rate limiting
            if not await pode_enviar(mensagem["cliente_id"]):
                # Reagendar para depois
                await fila_service.marcar_erro(
                    mensagem["id"],
                    "Rate limit atingido"
                )
                continue

            # Enviar mensagem
            telefone = mensagem["clientes"]["telefone"]
            await whatsapp_service.enviar_com_digitacao(
                telefone=telefone,
                texto=mensagem["conteudo"]
            )

            await fila_service.marcar_enviada(mensagem["id"])
            logger.info(f"Mensagem enviada: {mensagem['id']}")

            # Delay entre envios
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Erro no worker: {e}")
            if mensagem:
                await fila_service.marcar_erro(mensagem["id"], str(e))
            await asyncio.sleep(10)
```

## DoD

- [x] Tabela de fila criada
- [x] Serviço de enfileiramento funciona
- [x] Worker processa fila continuamente
- [x] Rate limiting respeitado
- [x] Retry com backoff exponencial
- [x] Priorização funciona

---

# S5.E2.2 - Agendador de campanhas

## Objetivo

> **Permitir agendar campanhas para execução futura.**

**Resultado esperado:** Campanhas podem ser criadas e agendadas via interface.

## Tarefas

### 1. Endpoint de criação de campanha

```python
# app/routes/campanhas.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/campanhas", tags=["campanhas"])

class CriarCampanha(BaseModel):
    nome: str
    tipo: str  # 'primeiro_contato', 'followup', 'promocional'
    mensagem_template: str
    filtro_especialidades: Optional[List[str]] = None
    filtro_regioes: Optional[List[str]] = None
    filtro_tags: Optional[List[str]] = None
    agendar_para: Optional[datetime] = None
    max_por_dia: int = 50


@router.post("/")
async def criar_campanha(dados: CriarCampanha):
    """Cria nova campanha."""
    # Contar destinatários
    destinatarios = await contar_destinatarios(
        especialidades=dados.filtro_especialidades,
        regioes=dados.filtro_regioes,
        tags=dados.filtro_tags
    )

    campanha = (
        supabase.table("campanhas")
        .insert({
            "nome": dados.nome,
            "tipo": dados.tipo,
            "mensagem_template": dados.mensagem_template,
            "status": "agendada" if dados.agendar_para else "rascunho",
            "total_destinatarios": destinatarios,
            "agendar_para": dados.agendar_para.isoformat() if dados.agendar_para else None,
            "config": {
                "filtro_especialidades": dados.filtro_especialidades,
                "filtro_regioes": dados.filtro_regioes,
                "filtro_tags": dados.filtro_tags,
                "max_por_dia": dados.max_por_dia
            }
        })
        .execute()
    ).data[0]

    return campanha


@router.post("/{campanha_id}/iniciar")
async def iniciar_campanha(campanha_id: str):
    """Inicia execução de campanha."""
    # Atualizar status
    supabase.table("campanhas").update({
        "status": "ativa",
        "iniciada_em": datetime.utcnow().isoformat()
    }).eq("id", campanha_id).execute()

    # Criar envios na fila
    await criar_envios_campanha(campanha_id)

    return {"status": "iniciada"}
```

### 2. Criar envios da campanha

```python
async def criar_envios_campanha(campanha_id: str):
    """Cria envios para todos os destinatários da campanha."""
    campanha = (
        supabase.table("campanhas")
        .select("*")
        .eq("id", campanha_id)
        .single()
        .execute()
    ).data

    config = campanha.get("config", {})

    # Buscar destinatários
    query = supabase.table("clientes").select("id, primeiro_nome, especialidade_nome")

    if config.get("filtro_especialidades"):
        query = query.in_("especialidade_nome", config["filtro_especialidades"])

    if config.get("filtro_regioes"):
        query = query.in_("regiao", config["filtro_regioes"])

    if config.get("filtro_tags"):
        for tag in config["filtro_tags"]:
            query = query.contains("tags", [tag])

    # Excluir optout
    query = query.neq("status", "optout")

    destinatarios = query.execute().data

    # Criar envio para cada destinatário
    for dest in destinatarios:
        # Personalizar mensagem
        mensagem = campanha["mensagem_template"].format(
            nome=dest.get("primeiro_nome", ""),
            especialidade=dest.get("especialidade_nome", "")
        )

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=dest["id"],
            conteudo=mensagem,
            tipo=campanha["tipo"],
            prioridade=3,  # Prioridade baixa para campanhas
            metadata={"campanha_id": campanha_id}
        )

    # Atualizar contagem
    supabase.table("campanhas").update({
        "envios_criados": len(destinatarios)
    }).eq("id", campanha_id).execute()
```

### 3. Job de campanhas agendadas

```python
async def processar_campanhas_agendadas():
    """
    Job que inicia campanhas agendadas.

    Executar a cada minuto.
    """
    agora = datetime.utcnow()

    # Buscar campanhas prontas
    campanhas = (
        supabase.table("campanhas")
        .select("id")
        .eq("status", "agendada")
        .lte("agendar_para", agora.isoformat())
        .execute()
    ).data

    for campanha in campanhas:
        await criar_envios_campanha(campanha["id"])
        supabase.table("campanhas").update({
            "status": "ativa",
            "iniciada_em": agora.isoformat()
        }).eq("id", campanha["id"]).execute()

        logger.info(f"Campanha iniciada: {campanha['id']}")
```

## DoD

- [x] Endpoint de criação funciona
- [x] Filtros por especialidade/região/tags
- [x] Agendamento para data futura
- [x] Job de execução automática
- [x] Mensagens personalizadas por destinatário

---

# S5.E2.3 - Follow-up automático

## Objetivo

> **Enviar follow-up automaticamente para quem não respondeu.**

**Resultado esperado:** Médicos que não responderam recebem lembrete.

## Tarefas

### 1. Definir regras de follow-up

```python
# app/config/followup.py

REGRAS_FOLLOWUP = {
    "primeiro_contato": {
        "dias_ate_followup": 3,
        "max_followups": 2,
        "mensagens": [
            "Oi {nome}! Vi que mandei msg outro dia mas não deu pra gente conversar. Ainda tem interesse em plantão?",
            "E aí {nome}, tudo bem? Só passando pra ver se conseguiu ver as vagas que te mandei. Qualquer coisa só falar!",
        ]
    },
    "pos_interesse": {
        "dias_ate_followup": 1,
        "max_followups": 1,
        "mensagens": [
            "Oi {nome}! Então, conseguiu pensar sobre aquela vaga? To aqui se precisar de mais info!",
        ]
    },
    "pos_oferta": {
        "dias_ate_followup": 2,
        "max_followups": 1,
        "mensagens": [
            "{nome}, a vaga que te ofereci ainda tá aberta! Se tiver interesse me avisa que reservo pra vc",
        ]
    },
}
```

### 2. Criar serviço de follow-up

```python
# app/services/followup.py

from datetime import datetime, timedelta

class FollowupService:

    async def verificar_followups_pendentes(self) -> list:
        """
        Identifica conversas que precisam de follow-up.

        Critérios:
        - Última mensagem foi da Júlia
        - Passou tempo configurado sem resposta
        - Não atingiu max de followups
        """
        pendentes = []

        for tipo, config in REGRAS_FOLLOWUP.items():
            dias = config["dias_ate_followup"]
            data_limite = datetime.utcnow() - timedelta(days=dias)

            # Conversas sem resposta há N dias
            conversas = (
                supabase.table("conversations")
                .select("""
                    id, cliente_id, ultimo_followup_em,
                    clientes(primeiro_nome, telefone),
                    interacoes(direcao, created_at)
                """)
                .eq("status", "ativa")
                .eq("controlled_by", "ai")
                .lt("followups_enviados", config["max_followups"])
                .order("created_at", desc=True)
                .execute()
            ).data

            for conv in conversas:
                # Verificar última mensagem
                interacoes = sorted(
                    conv.get("interacoes", []),
                    key=lambda x: x["created_at"],
                    reverse=True
                )

                if not interacoes:
                    continue

                ultima = interacoes[0]

                # Se última foi da Júlia e passou tempo
                if ultima["direcao"] == "saida":
                    ultima_data = datetime.fromisoformat(ultima["created_at"])
                    if ultima_data < data_limite:
                        pendentes.append({
                            "conversa": conv,
                            "tipo": tipo,
                            "config": config
                        })

        return pendentes

    async def enviar_followup(self, conversa_id: str, tipo: str):
        """Envia mensagem de follow-up."""
        config = REGRAS_FOLLOWUP.get(tipo)
        if not config:
            return

        # Buscar conversa
        conv = (
            supabase.table("conversations")
            .select("*, clientes(primeiro_nome, telefone)")
            .eq("id", conversa_id)
            .single()
            .execute()
        ).data

        # Escolher mensagem (baseado em quantos já enviou)
        followups_enviados = conv.get("followups_enviados", 0)
        if followups_enviados >= len(config["mensagens"]):
            return

        template = config["mensagens"][followups_enviados]
        mensagem = template.format(
            nome=conv["clientes"]["primeiro_nome"]
        )

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=conv["cliente_id"],
            conversa_id=conversa_id,
            conteudo=mensagem,
            tipo="followup",
            prioridade=4
        )

        # Atualizar contador
        supabase.table("conversations").update({
            "followups_enviados": followups_enviados + 1,
            "ultimo_followup_em": datetime.utcnow().isoformat()
        }).eq("id", conversa_id).execute()


followup_service = FollowupService()
```

### 3. Job de follow-up

```python
async def job_followup():
    """
    Job diário de follow-up.

    Executar 1x ao dia, às 10h.
    """
    pendentes = await followup_service.verificar_followups_pendentes()

    logger.info(f"Follow-ups pendentes: {len(pendentes)}")

    for item in pendentes:
        await followup_service.enviar_followup(
            conversa_id=item["conversa"]["id"],
            tipo=item["tipo"]
        )

    # Notificar resumo
    await slack_service.enviar_mensagem({
        "text": f"📩 Follow-ups agendados: {len(pendentes)}"
    })
```

## DoD

- [x] Regras de follow-up configuradas
- [x] Identificação de pendentes funciona
- [x] Mensagens personalizadas
- [x] Limite de follow-ups por conversa
- [x] Job diário executa corretamente

---

# S5.E2.4 - Segmentação de médicos

## Objetivo

> **Permitir segmentar médicos por diversos critérios.**

**Resultado esperado:** Campanhas podem ser direcionadas a segmentos específicos.

## Tarefas

### 1. Definir critérios de segmentação

```python
# app/services/segmentacao.py

class SegmentacaoService:

    CRITERIOS = {
        "especialidade": {
            "campo": "especialidade_nome",
            "operador": "eq"
        },
        "regiao": {
            "campo": "regiao",
            "operador": "eq"
        },
        "status": {
            "campo": "status",
            "operador": "eq"
        },
        "engajamento": {
            "campo": "total_interacoes",
            "operador": "gte"
        },
        "ultimo_contato": {
            "campo": "ultimo_contato_em",
            "operador": "gte"
        },
        "tag": {
            "campo": "tags",
            "operador": "contains"
        },
    }

    async def contar_segmento(self, filtros: dict) -> int:
        """Conta médicos que atendem aos filtros."""
        query = supabase.table("clientes").select("id", count="exact")

        for criterio, valor in filtros.items():
            config = self.CRITERIOS.get(criterio)
            if not config:
                continue

            if config["operador"] == "eq":
                query = query.eq(config["campo"], valor)
            elif config["operador"] == "gte":
                query = query.gte(config["campo"], valor)
            elif config["operador"] == "contains":
                query = query.contains(config["campo"], [valor])

        return query.execute().count

    async def buscar_segmento(self, filtros: dict, limite: int = 1000) -> list:
        """Busca médicos que atendem aos filtros."""
        query = supabase.table("clientes").select("*")

        for criterio, valor in filtros.items():
            config = self.CRITERIOS.get(criterio)
            if not config:
                continue

            if config["operador"] == "eq":
                query = query.eq(config["campo"], valor)
            elif config["operador"] == "gte":
                query = query.gte(config["campo"], valor)
            elif config["operador"] == "contains":
                query = query.contains(config["campo"], [valor])

        query = query.neq("status", "optout").limit(limite)
        return query.execute().data


segmentacao_service = SegmentacaoService()
```

### 2. Endpoint de preview de segmento

```python
# app/routes/campanhas.py (adicionar)

@router.post("/segmento/preview")
async def preview_segmento(filtros: dict):
    """
    Preview de um segmento antes de criar campanha.

    Retorna contagem e amostra de médicos.
    """
    total = await segmentacao_service.contar_segmento(filtros)
    amostra = await segmentacao_service.buscar_segmento(filtros, limite=10)

    return {
        "total": total,
        "amostra": [
            {
                "nome": m["primeiro_nome"],
                "especialidade": m.get("especialidade_nome"),
                "regiao": m.get("regiao")
            }
            for m in amostra
        ]
    }
```

### 3. Segmentos pré-definidos

```python
SEGMENTOS_PREDEFINIDOS = {
    "novos_7_dias": {
        "nome": "Novos últimos 7 dias",
        "filtros": {
            "ultimo_contato": (datetime.now() - timedelta(days=7)).isoformat()
        }
    },
    "engajados": {
        "nome": "Médicos engajados",
        "filtros": {
            "engajamento": 5  # >= 5 interações
        }
    },
    "inativos_30_dias": {
        "nome": "Inativos há 30 dias",
        "filtros": {
            "ultimo_contato": (datetime.now() - timedelta(days=30)).isoformat()
        }
    },
    "anestesistas_abc": {
        "nome": "Anestesistas do ABC",
        "filtros": {
            "especialidade": "Anestesiologia",
            "regiao": "abc"
        }
    },
}
```

## DoD

- [x] Critérios de segmentação definidos
- [x] Contagem de segmento funciona
- [x] Busca de segmento funciona
- [x] Preview disponível via API
- [x] Segmentos pré-definidos configurados

---

# S5.E2.5 - Relatório de campanhas

## Objetivo

> **Gerar relatórios detalhados de performance de campanhas.**

**Resultado esperado:** Métricas de cada campanha disponíveis.

## Tarefas

### 1. Coletar métricas da campanha

```python
# app/services/metricas_campanha.py

async def calcular_metricas_campanha(campanha_id: str) -> dict:
    """Calcula métricas de uma campanha."""

    # Buscar envios
    envios = (
        supabase.table("fila_mensagens")
        .select("status")
        .eq("metadata->campanha_id", campanha_id)
        .execute()
    ).data

    # Buscar conversas iniciadas
    campanha = (
        supabase.table("campanhas")
        .select("*")
        .eq("id", campanha_id)
        .single()
        .execute()
    ).data

    # Médicos que responderam
    destinatarios = await obter_destinatarios_campanha(campanha_id)
    conversas = (
        supabase.table("conversations")
        .select("cliente_id")
        .in_("cliente_id", [d["id"] for d in destinatarios])
        .gte("created_at", campanha.get("iniciada_em"))
        .execute()
    ).data

    responderam = set(c["cliente_id"] for c in conversas)

    # Calcular métricas
    total_enviados = len([e for e in envios if e["status"] == "enviada"])
    total_erros = len([e for e in envios if e["status"] == "erro"])
    total_pendentes = len([e for e in envios if e["status"] == "pendente"])

    return {
        "campanha_id": campanha_id,
        "nome": campanha["nome"],
        "status": campanha["status"],
        "envios": {
            "total": len(envios),
            "enviados": total_enviados,
            "erros": total_erros,
            "pendentes": total_pendentes,
            "taxa_entrega": total_enviados / len(envios) if envios else 0
        },
        "respostas": {
            "total": len(responderam),
            "taxa": len(responderam) / total_enviados if total_enviados > 0 else 0
        },
        "periodo": {
            "inicio": campanha.get("iniciada_em"),
            "fim": campanha.get("finalizada_em")
        }
    }
```

### 2. Endpoint de relatório

```python
@router.get("/{campanha_id}/relatorio")
async def relatorio_campanha(campanha_id: str):
    """Retorna relatório completo da campanha."""
    metricas = await calcular_metricas_campanha(campanha_id)

    # Adicionar detalhes
    metricas["detalhes"] = {
        "top_respondedores": await obter_top_respondedores(campanha_id, 10),
        "erros_comuns": await obter_erros_comuns(campanha_id),
    }

    return metricas


@router.get("/{campanha_id}/relatorio/csv")
async def exportar_relatorio_csv(campanha_id: str):
    """Exporta relatório em CSV."""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    metricas = await calcular_metricas_campanha(campanha_id)
    destinatarios = await obter_destinatarios_campanha(campanha_id)

    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nome", "Telefone", "Especialidade", "Status Envio", "Respondeu"])

    for dest in destinatarios:
        writer.writerow([
            dest["primeiro_nome"],
            dest["telefone"],
            dest.get("especialidade_nome"),
            dest.get("status_envio"),
            "Sim" if dest.get("respondeu") else "Não"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=campanha_{campanha_id}.csv"}
    )
```

## DoD

- [x] Métricas de envio calculadas
- [x] Taxa de resposta calculada
- [x] Endpoint de relatório funciona
- [ ] Exportação CSV disponível (opcional)
- [x] Detalhes de erros incluídos
