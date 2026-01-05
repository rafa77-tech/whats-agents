# Epic 03: Meta Policies RAG

**Status:** ✅ Completo

**Arquivos criados:**
- `app/services/warmer/meta_rag.py`

---

## Objetivo

Implementar sistema **RAG (Retrieval Augmented Generation)** para:
- Armazenar politicas Meta/WhatsApp Business
- Consultar politicas relevantes antes de acoes
- Manter base atualizada
- Verificar conformidade de acoes

## Contexto

**Por que RAG de Politicas?**

| Problema | Solucao |
|----------|---------|
| Politicas mudam frequentemente | Base atualizavel |
| Muitas regras para memorizar | Consulta por similaridade |
| Risco de ban por desconhecimento | Verificacao automatica |
| Diferentes contextos | Busca semantica |

**Fontes de Politicas:**
- WhatsApp Business Policy
- Meta Business Help Center
- 360Dialog Docs
- Turn.io Learn
- Experiencia de mercado

---

## Story 3.1: Seed de Politicas

### Objetivo
Popular banco com politicas iniciais.

### Implementacao

**Arquivo:** `app/services/meta_rag/policies_seed.py`

```python
"""
Seed de Politicas Meta.

Politicas iniciais extraidas de documentacao oficial e boas praticas.
"""

POLITICAS_SEED = [
    # ══════════════════════════════════════════════════════════
    # LIMITES DE MENSAGENS
    # ══════════════════════════════════════════════════════════
    {
        "categoria": "limites",
        "titulo": "Tiers de Limite de Mensagens",
        "conteudo": """
Limites de mensagens por dia (desde Outubro 2025):

- Tier 1: 1.000 destinatarios unicos/dia (inicial)
- Tier 2: 10.000 destinatarios unicos/dia
- Tier 3: 100.000 destinatarios unicos/dia
- Unlimited: Sem limite (empresas verificadas)

IMPORTANTE (Outubro 2025): O limite e compartilhado por todo o PORTFOLIO
(todos os numeros da empresa), nao mais por numero individual.

Para subir de tier:
- Quality rating media ou alta
- Usar pelo menos 50% do limite atual por 7 dias
- Enviar mensagens de alta qualidade
- Sem violacoes de politicas nos ultimos 7 dias
        """,
        "fonte_url": "https://docs.360dialog.com/docs/waba-management/capacity-quality-rating-and-messaging-limits",
        "fonte_nome": "360Dialog Docs",
    },
    {
        "categoria": "limites",
        "titulo": "Mensagens Iniciadas vs Respostas",
        "conteudo": """
Os limites se aplicam apenas a mensagens INICIADAS pelo negocio (outbound).

Respostas a mensagens de clientes (inbound) NAO contam para o limite.
Desde 2024, conversas iniciadas pelo usuario sao gratuitas.

Implicacao pratica:
- Prospeccao consome limite
- Follow-up consome limite
- Resposta a medico que mandou msg primeiro NAO consome

Estrategia: Priorizar respostas sobre prospeccao quando proximo do limite.
        """,
        "fonte_url": "https://learn.turn.io/l/en/article/uvdz8tz40l-quality-ratings-and-messaging-limits",
        "fonte_nome": "Turn.io Learn",
    },
    {
        "categoria": "limites",
        "titulo": "Janela de 24 Horas",
        "conteudo": """
Apos usuario responder, abre-se uma JANELA DE 24 HORAS para envio livre.

Durante a janela:
- Pode enviar mensagens de forma livre (free-form)
- Nao precisa usar templates aprovados
- Pode enviar midias, links, etc

Apos a janela fechar:
- Precisa usar template aprovado
- Ou aguardar usuario iniciar nova conversa

Para Julia:
- Aproveitar janela para engajamento
- Evitar deixar janela fechar sem resolver demanda
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },

    # ══════════════════════════════════════════════════════════
    # QUALITY RATING
    # ══════════════════════════════════════════════════════════
    {
        "categoria": "quality_rating",
        "titulo": "Sistema de Quality Rating",
        "conteudo": """
Quality Rating determina se voce pode subir de tier:

- Verde (Alta): Pode subir de tier
- Amarelo (Media): Mantem tier atual
- Vermelho (Baixa): Nao sobe de tier

MUDANCA OUTUBRO 2025: Qualidade baixa NAO causa mais downgrade de tier.
Apenas impede subir para o proximo tier.

Fatores que afetam qualidade (peso maior para eventos recentes):
- Bloqueios por usuarios (muito peso)
- Denuncias de spam (muito peso)
- Taxa de leitura das mensagens
- Feedback negativo nos ultimos 7 dias
        """,
        "fonte_url": "https://docs.360dialog.com/partner/messaging-and-calling/messaging-health-and-troubleshooting/messaging-limits-and-quality-rating",
        "fonte_nome": "360Dialog Partner Docs",
    },
    {
        "categoria": "quality_rating",
        "titulo": "Como Melhorar Quality Rating",
        "conteudo": """
Acoes para melhorar qualidade:

1. REDUZIR BLOQUEIOS
   - Enviar apenas para contatos que esperam suas mensagens
   - Personalizar mensagens (nao parecer spam)
   - Oferecer opt-out claro

2. REDUZIR DENUNCIAS
   - Nao enviar conteudo repetitivo
   - Respeitar horarios (8h-20h)
   - Nao insistir apos "nao"

3. AUMENTAR ENGAJAMENTO
   - Mensagens relevantes e uteis
   - Perguntas abertas
   - Conteudo de valor

4. TEMPO
   - Rating melhora naturalmente se parar de ter problemas
   - Peso maior para eventos recentes (ultimos 7 dias)
        """,
        "fonte_url": "https://docs.360dialog.com",
        "fonte_nome": "360Dialog Docs",
    },

    # ══════════════════════════════════════════════════════════
    # MOTIVOS DE BAN
    # ══════════════════════════════════════════════════════════
    {
        "categoria": "motivos_ban",
        "titulo": "Principais Motivos de Ban",
        "conteudo": """
Motivos que levam a ban/restricao (em ordem de gravidade):

1. SPAM: Mensagens em massa nao solicitadas
   - Muitas mensagens para contatos que nao conhecem voce
   - Conteudo repetitivo em escala

2. AUTOMACAO NAO AUTORIZADA: Bots sem API oficial
   - Usar apps modificados (GB WhatsApp, WhatsApp Plus)
   - Automacao sem usar Business API

3. FEEDBACK NEGATIVO: Muitos usuarios bloqueando/denunciando
   - Taxa de bloqueio > 2-3%
   - Denuncias de spam

4. CONTEUDO PROIBIDO: Ver lista de proibicoes
   - Armas, drogas, adulto, jogos de azar

5. VOLUME SUSPEITO: Muitas mensagens em curto periodo
   - Picos de envio anormais
   - Muitos contatos novos de uma vez

Estatistica: 6.8 milhoes de contas banidas no 1o semestre de 2025.
        """,
        "fonte_url": "https://support.wati.io/en/articles/11463217",
        "fonte_nome": "Wati.io Help Center",
    },
    {
        "categoria": "motivos_ban",
        "titulo": "Sinais de Automacao Detectados",
        "conteudo": """
WhatsApp usa machine learning para detectar automacao:

SINAIS DETECTADOS:
- Mensagens muito rapidas (sem delay humano)
- Padroes repetitivos de texto
- Horarios nao humanos (3h da manha)
- Ausencia de indicador 'digitando'
- Proporcao muito alta de enviadas vs recebidas
- Muitos contatos novos em pouco tempo
- Mensagens identicas para multiplos contatos

COMO EVITAR:
- Delays aleatorios entre 45-180 segundos
- Variar texto das mensagens
- Enviar apenas em horario comercial
- Mostrar 'digitando' antes de enviar
- Manter proporcao saudavel enviadas/recebidas
- Crescer base de contatos gradualmente
        """,
        "fonte_url": "https://whautomate.com/top-reasons-why-whatsapp-accounts-get-banned-in-2025-and-how-to-avoid-them/",
        "fonte_nome": "WhAutomate Blog",
    },

    # ══════════════════════════════════════════════════════════
    # BOAS PRATICAS
    # ══════════════════════════════════════════════════════════
    {
        "categoria": "boas_praticas",
        "titulo": "Boas Praticas de Messaging",
        "conteudo": """
Recomendacoes oficiais da Meta:

1. CONSENTIMENTO: Obter opt-in explicito antes de enviar
   - Nao comprar listas de contatos
   - Registrar quando/como obteve consentimento

2. UNSUBSCRIBE: Incluir opcao de descadastro
   - "Responda SAIR para nao receber mais"
   - Respeitar imediatamente

3. PERSONALIZACAO: Mensagens relevantes e personalizadas
   - Usar nome do contato
   - Referenciar contexto anterior

4. FREQUENCIA: Nao bombardear
   - Max 1-2 msgs/dia por contato (prospeccao)
   - Respostas nao tem limite

5. HORARIO: Enviar em horario comercial
   - 8h-20h em dias uteis
   - Evitar fins de semana para prospeccao

6. RESPOSTA RAPIDA: Responder dentro de 24h
   - Idealmente em minutos
   - Nunca deixar sem resposta

7. HUMANO DISPONIVEL: Oferecer encaminhamento
   - "Quer falar com alguem da equipe?"
   - Nao forcar interacao com bot
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },
    {
        "categoria": "boas_praticas",
        "titulo": "Warm-up de Numero Novo",
        "conteudo": """
Para numeros novos, seguir processo de warm-up:

SEMANA 1 (Setup):
- Preencher perfil completo
- Adicionar foto de perfil
- Status com informacoes da empresa
- NAO enviar mensagens em massa

SEMANA 2 (Primeiros Contatos):
- Conversar com contatos conhecidos
- Max 5-10 msgs/dia
- Foco em receber respostas

SEMANAS 3-4 (Expansao):
- Aumentar gradualmente
- Max 20-30 msgs/dia
- Manter taxa de resposta > 20%

SEMANAS 5+ (Operacao):
- Aumentar conforme quality rating
- Monitorar metricas constantemente
- Pausar se quality cair

REGRA: Numero novo + volume alto = BAN
        """,
        "fonte_url": "https://gallabox.com/blog/whatsapp-business-account-blocked",
        "fonte_nome": "Gallabox Blog",
    },

    # ══════════════════════════════════════════════════════════
    # PROIBICOES
    # ══════════════════════════════════════════════════════════
    {
        "categoria": "proibicoes",
        "titulo": "Conteudo Absolutamente Proibido",
        "conteudo": """
NAO enviar mensagens sobre (ban permanente):

PRODUTOS PROIBIDOS:
- Armas de fogo e municao
- Drogas e substancias controladas
- Produtos medicos restritos (sem receita)
- Animais vivos (exceto gado)
- Especies ameacadas
- Produtos roubados/falsificados

SERVICOS PROIBIDOS:
- Jogos de azar com dinheiro real
- Conteudo adulto/sexual
- Servicos de acompanhantes
- Servicos de encontros romanticos
- Marketing multinivel/piramide
- Credito consignado/adiantamento salario

CONTEUDO PROIBIDO:
- Discriminacao (raca, genero, religiao)
- Informacoes falsas/enganosas
- Incitacao a violencia
- Ameacas ou assedio

Violacao = ban PERMANENTE e possivel acao legal.
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },
    {
        "categoria": "proibicoes",
        "titulo": "Praticas de Marketing Proibidas",
        "conteudo": """
Praticas que resultam em ban:

1. COMPRA DE LISTAS
   - Enviar para contatos que nao conhecem voce
   - Usar listas de terceiros

2. SCRAPING
   - Coletar numeros de sites/redes sociais
   - Usar bots para extrair contatos

3. SPAM EM GRUPOS
   - Entrar em grupos so para divulgar
   - Enviar links sem contexto

4. MENSAGENS ENGANOSAS
   - Fingir ser outra empresa
   - Falsas urgencias ("ULTIMO DIA!")
   - Promessas que nao pode cumprir

5. IGNORAR OPT-OUT
   - Continuar enviando apos "SAIR"
   - Nao oferecer opcao de descadastro

6. AUTOMACAO AGRESSIVA
   - Responder instantaneamente sempre
   - Mensagens 24/7
   - Mesmo texto para todos
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },
]
```

