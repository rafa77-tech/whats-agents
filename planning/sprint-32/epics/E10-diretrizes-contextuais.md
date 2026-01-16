# E10: Diretrizes Contextuais

**Fase:** 3 - Interação Gestor
**Estimativa:** 4h
**Prioridade:** Média
**Dependências:** E09 (Gestor Comanda Julia)

---

## Objetivo

Implementar sistema de diretrizes contextuais que permite ao gestor definir margens de negociação e regras específicas por vaga ou por médico, com expiração automática.

## Tipos de Diretriz

| Escopo | Exemplo | Expira quando |
|--------|---------|---------------|
| **Por vaga** | "Vaga 123 pode até R$ 3.000" | Vaga é preenchida |
| **Por médico** | "Dr Carlos pode 15% a mais" | Médico diz que não tem interesse |
| **Por especialidade** | "Anestesistas podem 20% a mais" | Manual ou período |

---

## Tarefas

### T1: Criar tabela diretrizes_contextuais (30min)

**Migration:** `create_diretrizes_contextuais_table`

```sql
-- Migration: create_diretrizes_contextuais_table
-- Sprint 32 E10: Diretrizes contextuais para negociação

CREATE TABLE IF NOT EXISTS diretrizes_contextuais (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tipo da diretriz
    tipo TEXT NOT NULL,  -- margem_negociacao | regra_comportamento | bloqueio | prioridade

    -- Escopo
    escopo TEXT NOT NULL,  -- vaga | medico | especialidade | hospital | global
    vaga_id UUID REFERENCES vagas(id),
    cliente_id UUID REFERENCES clientes(id),
    especialidade TEXT,
    hospital_id UUID REFERENCES hospitais(id),

    -- Conteúdo da diretriz
    valor_tipo TEXT,  -- percentual | valor_maximo | texto
    valor_numerico NUMERIC(10,2),
    valor_texto TEXT,

    -- Descrição legível
    descricao TEXT NOT NULL,

    -- Origem
    criado_por TEXT NOT NULL,  -- ID do gestor Slack
    criado_via TEXT NOT NULL,  -- slack | dashboard
    comando_origem_id UUID REFERENCES comandos_gestor(id),

    -- Status
    status TEXT NOT NULL DEFAULT 'ativa',  -- ativa | expirada | cancelada
    motivo_expiracao TEXT,  -- vaga_preenchida | medico_sem_interesse | cancelado_gestor | periodo_fim

    -- Período de validade
    valido_de TIMESTAMPTZ DEFAULT now(),
    valido_ate TIMESTAMPTZ,  -- NULL = sem expiração por tempo

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    expirado_em TIMESTAMPTZ,

    CONSTRAINT chk_diretriz_tipo CHECK (tipo IN ('margem_negociacao', 'regra_comportamento', 'bloqueio', 'prioridade')),
    CONSTRAINT chk_diretriz_escopo CHECK (escopo IN ('vaga', 'medico', 'especialidade', 'hospital', 'global')),
    CONSTRAINT chk_diretriz_status CHECK (status IN ('ativa', 'expirada', 'cancelada'))
);

-- Índices
CREATE INDEX idx_diretrizes_ativas
ON diretrizes_contextuais (status, escopo)
WHERE status = 'ativa';

CREATE INDEX idx_diretrizes_vaga
ON diretrizes_contextuais (vaga_id)
WHERE vaga_id IS NOT NULL AND status = 'ativa';

CREATE INDEX idx_diretrizes_cliente
ON diretrizes_contextuais (cliente_id)
WHERE cliente_id IS NOT NULL AND status = 'ativa';

-- Comentários
COMMENT ON TABLE diretrizes_contextuais IS 'Diretrizes contextuais de negociação e comportamento';
COMMENT ON COLUMN diretrizes_contextuais.escopo IS 'vaga: por vaga específica, medico: por médico específico, especialidade: por especialidade, hospital: por hospital, global: vale para todos';
```

### T2: Criar serviço de diretrizes (60min)

**Arquivo:** `app/services/diretrizes_contextuais.py`

