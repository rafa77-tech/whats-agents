# E14 - Reestruturar Tabela Campanhas

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 4 - Arquitetura de Dados
**Dependências:** E01 (Prompts por Tipo)
**Estimativa:** 4h

---

## Objetivo

Reestruturar a tabela `campanhas` para suportar o novo modelo de **comportamento** ao invés de **template**. Remover campos legados e adicionar novos campos para objetivo, regras e escopo de oferta.

---

## Problema Atual

A tabela `campanhas` foi projetada com mentalidade de "templates":

```sql
-- Estrutura atual (problemática)
campanhas (
    id,
    nome,
    corpo TEXT,           -- ❌ Mensagem pré-escrita
    nome_template TEXT,   -- ❌ Referência a template
    tipo TEXT,            -- Existe mas subutilizado
    status,
    ...
)
```

**Problemas:**
1. Campo `corpo` contém mensagem pré-escrita - Julia não gera
2. Campo `nome_template` é conceito legado de Twilio
3. Não tem campo para objetivo em linguagem natural
4. Não tem campo para regras comportamentais
5. Não tem campo para escopo de vagas (tipo=oferta)

---

## Solução

Migrar para estrutura baseada em **comportamento**:

```sql
-- Nova estrutura
campanhas (
    id,
    nome,
    tipo TEXT NOT NULL,           -- discovery | oferta | followup | feedback | reativacao
    objetivo TEXT,                -- NOVO: Objetivo em linguagem natural
    regras JSONB,                 -- NOVO: Array de regras comportamentais
    escopo_vagas JSONB,           -- NOVO: Filtro de vagas (para tipo=oferta)
    pode_ofertar BOOLEAN,         -- NOVO: Se pode ofertar proativamente
    status,
    ...
)
```

---

## Tasks

### T1: Criar migration para novos campos (30min)

**Migration:** `adicionar_campos_comportamento_campanhas`

```sql
-- Migration: adicionar_campos_comportamento_campanhas
-- Adiciona campos para novo modelo de comportamento

-- 1. Adicionar novos campos
ALTER TABLE campanhas
ADD COLUMN IF NOT EXISTS objetivo TEXT,
ADD COLUMN IF NOT EXISTS regras JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS escopo_vagas JSONB,
ADD COLUMN IF NOT EXISTS pode_ofertar BOOLEAN DEFAULT false;

-- 2. Comentários
COMMENT ON COLUMN campanhas.objetivo IS 'Objetivo da campanha em linguagem natural para o prompt';
COMMENT ON COLUMN campanhas.regras IS 'Array de regras comportamentais específicas';
COMMENT ON COLUMN campanhas.escopo_vagas IS 'Filtro de vagas para campanhas tipo=oferta';
COMMENT ON COLUMN campanhas.pode_ofertar IS 'Se Julia pode ofertar proativamente nesta campanha';

-- 3. Índice para tipo
CREATE INDEX IF NOT EXISTS idx_campanhas_tipo ON campanhas(tipo);

-- 4. Atualizar constraint de tipo (se não existir)
-- Primeiro remove constraint antiga se existir
ALTER TABLE campanhas DROP CONSTRAINT IF EXISTS campanhas_tipo_check;

-- Adiciona nova constraint
ALTER TABLE campanhas ADD CONSTRAINT campanhas_tipo_check
CHECK (tipo IN ('discovery', 'oferta', 'followup', 'feedback', 'reativacao'));
```

---

### T2: Criar migration para deprecar campos antigos (30min)

Não deletar imediatamente - marcar como deprecated e criar view de compatibilidade.

**Migration:** `deprecar_campos_legados_campanhas`