### DoD

- [x] Todas as politicas documentadas
- [x] Categorias consistentes
- [x] Fontes referenciadas

---

## Story 3.2: Servico de RAG

### Objetivo
Implementar consulta e verificacao de politicas.

### Implementacao

**Arquivo:** `app/services/meta_rag/service.py`

```python
"""
Meta Policies RAG Service.

Consulta e verificacao de conformidade com politicas Meta.
"""
import logging
from typing import List, Optional
from datetime import date

from app.services.supabase import supabase
from app.services.embeddings import gerar_embedding
from app.services.meta_rag.policies_seed import POLITICAS_SEED

logger = logging.getLogger(__name__)


class MetaPoliciesRAG:
    """Servico RAG de Politicas Meta."""

    async def seed_politicas(self):
        """
        Popula banco com politicas iniciais.

        Idempotente - atualiza se ja existir.
        """
        count = 0
        for politica in POLITICAS_SEED:
            try:
                # Gerar embedding
                texto_completo = f"{politica['titulo']}\n\n{politica['conteudo']}"
                embedding = await gerar_embedding(texto_completo)

                # Upsert no banco
                supabase.table("meta_policies").upsert({
                    "categoria": politica["categoria"],
                    "titulo": politica["titulo"],
                    "conteudo": politica["conteudo"],
                    "fonte_url": politica.get("fonte_url"),
                    "fonte_nome": politica.get("fonte_nome"),
                    "embedding": embedding,
                }, on_conflict="titulo").execute()

                count += 1

            except Exception as e:
                logger.error(f"[MetaRAG] Erro ao inserir '{politica['titulo']}': {e}")

        logger.info(f"[MetaRAG] {count}/{len(POLITICAS_SEED)} politicas inseridas/atualizadas")
        return count

    async def consultar(
        self,
        pergunta: str,
        categoria: Optional[str] = None,
        limite: int = 5,
        threshold: float = 0.7,
    ) -> List[dict]:
        """
        Consulta politicas relevantes via RAG.

        Args:
            pergunta: Texto da consulta
            categoria: Filtrar por categoria (opcional)
            limite: Max resultados
            threshold: Similaridade minima

        Returns:
            Lista de politicas relevantes com similarity score
        """
        # Gerar embedding da pergunta
        query_embedding = await gerar_embedding(pergunta)

        # Buscar similares via funcao SQL
        result = supabase.rpc(
            "match_meta_policies",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limite,
                "filter_categoria": categoria,
            }
        ).execute()

        politicas = result.data or []

        logger.debug(
            f"[MetaRAG] Consulta '{pergunta[:50]}...' retornou {len(politicas)} resultados"
        )

        return politicas

    async def verificar_acao(self, acao: str) -> dict:
        """
        Verifica se uma acao esta em conformidade com politicas.

        Args:
            acao: Descricao da acao (ex: "enviar 100 mensagens de prospeccao")

        Returns:
            {
                "permitido": bool,
                "risco": "baixo" | "medio" | "alto" | "proibido",
                "alertas": ["..."],
                "recomendacoes": ["..."],
                "politicas_relacionadas": [...]
            }
        """
        # Consultar politicas relacionadas
        politicas = await self.consultar(acao, limite=5, threshold=0.6)

        # Analise basica de risco
        alertas = []
        recomendacoes = []
        risco = "baixo"

        # Verificar palavras-chave de risco
        acao_lower = acao.lower()

        # Alto risco - proibido
        if any(termo in acao_lower for termo in [
            "armas", "drogas", "adulto", "jogos de azar", "piramide"
        ]):
            risco = "proibido"
            alertas.append("Conteudo proibido detectado")

        # Alto risco - spam
        elif any(termo in acao_lower for termo in [
            "massa", "spam", "lista comprada", "scraping"
        ]):
            risco = "alto"
            alertas.append("Possivel violacao de politica anti-spam")

        # Medio risco - volume
        elif any(termo in acao_lower for termo in [
            "100 mensagens", "200 mensagens", "enviar para todos"
        ]):
            risco = "medio"
            alertas.append("Volume alto pode afetar quality rating")
            recomendacoes.append("Distribuir envios ao longo do dia")

        # Adicionar recomendacoes das politicas encontradas
        for p in politicas[:3]:
            if p.get("similarity", 0) > 0.8:
                # Politica muito relevante
                if "proibido" in p.get("conteudo", "").lower():
                    risco = "alto"
                    alertas.append(f"Verificar: {p['titulo']}")

        return {
            "permitido": risco != "proibido",
            "risco": risco,
            "alertas": alertas,
            "recomendacoes": recomendacoes,
            "politicas_relacionadas": politicas,
        }

    async def obter_limites_atuais(self) -> dict:
        """
        Retorna informacoes sobre limites de mensagens.

        Returns:
            Dict com tiers e recomendacoes
        """
        # Buscar politica especifica
        result = supabase.table("meta_policies").select("*").eq(
            "titulo", "Tiers de Limite de Mensagens"
        ).single().execute()

        if result.data:
            return {
                "conteudo": result.data["conteudo"],
                "fonte": result.data.get("fonte_url"),
                "atualizado_em": result.data.get("updated_at"),
            }

        return {"conteudo": "Politica nao encontrada", "fonte": None}

    async def obter_boas_praticas(self, contexto: str) -> List[dict]:
        """
        Retorna boas praticas relevantes para um contexto.

        Args:
            contexto: Ex: "prospeccao fria", "follow-up", "warm-up"

        Returns:
            Lista de boas praticas
        """
        return await self.consultar(
            f"boas praticas para {contexto}",
            categoria="boas_praticas",
            limite=3
        )

    async def listar_proibicoes(self) -> List[dict]:
        """
        Lista todas as proibicoes.

        Returns:
            Lista de politicas de proibicao
        """
        result = supabase.table("meta_policies").select("*").eq(
            "categoria", "proibicoes"
        ).execute()

        return result.data or []


# Singleton
meta_rag = MetaPoliciesRAG()
```

