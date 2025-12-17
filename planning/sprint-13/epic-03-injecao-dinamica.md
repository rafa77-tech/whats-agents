# Epic 03: Injeção Dinâmica de Contexto

## Objetivo

Integrar detectores e buscador com o PromptBuilder para injetar conhecimento relevante nos prompts da Julia automaticamente.

## Contexto

Com os épicos anteriores temos:
- E01: Base de conhecimento indexada (~100+ chunks)
- E02: Detectores que identificam situação (objeção, perfil, objetivo)

Agora precisamos:
1. Buscar conhecimento baseado na análise
2. Injetar no prompt de forma eficiente
3. Não poluir o contexto com informações irrelevantes

## Pré-requisitos

- [x] E01 concluído (base indexada)
- [x] E02 concluído (detectores funcionando)
- [x] `app/prompts/builder.py` existente

---

## Story 3.1: Serviço de Busca de Conhecimento Relevante

### Objetivo
Criar serviço que usa análise do orquestrador para buscar conhecimento específico.

### Tarefas

1. **Criar** `app/services/conhecimento/injetor.py`:
```python
"""
Injetor de conhecimento nos prompts.

Usa análise conversacional para buscar e formatar conhecimento relevante.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from .orquestrador import AnaliseConversacional, ContextoMedico, OrquestradorDeteccao
from .buscador import BuscadorConhecimento, ResultadoBusca

logger = logging.getLogger(__name__)

# Limites para evitar contexto muito grande
MAX_CHUNKS_OBJECAO = 2
MAX_CHUNKS_PERFIL = 2
MAX_CHUNKS_EXEMPLO = 1
MAX_CARACTERES_TOTAL = 2000


@dataclass
class ConhecimentoInjetado:
    """Conhecimento pronto para injeção no prompt."""
    texto: str
    chunks_usados: int
    tipos_usados: list[str]
    latencia_ms: float


class InjetorConhecimento:
    """
    Busca e formata conhecimento para injeção em prompts.

    Uso:
        injetor = InjetorConhecimento()
        conhecimento = await injetor.buscar_para_situacao(
            mensagem="Vocês pagam muito pouco",
            contexto=ContextoMedico(anos_formacao=20),
            primeira_mensagem=False,
            num_interacoes=5
        )
        # conhecimento.texto pode ser adicionado ao prompt
    """

    def __init__(self):
        self.orquestrador = OrquestradorDeteccao()
        self.buscador = BuscadorConhecimento()

    async def buscar_para_situacao(
        self,
        mensagem: str,
        contexto: ContextoMedico,
        primeira_mensagem: bool = False,
        num_interacoes: int = 0,
        vaga_oferecida: bool = False
    ) -> ConhecimentoInjetado:
        """
        Busca conhecimento relevante para a situação.

        Args:
            mensagem: Última mensagem do médico
            contexto: Contexto conhecido
            primeira_mensagem: Se é primeira interação
            num_interacoes: Total de trocas
            vaga_oferecida: Se já oferecemos vaga

        Returns:
            Conhecimento formatado para injeção
        """
        import time
        inicio = time.time()

        # 1. Analisar situação
        analise = self.orquestrador.analisar(
            mensagem=mensagem,
            contexto=contexto,
            primeira_mensagem=primeira_mensagem,
            num_interacoes=num_interacoes,
            vaga_oferecida=vaga_oferecida
        )

        # 2. Coletar chunks relevantes
        chunks: list[ResultadoBusca] = []
        tipos_usados = []

        # 2.1 Conhecimento sobre objeção
        if analise.precisa_conhecimento_objecao:
            objecao_chunks = await self.buscador.buscar_para_objecao(mensagem)
            chunks.extend(objecao_chunks[:MAX_CHUNKS_OBJECAO])
            if objecao_chunks:
                tipos_usados.append(f"objecao:{analise.objecao.tipo.value}")

        # 2.2 Conhecimento sobre perfil
        if analise.precisa_conhecimento_perfil:
            perfil_chunks = await self.buscador.buscar_para_perfil(
                analise.perfil.perfil.value
            )
            chunks.extend(perfil_chunks[:MAX_CHUNKS_PERFIL])
            if perfil_chunks:
                tipos_usados.append(f"perfil:{analise.perfil.perfil.value}")

        # 2.3 Exemplos de conversa
        if analise.precisa_exemplos:
            # Construir query contextual
            query_exemplo = f"{analise.objetivo.objetivo.value} {mensagem[:100]}"
            exemplo_chunks = await self.buscador.buscar_exemplos_conversa(query_exemplo)
            chunks.extend(exemplo_chunks[:MAX_CHUNKS_EXEMPLO])
            if exemplo_chunks:
                tipos_usados.append("exemplo")

        # 3. Formatar para prompt
        texto = self._formatar_para_prompt(chunks, analise)

        latencia = (time.time() - inicio) * 1000

        logger.info(
            f"Conhecimento injetado: {len(chunks)} chunks, "
            f"{len(texto)} chars, {latencia:.0f}ms"
        )

        return ConhecimentoInjetado(
            texto=texto,
            chunks_usados=len(chunks),
            tipos_usados=tipos_usados,
            latencia_ms=latencia
        )

    def _formatar_para_prompt(
        self,
        chunks: list[ResultadoBusca],
        analise: AnaliseConversacional
    ) -> str:
        """Formata chunks para injeção no prompt."""
        if not chunks:
            return ""

        partes = ["[CONHECIMENTO RELEVANTE PARA ESTA SITUAÇÃO]"]

        # Adicionar resumo da análise
        partes.append(f"Situação: {analise.resumo}")
        partes.append("")

        # Adicionar chunks
        caracteres_usados = 0
        for chunk in chunks:
            # Limitar para não estourar contexto
            if caracteres_usados + len(chunk.conteudo) > MAX_CARACTERES_TOTAL:
                partes.append("(conhecimento adicional omitido por limite)")
                break

            partes.append(f"--- {chunk.tipo.upper()}: {chunk.secao} ---")
            partes.append(chunk.conteudo)
            partes.append("")
            caracteres_usados += len(chunk.conteudo)

        partes.append("[FIM DO CONHECIMENTO]")

        return "\n".join(partes)

    async def buscar_rapido(
        self,
        query: str,
        tipo: Optional[str] = None,
        limite: int = 2
    ) -> str:
        """
        Busca rápida de conhecimento (sem análise completa).

        Útil para buscas específicas ad-hoc.

        Args:
            query: Texto de busca
            tipo: Tipo opcional (objecao, perfil, etc)
            limite: Máximo de resultados

        Returns:
            Texto formatado
        """
        chunks = await self.buscador.buscar(query, tipo=tipo, limite=limite)

        if not chunks:
            return ""

        partes = []
        for chunk in chunks:
            partes.append(f"[{chunk.tipo}] {chunk.conteudo[:500]}")

        return "\n\n".join(partes)
```