```python
"""
Serviço de diretrizes contextuais.

Sprint 32 E10 - Margens e regras por vaga/médico.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Literal

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

TipoDiretriz = Literal["margem_negociacao", "regra_comportamento", "bloqueio", "prioridade"]
EscopoDiretriz = Literal["vaga", "medico", "especialidade", "hospital", "global"]


async def criar_diretriz(
    tipo: TipoDiretriz,
    escopo: EscopoDiretriz,
    descricao: str,
    criado_por: str,
    criado_via: str = "slack",
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    especialidade: Optional[str] = None,
    hospital_id: Optional[str] = None,
    valor_tipo: Optional[str] = None,
    valor_numerico: Optional[float] = None,
    valor_texto: Optional[str] = None,
    valido_ate: Optional[datetime] = None,
) -> Optional[str]:
    """
    Cria uma nova diretriz contextual.

    Args:
        tipo: Tipo da diretriz
        escopo: Escopo de aplicação
        descricao: Descrição legível
        criado_por: ID do gestor
        criado_via: Origem (slack/dashboard)
        vaga_id: ID da vaga (se escopo=vaga)
        cliente_id: ID do médico (se escopo=medico)
        especialidade: Especialidade (se escopo=especialidade)
        hospital_id: ID do hospital (se escopo=hospital)
        valor_tipo: Tipo do valor (percentual/valor_maximo/texto)
        valor_numerico: Valor numérico
        valor_texto: Valor em texto
        valido_ate: Data de expiração

    Returns:
        ID da diretriz criada
    """
    try:
        response = supabase.table("diretrizes_contextuais").insert({
            "tipo": tipo,
            "escopo": escopo,
            "descricao": descricao,
            "criado_por": criado_por,
            "criado_via": criado_via,
            "vaga_id": vaga_id,
            "cliente_id": cliente_id,
            "especialidade": especialidade,
            "hospital_id": hospital_id,
            "valor_tipo": valor_tipo,
            "valor_numerico": valor_numerico,
            "valor_texto": valor_texto,
            "valido_ate": valido_ate.isoformat() if valido_ate else None,
            "status": "ativa",
        }).execute()

        if response.data:
            diretriz_id = response.data[0]["id"]
            logger.info(f"Diretriz criada: {tipo} para {escopo} - {descricao}")
            return diretriz_id

        return None

    except Exception as e:
        logger.error(f"Erro ao criar diretriz: {e}")
        return None


async def buscar_diretrizes_para_contexto(
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    especialidade: Optional[str] = None,
    hospital_id: Optional[str] = None,
) -> list[dict]:
    """
    Busca diretrizes ativas aplicáveis ao contexto.

    Ordem de prioridade:
    1. Vaga específica
    2. Médico específico
    3. Hospital
    4. Especialidade
    5. Global

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do médico
        especialidade: Especialidade
        hospital_id: ID do hospital

    Returns:
        Lista de diretrizes aplicáveis, ordenadas por prioridade
    """
    diretrizes = []

    # 1. Buscar por vaga específica
    if vaga_id:
        response = (
            supabase.table("diretrizes_contextuais")
            .select("*")
            .eq("vaga_id", vaga_id)
            .eq("status", "ativa")
            .execute()
        )
        diretrizes.extend(response.data or [])

    # 2. Buscar por médico específico
    if cliente_id:
        response = (
            supabase.table("diretrizes_contextuais")
            .select("*")
            .eq("cliente_id", cliente_id)
            .eq("status", "ativa")
            .execute()
        )
        diretrizes.extend(response.data or [])

    # 3. Buscar por hospital
    if hospital_id:
        response = (
            supabase.table("diretrizes_contextuais")
            .select("*")
            .eq("hospital_id", hospital_id)
            .eq("status", "ativa")
            .execute()
        )
        diretrizes.extend(response.data or [])

    # 4. Buscar por especialidade
    if especialidade:
        response = (
            supabase.table("diretrizes_contextuais")
            .select("*")
            .eq("especialidade", especialidade)
            .eq("status", "ativa")
            .execute()
        )
        diretrizes.extend(response.data or [])

    # 5. Buscar globais
    response = (
        supabase.table("diretrizes_contextuais")
        .select("*")
        .eq("escopo", "global")
        .eq("status", "ativa")
        .execute()
    )
    diretrizes.extend(response.data or [])

    # Ordenar por prioridade de escopo
    ordem_escopo = {"vaga": 0, "medico": 1, "hospital": 2, "especialidade": 3, "global": 4}
    diretrizes.sort(key=lambda d: ordem_escopo.get(d["escopo"], 5))

    return diretrizes


async def obter_margem_negociacao(
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    especialidade: Optional[str] = None,
) -> Optional[dict]:
    """
    Obtém margem de negociação aplicável ao contexto.

    Retorna a margem mais específica encontrada.

    Returns:
        Dict com {tipo, valor, escopo} ou None
    """
    diretrizes = await buscar_diretrizes_para_contexto(
        vaga_id=vaga_id,
        cliente_id=cliente_id,
        especialidade=especialidade,
    )

    # Filtrar apenas margens de negociação
    margens = [d for d in diretrizes if d["tipo"] == "margem_negociacao"]

    if not margens:
        return None

    # Pegar a mais específica (primeira após ordenação)
    margem = margens[0]

    return {
        "tipo": margem["valor_tipo"],
        "valor": margem["valor_numerico"],
        "escopo": margem["escopo"],
        "descricao": margem["descricao"],
    }


async def expirar_diretriz(
    diretriz_id: str,
    motivo: str,
) -> bool:
    """
    Marca diretriz como expirada.

    Args:
        diretriz_id: ID da diretriz
        motivo: Motivo da expiração

    Returns:
        True se expirou com sucesso
    """
    try:
        response = (
            supabase.table("diretrizes_contextuais")
            .update({
                "status": "expirada",
                "motivo_expiracao": motivo,
                "expirado_em": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", diretriz_id)
            .eq("status", "ativa")
            .execute()
        )

        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao expirar diretriz: {e}")
        return False


async def cancelar_diretriz(
    diretriz_id: str,
    cancelado_por: str,
) -> bool:
    """Cancela diretriz manualmente."""
    return await expirar_diretriz(diretriz_id, f"cancelado_gestor:{cancelado_por}")


async def verificar_expiracoes_automaticas():
    """
    Verifica e expira diretrizes automaticamente.

    - Vagas preenchidas → expira diretriz da vaga
    - Período expirado → expira por tempo
    """
    agora = datetime.now(timezone.utc)

    # 1. Expirar por período
    response = (
        supabase.table("diretrizes_contextuais")
        .select("id")
        .eq("status", "ativa")
        .lt("valido_ate", agora.isoformat())
        .execute()
    )

    for diretriz in (response.data or []):
        await expirar_diretriz(diretriz["id"], "periodo_fim")

    # 2. Expirar por vaga preenchida
    # Buscar diretrizes de vaga onde vaga foi preenchida
    response = supabase.rpc(
        "buscar_diretrizes_vaga_preenchida"
    ).execute()

    for diretriz in (response.data or []):
        await expirar_diretriz(diretriz["id"], "vaga_preenchida")

    logger.info("Verificação de expirações concluída")
```