```sql
-- Migration: deprecar_campos_legados_campanhas
-- Marca campos legados como deprecated (não deleta ainda)

-- 1. Renomear campos legados com prefixo _deprecated
-- Isso permite rollback fácil se necessário
ALTER TABLE campanhas
RENAME COLUMN corpo TO _deprecated_corpo;

ALTER TABLE campanhas
RENAME COLUMN nome_template TO _deprecated_nome_template;

-- 2. Comentários indicando deprecation
COMMENT ON COLUMN campanhas._deprecated_corpo IS 'DEPRECATED: Usar objetivo + regras. Será removido na Sprint 34.';
COMMENT ON COLUMN campanhas._deprecated_nome_template IS 'DEPRECATED: Legado Twilio. Será removido na Sprint 34.';

-- 3. Criar view de compatibilidade para queries antigas
CREATE OR REPLACE VIEW campanhas_compat AS
SELECT
    id,
    nome,
    tipo,
    objetivo,
    regras,
    escopo_vagas,
    pode_ofertar,
    status,
    created_at,
    updated_at,
    -- Campos legados (para compatibilidade)
    _deprecated_corpo AS corpo,
    _deprecated_nome_template AS nome_template
FROM campanhas;

-- 4. Log de deprecation para auditoria
INSERT INTO migration_notes (migration_name, note, created_at)
VALUES (
    'deprecar_campos_legados_campanhas',
    'Campos corpo e nome_template marcados deprecated. Remover completamente na Sprint 34.',
    now()
);
```

---

### T3: Criar schema de validação (45min)

Pydantic models para validar estrutura dos novos campos.

**Arquivo:** `app/schemas/campanha.py`

```python
"""
Schemas para campanhas.
"""
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class TipoCampanha(str, Enum):
    """Tipos de campanha suportados."""
    DISCOVERY = "discovery"
    OFERTA = "oferta"
    FOLLOWUP = "followup"
    FEEDBACK = "feedback"
    REATIVACAO = "reativacao"


class EscopoVagas(BaseModel):
    """
    Escopo de vagas para campanhas tipo=oferta.

    Define quais vagas Julia pode ofertar nesta campanha.
    """
    especialidade_id: Optional[str] = None
    hospital_id: Optional[str] = None
    regiao: Optional[str] = None
    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None
    turno: Optional[str] = None  # diurno | noturno | ambos
    valor_minimo: Optional[float] = None
    valor_maximo: Optional[float] = None

    @field_validator("turno")
    @classmethod
    def validar_turno(cls, v):
        if v and v not in ("diurno", "noturno", "ambos"):
            raise ValueError("Turno deve ser: diurno, noturno ou ambos")
        return v


class CampanhaBase(BaseModel):
    """Base para campanha."""
    nome: str = Field(..., min_length=3, max_length=100)
    tipo: TipoCampanha
    objetivo: Optional[str] = Field(None, max_length=500)
    regras: list[str] = Field(default_factory=list)
    escopo_vagas: Optional[EscopoVagas] = None
    pode_ofertar: bool = False

    @field_validator("escopo_vagas")
    @classmethod
    def validar_escopo_obrigatorio_para_oferta(cls, v, info):
        tipo = info.data.get("tipo")
        if tipo == TipoCampanha.OFERTA and not v:
            raise ValueError("escopo_vagas é obrigatório para campanhas tipo=oferta")
        return v

    @field_validator("pode_ofertar")
    @classmethod
    def validar_pode_ofertar(cls, v, info):
        tipo = info.data.get("tipo")
        # Discovery nunca pode ofertar proativamente
        if tipo == TipoCampanha.DISCOVERY and v:
            raise ValueError("Campanhas discovery não podem ofertar proativamente")
        return v


class CampanhaCreate(CampanhaBase):
    """Schema para criar campanha."""
    pass


class CampanhaUpdate(BaseModel):
    """Schema para atualizar campanha."""
    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    objetivo: Optional[str] = Field(None, max_length=500)
    regras: Optional[list[str]] = None
    escopo_vagas: Optional[EscopoVagas] = None
    pode_ofertar: Optional[bool] = None


class CampanhaResponse(CampanhaBase):
    """Schema de resposta."""
    id: str
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Regras padrão por tipo de campanha
REGRAS_PADRAO = {
    TipoCampanha.DISCOVERY: [
        "Nunca mencionar vagas ou oportunidades",
        "Não falar de valores",
        "Foco em conhecer o médico",
        "Perguntar sobre especialidade e preferências",
        "Só ofertar se médico perguntar explicitamente"
    ],
    TipoCampanha.OFERTA: [
        "Apresentar apenas vagas dentro do escopo definido",
        "Consultar sistema antes de mencionar qualquer vaga",
        "Nunca inventar ou prometer vagas",
        "Respeitar margem de negociação definida"
    ],
    TipoCampanha.FOLLOWUP: [
        "Perguntar como o médico está",
        "Manter conversa leve e natural",
        "Só ofertar se médico perguntar"
    ],
    TipoCampanha.FEEDBACK: [
        "Perguntar como foi o plantão",
        "Coletar elogios e reclamações",
        "Não ofertar novo plantão proativamente"
    ],
    TipoCampanha.REATIVACAO: [
        "Reestabelecer contato de forma natural",
        "Perguntar se ainda tem interesse em plantões",
        "Não ofertar imediatamente",
        "Esperar confirmação de interesse antes de ofertar"
    ]
}


def get_regras_padrao(tipo: TipoCampanha) -> list[str]:
    """Retorna regras padrão para um tipo de campanha."""
    return REGRAS_PADRAO.get(tipo, [])
```