### DoD

- [ ] `InjetorConhecimento` implementado
- [ ] Integra orquestrador + buscador
- [ ] Respeita limites de tamanho (MAX_CARACTERES_TOTAL)
- [ ] Formato claro para prompt
- [ ] Latência registrada em logs
- [ ] Método `buscar_rapido()` para uso ad-hoc

### Testes

```python
# tests/conhecimento/test_injetor.py
import pytest
from app.services.conhecimento.injetor import InjetorConhecimento, ConhecimentoInjetado
from app.services.conhecimento import ContextoMedico

@pytest.fixture
def injetor():
    return InjetorConhecimento()

@pytest.mark.asyncio
async def test_buscar_para_objecao(injetor):
    """Busca conhecimento para objeção."""
    result = await injetor.buscar_para_situacao(
        mensagem="Vocês pagam muito pouco",
        contexto=ContextoMedico(anos_formacao=10),
        primeira_mensagem=False,
        num_interacoes=5
    )

    assert isinstance(result, ConhecimentoInjetado)
    assert "objecao" in str(result.tipos_usados).lower()
    assert result.latencia_ms > 0

@pytest.mark.asyncio
async def test_buscar_para_senior(injetor):
    """Busca conhecimento para médico sênior."""
    result = await injetor.buscar_para_situacao(
        mensagem="Me conta mais",
        contexto=ContextoMedico(anos_formacao=25),
        primeira_mensagem=False,
        num_interacoes=3
    )

    assert "perfil:senior" in str(result.tipos_usados).lower()

@pytest.mark.asyncio
async def test_primeira_mensagem_sem_conhecimento(injetor):
    """Primeira mensagem não precisa de muito conhecimento."""
    result = await injetor.buscar_para_situacao(
        mensagem="Oi",
        contexto=ContextoMedico(),
        primeira_mensagem=True,
        num_interacoes=0
    )

    # Primeira mensagem = prospectar, sem objeção
    assert result.chunks_usados <= 2

@pytest.mark.asyncio
async def test_respeita_limite_caracteres(injetor):
    """Não ultrapassa limite de caracteres."""
    result = await injetor.buscar_para_situacao(
        mensagem="Vocês pagam pouco e não tenho tempo e não confio",
        contexto=ContextoMedico(anos_formacao=20),
        primeira_mensagem=False,
        num_interacoes=10
    )

    assert len(result.texto) <= 2500  # MAX + formatação

@pytest.mark.asyncio
async def test_buscar_rapido(injetor):
    """Busca rápida funciona."""
    result = await injetor.buscar_rapido("como negociar valor", tipo="objecao")

    assert isinstance(result, str)
```

