# Epic 03: Refatorar Repository

## Objetivo

Criar `app/services/campanhas/repository.py` com acesso correto ao banco, seguindo o schema atual.

## Contexto

O codigo atual em `app/services/campanha.py` acessa o banco diretamente com nomes de colunas errados. Este epico cria uma camada de repository com os nomes corretos.

---

## Story 3.1: Criar Estrutura do Modulo

### Objetivo

Criar estrutura de pastas para o novo modulo de campanhas.

### Tarefas

1. **Criar diretorio** `app/services/campanhas/`

2. **Criar arquivo** `app/services/campanhas/__init__.py`:

```python
"""
Modulo de campanhas.

Estrutura:
- repository: Acesso ao banco de dados
- executor: Execucao de campanhas
- types: Tipos e enums
"""
from app.services.campanhas.repository import CampanhaRepository, campanha_repository
from app.services.campanhas.types import (
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
    CampanhaData,
)

__all__ = [
    "CampanhaRepository",
    "campanha_repository",
    "TipoCampanha",
    "StatusCampanha",
    "AudienceFilters",
    "CampanhaData",
]
```

3. **Criar arquivo** `app/services/campanhas/types.py`:

```python
"""
Tipos e enums para campanhas.
"""
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime


class TipoCampanha(str, Enum):
    """Tipos de campanha disponiveis."""
    DISCOVERY = "discovery"
    OFERTA = "oferta"
    REATIVACAO = "reativacao"
    FOLLOWUP = "followup"


class StatusCampanha(str, Enum):
    """Status possiveis de uma campanha."""
    RASCUNHO = "rascunho"
    AGENDADA = "agendada"
    ATIVA = "ativa"
    PAUSADA = "pausada"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


@dataclass
class AudienceFilters:
    """Filtros de audiencia da campanha."""
    regioes: List[str] = field(default_factory=list)
    especialidades: List[str] = field(default_factory=list)
    quantidade_alvo: int = 50
    pressure_score_max: int = 70
    excluir_opt_out: bool = True

    def to_dict(self) -> dict:
        """Converte para dicionario."""
        return {
            "regioes": self.regioes,
            "especialidades": self.especialidades,
            "quantidade_alvo": self.quantidade_alvo,
            "pressure_score_max": self.pressure_score_max,
            "excluir_opt_out": self.excluir_opt_out,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AudienceFilters":
        """Cria a partir de dicionario."""
        return cls(
            regioes=data.get("regioes", []),
            especialidades=data.get("especialidades", []),
            quantidade_alvo=data.get("quantidade_alvo", 50),
            pressure_score_max=data.get("pressure_score_max", 70),
            excluir_opt_out=data.get("excluir_opt_out", True),
        )


@dataclass
class CampanhaData:
    """Dados de uma campanha."""
    id: int
    nome_template: str
    tipo_campanha: TipoCampanha
    corpo: Optional[str] = None
    tom: Optional[str] = None
    status: StatusCampanha = StatusCampanha.RASCUNHO
    agendar_para: Optional[datetime] = None
    audience_filters: Optional[AudienceFilters] = None
    pode_ofertar: bool = False
    total_destinatarios: int = 0
    enviados: int = 0
    entregues: int = 0
    respondidos: int = 0

    @classmethod
    def from_db_row(cls, row: dict) -> "CampanhaData":
        """Cria a partir de linha do banco."""
        return cls(
            id=row["id"],
            nome_template=row.get("nome_template", ""),
            tipo_campanha=TipoCampanha(row.get("tipo_campanha", "discovery")),
            corpo=row.get("corpo"),
            tom=row.get("tom"),
            status=StatusCampanha(row.get("status", "rascunho")),
            agendar_para=row.get("agendar_para"),
            audience_filters=AudienceFilters.from_dict(row.get("audience_filters") or {}),
            pode_ofertar=row.get("pode_ofertar", False),
            total_destinatarios=row.get("total_destinatarios", 0),
            enviados=row.get("enviados", 0),
            entregues=row.get("entregues", 0),
            respondidos=row.get("respondidos", 0),
        )
```