### DoD

- [x] Seed funcionando
- [x] Consulta RAG funcionando
- [x] Verificacao de acao
- [x] Metodos auxiliares

---

## Story 3.3: Endpoints API

### Objetivo
Expor RAG via API para consultas.

### Implementacao

**Arquivo:** `app/api/routes/meta_rag.py`

```python
"""
Endpoints para Meta Policies RAG.
"""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.meta_rag.service import meta_rag

router = APIRouter(prefix="/meta-policies", tags=["meta-rag"])


@router.get("/consultar")
async def consultar_politicas(
    pergunta: str = Query(..., description="Texto da consulta"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    limite: int = Query(5, ge=1, le=20),
):
    """
    Consulta politicas Meta via RAG.

    Categorias: limites, proibicoes, boas_praticas, motivos_ban, quality_rating
    """
    return await meta_rag.consultar(pergunta, categoria, limite)


@router.post("/verificar-acao")
async def verificar_acao(acao: str):
    """
    Verifica se uma acao esta em conformidade.

    Retorna nivel de risco e alertas.
    """
    return await meta_rag.verificar_acao(acao)


@router.get("/limites")
async def obter_limites():
    """Retorna informacoes sobre limites de mensagens."""
    return await meta_rag.obter_limites_atuais()


@router.get("/boas-praticas")
async def obter_boas_praticas(
    contexto: str = Query(..., description="Ex: prospeccao, follow-up, warm-up")
):
    """Retorna boas praticas para um contexto."""
    return await meta_rag.obter_boas_praticas(contexto)


@router.get("/proibicoes")
async def listar_proibicoes():
    """Lista todas as proibicoes."""
    return await meta_rag.listar_proibicoes()


@router.post("/seed")
async def seed_politicas():
    """
    Popula/atualiza banco com politicas.

    Usar apos atualizacoes de politicas Meta.
    """
    count = await meta_rag.seed_politicas()
    return {"status": "ok", "politicas_atualizadas": count}
```