---

## Story 3.2: Integração com PromptBuilder

### Objetivo
Adicionar método `com_conhecimento()` ao PromptBuilder para injeção automática.

### Tarefas

1. **Ler** `app/prompts/builder.py` para entender estrutura atual

2. **Adicionar método** ao `PromptBuilder`:
```python
# Em app/prompts/builder.py

from app.services.conhecimento import ContextoMedico

class PromptBuilder:
    # ... métodos existentes ...

    async def com_conhecimento(
        self,
        mensagem: str,
        contexto_medico: Optional[ContextoMedico] = None,
        primeira_mensagem: bool = False,
        num_interacoes: int = 0,
        vaga_oferecida: bool = False
    ) -> "PromptBuilder":
        """
        Injeta conhecimento relevante baseado na situação.

        Args:
            mensagem: Última mensagem do médico
            contexto_medico: Contexto conhecido (opcional)
            primeira_mensagem: Se é primeira interação
            num_interacoes: Total de trocas
            vaga_oferecida: Se já oferecemos vaga

        Returns:
            Self para encadeamento
        """
        from app.services.conhecimento.injetor import InjetorConhecimento

        injetor = InjetorConhecimento()

        conhecimento = await injetor.buscar_para_situacao(
            mensagem=mensagem,
            contexto=contexto_medico or ContextoMedico(),
            primeira_mensagem=primeira_mensagem,
            num_interacoes=num_interacoes,
            vaga_oferecida=vaga_oferecida
        )

        if conhecimento.texto:
            self._conhecimento = conhecimento.texto
            self._conhecimento_meta = {
                "chunks": conhecimento.chunks_usados,
                "tipos": conhecimento.tipos_usados,
                "latencia_ms": conhecimento.latencia_ms
            }

        return self

    def build(self) -> str:
        """Constrói prompt final."""
        partes = []

        # Base
        if self._base:
            partes.append(self._base)

        # Tools
        if self._tools:
            partes.append(self._tools)

        # Especialidade
        if self._especialidade:
            partes.append(self._especialidade)

        # Diretrizes
        if self._diretrizes:
            partes.append(f"## DIRETRIZES DO GESTOR\n{self._diretrizes}")

        # NOVO: Conhecimento dinâmico (antes de memórias)
        if hasattr(self, '_conhecimento') and self._conhecimento:
            partes.append(self._conhecimento)

        # Memórias RAG
        if self._memorias:
            partes.append(f"## MEMÓRIAS DO MÉDICO\n{self._memorias}")

        # Contexto
        if self._contexto:
            partes.append(f"## CONTEXTO ATUAL\n{self._contexto}")

        # Primeira mensagem
        if self._primeira_msg:
            partes.append(self._primeira_msg)

        return "\n\n".join(partes)
```