### DoD

- [ ] Diretorio `app/services/campanhas/` criado
- [ ] Arquivo `__init__.py` com exports
- [ ] Arquivo `types.py` com enums e dataclasses
- [ ] Tipos tipados corretamente

---

## Story 3.2: Criar Repository

### Objetivo

Criar classe repository com metodos de acesso ao banco.

### Tarefas

1. **Criar arquivo** `app/services/campanhas/repository.py`:

```python
"""
Repository para campanhas.

Acesso ao banco de dados com nomes de colunas corretos.
"""
import logging
from typing import Optional, List
from datetime import datetime

from app.services.supabase import supabase
from app.services.campanhas.types import (
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
    AudienceFilters,
)

logger = logging.getLogger(__name__)


class CampanhaRepository:
    """Repository para operacoes de campanhas no banco."""

    TABLE = "campanhas"

    async def buscar_por_id(self, campanha_id: int) -> Optional[CampanhaData]:
        """
        Busca campanha por ID.

        Args:
            campanha_id: ID da campanha

        Returns:
            CampanhaData ou None se nao encontrada
        """
        try:
            response = (
                supabase.table(self.TABLE)
                .select("*")
                .eq("id", campanha_id)
                .single()
                .execute()
            )

            if not response.data:
                return None

            return CampanhaData.from_db_row(response.data)

        except Exception as e:
            logger.error(f"Erro ao buscar campanha {campanha_id}: {e}")
            return None

    async def listar_agendadas(self, agora: datetime = None) -> List[CampanhaData]:
        """
        Lista campanhas agendadas para execucao.

        Args:
            agora: Datetime atual (default: utcnow)

        Returns:
            Lista de campanhas agendadas
        """
        agora = agora or datetime.utcnow()

        try:
            response = (
                supabase.table(self.TABLE)
                .select("*")
                .eq("status", StatusCampanha.AGENDADA.value)
                .lte("agendar_para", agora.isoformat())
                .execute()
            )

            return [CampanhaData.from_db_row(row) for row in (response.data or [])]

        except Exception as e:
            logger.error(f"Erro ao listar campanhas agendadas: {e}")
            return []

    async def listar_ativas(self) -> List[CampanhaData]:
        """
        Lista campanhas ativas.

        Returns:
            Lista de campanhas ativas
        """
        try:
            response = (
                supabase.table(self.TABLE)
                .select("*")
                .eq("status", StatusCampanha.ATIVA.value)
                .execute()
            )

            return [CampanhaData.from_db_row(row) for row in (response.data or [])]

        except Exception as e:
            logger.error(f"Erro ao listar campanhas ativas: {e}")
            return []

    async def criar(
        self,
        nome_template: str,
        tipo_campanha: TipoCampanha,
        corpo: Optional[str] = None,
        tom: Optional[str] = None,
        agendar_para: Optional[datetime] = None,
        audience_filters: Optional[AudienceFilters] = None,
        pode_ofertar: bool = False,
        created_by: str = "sistema",
    ) -> Optional[CampanhaData]:
        """
        Cria nova campanha.

        Args:
            nome_template: Nome da campanha
            tipo_campanha: Tipo (discovery, oferta, etc)
            corpo: Template da mensagem
            tom: Tom a usar
            agendar_para: Quando iniciar
            audience_filters: Filtros de audiencia
            pode_ofertar: Se pode ofertar vagas
            created_by: Quem criou

        Returns:
            CampanhaData criada ou None se erro
        """
        status = StatusCampanha.AGENDADA if agendar_para else StatusCampanha.RASCUNHO

        data = {
            "nome_template": nome_template,
            "tipo_campanha": tipo_campanha.value,
            "corpo": corpo,
            "tom": tom,
            "status": status.value,
            "agendar_para": agendar_para.isoformat() if agendar_para else None,
            "audience_filters": audience_filters.to_dict() if audience_filters else {},
            "pode_ofertar": pode_ofertar,
            "created_by": created_by,
        }

        try:
            response = supabase.table(self.TABLE).insert(data).execute()

            if not response.data:
                return None

            return CampanhaData.from_db_row(response.data[0])

        except Exception as e:
            logger.error(f"Erro ao criar campanha: {e}")
            return None

    async def atualizar_status(
        self,
        campanha_id: int,
        novo_status: StatusCampanha,
    ) -> bool:
        """
        Atualiza status da campanha.

        Args:
            campanha_id: ID da campanha
            novo_status: Novo status

        Returns:
            True se atualizado com sucesso
        """
        data = {
            "status": novo_status.value,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Adicionar timestamps especificos
        if novo_status == StatusCampanha.ATIVA:
            data["iniciada_em"] = datetime.utcnow().isoformat()
            data["started_at"] = data["iniciada_em"]
        elif novo_status == StatusCampanha.CONCLUIDA:
            data["concluida_em"] = datetime.utcnow().isoformat()
            data["completed_at"] = data["concluida_em"]

        try:
            supabase.table(self.TABLE).update(data).eq("id", campanha_id).execute()
            logger.info(f"Campanha {campanha_id} atualizada para status {novo_status.value}")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar status da campanha {campanha_id}: {e}")
            return False

    async def incrementar_enviados(self, campanha_id: int, quantidade: int = 1) -> bool:
        """
        Incrementa contador de enviados.

        Args:
            campanha_id: ID da campanha
            quantidade: Quantidade a incrementar

        Returns:
            True se incrementado com sucesso
        """
        try:
            # Buscar valor atual
            response = (
                supabase.table(self.TABLE)
                .select("enviados")
                .eq("id", campanha_id)
                .single()
                .execute()
            )

            if not response.data:
                return False

            atual = response.data.get("enviados", 0) or 0

            # Atualizar
            supabase.table(self.TABLE).update({
                "enviados": atual + quantidade,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", campanha_id).execute()

            return True

        except Exception as e:
            logger.error(f"Erro ao incrementar enviados da campanha {campanha_id}: {e}")
            return False

    async def atualizar_total_destinatarios(
        self,
        campanha_id: int,
        total: int,
    ) -> bool:
        """
        Atualiza total de destinatarios.

        Args:
            campanha_id: ID da campanha
            total: Total de destinatarios

        Returns:
            True se atualizado com sucesso
        """
        try:
            supabase.table(self.TABLE).update({
                "total_destinatarios": total,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", campanha_id).execute()

            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar total_destinatarios da campanha {campanha_id}: {e}")
            return False


# Instancia singleton
campanha_repository = CampanhaRepository()
```