---

### T4: Atualizar serviço de campanhas (1h)

Adaptar serviço para usar novos campos.

**Arquivo:** `app/services/campanhas/campanha_service.py` (modificar)

```python
"""
Serviço de campanhas - adaptado para novo modelo.
"""
from datetime import datetime
from app.services.supabase import supabase
from app.schemas.campanha import (
    CampanhaCreate,
    CampanhaUpdate,
    TipoCampanha,
    EscopoVagas,
    get_regras_padrao
)
from app.core.logging import get_logger
from app.core.exceptions import ValidationError, NotFoundError

logger = get_logger(__name__)


async def criar_campanha(dados: CampanhaCreate, criado_por: str) -> dict:
    """
    Cria nova campanha.

    Args:
        dados: Dados da campanha
        criado_por: ID de quem está criando

    Returns:
        Campanha criada
    """
    # Preencher regras padrão se não fornecidas
    regras = dados.regras or get_regras_padrao(dados.tipo)

    # Definir pode_ofertar baseado no tipo
    pode_ofertar = dados.pode_ofertar
    if dados.tipo == TipoCampanha.OFERTA:
        pode_ofertar = True  # Oferta sempre pode ofertar
    elif dados.tipo == TipoCampanha.DISCOVERY:
        pode_ofertar = False  # Discovery nunca pode ofertar

    campanha_data = {
        "nome": dados.nome,
        "tipo": dados.tipo.value,
        "objetivo": dados.objetivo,
        "regras": regras,
        "escopo_vagas": dados.escopo_vagas.model_dump() if dados.escopo_vagas else None,
        "pode_ofertar": pode_ofertar,
        "status": "rascunho",
        "criado_por": criado_por,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    resultado = supabase.table("campanhas").insert(campanha_data).execute()

    if resultado.data:
        logger.info(f"Campanha criada: {resultado.data[0]['id']} - {dados.nome}")
        return resultado.data[0]

    raise ValidationError("Erro ao criar campanha")


async def buscar_campanha(campanha_id: str) -> dict:
    """
    Busca campanha por ID.

    Args:
        campanha_id: ID da campanha

    Returns:
        Dados da campanha

    Raises:
        NotFoundError: Campanha não encontrada
    """
    resultado = supabase.table("campanhas").select("*").eq(
        "id", campanha_id
    ).single().execute()

    if not resultado.data:
        raise NotFoundError(f"Campanha {campanha_id} não encontrada")

    return resultado.data


async def atualizar_campanha(
    campanha_id: str,
    dados: CampanhaUpdate,
    atualizado_por: str
) -> dict:
    """
    Atualiza campanha existente.

    Args:
        campanha_id: ID da campanha
        dados: Dados a atualizar
        atualizado_por: ID de quem está atualizando

    Returns:
        Campanha atualizada
    """
    # Verificar se existe
    await buscar_campanha(campanha_id)

    update_data = {
        "updated_at": datetime.utcnow().isoformat()
    }

    if dados.nome is not None:
        update_data["nome"] = dados.nome
    if dados.objetivo is not None:
        update_data["objetivo"] = dados.objetivo
    if dados.regras is not None:
        update_data["regras"] = dados.regras
    if dados.escopo_vagas is not None:
        update_data["escopo_vagas"] = dados.escopo_vagas.model_dump()
    if dados.pode_ofertar is not None:
        update_data["pode_ofertar"] = dados.pode_ofertar

    resultado = supabase.table("campanhas").update(update_data).eq(
        "id", campanha_id
    ).execute()

    if resultado.data:
        logger.info(f"Campanha atualizada: {campanha_id}")
        return resultado.data[0]

    raise ValidationError("Erro ao atualizar campanha")


async def validar_disparo_campanha(campanha_id: str) -> dict:
    """
    Valida se campanha pode ser disparada.

    Para tipo=oferta, verifica se existem vagas no escopo.

    Args:
        campanha_id: ID da campanha

    Returns:
        {pode_disparar: bool, motivo: str | None}
    """
    campanha = await buscar_campanha(campanha_id)

    # Validações básicas
    if campanha["status"] not in ("rascunho", "agendada"):
        return {
            "pode_disparar": False,
            "motivo": f"Status inválido: {campanha['status']}"
        }

    # Para tipo=oferta, verificar se há vagas
    if campanha["tipo"] == TipoCampanha.OFERTA.value:
        escopo = campanha.get("escopo_vagas")

        if not escopo:
            return {
                "pode_disparar": False,
                "motivo": "Campanha de oferta sem escopo de vagas definido"
            }

        # Buscar vagas no escopo
        vagas = await _buscar_vagas_no_escopo(escopo)

        if not vagas:
            return {
                "pode_disparar": False,
                "motivo": "Não existem vagas no escopo definido"
            }

        return {
            "pode_disparar": True,
            "motivo": None,
            "vagas_disponiveis": len(vagas)
        }

    return {"pode_disparar": True, "motivo": None}


async def _buscar_vagas_no_escopo(escopo: dict) -> list[dict]:
    """
    Busca vagas que correspondem ao escopo.

    Args:
        escopo: Filtros do escopo

    Returns:
        Lista de vagas
    """
    query = supabase.table("vagas").select("id, data, hospital_id, valor").eq(
        "status", "aberta"
    )

    if escopo.get("especialidade_id"):
        query = query.eq("especialidade_id", escopo["especialidade_id"])

    if escopo.get("hospital_id"):
        query = query.eq("hospital_id", escopo["hospital_id"])

    if escopo.get("periodo_inicio"):
        query = query.gte("data", escopo["periodo_inicio"])

    if escopo.get("periodo_fim"):
        query = query.lte("data", escopo["periodo_fim"])

    if escopo.get("valor_minimo"):
        query = query.gte("valor", escopo["valor_minimo"])

    if escopo.get("valor_maximo"):
        query = query.lte("valor", escopo["valor_maximo"])

    resultado = query.execute()
    return resultado.data or []


async def get_contexto_campanha(campanha_id: str) -> dict:
    """
    Retorna contexto da campanha para injeção no prompt.

    Args:
        campanha_id: ID da campanha

    Returns:
        Contexto formatado para PromptBuilder
    """
    campanha = await buscar_campanha(campanha_id)

    return {
        "campaign_type": campanha["tipo"],
        "campaign_objective": campanha.get("objetivo", ""),
        "campaign_rules": campanha.get("regras", []),
        "can_offer": campanha.get("pode_ofertar", False),
        "offer_scope": campanha.get("escopo_vagas"),
    }
```