3. **Atualizar** `montar_prompt_julia()` em `app/core/prompts.py`:
```python
async def montar_prompt_julia_v2(
    cliente_id: str,
    mensagem_atual: str,
    contexto: str,
    primeira_mensagem: bool = False,
    num_interacoes: int = 0,
    memorias: Optional[str] = None,
    especialidade_id: Optional[int] = None,
    vaga_oferecida: bool = False
) -> str:
    """
    Monta prompt completo da Julia com conhecimento dinâmico.

    Nova versão com RAG de conhecimento.
    """
    from app.prompts.builder import PromptBuilder
    from app.services.conhecimento import ContextoMedico
    from app.services.supabase import supabase

    # Buscar info do médico para contexto
    cliente = supabase.table("clientes").select("*").eq("id", cliente_id).single().execute()
    anos_formacao = None
    if cliente.data and cliente.data.get("ano_formatura"):
        from datetime import datetime
        anos_formacao = datetime.now().year - cliente.data["ano_formatura"]

    tem_reserva = False
    if cliente.data:
        reservas = supabase.table("reservas_plantao").select("id").eq(
            "medico_id", cliente_id
        ).eq("status", "confirmada").execute()
        tem_reserva = len(reservas.data) > 0

    contexto_medico = ContextoMedico(
        nome=cliente.data.get("nome") if cliente.data else None,
        especialidade=cliente.data.get("especialidade") if cliente.data else None,
        anos_formacao=anos_formacao,
        tem_reserva_ativa=tem_reserva
    )

    # Montar prompt
    builder = PromptBuilder()
    await builder.com_base()
    await builder.com_tools()

    if especialidade_id:
        await builder.com_especialidade(especialidade_id)

    if primeira_mensagem:
        await builder.com_primeira_msg()

    # NOVO: Injetar conhecimento dinâmico
    await builder.com_conhecimento(
        mensagem=mensagem_atual,
        contexto_medico=contexto_medico,
        primeira_mensagem=primeira_mensagem,
        num_interacoes=num_interacoes,
        vaga_oferecida=vaga_oferecida
    )

    if memorias:
        builder.com_memorias(memorias)

    builder.com_contexto(contexto)

    return builder.build()
```

### DoD

- [ ] Método `com_conhecimento()` no PromptBuilder
- [ ] Integração com InjetorConhecimento
- [ ] Ordem correta no `build()` (conhecimento antes de memórias)
- [ ] `montar_prompt_julia_v2()` criada
- [ ] Metadados de conhecimento disponíveis

### Testes

```python
# tests/prompts/test_builder_conhecimento.py
import pytest
from app.prompts.builder import PromptBuilder
from app.services.conhecimento import ContextoMedico

@pytest.mark.asyncio
async def test_builder_com_conhecimento():
    """Builder injeta conhecimento."""
    builder = PromptBuilder()
    await builder.com_base()
    await builder.com_conhecimento(
        mensagem="Vocês pagam muito pouco",
        contexto_medico=ContextoMedico(anos_formacao=20),
        primeira_mensagem=False,
        num_interacoes=5
    )

    prompt = builder.build()

    assert "[CONHECIMENTO RELEVANTE" in prompt
    assert "Situação:" in prompt

@pytest.mark.asyncio
async def test_builder_ordem_correta():
    """Conhecimento vem na ordem correta."""
    builder = PromptBuilder()
    await builder.com_base()
    await builder.com_conhecimento(
        mensagem="teste",
        contexto_medico=ContextoMedico()
    )
    builder.com_memorias("Memória teste")
    builder.com_contexto("Contexto teste")

    prompt = builder.build()

    # Conhecimento deve vir antes de memórias
    pos_conhecimento = prompt.find("[CONHECIMENTO RELEVANTE")
    pos_memorias = prompt.find("## MEMÓRIAS DO MÉDICO")

    if pos_conhecimento > 0 and pos_memorias > 0:
        assert pos_conhecimento < pos_memorias

@pytest.mark.asyncio
async def test_builder_sem_conhecimento():
    """Builder funciona sem conhecimento."""
    builder = PromptBuilder()
    await builder.com_base()

    prompt = builder.build()

    assert "[CONHECIMENTO RELEVANTE" not in prompt
```

---

## Story 3.3: Integração no Pipeline de Processamento

### Objetivo
Integrar busca de conhecimento no pipeline de mensagens (ProcessorContext).

### Tarefas