### DoD

- [x] Endpoints funcionando
- [x] Documentacao OpenAPI

---

## Story 3.4: Job de Atualizacao

### Objetivo
Atualizar politicas periodicamente.

### Implementacao

**Arquivo:** `app/workers/meta_rag_updater.py`

```python
"""
Job para atualizar politicas Meta.

Roda semanalmente para garantir que base esta atualizada.
"""
import logging
from datetime import datetime

from app.services.meta_rag.service import meta_rag
from app.services.notificacoes import notificar_slack

logger = logging.getLogger(__name__)


async def atualizar_politicas():
    """
    Job semanal de atualizacao.

    TODO: Implementar scraping de fontes oficiais.
    Por enquanto, apenas re-aplica seed.
    """
    logger.info("[MetaRAG Updater] Iniciando atualizacao semanal")

    try:
        count = await meta_rag.seed_politicas()

        await notificar_slack(
            f":page_facing_up: *Politicas Meta atualizadas*: {count} politicas",
            canal="operacoes"
        )

        logger.info(f"[MetaRAG Updater] {count} politicas atualizadas")

    except Exception as e:
        logger.error(f"[MetaRAG Updater] Erro: {e}")

        await notificar_slack(
            f":warning: *Erro ao atualizar politicas Meta*: {str(e)}",
            canal="alertas"
        )


# Registrar no scheduler
# scheduler.add_job(atualizar_politicas, 'cron', day_of_week='mon', hour=3)
```

### DoD

- [x] Job funcionando
- [x] Notificacoes configuradas

---

## Checklist do Epico

- [x] **E03.1** - Seed de politicas completo
- [x] **E03.2** - Servico RAG funcionando
- [x] **E03.3** - Endpoints API
- [x] **E03.4** - Job de atualizacao
- [x] Embeddings gerando corretamente
- [x] Busca por similaridade funcionando
- [x] Verificacao de conformidade

---

## Exemplo de Uso

```python
# Consultar antes de enviar prospeccao
verificacao = await meta_rag.verificar_acao(
    "enviar 50 mensagens de prospeccao para medicos que nunca contactei"
)

if not verificacao["permitido"]:
    logger.warning(f"Acao bloqueada: {verificacao['alertas']}")
    return

if verificacao["risco"] == "alto":
    # Reduzir volume
    pass

# Buscar boas praticas para contexto
praticas = await meta_rag.obter_boas_praticas("prospeccao fria")

# Consulta livre
resultados = await meta_rag.consultar(
    "como evitar ser detectado como spam?",
    categoria="boas_praticas"
)
```