---

### T5: Migrar campanhas existentes (1h)

Script para migrar campanhas existentes para novo formato.

**Arquivo:** `app/scripts/migrar_campanhas.py`

```python
"""
Script para migrar campanhas existentes para novo formato.

Analisa campanhas legadas e preenche novos campos baseado no tipo.

Uso:
    python -m app.scripts.migrar_campanhas [--dry-run]
"""
import asyncio
import sys
from app.services.supabase import supabase
from app.schemas.campanha import TipoCampanha, get_regras_padrao
from app.core.logging import get_logger

logger = get_logger(__name__)

# Mapeamento de tipos antigos para novos
MAPEAMENTO_TIPOS = {
    "prospecção": TipoCampanha.DISCOVERY,
    "prospeccao": TipoCampanha.DISCOVERY,
    "discovery": TipoCampanha.DISCOVERY,
    "oferta": TipoCampanha.OFERTA,
    "vaga": TipoCampanha.OFERTA,
    "followup": TipoCampanha.FOLLOWUP,
    "follow-up": TipoCampanha.FOLLOWUP,
    "acompanhamento": TipoCampanha.FOLLOWUP,
    "feedback": TipoCampanha.FEEDBACK,
    "avaliação": TipoCampanha.FEEDBACK,
    "avaliacao": TipoCampanha.FEEDBACK,
    "reativação": TipoCampanha.REATIVACAO,
    "reativacao": TipoCampanha.REATIVACAO,
    "retomada": TipoCampanha.REATIVACAO,
}


def inferir_tipo(campanha: dict) -> TipoCampanha:
    """
    Infere o tipo da campanha baseado em campos existentes.

    Args:
        campanha: Dados da campanha

    Returns:
        Tipo inferido
    """
    # Primeiro tentar mapeamento direto
    tipo_atual = (campanha.get("tipo") or "").lower()
    if tipo_atual in MAPEAMENTO_TIPOS:
        return MAPEAMENTO_TIPOS[tipo_atual]

    # Tentar inferir pelo nome
    nome = (campanha.get("nome") or "").lower()

    if any(p in nome for p in ["prospecção", "discovery", "conhecer"]):
        return TipoCampanha.DISCOVERY

    if any(p in nome for p in ["oferta", "vaga", "plantão"]):
        return TipoCampanha.OFERTA

    if any(p in nome for p in ["follow", "acompanhamento"]):
        return TipoCampanha.FOLLOWUP

    if any(p in nome for p in ["feedback", "avaliação"]):
        return TipoCampanha.FEEDBACK

    if any(p in nome for p in ["reativ", "retomada"]):
        return TipoCampanha.REATIVACAO

    # Tentar inferir pelo corpo
    corpo = (campanha.get("_deprecated_corpo") or campanha.get("corpo") or "").lower()

    if any(p in corpo for p in ["conhecer", "especialidade", "região"]):
        return TipoCampanha.DISCOVERY

    if any(p in corpo for p in ["vaga", "plantão", "r$", "valor"]):
        return TipoCampanha.OFERTA

    # Default: Discovery (mais seguro)
    return TipoCampanha.DISCOVERY


def gerar_objetivo(campanha: dict, tipo: TipoCampanha) -> str:
    """
    Gera objetivo baseado no tipo e dados existentes.

    Args:
        campanha: Dados da campanha
        tipo: Tipo da campanha

    Returns:
        Objetivo em linguagem natural
    """
    nome = campanha.get("nome", "")

    objetivos_padrao = {
        TipoCampanha.DISCOVERY: f"Conhecer novos médicos e entender suas preferências",
        TipoCampanha.OFERTA: f"Ofertar vagas disponíveis conforme escopo definido",
        TipoCampanha.FOLLOWUP: f"Manter relacionamento ativo com médicos",
        TipoCampanha.FEEDBACK: f"Coletar feedback sobre plantões realizados",
        TipoCampanha.REATIVACAO: f"Retomar contato com médicos inativos",
    }

    return objetivos_padrao.get(tipo, "")


async def migrar_campanhas(dry_run: bool = True) -> dict:
    """
    Migra todas as campanhas para novo formato.

    Args:
        dry_run: Se True, apenas simula sem alterar banco

    Returns:
        Estatísticas da migração
    """
    stats = {"total": 0, "migradas": 0, "erros": 0, "sem_mudanca": 0}

    # Buscar campanhas sem os novos campos preenchidos
    campanhas = supabase.table("campanhas").select("*").execute()

    for campanha in campanhas.data or []:
        stats["total"] += 1

        try:
            # Verificar se já foi migrada
            if campanha.get("objetivo"):
                stats["sem_mudanca"] += 1
                continue

            # Inferir tipo
            tipo = inferir_tipo(campanha)

            # Gerar objetivo
            objetivo = gerar_objetivo(campanha, tipo)

            # Regras padrão
            regras = get_regras_padrao(tipo)

            # Pode ofertar
            pode_ofertar = tipo == TipoCampanha.OFERTA

            update_data = {
                "tipo": tipo.value,
                "objetivo": objetivo,
                "regras": regras,
                "pode_ofertar": pode_ofertar
            }

            logger.info(
                f"Campanha {campanha['id']} ({campanha.get('nome')}): "
                f"tipo={tipo.value}, pode_ofertar={pode_ofertar}"
            )

            if not dry_run:
                supabase.table("campanhas").update(update_data).eq(
                    "id", campanha["id"]
                ).execute()

            stats["migradas"] += 1

        except Exception as e:
            logger.error(f"Erro ao migrar campanha {campanha['id']}: {e}")
            stats["erros"] += 1

    return stats


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv

    if dry_run:
        print("Modo dry-run: nenhuma alteração será feita")
    else:
        print("ATENÇÃO: Alterações serão feitas no banco!")
        input("Pressione Enter para continuar ou Ctrl+C para cancelar...")

    resultado = asyncio.run(migrar_campanhas(dry_run))
    print(f"\nResultado: {resultado}")
```