1. **Atualizar** `app/pipeline/context.py` para incluir conhecimento:
```python
@dataclass
class ProcessorContext:
    # ... campos existentes ...

    # NOVO: Conhecimento dinâmico
    conhecimento_texto: Optional[str] = None
    conhecimento_meta: Optional[dict] = None
```

2. **Criar** `app/pipeline/conhecimento_processor.py`:
```python
"""
Processor para injeção de conhecimento dinâmico.
"""
import logging
from typing import Optional

from .base import BasePreProcessor
from .context import ProcessorContext
from app.services.conhecimento import ContextoMedico
from app.services.conhecimento.injetor import InjetorConhecimento

logger = logging.getLogger(__name__)


class ConhecimentoProcessor(BasePreProcessor):
    """
    Processor que busca conhecimento relevante.

    Prioridade: 40 (após parsing, antes do agente)
    """

    def __init__(self):
        self.injetor = InjetorConhecimento()

    @property
    def priority(self) -> int:
        return 40

    async def process(self, context: ProcessorContext) -> ProcessorContext:
        """
        Busca e injeta conhecimento relevante.

        Args:
            context: Contexto do processamento

        Returns:
            Contexto com conhecimento adicionado
        """
        try:
            # Montar contexto do médico
            contexto_medico = ContextoMedico(
                nome=context.nome_contato,
                especialidade=context.metadata.get("especialidade"),
                anos_formacao=context.metadata.get("anos_formacao"),
                tem_reserva_ativa=context.metadata.get("tem_reserva", False),
                historico_mensagens=context.metadata.get("historico_recente", [])
            )

            # Buscar conhecimento
            conhecimento = await self.injetor.buscar_para_situacao(
                mensagem=context.mensagem.texto,
                contexto=contexto_medico,
                primeira_mensagem=context.metadata.get("primeira_mensagem", False),
                num_interacoes=context.metadata.get("num_interacoes", 0),
                vaga_oferecida=context.metadata.get("vaga_oferecida", False)
            )

            # Armazenar no contexto
            context.conhecimento_texto = conhecimento.texto
            context.conhecimento_meta = {
                "chunks": conhecimento.chunks_usados,
                "tipos": conhecimento.tipos_usados,
                "latencia_ms": conhecimento.latencia_ms
            }

            logger.info(
                f"Conhecimento injetado: {conhecimento.chunks_usados} chunks, "
                f"{conhecimento.latencia_ms:.0f}ms"
            )

        except Exception as e:
            logger.warning(f"Erro ao buscar conhecimento: {e}")
            # Não falha o pipeline, apenas não injeta conhecimento

        context.should_continue = True
        return context
```

3. **Registrar processor** em `app/pipeline/setup.py`:
```python
from .conhecimento_processor import ConhecimentoProcessor

def setup_pipeline() -> MessagePipeline:
    pipeline = MessagePipeline()

    # ... outros processors ...

    # NOVO: Conhecimento dinâmico (prioridade 40)
    pipeline.add_pre_processor(ConhecimentoProcessor())

    # ... continua ...
```

### DoD

- [ ] `ProcessorContext` atualizado com campos de conhecimento
- [ ] `ConhecimentoProcessor` implementado
- [ ] Prioridade 40 (após parsing, antes do agente)
- [ ] Registrado no pipeline
- [ ] Erro não quebra pipeline (graceful degradation)

### Testes

```python
# tests/pipeline/test_conhecimento_processor.py
import pytest
from unittest.mock import AsyncMock, patch
from app.pipeline.conhecimento_processor import ConhecimentoProcessor
from app.pipeline.context import ProcessorContext
from app.schemas.mensagem import MensagemRecebida

@pytest.fixture
def processor():
    return ConhecimentoProcessor()

@pytest.fixture
def context():
    return ProcessorContext(
        mensagem=MensagemRecebida(
            texto="Vocês pagam muito pouco",
            telefone="5511999999999",
            nome="Dr. Teste"
        ),
        nome_contato="Dr. Teste",
        metadata={"num_interacoes": 5}
    )

@pytest.mark.asyncio
async def test_processor_injeta_conhecimento(processor, context):
    """Processor injeta conhecimento no contexto."""
    result = await processor.process(context)

    assert result.should_continue is True
    assert result.conhecimento_texto is not None or result.conhecimento_meta is not None

@pytest.mark.asyncio
async def test_processor_prioridade(processor):
    """Processor tem prioridade correta."""
    assert processor.priority == 40

@pytest.mark.asyncio
async def test_processor_graceful_error(processor, context):
    """Processor não quebra em erro."""
    with patch.object(processor.injetor, 'buscar_para_situacao', side_effect=Exception("erro")):
        result = await processor.process(context)

    # Deve continuar mesmo com erro
    assert result.should_continue is True
```