### DoD

- [ ] Arquivo `repository.py` criado
- [ ] Metodo `buscar_por_id` implementado
- [ ] Metodo `listar_agendadas` implementado
- [ ] Metodo `listar_ativas` implementado
- [ ] Metodo `criar` implementado
- [ ] Metodo `atualizar_status` implementado
- [ ] Metodo `incrementar_enviados` implementado
- [ ] Metodo `atualizar_total_destinatarios` implementado
- [ ] Instancia singleton exportada

---

## Story 3.3: Criar Testes do Repository

### Objetivo

Criar testes unitarios para o repository.

### Tarefas

1. **Criar arquivo** `tests/services/campanhas/test_repository.py`:

```python
"""Testes do repository de campanhas."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.services.campanhas.repository import CampanhaRepository
from app.services.campanhas.types import (
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
)


@pytest.fixture
def repository():
    """Instancia do repository."""
    return CampanhaRepository()


@pytest.fixture
def mock_campanha_row():
    """Linha do banco mockada."""
    return {
        "id": 16,
        "nome_template": "Piloto Discovery",
        "tipo_campanha": "discovery",
        "corpo": "[DISCOVERY] Usar aberturas dinamicas",
        "tom": "amigavel",
        "status": "agendada",
        "agendar_para": "2026-01-21T12:00:00Z",
        "audience_filters": {
            "regioes": [],
            "especialidades": [],
            "quantidade_alvo": 50,
        },
        "pode_ofertar": False,
        "total_destinatarios": 50,
        "enviados": 0,
        "entregues": 0,
        "respondidos": 0,
    }


@pytest.mark.asyncio
async def test_buscar_por_id_encontrado(repository, mock_campanha_row):
    """Testa busca por ID quando existe."""
    with patch("app.services.campanhas.repository.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_row

        result = await repository.buscar_por_id(16)

        assert result is not None
        assert result.id == 16
        assert result.nome_template == "Piloto Discovery"
        assert result.tipo_campanha == TipoCampanha.DISCOVERY
        assert result.status == StatusCampanha.AGENDADA


@pytest.mark.asyncio
async def test_buscar_por_id_nao_encontrado(repository):
    """Testa busca por ID quando nao existe."""
    with patch("app.services.campanhas.repository.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        result = await repository.buscar_por_id(999)

        assert result is None


@pytest.mark.asyncio
async def test_listar_agendadas(repository, mock_campanha_row):
    """Testa listagem de campanhas agendadas."""
    with patch("app.services.campanhas.repository.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = [mock_campanha_row]

        result = await repository.listar_agendadas()

        assert len(result) == 1
        assert result[0].id == 16


@pytest.mark.asyncio
async def test_criar_campanha(repository):
    """Testa criacao de campanha."""
    with patch("app.services.campanhas.repository.supabase") as mock_supabase:
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": 17,
            "nome_template": "Nova Campanha",
            "tipo_campanha": "oferta",
            "status": "rascunho",
            "audience_filters": {},
        }]

        result = await repository.criar(
            nome_template="Nova Campanha",
            tipo_campanha=TipoCampanha.OFERTA,
        )

        assert result is not None
        assert result.id == 17
        assert result.tipo_campanha == TipoCampanha.OFERTA


@pytest.mark.asyncio
async def test_atualizar_status(repository):
    """Testa atualizacao de status."""
    with patch("app.services.campanhas.repository.supabase") as mock_supabase:
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = await repository.atualizar_status(16, StatusCampanha.ATIVA)

        assert result is True
        # Verificar que update foi chamado com status correto
        call_args = mock_supabase.table.return_value.update.call_args
        assert call_args[0][0]["status"] == "ativa"
        assert "iniciada_em" in call_args[0][0]


@pytest.mark.asyncio
async def test_incrementar_enviados(repository):
    """Testa incremento de enviados."""
    with patch("app.services.campanhas.repository.supabase") as mock_supabase:
        # Mock busca atual
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"enviados": 10}
        # Mock update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = await repository.incrementar_enviados(16, 5)

        assert result is True
        # Verificar que update foi chamado com valor correto (10 + 5 = 15)
        update_calls = [c for c in mock_supabase.table.return_value.update.call_args_list]
        assert len(update_calls) > 0
```

2. **Criar arquivo** `tests/services/campanhas/__init__.py` (vazio)

3. **Rodar testes**:

```bash
uv run pytest tests/services/campanhas/test_repository.py -v
```

### DoD

- [ ] Arquivo de testes criado
- [ ] Teste `test_buscar_por_id_encontrado` passa
- [ ] Teste `test_buscar_por_id_nao_encontrado` passa
- [ ] Teste `test_listar_agendadas` passa
- [ ] Teste `test_criar_campanha` passa
- [ ] Teste `test_atualizar_status` passa
- [ ] Teste `test_incrementar_enviados` passa

---

## Checklist do Epico

- [ ] **S35.E03.1** - Estrutura do modulo criada
- [ ] **S35.E03.2** - Repository implementado
- [ ] **S35.E03.3** - Testes passando

### Arquivos Criados

- `app/services/campanhas/__init__.py`
- `app/services/campanhas/types.py`
- `app/services/campanhas/repository.py`
- `tests/services/campanhas/__init__.py`
- `tests/services/campanhas/test_repository.py`

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 3.1 Estrutura do modulo | 30min |
| 3.2 Repository | 1h30min |
| 3.3 Testes | 1h |
| **Total** | **3h** |