---

### T6: Criar testes (30min)

**Arquivo:** `tests/campanhas/test_campanha_service.py`

```python
"""
Testes para serviço de campanhas reestruturado.
"""
import pytest
from app.schemas.campanha import (
    CampanhaCreate,
    CampanhaUpdate,
    TipoCampanha,
    EscopoVagas,
    get_regras_padrao
)
from app.services.campanhas.campanha_service import (
    criar_campanha,
    buscar_campanha,
    validar_disparo_campanha,
    get_contexto_campanha
)


class TestCriarCampanha:
    """Testes para criação de campanha."""

    @pytest.mark.asyncio
    async def test_criar_discovery(self, supabase_mock):
        """Cria campanha de discovery."""
        dados = CampanhaCreate(
            nome="Discovery Janeiro",
            tipo=TipoCampanha.DISCOVERY,
            objetivo="Conhecer médicos cardiologistas"
        )

        resultado = await criar_campanha(dados, criado_por="gestor-123")

        assert resultado["tipo"] == "discovery"
        assert resultado["pode_ofertar"] is False  # Discovery nunca pode ofertar
        assert len(resultado["regras"]) > 0

    @pytest.mark.asyncio
    async def test_criar_oferta_com_escopo(self, supabase_mock):
        """Cria campanha de oferta com escopo."""
        escopo = EscopoVagas(
            especialidade_id="esp-cardio",
            periodo_inicio="2026-03-01",
            periodo_fim="2026-03-31"
        )

        dados = CampanhaCreate(
            nome="Oferta Março Cardio",
            tipo=TipoCampanha.OFERTA,
            objetivo="Ofertar vagas de cardiologia para março",
            escopo_vagas=escopo
        )

        resultado = await criar_campanha(dados, criado_por="gestor-123")

        assert resultado["tipo"] == "oferta"
        assert resultado["pode_ofertar"] is True
        assert resultado["escopo_vagas"] is not None

    @pytest.mark.asyncio
    async def test_oferta_sem_escopo_falha(self, supabase_mock):
        """Campanha de oferta sem escopo deve falhar."""
        with pytest.raises(ValueError):
            CampanhaCreate(
                nome="Oferta sem escopo",
                tipo=TipoCampanha.OFERTA
                # Sem escopo_vagas
            )

    @pytest.mark.asyncio
    async def test_discovery_com_pode_ofertar_falha(self, supabase_mock):
        """Discovery não pode ter pode_ofertar=True."""
        with pytest.raises(ValueError):
            CampanhaCreate(
                nome="Discovery errado",
                tipo=TipoCampanha.DISCOVERY,
                pode_ofertar=True  # Não permitido
            )


class TestValidarDisparo:
    """Testes para validação de disparo."""

    @pytest.mark.asyncio
    async def test_oferta_com_vagas_pode_disparar(
        self, supabase_mock, campanha_oferta_com_vagas
    ):
        """Oferta com vagas no escopo pode disparar."""
        resultado = await validar_disparo_campanha(campanha_oferta_com_vagas["id"])

        assert resultado["pode_disparar"] is True
        assert resultado.get("vagas_disponiveis", 0) > 0

    @pytest.mark.asyncio
    async def test_oferta_sem_vagas_nao_pode_disparar(
        self, supabase_mock, campanha_oferta_sem_vagas
    ):
        """Oferta sem vagas no escopo não pode disparar."""
        resultado = await validar_disparo_campanha(campanha_oferta_sem_vagas["id"])

        assert resultado["pode_disparar"] is False
        assert "sem vagas" in resultado["motivo"].lower() or "não existem" in resultado["motivo"].lower()

    @pytest.mark.asyncio
    async def test_discovery_sempre_pode_disparar(
        self, supabase_mock, campanha_discovery
    ):
        """Discovery sempre pode disparar (não depende de vagas)."""
        resultado = await validar_disparo_campanha(campanha_discovery["id"])

        assert resultado["pode_disparar"] is True


class TestContextoCampanha:
    """Testes para contexto de campanha."""

    @pytest.mark.asyncio
    async def test_contexto_discovery(self, supabase_mock, campanha_discovery):
        """Contexto de discovery não permite oferta."""
        contexto = await get_contexto_campanha(campanha_discovery["id"])

        assert contexto["campaign_type"] == "discovery"
        assert contexto["can_offer"] is False

    @pytest.mark.asyncio
    async def test_contexto_oferta(self, supabase_mock, campanha_oferta_com_vagas):
        """Contexto de oferta permite oferta."""
        contexto = await get_contexto_campanha(campanha_oferta_com_vagas["id"])

        assert contexto["campaign_type"] == "oferta"
        assert contexto["can_offer"] is True
        assert contexto["offer_scope"] is not None


class TestRegrasPadrao:
    """Testes para regras padrão."""

    def test_regras_discovery(self):
        """Discovery tem regras de não ofertar."""
        regras = get_regras_padrao(TipoCampanha.DISCOVERY)

        assert any("nunca" in r.lower() and "mencionar" in r.lower() for r in regras)

    def test_regras_oferta(self):
        """Oferta tem regras de consultar sistema."""
        regras = get_regras_padrao(TipoCampanha.OFERTA)

        assert any("consultar" in r.lower() or "sistema" in r.lower() for r in regras)
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Novos campos adicionados (objetivo, regras, escopo_vagas, pode_ofertar)
- [ ] Campos legados renomeados com prefixo `_deprecated_`
- [ ] View de compatibilidade criada
- [ ] Constraint de tipos atualizada
- [ ] Schema Pydantic com validações
- [ ] Serviço usando novos campos

### Migração
- [ ] Script de migração criado
- [ ] Dry-run testado
- [ ] Campanhas existentes migradas

### Testes
- [ ] Testes de criação com novos campos
- [ ] Testes de validação de disparo
- [ ] Testes de contexto para prompt
- [ ] Testes de regras padrão

### Verificação Manual

1. **Verificar novos campos:**
   ```sql
   SELECT id, nome, tipo, objetivo, regras, pode_ofertar
   FROM campanhas
   LIMIT 5;
   ```

2. **Criar campanha discovery:**
   ```python
   dados = CampanhaCreate(
       nome="Test Discovery",
       tipo=TipoCampanha.DISCOVERY
   )
   resultado = await criar_campanha(dados, "gestor-123")
   assert resultado["pode_ofertar"] is False
   ```

3. **Criar campanha oferta:**
   ```python
   dados = CampanhaCreate(
       nome="Test Oferta",
       tipo=TipoCampanha.OFERTA,
       escopo_vagas=EscopoVagas(especialidade_id="cardio")
   )
   resultado = await criar_campanha(dados, "gestor-123")
   assert resultado["pode_ofertar"] is True
   ```

4. **Validar disparo sem vagas:**
   ```python
   resultado = await validar_disparo_campanha(campanha_oferta_sem_vagas_id)
   assert resultado["pode_disparar"] is False
   ```

---

## Notas para Dev

1. **Não deletar campos imediatamente:** Renomear com prefixo `_deprecated_` para rollback fácil
2. **View de compatibilidade:** `campanhas_compat` mantém queries legadas funcionando
3. **Regras padrão:** Sempre preencher se não fornecidas
4. **Discovery:** NUNCA pode ter `pode_ofertar=True`
5. **Oferta:** SEMPRE precisa de `escopo_vagas`
6. **Sprint 34:** Remover campos deprecated completamente

---

## Rollback

Se necessário reverter:

```sql
-- Reverter nomes de campos
ALTER TABLE campanhas
RENAME COLUMN _deprecated_corpo TO corpo;

ALTER TABLE campanhas
RENAME COLUMN _deprecated_nome_template TO nome_template;

-- Remover novos campos (se necessário)
ALTER TABLE campanhas
DROP COLUMN objetivo,
DROP COLUMN regras,
DROP COLUMN escopo_vagas,
DROP COLUMN pode_ofertar;

-- Dropar view
DROP VIEW IF EXISTS campanhas_compat;
```

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Campanhas migradas | 100% |
| Campanhas discovery sem pode_ofertar | 100% |
| Campanhas oferta com escopo | 100% |