---

## Story 3.4: Métricas e Observabilidade

### Objetivo
Adicionar métricas de uso do conhecimento para monitoramento e otimização.

### Tarefas

1. **Criar tabela de métricas** via migration:
```sql
CREATE TABLE metricas_conhecimento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificadores
    cliente_id UUID REFERENCES clientes(id),
    conversa_id UUID REFERENCES conversations(id),

    -- Análise
    objecao_detectada BOOLEAN DEFAULT false,
    tipo_objecao TEXT,
    perfil_detectado TEXT,
    objetivo_detectado TEXT,

    -- Conhecimento usado
    chunks_usados INT DEFAULT 0,
    tipos_conhecimento TEXT[],  -- ['objecao:preco', 'perfil:senior']

    -- Performance
    latencia_analise_ms FLOAT,
    latencia_busca_ms FLOAT,
    latencia_total_ms FLOAT,

    -- Qualidade (pode ser preenchido depois)
    conhecimento_util BOOLEAN,  -- Feedback manual
    resposta_adequada BOOLEAN,  -- Baseado em continuidade da conversa

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metricas_conhecimento_cliente ON metricas_conhecimento(cliente_id);
CREATE INDEX idx_metricas_conhecimento_data ON metricas_conhecimento(created_at);
CREATE INDEX idx_metricas_conhecimento_tipo ON metricas_conhecimento(tipo_objecao);
```

2. **Criar serviço de métricas** `app/services/conhecimento/metricas.py`:
```python
"""
Métricas de uso do conhecimento dinâmico.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetricasConhecimento:
    """Registra e consulta métricas de conhecimento."""

    async def registrar(
        self,
        cliente_id: UUID,
        conversa_id: UUID,
        objecao_detectada: bool,
        tipo_objecao: Optional[str],
        perfil_detectado: str,
        objetivo_detectado: str,
        chunks_usados: int,
        tipos_conhecimento: list[str],
        latencia_analise_ms: float,
        latencia_busca_ms: float,
        latencia_total_ms: float
    ) -> None:
        """Registra uso de conhecimento."""
        try:
            supabase.table("metricas_conhecimento").insert({
                "cliente_id": str(cliente_id),
                "conversa_id": str(conversa_id),
                "objecao_detectada": objecao_detectada,
                "tipo_objecao": tipo_objecao,
                "perfil_detectado": perfil_detectado,
                "objetivo_detectado": objetivo_detectado,
                "chunks_usados": chunks_usados,
                "tipos_conhecimento": tipos_conhecimento,
                "latencia_analise_ms": latencia_analise_ms,
                "latencia_busca_ms": latencia_busca_ms,
                "latencia_total_ms": latencia_total_ms
            }).execute()
        except Exception as e:
            logger.error(f"Erro ao registrar métrica: {e}")

    async def obter_resumo_dia(self, data: Optional[datetime] = None) -> dict:
        """Obtém resumo de métricas do dia."""
        data = data or datetime.now()
        inicio = data.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(days=1)

        result = supabase.table("metricas_conhecimento").select(
            "objecao_detectada, tipo_objecao, perfil_detectado, chunks_usados, latencia_total_ms"
        ).gte("created_at", inicio.isoformat()).lt("created_at", fim.isoformat()).execute()

        if not result.data:
            return {"total": 0}

        total = len(result.data)
        com_objecao = sum(1 for r in result.data if r["objecao_detectada"])
        chunks_total = sum(r["chunks_usados"] for r in result.data)
        latencia_media = sum(r["latencia_total_ms"] for r in result.data) / total

        # Contar por tipo de objeção
        objecoes = {}
        for r in result.data:
            if r["tipo_objecao"]:
                objecoes[r["tipo_objecao"]] = objecoes.get(r["tipo_objecao"], 0) + 1

        # Contar por perfil
        perfis = {}
        for r in result.data:
            if r["perfil_detectado"]:
                perfis[r["perfil_detectado"]] = perfis.get(r["perfil_detectado"], 0) + 1

        return {
            "total": total,
            "com_objecao": com_objecao,
            "taxa_objecao": com_objecao / total if total > 0 else 0,
            "chunks_total": chunks_total,
            "chunks_media": chunks_total / total if total > 0 else 0,
            "latencia_media_ms": latencia_media,
            "objecoes_por_tipo": objecoes,
            "perfis_detectados": perfis
        }

    async def obter_latencia_media(self, ultimos_minutos: int = 60) -> float:
        """Obtém latência média recente."""
        desde = datetime.now() - timedelta(minutes=ultimos_minutos)

        result = supabase.table("metricas_conhecimento").select(
            "latencia_total_ms"
        ).gte("created_at", desde.isoformat()).execute()

        if not result.data:
            return 0.0

        return sum(r["latencia_total_ms"] for r in result.data) / len(result.data)
```