### T3: Criar RPC para vagas preenchidas (20min)

**Migration:** `create_buscar_diretrizes_vaga_preenchida_rpc`

```sql
-- Migration: create_buscar_diretrizes_vaga_preenchida_rpc
-- Sprint 32 E10: Função para encontrar diretrizes de vagas preenchidas

CREATE OR REPLACE FUNCTION buscar_diretrizes_vaga_preenchida()
RETURNS TABLE (id UUID)
LANGUAGE sql
STABLE
AS $$
    SELECT d.id
    FROM diretrizes_contextuais d
    JOIN vagas v ON v.id = d.vaga_id
    WHERE d.status = 'ativa'
      AND d.escopo = 'vaga'
      AND v.status != 'aberta';  -- Vaga preenchida ou cancelada
$$;

COMMENT ON FUNCTION buscar_diretrizes_vaga_preenchida() IS 'Encontra diretrizes de vagas que já foram preenchidas para expiração automática';
```

### T4: Integrar com PromptBuilder (30min)

**Arquivo:** `app/prompts/builder.py`

**Adicionar busca de diretrizes:**

```python
from app.services.diretrizes_contextuais import (
    buscar_diretrizes_para_contexto,
    obter_margem_negociacao,
)

async def construir_prompt_julia(
    # ... parâmetros existentes ...
    vaga_id: Optional[str] = None,  # NOVO
    cliente_id: Optional[str] = None,  # NOVO (já existe?)
) -> str:
    """Constrói prompt com diretrizes contextuais."""

    # ... código existente ...

    # NOVO: Buscar diretrizes contextuais
    if vaga_id or cliente_id:
        # Buscar especialidade do médico se não fornecida
        especialidade = None
        if cliente_id:
            medico = supabase.table("clientes").select("especialidade").eq("id", cliente_id).single().execute()
            especialidade = medico.data.get("especialidade") if medico.data else None

        # Buscar margem de negociação
        margem = await obter_margem_negociacao(
            vaga_id=vaga_id,
            cliente_id=cliente_id,
            especialidade=especialidade,
        )

        if margem:
            # Injetar margem no prompt
            negotiation_margin = margem

    # ... resto do código ...
```

### T5: Criar comando Slack para diretrizes (30min)

**Arquivo:** `app/api/routes/slack.py`

**Adicionar handler:**