3. **Integrar métricas no ConhecimentoProcessor**:
```python
# Em conhecimento_processor.py, após buscar conhecimento:

from app.services.conhecimento.metricas import MetricasConhecimento

# Dentro do process():
metricas = MetricasConhecimento()
await metricas.registrar(
    cliente_id=context.cliente_id,
    conversa_id=context.conversa_id,
    objecao_detectada=context.conhecimento_meta.get("objecao_detectada", False),
    tipo_objecao=context.conhecimento_meta.get("tipo_objecao"),
    perfil_detectado=context.conhecimento_meta.get("perfil"),
    objetivo_detectado=context.conhecimento_meta.get("objetivo"),
    chunks_usados=context.conhecimento_meta.get("chunks", 0),
    tipos_conhecimento=context.conhecimento_meta.get("tipos", []),
    latencia_analise_ms=context.conhecimento_meta.get("latencia_analise_ms", 0),
    latencia_busca_ms=context.conhecimento_meta.get("latencia_busca_ms", 0),
    latencia_total_ms=context.conhecimento_meta.get("latencia_ms", 0)
)
```

### DoD

- [ ] Tabela `metricas_conhecimento` criada
- [ ] `MetricasConhecimento` serviço implementado
- [ ] Registro automático em cada processamento
- [ ] Método `obter_resumo_dia()` funciona
- [ ] Método `obter_latencia_media()` funciona

### Testes

```python
# tests/conhecimento/test_metricas.py
import pytest
from uuid import uuid4
from app.services.conhecimento.metricas import MetricasConhecimento

@pytest.fixture
def metricas():
    return MetricasConhecimento()

@pytest.mark.asyncio
async def test_registrar_metrica(metricas):
    """Registra métrica no banco."""
    await metricas.registrar(
        cliente_id=uuid4(),
        conversa_id=uuid4(),
        objecao_detectada=True,
        tipo_objecao="preco",
        perfil_detectado="senior",
        objetivo_detectado="negociar",
        chunks_usados=2,
        tipos_conhecimento=["objecao:preco", "perfil:senior"],
        latencia_analise_ms=10.5,
        latencia_busca_ms=80.3,
        latencia_total_ms=90.8
    )

    # Se não deu erro, registrou

@pytest.mark.asyncio
async def test_resumo_dia(metricas):
    """Obtém resumo do dia."""
    resumo = await metricas.obter_resumo_dia()

    assert "total" in resumo
    assert "com_objecao" in resumo
    assert "latencia_media_ms" in resumo
```

---

## Checklist do Épico

- [ ] **S13.E3.1** - InjetorConhecimento implementado
- [ ] **S13.E3.2** - PromptBuilder integrado
- [ ] **S13.E3.3** - Pipeline atualizado
- [ ] **S13.E3.4** - Métricas implementadas
- [ ] Todos os testes passando
- [ ] Conhecimento aparece nos prompts
- [ ] Latência < 200ms
- [ ] Métricas registradas