```python
# Padrões para criar diretriz
# "margem de 15% para o Dr Carlos"
# "vaga 123 pode até R$ 3000"

async def _processar_comando_margem(event: dict):
    """Processa comando de margem do gestor."""
    texto = event.get("text", "")
    user_id = event.get("user")

    # Usar LLM para extrair dados
    dados = await _extrair_dados_margem(texto)

    if not dados:
        await slack_client.enviar_mensagem(
            canal=event.get("channel"),
            texto="❌ Não consegui entender. Exemplos:\n"
                  "• 'margem de 15% para Dr Carlos'\n"
                  "• 'vaga 123 pode até R$ 3000'\n"
                  "• 'anestesistas podem 20% a mais'",
            thread_ts=event.get("ts"),
        )
        return

    # Criar diretriz
    from app.services.diretrizes_contextuais import criar_diretriz

    diretriz_id = await criar_diretriz(
        tipo="margem_negociacao",
        escopo=dados["escopo"],
        descricao=dados["descricao"],
        criado_por=user_id,
        criado_via="slack",
        vaga_id=dados.get("vaga_id"),
        cliente_id=dados.get("cliente_id"),
        especialidade=dados.get("especialidade"),
        valor_tipo=dados["valor_tipo"],
        valor_numerico=dados["valor"],
    )

    if diretriz_id:
        await slack_client.enviar_mensagem(
            canal=event.get("channel"),
            texto=f"✅ Margem definida!\n{dados['descricao']}",
            thread_ts=event.get("ts"),
        )
```

### T6: Criar testes (30min)

**Arquivo:** `tests/unit/test_diretrizes_contextuais.py`

```python
import pytest
from unittest.mock import patch
from app.services.diretrizes_contextuais import (
    criar_diretriz,
    buscar_diretrizes_para_contexto,
    obter_margem_negociacao,
)


class TestCriarDiretriz:
    """Testes para criação de diretrizes."""

    @pytest.mark.asyncio
    async def test_cria_margem_por_vaga(self):
        """Deve criar margem para vaga específica."""
        with patch("app.services.diretrizes_contextuais.supabase") as mock_sb:
            mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "dir-123"}
            ]

            diretriz_id = await criar_diretriz(
                tipo="margem_negociacao",
                escopo="vaga",
                descricao="Vaga pode até R$ 3000",
                criado_por="U123",
                vaga_id="vaga-1",
                valor_tipo="valor_maximo",
                valor_numerico=3000,
            )

            assert diretriz_id == "dir-123"


class TestBuscarDiretrizes:
    """Testes para busca de diretrizes."""

    @pytest.mark.asyncio
    async def test_prioriza_escopo_mais_especifico(self):
        """Deve retornar diretriz de vaga antes de global."""
        with patch("app.services.diretrizes_contextuais.supabase") as mock_sb:
            # Simular diretrizes encontradas
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = [
                AsyncMock(data=[{"id": "1", "escopo": "vaga", "tipo": "margem_negociacao"}]),  # vaga
                AsyncMock(data=[]),  # cliente
                AsyncMock(data=[]),  # hospital
                AsyncMock(data=[]),  # especialidade
                AsyncMock(data=[{"id": "2", "escopo": "global", "tipo": "margem_negociacao"}]),  # global
            ]

            diretrizes = await buscar_diretrizes_para_contexto(vaga_id="vaga-1")

            # Vaga deve vir primeiro
            assert diretrizes[0]["escopo"] == "vaga"
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Tabela diretrizes_contextuais criada**
  - [ ] Migration aplicada
  - [ ] Índices funcionando

- [ ] **CRUD de diretrizes funciona**
  - [ ] `criar_diretriz()` funciona
  - [ ] `buscar_diretrizes_para_contexto()` funciona
  - [ ] `obter_margem_negociacao()` funciona
  - [ ] `expirar_diretriz()` funciona

- [ ] **Expiração automática funciona**
  - [ ] Por período (valido_ate)
  - [ ] Por vaga preenchida

- [ ] **Integração com PromptBuilder**
  - [ ] Margem é injetada no prompt

- [ ] **Comando Slack funciona**
  - [ ] Gestor pode criar diretriz via Slack

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_diretrizes_contextuais.py -v` = OK

---

## Notas para o Desenvolvedor

1. **Prioridade de escopos:**
   - Vaga > Médico > Hospital > Especialidade > Global
   - Mais específico sempre ganha

2. **Expiração automática:**
   - Job deve rodar periodicamente
   - Verificar vagas preenchidas
   - Verificar períodos expirados

3. **UI no dashboard:**
   - E18 implementará tela de gestão
